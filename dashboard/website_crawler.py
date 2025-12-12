# dashboard/website_crawler.py
"""
Website crawler service - extracts body content sectioned by headings.
Converted from Streamlit script for Django backend use.
"""
from urllib.parse import urljoin, urlparse
import time
import re
import requests
from bs4 import BeautifulSoup, Tag
import urllib.robotparser as robotparser

HEADERS = {"User-Agent": "RedbotCrawler/1.0"}

def fetch_url(url: str, timeout: int = 8):
    """Fetch URL content with timeout."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception:
        return None

def allowed_by_robots(base_url: str):
    """Check robots.txt for crawling permission."""
    try:
        parsed = urlparse(base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = robotparser.RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp
    except Exception:
        return None

def _normalize_domain(netloc: str) -> str:
    """Normalize domain by stripping 'www.' and port."""
    if not netloc:
        return ""
    # Strip port if present
    netloc = netloc.split(':')[0]
    # Strip www prefix
    if netloc.lower().startswith('www.'):
        netloc = netloc[4:]
    return netloc.lower()

def is_same_domain(base_netloc: str, link: str) -> bool:
    """Check if link is from same domain (ignoring www)."""
    try:
        p = urlparse(link)
        if not p.netloc:
            # Relative link
            return True
            
        base_norm = _normalize_domain(base_netloc)
        link_norm = _normalize_domain(p.netloc)
        
        return base_norm == link_norm
    except Exception:
        return False

def extract_links(html: str, base_url: str):
    """Extract all links from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for a in soup.find_all("a", href=True):
        href = a.get("href").split("#")[0].strip()
        if not href:
            continue
        if href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        links.add(urljoin(base_url, href))
    return links

def _clean_tag(tag: Tag):
    """Remove boilerplate and junk tags from the tree."""
    # Tags to remove completely (including content)
    junk_tags = [
        "script", "style", "noscript", "iframe", "svg", "canvas",
        "button", "input", "select", "textarea", 
        "nav", "footer", "header", "aside", "form",
        "menu", "dialog", "map"
    ]
    for bad in tag.find_all(junk_tags):
        bad.decompose()
    
    # Remove elements by class/id heuristics (simple spam filter)
    junk_classes = re.compile(r"(sidebar|menu|footer|header|nav|popup|cookie|ad-|advert)", re.I)
    for bad in tag.find_all(attrs={"class": junk_classes}):
        bad.decompose()
    for bad in tag.find_all(attrs={"id": junk_classes}):
        bad.decompose()

    return tag

def _elem_to_text(elem: Tag) -> str:
    """Extract clean text from a block element, handling lists nicely."""
    name = elem.name.lower()
    if name in ("ul", "ol"):
        items = []
        for li in elem.find_all("li"):
            t = li.get_text(separator=" ", strip=True)
            t = re.sub(r'\s+', ' ', t).strip()
            if t:
                items.append("- " + t)
        return "\n".join(items)
    
    # For content that might contain line breaks (pre), preserve them?
    # For now, just space separator is consistent with previous logic.
    text = elem.get_text(separator=" ", strip=True)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_body_sections(html: str):
    """
    Extract sections from HTML body based on headings using linearization.
    Returns: [{"heading": ..., "content": ...}, ...]
    """
    soup = BeautifulSoup(html, "html.parser")
    body = soup.body or soup
    _clean_tag(body)
    
    sections = []
    current_heading = "Intro"
    current_content = []
    
    # Strategy: Linearize the document by finding all meaningful block elements
    # We Iterate over all descendants and pick top-most valid blocks.
    
    interesting_tags = ['h1', 'h2', 'h3', 'h4', 'p', 'ul', 'ol', 'pre', 'blockquote', 'table']
    
    # We iterate distinct top-level blocks.
    
    for child in body.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'ul', 'ol', 'pre', 'table', 'blockquote']):
        # If this element is inside another element in our list, likely valid nesting (li in ul) 
        # or invalid (p in table).
        # We want to avoid double text.
        
        # Check if any parent is in the list of interest (excluding self)
        # But careful with <ul> and <li>.
        # We included <ul> in search, so we handle <ul> as a block.
        # We should NOT include <li> in search if we handle <ul>.
        # If we process <ul>, we get text of all LIs.
        
        # Check parents
        has_parent_block = False
        for parent in child.parents:
            if parent.name in ['ul', 'ol', 'table', 'blockquote', 'pre']: # Containers we handle as a whole
                has_parent_block = True
                break
        
        if has_parent_block:
            continue
            
        # Process this block
        tag_name = child.name.lower()
        text = _elem_to_text(child)
        if not text: 
            continue
            
        if tag_name in ('h1', 'h2', 'h3', 'h4'):
            # Flush current content
            if current_content:
                sections.append({"heading": current_heading, "content": "\n\n".join(current_content)})
                current_content = []
            current_heading = text
        else:
            current_content.append(text)
            
    # Flush remaining
    if current_content:
        sections.append({"heading": current_heading, "content": "\n\n".join(current_content)})
            
    if not sections:
        # Fallback if no specific blocks found (maybe just text in divs)
        text = body.get_text(separator="\n", strip=True)
        sections = [{"heading": "Content", "content": text}]
        
    return sections

def crawl_site(start_url: str, max_pages: int = 50):
    """
    Crawl website starting from start_url.
    Returns: [{"url": ..., "title": ..., "path": ..., "sections": [...]}, ...]
    """
    parsed = urlparse(start_url)
    base_netloc = parsed.netloc
    base_root = f"{parsed.scheme}://{parsed.netloc}"

    rp = allowed_by_robots(start_url)
    to_visit = [start_url]
    seen = set()
    results = []

    while to_visit and len(results) < max_pages:
        url = to_visit.pop(0)
        if url in seen:
            continue
        seen.add(url)

        # Check robots.txt
        if rp:
            try:
                allowed = rp.can_fetch(HEADERS["User-Agent"], url)
            except Exception:
                allowed = True
        else:
            allowed = True

        if not allowed:
            continue

        html = fetch_url(url)
        if not html:
            continue

        sections = extract_body_sections(html)
        
        # Get title from first H1/H2 in body
        title = ""
        soup = BeautifulSoup(html, "html.parser")
        if soup.body:
            h = soup.body.find(re.compile(r"^h[1-2]$", re.I))
            if h:
                title = h.get_text(strip=True)
        if not title:
            title = urlparse(url).netloc

        results.append({
            "url": url,
            "title": title,
            "path": urlparse(url).path or "/",
            "sections": sections
        })

        # Discover links
        links = extract_links(html, base_root)
        for link in links:
            if not is_same_domain(base_netloc, link):
                continue
            parsed_l = urlparse(link)
            norm = parsed_l._replace(fragment="").geturl()
            if norm not in seen and norm not in to_visit:
                to_visit.append(norm)

        time.sleep(0.2)  # Be polite

    return results
