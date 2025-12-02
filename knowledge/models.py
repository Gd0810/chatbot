import uuid
import requests
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from sentence_transformers import SentenceTransformer
from bots.models import Bot

# ✅ Load embedding model globally (for performance)
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')


# ---------------------------------
# KNOWLEDGE SOURCE MODEL
# ---------------------------------
class KnowledgeSource(models.Model):
    SOURCE_TYPES = (
        ('TEXT', 'Text'),
        ('JSON', 'JSON'),
    )

    bot = models.ForeignKey(Bot, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, null=True, blank=True)
    source_type = models.CharField(max_length=10, choices=SOURCE_TYPES)
    content = models.TextField(help_text="Raw text or JSON content.")
    status = models.CharField(max_length=20, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # ✅ track updates

    def __str__(self):
        return self.title or f"Source {self.pk}"

    def save(self, *args, **kwargs):
        """Auto create or refresh chunks on save."""
        creating = self.pk is None
        super().save(*args, **kwargs)

        # ✅ If updating, delete old chunks first
        if not creating:
    # Delete chunks individually so their `delete()` runs (which removes vectors from Qdrant)
            for chunk in list(self.chunks.all()):
                chunk.delete()


        # ✅ Always recreate chunks with embeddings
        self.create_chunks()

    def create_chunks(self, chunk_size=500):
        """Split content into chunks, embed, and create Chunk records."""
        text = (self.content or "").strip()
        if not text:
            return

        words = text.split()
        chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]

        for chunk_text in chunks:
            embedding = embedding_model.encode(chunk_text).tolist()
            Chunk.objects.create(
                knowledge_source=self,
                text=chunk_text,
                embedding=embedding,
                qdrant_url=getattr(settings, "QDRANT_URL", None),
                qdrant_api_key=getattr(settings, "QDRANT_API_KEY", None),
            )

    def delete(self, *args, **kwargs):
        """Delete all chunks and vectors when source is deleted."""
        for chunk in self.chunks.all():
            chunk.delete()  # triggers Qdrant vector deletion
        super().delete(*args, **kwargs)


# ---------------------------------
# CHUNK MODEL
# ---------------------------------
class Chunk(models.Model):
    knowledge_source = models.ForeignKey(KnowledgeSource, on_delete=models.CASCADE, related_name="chunks")

    text = models.TextField()
    embedding = models.JSONField(null=True, blank=True)

    qdrant_url = models.URLField(blank=True, null=True)
    qdrant_api_key = models.CharField(max_length=255, blank=True, null=True)
    collection_name = models.CharField(max_length=255, blank=True, null=True)

    vector_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chunk of {self.knowledge_source.title or 'Untitled'}"

    # --------------------------
    # OVERRIDDEN SAVE
    # --------------------------
    def save(self, *args, **kwargs):
        """On save — re-embed if text changed, push to Qdrant."""
        if self.text and not self.embedding:
            self.embedding = embedding_model.encode(self.text).tolist()

        super().save(*args, **kwargs)

        if self.qdrant_url and self.qdrant_api_key:
            self.push_to_qdrant()

    # --------------------------
    # QDRANT OPERATIONS
    # --------------------------
    def push_to_qdrant(self):
        """Create or update this vector in Qdrant."""
        if not self.embedding:
            return

        try:
            collection_name = self.collection_name or slugify(self.knowledge_source.title or f"bot-{self.knowledge_source.bot.id}")
            self.collection_name = collection_name

            headers = {
                "Content-Type": "application/json",
                "api-key": self.qdrant_api_key,
            }

            # ✅ Ensure collection exists
            create_url = f"{self.qdrant_url}/collections/{collection_name}"
            requests.put(create_url, headers=headers, json={
                "vectors": {"size": len(self.embedding), "distance": "Cosine"}
            })

            # ✅ Create or replace vector
            self.vector_id = self.vector_id or str(uuid.uuid4())
            points_url = f"{self.qdrant_url}/collections/{collection_name}/points"
            payload = {
                "points": [
                    {
                        "id": self.vector_id,
                        "vector": self.embedding,
                        "payload": {
                            "text": self.text,
                            "knowledge_source": self.knowledge_source.title,
                            "source_id": self.knowledge_source.id,
                            "chunk_id": self.id,
                        },
                    }
                ]
            }

            response = requests.put(points_url, headers=headers, json=payload)
            if response.status_code not in (200, 201):
                print("⚠️ Qdrant upload failed:", response.text)
            else:
                super().save(update_fields=["vector_id", "collection_name"])

        except Exception as e:
            print("❌ Error pushing to Qdrant:", str(e))

    def delete(self, *args, **kwargs):
        """Remove this chunk and its Qdrant vector (if present)."""
        if self.qdrant_url and self.qdrant_api_key and self.vector_id and self.collection_name:
            try:
                delete_url = f"{self.qdrant_url}/collections/{self.collection_name}/points/delete"
                headers = {"api-key": self.qdrant_api_key, "Content-Type": "application/json"}
                payload = {"points": [self.vector_id]}
                resp = requests.post(delete_url, headers=headers, json=payload, timeout=15)
                if resp.status_code not in (200, 204, 202):
                    print("⚠️ Qdrant vector deletion returned:", resp.status_code, resp.text)
            except Exception as e:
                print("⚠️ Qdrant vector deletion failed:", e)


        # finally delete local DB row
        super().delete(*args, **kwargs)


# ---------------------------------
# QA PAIR MODEL (Hierarchical)
# ---------------------------------
class QAPair(models.Model):
    bot = models.ForeignKey(Bot, on_delete=models.CASCADE, related_name='qa_pairs')
    question = models.CharField(max_length=255, help_text="The main question or category.")
    answer = models.TextField(blank=True, null=True, help_text="The answer (if leaf node) or description.")
    
    # Hierarchy: parent=None means it's a root-level question
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    
    order = models.PositiveIntegerField(default=0, help_text="Ordering index")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = "Q&A Pair"
        verbose_name_plural = "Q&A Pairs"

    def __str__(self):
        return f"{'--' * self.depth} {self.question}"

    @property
    def depth(self):
        """Calculate depth for display purposes (0 = root)."""
        d = 0
        p = self.parent
        while p:
            d += 1
            p = p.parent
        return d

