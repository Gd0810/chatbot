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

def is_same_domain(base_netloc: str, link: str) -> bool:
    """Check if link is from same domain."""
    try:
        p = urlparse(link)
        if not p.netloc:
            return True
        return p.netloc == base_netloc
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
    """Remove scripts/styles/noscript from a subtree."""
    for bad in tag.find_all(["script", "style", "noscript", "iframe"]):
        bad.decompose()
    return tag

def _elem_to_text(elem: Tag) -> str:
    """Convert tag to readable text - lists as bullets, paragraphs as single lines."""
    name = elem.name.lower()
    if name in ("ul", "ol"):
        items = []
        for li in elem.find_all("li"):
            t = li.get_text(separator=" ", strip=True)
            if t:
                items.append("- " + re.sub(r"\s+", " ", t))
        return "\n".join(items).strip()
    else:
        text = elem.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()
        return text

def extract_body_sections(html: str):
    """
    Extract sections from HTML body based on headings.
    Returns: [{"heading": "Intro" or heading_text, "content": "..."}, ...]
    """
    soup = BeautifulSoup(html, "html.parser")
    body = soup.body or soup
    _clean_tag(body)

    sections = []
    current_heading = "Intro"
    current_lines = []

    for child in body.children:
        if not isinstance(child, Tag):
            txt = (child.string or "").strip()
            if txt:
                current_lines.append(re.sub(r"\s+", " ", txt))
            continue

        tag_name = child.name.lower()

        # Headings as section delimiters
        if re.match(r"h[1-4]$", tag_name):
            if current_lines:
                content = "\n\n".join([l for l in current_lines if l])
                sections.append({"heading": current_heading, "content": content})
            current_heading = child.get_text(separator=" ", strip=True)
            current_lines = []
            continue

        # Collect content from paragraphs, lists, divs
        if tag_name in ("p", "div", "section", "article", "ul", "ol", "address"):
            txt = _elem_to_text(child)
            if txt:
                current_lines.append(txt)
            continue

        # Skip nav, footer, header to avoid boilerplate
        if tag_name in ("nav", "footer", "header", "form", "script", "style"):
            continue

        # Fallback
        txt = child.get_text(separator=" ", strip=True)
        if txt:
            current_lines.append(re.sub(r"\s+", " ", txt))

    # Flush remaining
    if current_lines:
        content = "\n\n".join([l for l in current_lines if l])
        sections.append({"heading": current_heading, "content": content})
    
    if not sections:
        sections = [{"heading": "Intro", "content": ""}]
    
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
