from celery import shared_task
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI
from qdrant_client.http.models import PointStruct, VectorParams, Distance
from redbot.settings import QDRANT_CLIENT, OPENAI_API_KEY  # Use global for dev; later per-bot
from .models import KnowledgeSource, Chunk
import uuid

@shared_task
def ingest_knowledge(source_id):
    source = KnowledgeSource.objects.get(id=source_id)
    try:
        # Parse content (simplified: assume text for now; add file/URL parsers later)
        text = source.content

        # Chunk
        splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
        chunks = splitter.split_text(text)

        # Embed (use OpenAI)
        client = OpenAI(api_key=OPENAI_API_KEY)  # Later: use bot.ai_api_key
        collection_name = f"bot_{source.bot.id}"
        
        # Create Qdrant collection if not exists
        if not QDRANT_CLIENT.has_collection(collection_name):
            QDRANT_CLIENT.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE)  # ada-002 dim
            )

        # Embed and upsert
        points = []
        for chunk_text in chunks:
            embedding = client.embeddings.create(input=chunk_text, model="text-embedding-ada-002").data[0].embedding
            point_id = str(uuid.uuid4())
            points.append(PointStruct(id=point_id, vector=embedding, payload={"text": chunk_text, "source_id": source.id}))
            
            # Save chunk
            Chunk.objects.create(source=source, text=chunk_text, vector_id=point_id)

        QDRANT_CLIENT.upsert(collection_name=collection_name, points=points)
        
        source.status = 'INGESTED'
    except Exception as e:
        source.status = 'FAILED'
        print(f"Ingestion failed: {e}")
    source.save()