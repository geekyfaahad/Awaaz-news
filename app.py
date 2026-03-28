
# aiohttp code


from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for
from cryptography.fernet import Fernet
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from flask_compress import Compress
import logging
from threading import Thread, Lock
import time
from collections import defaultdict
from datetime import datetime, timedelta
import atexit
from urllib.parse import urlparse, parse_qs, unquote, urljoin, urlencode
from html import unescape
import xml.etree.ElementTree as ET
import json
import re
from pathlib import Path
from typing import Optional
import firebase_admin
from firebase_admin import credentials, firestore, auth
import os
import requests
from apify_client import ApifyClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _load_dotenv_file() -> None:
    """Load ``KEY=value`` pairs from project ``.env`` if present (no extra dependency)."""
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.is_file():
        return
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip().strip('"').strip("'")
            if key:
                os.environ.setdefault(key, val)
    except OSError as e:
        logger.warning("Could not read .env: %s", e)


_load_dotenv_file()

app = Flask(__name__)
app.secret_key = 'sdfsd232@!43f2!sad'  # Change this to a secure secret key
Compress(app)

# Firebase configuration
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyAaJM_bueD7iIL0mBD__2b4xHrWYzUinws",
    "authDomain": "awaaz-4a5d9.firebaseapp.com",
    "projectId": "awaaz-4a5d9",
    "storageBucket": "awaaz-4a5d9.firebasestorage.app",
    "messagingSenderId": "725877723724",
    "appId": "1:725877723724:web:55c542c2767e5defd9dae9"
}

# Initialize Firebase Admin SDK
try:
    # Use service account key if available, otherwise use default credentials
    if os.path.exists('firebase-service-account.json'):
        cred = credentials.Certificate('firebase-service-account.json')
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        logger.info("Firebase Admin SDK initialized successfully with service account")
    else:
        # For local development without Firebase credentials, use default sources
        logger.info("No Firebase credentials found. Using default news sources.")
        db = None
except Exception as e:
    logger.error(f"Failed to initialize Firebase: {e}")
    db = None

rate_limit = 100
rate_limit_window = 43200  # 12 hours in seconds
request_counts = defaultdict(lambda: {"count": 0, "reset_time": datetime.now()})
lock = Lock()

def get_client_ip():
    """Retrieve the IP address of the client."""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0]
    return request.remote_addr

def is_rate_limited(ip):
    now = datetime.now()
    with lock:
        if now >= request_counts[ip]["reset_time"]:
            request_counts[ip]["count"] = 1  # Reset count with current request
            request_counts[ip]["reset_time"] = now + timedelta(seconds=rate_limit_window)
            return False
        else:
            request_counts[ip]["count"] += 1
            if request_counts[ip]["count"] > rate_limit:
                return True
        return False

def cleanup_request_counts():
    now = datetime.now()
    to_remove = [ip for ip, data in request_counts.items() if now >= data["reset_time"] and data["count"] == 0]
    for ip in to_remove:
        del request_counts[ip]

def start_cleanup():
    while True:
        cleanup_request_counts()
        time.sleep(3600)  # Clean up every hour

cleanup_thread = Thread(target=start_cleanup)
cleanup_thread.daemon = True
cleanup_thread.start()

atexit.register(cleanup_request_counts)

# Default news sources
DEFAULT_NEWS_SOURCES = [
    {"domain": "kashmirobserver.net", "name": "Kashmir Observer", "enabled": True},
    {"domain": "thekashmiriyat.co.uk", "name": "The Kashmiriyat", "enabled": True},
    {"domain": "kashmirnews.in", "name": "Kashmir News", "enabled": True},
    {"domain": "kashmirdespatch.com", "name": "Kashmir Dispatch", "enabled": True},
    {"domain": "kashmirlife.net", "name": "Kashmir Life", "enabled": True},
    {"domain": "greaterkashmir.com", "name": "Greater Kashmir", "enabled": True},
    {"domain": "asiannewshub.com", "name": "Asian News Hub", "enabled": True},
    {"domain": "thekashmirmonitor.net", "name": "The Kashmir Monitor", "enabled": True},
    {"domain": "kashmirtimes.com", "name": "Kashmir Times", "enabled": True},
    {"domain": "newsvibesofindia.com", "name": "News Vibes of India", "enabled": True},
    {"domain": "kashmirvision.in", "name": "Kashmir Vision", "enabled": True}
]

# Domains that publish international news and need strict Kashmir filtering
# These domains will have Kashmir keywords added to their search queries
INTERNATIONAL_NEWS_DOMAINS = [
    "asiannewshub.com",
    "asianewsnetwork.net",
    "newsvibesofindia.com"
]

############################
# Local storage (fallback) #
############################

LOCAL_DATA_DIR: Path = Path("data")
LOCAL_SOURCES_FILE: Path = LOCAL_DATA_DIR / "news_sources.json"
_sources_file_lock: Lock = Lock()

def _ensure_local_sources_file_exists() -> None:
    if not LOCAL_DATA_DIR.exists():
        LOCAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not LOCAL_SOURCES_FILE.exists():
        # Seed with defaults and deterministic ids (use domain as id)
        seeded = []
        for src in DEFAULT_NEWS_SOURCES:
            seeded.append({**src, "id": src["domain"]})
        with _sources_file_lock:
            LOCAL_SOURCES_FILE.write_text(json.dumps(seeded, indent=2), encoding="utf-8")

def load_local_sources() -> list:
    _ensure_local_sources_file_exists()
    with _sources_file_lock:
        try:
            raw = LOCAL_SOURCES_FILE.read_text(encoding="utf-8")
            sources = json.loads(raw)
            # Ensure each has id
            for s in sources:
                if "id" not in s:
                    s["id"] = s.get("domain")
            return sources
        except Exception as e:
            logger.error(f"Failed to read local sources: {e}")
            # Fall back to defaults if read fails
            seeded = [{**s, "id": s["domain"]} for s in DEFAULT_NEWS_SOURCES]
            return seeded

def save_local_sources(sources: list) -> None:
    with _sources_file_lock:
        try:
            LOCAL_SOURCES_FILE.write_text(json.dumps(sources, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to write local sources: {e}")

def toggle_source_local(source_id: str, enabled: bool) -> bool:
    sources = load_local_sources()
    updated = False
    for s in sources:
        if s.get("id") == source_id or s.get("domain") == source_id:
            s["enabled"] = enabled
            updated = True
            break
    if updated:
        save_local_sources(sources)
    return updated

def add_source_local(domain: str, name: str) -> bool:
    domain = (domain or "").strip().lower()
    name = (name or "").strip()
    if not domain or not name:
        return False
    sources = load_local_sources()
    # Prevent duplicates by domain
    for s in sources:
        if s.get("domain").lower() == domain:
            return False
    sources.append({"id": domain, "domain": domain, "name": name, "enabled": True})
    save_local_sources(sources)
    return True

def delete_source_local(source_id: str) -> bool:
    sources = load_local_sources()
    new_sources = [s for s in sources if s.get("id") != source_id and s.get("domain") != source_id]
    if len(new_sources) == len(sources):
        return False
    save_local_sources(new_sources)
    return True

def initialize_news_sources():
    """Initialize news sources in Firebase if they don't exist"""
    if db is None:
        # Initialize local file
        _ensure_local_sources_file_exists()
        logger.info("Initialized local news_sources.json store")
        return
    try:
        sources_ref = db.collection('news_sources')
        existing_sources = [doc.to_dict() for doc in sources_ref.stream()]
        if not existing_sources:
            for source in DEFAULT_NEWS_SOURCES:
                sources_ref.add(source)
            logger.info("News sources initialized in Firebase")
        else:
            logger.info("News sources already exist in Firebase")
    except Exception as e:
        logger.error(f"Error initializing news sources: {e}")

def get_news_sources():
    """Get news sources from Firebase with caching"""
    global news_sources_cache, news_sources_cache_time
    
    # Check cache first
    if (news_sources_cache is not None and 
        news_sources_cache_time is not None and
        (datetime.now() - news_sources_cache_time).total_seconds() < news_sources_cache_duration):
        return news_sources_cache
    
    if db is None:
        news_sources_cache = load_local_sources()
        news_sources_cache_time = datetime.now()
        return news_sources_cache
    
    try:
        sources_ref = db.collection('news_sources')
        sources = []
        for doc in sources_ref.stream():
            source_data = doc.to_dict()
            source_data['id'] = doc.id
            sources.append(source_data)
        
        # Update cache
        news_sources_cache = sources
        news_sources_cache_time = datetime.now()
        return sources
    except Exception as e:
        logger.error(f"Error getting news sources: {e}")
        # Fallback to local
        news_sources_cache = load_local_sources()
        news_sources_cache_time = datetime.now()
        return news_sources_cache

def is_admin_authenticated():
    """Check if user is authenticated as admin"""
    return session.get('admin_authenticated', False)

def require_admin_auth(f):
    """Decorator to require admin authentication"""
    def decorated_function(*args, **kwargs):
        if not is_admin_authenticated():
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def get_time_range(user_choice):
    time_ranges = {
        "rf": "h,sbd:1",  # Recent news (last hour)
        "dn": "d",  # News from the past day
        "wn": "w",  # News from the past week
        "mn": "m",  # News from the past month
        "yn": "y",  # News from the past year
    }
    return time_ranges.get(user_choice, "")


def time_range_to_when_clause(time_range: str) -> str:
    """Map internal tbs-style range to Google News RSS ``when:`` clause."""
    return {
        "h,sbd:1": "1h",
        "d": "1d",
        "w": "7d",
        "m": "1m",
        "y": "1y",
    }.get(time_range, "7d")


def sanitize_city(raw: Optional[str]) -> Optional[str]:
    """Strip and limit city for RSS query; returns None if empty after sanitization."""
    if not raw:
        return None
    s = re.sub(r"[^a-zA-Z0-9\s\-'.]", "", (raw or "").strip())
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        return None
    return s[:80]


def city_clause_for_news_query(city: str) -> str:
    """Phrase for Google News ``q`` (quoted if multi-word)."""
    inner = city.replace('"', " ").strip()
    if not inner:
        return ""
    if " " in inner:
        return f'"{inner}"'
    return inner


# Cities that should keep the curated Kashmir outlet feed (site:… + Kashmir keywords).
KASHMIR_REGION_CITIES = frozenset({
    "srinagar", "jammu", "kashmir", "ladakh", "kupwara", "baramulla", "anantnag", "pulwama",
    "shopian", "kulgam", "budgam", "ganderbal", "bandipora", "poonch", "rajouri", "doda",
    "kishtwar", "kathua", "udhampur", "reasi", "ramban", "leh", "kargil", "handwara", "sopore",
    "nowgam", "gulmarg", "pahalgam", "sonamarg", "sonmarg", "awantipora",
    "jammu and kashmir", "jammu kashmir", "j and k", "jk",
})


def is_kashmir_region_city(city: str) -> bool:
    """True if the user’s city should use the Kashmir-only news sources feed."""
    if not city:
        return False
    key = re.sub(r"\s+", " ", city.strip().lower())
    key = key.replace("&", " and ")
    if key in KASHMIR_REGION_CITIES:
        return True
    if key.endswith(" kashmir") or key.startswith("kashmir "):
        return True
    return False


def build_location_news_query(city: str, when: str) -> str:
    """Google News ``q`` for a general city (no ``site:`` restrictions)."""
    low = re.sub(r"\s+", " ", city.strip()).lower()
    if low in ("new delhi", "delhi", "nct delhi", "national capital territory"):
        core = '("New Delhi" OR Delhi)'
    elif low in ("bengaluru", "bangalore"):
        core = '(Bengaluru OR Bangalore)'
    elif low in ("mumbai", "bombay"):
        core = '(Mumbai OR Bombay)'
    elif low in ("kolkata", "calcutta"):
        core = '(Kolkata OR Calcutta)'
    elif low in ("chennai", "madras"):
        core = '(Chennai OR Madras)'
    elif low == "hyderabad":
        core = 'Hyderabad'
    elif low == "pune":
        core = 'Pune'
    elif low == "ahmedabad":
        core = 'Ahmedabad'
    else:
        cq = city_clause_for_news_query(city.strip())
        core = f"({cq})" if cq else "India"
    return f"{core} when:{when}"


def load_key():
    try:
        with open("encryption_key.key", "rb") as key_file:
            return key_file.read()
    except FileNotFoundError:
        logger.error("Encryption key file not found.")
        raise
    except Exception as e:
        logger.error(f"Error loading encryption key: {e}")
        raise

def decrypt_url(encrypted_url, key):
    try:
        cipher = Fernet(key)
        return cipher.decrypt(encrypted_url).decode()
    except Exception as e:
        logger.error(f"Error decrypting URL: {e}")
        raise
# Keywords that indicate Kashmir-related content (used for post-fetch filtering)
RELEVANCE_KEYWORDS = [
    # Regions - Major
    "kashmir", "srinagar", "jammu", "ladakh", "kashmiri",
    # Regions - Districts
    "kupwara", "baramulla", "anantnag", "pulwama", "shopian", 
    "kulgam", "budgam", "ganderbal", "bandipora", "poonch", 
    "rajouri", "doda", "kishtwar", "kathua", "udhampur", 
    "reasi", "ramban", "leh", "kargil",
    # Entities & Abbreviations
    "j&k", "j and k", "j-k", "jk", "lgw",
    # Tourist/Cultural places
    "dal lake", "gulmarg", "pahalgam", "sonamarg", "amarnath", 
    "vaishno devi", "patnitop", "bhaderwah", "sonmarg",
    # Local context
    "loc", "line of control", "uri", "handwara", "sopore", "nowgam"
]

# Keywords for Google search query (subset for query building)
SEARCH_KEYWORDS = "kashmir OR srinagar OR jammu OR \"j&k\" OR ladakh"


def normalize_google_news_article_url(url: str) -> str:
    """Use the /articles/ HTML document; /rss/articles/ is a lighter shell with worse metadata."""
    if not url:
        return url
    return url.replace(
        "https://news.google.com/rss/articles/",
        "https://news.google.com/articles/",
    ).replace(
        "http://news.google.com/rss/articles/",
        "http://news.google.com/articles/",
    )


def upgrade_google_cdn_image_url(url: str) -> str:
    """Ask Google's CDN for a larger thumbnail when the page emits a small =s0-wNNN tile."""
    if not url or "googleusercontent.com" not in url:
        return url
    base = re.sub(r"=s\d+(-w\d+)?(-rw)?(\?.*)?$", "", url.split("?")[0])
    return f"{base}=s1200" if base else url


def extract_publisher_url_from_description(
    raw_desc: str, allowed_domains: Optional[set]
) -> str:
    """Return a direct publisher article URL if the RSS description includes one.

    If ``allowed_domains`` is None, return the first non–Google-News publisher link.
    """
    if not raw_desc:
        return ""
    try:
        soup = BeautifulSoup(unescape(raw_desc), "html.parser")
        for a in soup.find_all("a", href=True):
            href = (a.get("href") or "").strip()
            if not href or "news.google.com" in href:
                continue
            try:
                netloc = urlparse(href).netloc.lower().replace("www.", "")
            except Exception:
                continue
            if not netloc:
                continue
            if allowed_domains is None:
                return href
            for d in allowed_domains:
                if netloc == d or netloc.endswith("." + d):
                    return href
    except Exception:
        pass
    return ""


def extract_best_image_from_soup(soup: BeautifulSoup, page_url: str) -> str:
    """Resolve og/twitter/JSON-LD image to an absolute URL."""

    def absolutize(u: str) -> str:
        u = (u or "").strip()
        if not u or u.startswith("data:"):
            return ""
        return urljoin(page_url, u)

    for sel in (
        'meta[property="og:image:secure_url"]',
        'meta[property="og:image"]',
        'meta[name="twitter:image:src"]',
        'meta[name="twitter:image"]',
    ):
        tag = soup.select_one(sel)
        if tag and tag.get("content"):
            u = absolutize(tag["content"])
            if u:
                return u

    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text() or ""
        if not raw.strip():
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        objs = data if isinstance(data, list) else [data]
        for obj in objs:
            if not isinstance(obj, dict):
                continue
            img = obj.get("image")
            if isinstance(img, str):
                u = absolutize(img)
                if u:
                    return u
            if isinstance(img, dict):
                u = absolutize(img.get("url") or img.get("@id") or "")
                if u:
                    return u
            if isinstance(img, list) and img:
                first = img[0]
                if isinstance(first, dict) and first.get("url"):
                    u = absolutize(first["url"])
                    if u:
                        return u
                elif isinstance(first, str):
                    u = absolutize(first)
                    if u:
                        return u
    return ""


async def fetch_news(time_range, extract_images=True, city=None):
    """
    Fetch news via Google News RSS.

    Default (no city or Kashmir-region city): curated Kashmir outlets + keywords.

    Other cities (e.g. New Delhi): broad location query without ``site:`` restrictions
    so results match the place instead of only Kashmir publishers.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        when = time_range_to_when_clause(time_range)
        location_mode = bool(city) and not is_kashmir_region_city(city)

        news_sources = get_news_sources()
        enabled_sources = [source["domain"] for source in news_sources if source.get("enabled", True)]

        if not location_mode:
            if not enabled_sources:
                logger.warning("No news sources are enabled")
                return []

            query_parts = []
            for domain in enabled_sources:
                clean_domain = domain.replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")
                query_parts.append(f"site:{clean_domain}")
            sources_query = " OR ".join(query_parts)
            city_q = city_clause_for_news_query(city) if city else ""
            if city_q:
                full_q = f"({sources_query}) ({SEARCH_KEYWORDS}) ({city_q}) when:{when}"
            else:
                full_q = f"({sources_query}) ({SEARCH_KEYWORDS}) when:{when}"
            logger.info("Google News RSS: Kashmir curated feed")
        else:
            full_q = build_location_news_query(city, when)
            logger.info(f"Google News RSS: location feed for city={city!r} q={full_q[:200]}...")

        rss_url = "https://news.google.com/rss/search?" + urlencode(
            {"q": full_q, "hl": "en", "gl": "IN", "ceid": "IN:en"}
        )
        logger.info(f"Google News RSS request length: {len(rss_url)} chars")

        excluded_keywords = [
            "Greater Kashmir", "Page 1 Archives", "National Archives",
            "Kashmir Latest News Archives", "Todays Paper", "Articles Written By",
            "LATEST NEWS", "Irfan Yattoo", "Top Stories",
            "You searched for ramadhan 2025 ", "Video: Kashmir Observer News Roundup",
            "You searched for out of-syllabus ", "City", "Sports", "Editorial", "Opinion",
        ]
        excluded_url_prefixes = [
            "https://kashmirobserver.net/author/",
            "https://m.greaterkashmir.com/topic/",
            "https://www.greaterkashmir.com/tag/",
            "https://kashmirlife.net/tag/",
            "https://www.kashmirlife.net/tag/",
            "https://epaper.greaterkashmir.com",
            "https://asianewsnetwork.net/category/",
            "https://www.thekashmirmonitor.net/politics/",
        ]
        excluded_page_numbers = [
            "page-1", "page-2", "page-3", "page-4", "page-5",
            "p=1", "p=2", "p=3", "p=4", "p=5",
            "/1/", "/2/", "/3/", "/4/", "/5/",
            "page1", "page2", "page3", "page4", "page5",
        ]

        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(rss_url, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"Google News RSS failed. Status: {response.status}")
                    return []
                xml_content = await response.text()

            try:
                root = ET.fromstring(xml_content)
            except ET.ParseError as e:
                logger.error(f"Failed to parse Google News RSS XML: {e}")
                return []

            allowed_domains: Optional[set] = None if location_mode else set()
            if allowed_domains is not None:
                for domain in enabled_sources:
                    cd = domain.replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/").lower()
                    if cd:
                        allowed_domains.add(cd)

            news_items_data = []
            for item in root.findall(".//item"):
                headline = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                time_text = (item.findtext("pubDate") or "").strip() or "Recent"
                raw_desc = item.findtext("description") or ""
                source_el = item.find("source")
                source_site_url = ""
                if source_el is not None:
                    source_site_url = (source_el.get("url") or "").strip()
                publisher_article_url = extract_publisher_url_from_description(raw_desc, allowed_domains)

                summary_text = "No summary available"
                if raw_desc:
                    try:
                        summary_text = BeautifulSoup(unescape(raw_desc), "html.parser").get_text(
                            separator=" ", strip=True
                        )
                        if len(summary_text) > 500:
                            summary_text = summary_text[:500].rsplit(" ", 1)[0] + "..."
                    except Exception:
                        summary_text = raw_desc[:300]

                if not headline or not link:
                    continue

                headline_lower = headline.lower()
                if headline_lower.startswith(("page", "page-", "page ")):
                    continue
                if headline_lower.startswith(("you searched for", "you searched", "searched for")):
                    continue

                if any(kw.lower() in headline.lower() for kw in excluded_keywords):
                    continue
                if any(link.startswith(prefix) for prefix in excluded_url_prefixes):
                    continue
                if any(pn in link.lower() for pn in excluded_page_numbers):
                    continue
                if any(pn in headline.lower() for pn in excluded_page_numbers):
                    continue

                news_items_data.append({
                    "headline": headline,
                    "summary": summary_text,
                    "time": time_text,
                    "link": link,
                    "source_site_url": source_site_url,
                    "publisher_article_url": publisher_article_url,
                })

            logger.info(f"Google News RSS returned {len(news_items_data)} items after basic filters")

            # Optimization: Limit to 20 articles for 4x faster response times
            max_articles = 20 if not location_mode else 12 
            news_items_data = news_items_data[:max_articles]

            def is_from_international_domain(article_link):
                link_lower = article_link.lower()
                return any(intl_domain in link_lower for intl_domain in INTERNATIONAL_NEWS_DOMAINS)

            def is_relevant_to_kashmir(article):
                text_to_check = (article.get("headline", "") + " " + article.get("summary", "")).lower()
                return any(keyword.lower() in text_to_check for keyword in RELEVANCE_KEYWORDS)

            original_count = len(news_items_data)
            if location_mode:
                filtered_articles = list(news_items_data)
            else:
                filtered_articles = []
                for item in news_items_data:
                    if is_from_international_domain(item.get("link", "")):
                        if is_relevant_to_kashmir(item):
                            filtered_articles.append(item)
                        else:
                            logger.info(
                                f"Filtered out (no Kashmir keywords): {item.get('headline', 'Unknown')[:50]}..."
                            )
                    else:
                        filtered_articles.append(item)

            news_items_data = filtered_articles
            filtered_count = original_count - len(news_items_data)
            if not location_mode and filtered_count > 0:
                logger.info(
                    f"Filtered out {filtered_count} non-Kashmir articles from international domains "
                    f"(kept {len(news_items_data)} articles)"
                )

            async def extract_article_details(article_data):
                image_url = "No image available"
                summary = article_data.get("summary", "No summary available")
                pub_url = (article_data.get("publisher_article_url") or "").strip()
                page_url = pub_url or normalize_google_news_article_url(article_data.get("link") or "")
                # Optimization: Tight 10-second timeout for article metadata
                fetch_timeout = aiohttp.ClientTimeout(total=10, connect=3, sock_read=7)

                try:
                    async with session.get(page_url, headers=headers, timeout=fetch_timeout) as article_response:
                        if article_response.status == 200:
                            article_html = await article_response.text()
                            article_soup = BeautifulSoup(article_html, "html.parser")

                            if summary == "No summary available":
                                meta_desc = article_soup.select_one('meta[property="og:description"]') or \
                                    article_soup.select_one('meta[name="description"]') or \
                                    article_soup.select_one('meta[name="twitter:description"]')

                                if meta_desc and meta_desc.get("content"):
                                    extracted_summary = meta_desc.get("content").strip()
                                    if extracted_summary and len(extracted_summary) > 20:
                                        summary = extracted_summary[:200]
                                        if len(extracted_summary) > 200:
                                            summary = summary.rsplit(' ', 1)[0] + '...'
                                        logger.info(f"Extracted summary from meta for: {article_data['headline'][:30]}...")

                                if summary == "No summary available":
                                    paragraph_selectors = [
                                        'article p',
                                        '.article-content p',
                                        '.post-content p',
                                        '.entry-content p',
                                        '.content p',
                                        '.story-content p',
                                        '.news-content p',
                                        'main p'
                                    ]

                                    for selector in paragraph_selectors:
                                        paragraphs = article_soup.select(selector)
                                        if paragraphs:
                                            text_parts = []
                                            for p in paragraphs[:3]:
                                                p_text = p.get_text().strip()
                                                if len(p_text) > 30 and not p_text.startswith(('By ', 'Published', 'Updated', 'Share')):
                                                    text_parts.append(p_text)

                                            if text_parts:
                                                combined_text = ' '.join(text_parts)
                                                summary = combined_text[:200]
                                                if len(combined_text) > 200:
                                                    summary = summary.rsplit(' ', 1)[0] + '...'
                                                logger.info(f"Extracted summary from paragraphs for: {article_data['headline'][:30]}...")
                                                break

                            best = extract_best_image_from_soup(article_soup, page_url)
                            if best:
                                image_url = upgrade_google_cdn_image_url(best)
                                logger.info(f"Resolved hero image from page metadata: {image_url[:100]}...")

                            if image_url == "No image available":
                                img_selectors = [
                                    "img[src*='.jpg']", "img[src*='.jpeg']", "img[src*='.png']", "img[src*='.webp']",
                                    ".article-image img", ".post-image img", ".featured-image img",
                                    ".entry-image img", ".content-image img", ".main-image img",
                                    ".hero-image img", ".banner-image img", ".thumbnail img",
                                    "article img", ".article img", ".post img", ".content img",
                                    ".story-image img", ".news-image img", ".media img",
                                    "#post-feat-img img"
                                ]

                                for selector in img_selectors:
                                    img_tag = article_soup.select_one(selector)
                                    if img_tag:
                                        cand = img_tag.get("src", "")
                                        if cand and cand != "No image available":
                                            image_url = upgrade_google_cdn_image_url(urljoin(page_url, cand))
                                            logger.info(f"Found selector image: {image_url[:100]}...")
                                            break

                            if image_url == "No image available":
                                all_images = article_soup.find_all("img")
                                for img in all_images:
                                    src = img.get("src", "")
                                    if src and any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                                        width = img.get("width", "")
                                        height = img.get("height", "")
                                        alt = img.get("alt", "").lower()

                                        if (width and str(width).isdigit() and int(width) < 100) or (height and str(height).isdigit() and int(height) < 100):
                                            continue
                                        if any(skip_word in alt for skip_word in ['icon', 'logo', 'avatar', 'profile']):
                                            continue

                                        image_url = upgrade_google_cdn_image_url(urljoin(page_url, src))
                                        logger.info(f"Found fallback image: {image_url[:100]}...")
                                        break

                except Exception as e:
                    logger.warning(f"Error extracting details from {page_url}: {e}")
                    image_url = "No image available"

                if image_url == "No image available":
                    logger.info(f"No image found for: {article_data['headline'][:50]}...")
                    try:
                        parsed_link = urlparse(article_data["link"])
                        domain = parsed_link.netloc.lower()
                        if "greaterkashmir" in domain:
                            image_url = "https://placehold.co/400x200/3f51b5/ffffff?text=Greater+Kashmir+News"
                        elif "kashmirobserver" in domain:
                            image_url = "https://placehold.co/400x200/ff5722/ffffff?text=Kashmir+Observer"
                        elif "kashmirnews" in domain:
                            image_url = "https://placehold.co/400x200/4caf50/ffffff?text=Kashmir+News"
                        elif "kashmirlife" in domain:
                            image_url = "https://placehold.co/400x200/9c27b0/ffffff?text=Kashmir+Life"
                        else:
                            image_url = "https://placehold.co/400x200/607d8b/ffffff?text=News+Article"
                    except Exception:
                        image_url = "https://placehold.co/400x200/607d8b/ffffff?text=News+Article"
                    logger.info(f"Using fallback image: {image_url}")
                else:
                    logger.info(f"✅ SUCCESS: Image found for '{article_data['headline'][:50]}...' -> {image_url}")

                out = {k: v for k, v in article_data.items() if k not in ("source_site_url", "publisher_article_url")}
                return {**out, "image": image_url, "summary": summary}

            if news_items_data and extract_images:
                # Optimization: High-concurrency (15 parallel requests)
                semaphore = asyncio.Semaphore(15)

                async def extract_with_semaphore(item):
                    async with semaphore:
                        return await extract_article_details(item)

                tasks = [extract_with_semaphore(item) for item in news_items_data]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                valid_results = []
                for result in results:
                    if isinstance(result, Exception):
                        logger.error(f"Error processing article: {result}")
                        continue
                    valid_results.append(result)

                return valid_results
            if news_items_data:
                rows = []
                for item in news_items_data:
                    base = {k: v for k, v in item.items() if k not in ("source_site_url", "publisher_article_url")}
                    rows.append({"image": "https://placehold.co/400x200/607d8b/ffffff?text=News+Article", **base})
                return rows

            return []
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return []

# Add caching for news data
news_cache = {}
cache_duration = 300  # 5 minutes cache
news_sources_cache = None
news_sources_cache_time = None
news_sources_cache_duration = 60  # 1 minute cache for news sources

def cleanup_cache():
    """Clean up expired cache entries"""
    current_time = datetime.now()
    expired_keys = []
    for key, (cache_time, _) in news_cache.items():
        if (current_time - cache_time).total_seconds() > cache_duration:
            expired_keys.append(key)
    
    for key in expired_keys:
        del news_cache[key]
    
    if expired_keys:
        logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")


GOOGLE_NEWS_RSS_BASE = "https://news.google.com/rss/search"

NEWS_ASSISTANT_SYSTEM = """You are a careful news literacy assistant. Users ask whether claims or news might be legitimate.

You may receive recent headlines from Google News RSS (the same source this app uses for articles). Use those headlines only as corroboration signals — they are not proof, and coverage can lag or miss niche topics.

Rules:
- Open your response with a clear status line on its own first line: "STATUS: VERIFIED", "STATUS: FAKE", or "STATUS: UNVERIFIED".
- Then provide your explanation.
- Keep replies under 320 words unless the user pasted very long text.
- Close with one line: "Overall:" plus a brief verdict."""


# ── Local Semantic Verification Engine (no external API needed) ──

# Negative action words — if the claim implies X happened to someone but the
# headline says someone *else* was subject of the action, that is a mismatch.
_NEGATIVE_ACTION_WORDS = frozenset({
    "killed", "dead", "died", "dies", "death", "murder", "murdered",
    "assassinated", "shot", "shooting", "arrested", "detained", "kidnapped",
    "attacked", "injured", "bomb", "bombed", "explosion", "blast",
    "resign", "resigned", "resigns", "sacked", "fired", "suspended",
    "missing", "crash", "collapsed", "suicide",
})

# Words that indicate the subject is commenting/reacting, not being acted upon
_COMMENTARY_VERBS = frozenset({
    "questions", "condemns", "slams", "demands", "seeks", "says", "said",
    "asks", "urges", "calls", "criticizes", "criticises", "warns",
    "reacts", "responds", "mourns", "condoles", "appeals", "addresses",
    "discusses", "speaks", "tweets", "posts", "comments", "hails",
    "welcomes", "praises", "salutes", "lauds", "supports", "opposes",
    "denies", "refutes", "clarifies", "announces", "declares",
    "orders", "directs", "reviews", "meets", "visits", "inaugurates",
})

_SERIOUS_CLAIM_BRIDGE_WORDS = frozenset({
    "is", "was", "were", "has", "have", "had", "been", "being", "be",
    "found", "confirmed", "reportedly", "reported", "declared",
    "officially", "now", "feared",
})

_NEGATION_OR_RUMOR_CUES = frozenset({
    "no", "not", "fake", "false", "hoax", "rumor", "rumour",
    "rumors", "rumours", "debunk", "debunked", "debunks", "denies",
    "deny", "denied", "alive", "safe", "unharmed",
})


def _tokenize_lower(text: str) -> list:
    """Split text into lowercase word tokens."""
    return re.findall(r"[a-z0-9']+", (text or "").lower())


def _extract_claim_subject_tokens(claim_tokens: list) -> list:
    seen = set()
    subject_tokens = []
    for token in claim_tokens:
        if (
            token in _NEGATIVE_ACTION_WORDS
            or token in _X_STOP_WORDS
            or len(token) <= 2
            or token in seen
        ):
            continue
        seen.add(token)
        subject_tokens.append(token)
    return subject_tokens


def _find_subject_spans(claim_subjects: list, headline_tokens: list) -> list:
    """
    Find tight, ordered spans where the claim subject appears in the headline.

    For person-name claims we prefer compact spans like "omar abdullah", not
    loose token matches scattered across the headline.
    """
    if not claim_subjects or not headline_tokens:
        return []

    unique_subjects = list(dict.fromkeys(claim_subjects))
    required_matches = 1 if len(unique_subjects) == 1 else 2
    spans = []

    for start in range(len(headline_tokens)):
        if headline_tokens[start] != unique_subjects[0]:
            continue

        matched = 1
        last_pos = start
        for token in unique_subjects[1:]:
            found_pos = None
            for pos in range(last_pos + 1, min(len(headline_tokens), last_pos + 3)):
                if headline_tokens[pos] == token:
                    found_pos = pos
                    break
            if found_pos is None:
                break
            matched += 1
            last_pos = found_pos

        if matched >= required_matches:
            spans.append((start, last_pos))

    return spans


def _semantic_verify_claim(user_claim: str, headlines: list) -> dict:
    """
    Analyze whether the user's claim is semantically supported by the headlines.

    Returns dict with:
        verified: bool — whether the claim is truly supported
        confidence: str — "high", "medium", "low"
        reason: str — human-readable explanation
        matching_headlines: list — indices of truly matching headlines
    """
    claim_tokens = _tokenize_lower(user_claim)
    if not claim_tokens or not headlines:
        return {
            "verified": False,
            "confidence": "low",
            "reason": "Insufficient data to verify.",
            "matching_headlines": [],
        }

    # ── Step 1: Extract the claim's subject & action ──
    # The subject is the entity (noun phrase) and the action is what happened
    claim_set = set(claim_tokens)
    claim_action_words = claim_set & _NEGATIVE_ACTION_WORDS
    has_serious_claim = bool(claim_action_words)  # "killed", "dead", etc.
    claim_subject_tokens = _extract_claim_subject_tokens(claim_tokens)

    # ── Step 2: Score each headline ──
    matching = []
    contradicting = []
    neutral = []

    for idx, item in enumerate(headlines):
        title = item.get("title") or ""
        title_tokens = _tokenize_lower(title)
        title_set = set(title_tokens)

        # Basic word overlap
        overlap = claim_set & title_set
        overlap_ratio = len(overlap) / max(len(claim_set), 1)

        if overlap_ratio < 0.3:
            neutral.append(idx)
            continue

        if has_serious_claim:
            # Check if the headline has the same action word
            headline_actions = title_set & _NEGATIVE_ACTION_WORDS
            headline_commentary = title_set & _COMMENTARY_VERBS

            if headline_actions:
                action_subject_match = _check_subject_action_alignment(
                    claim_subject_tokens, claim_action_words,
                    title_tokens, headline_actions
                )
                negates_claim = _headline_negates_claim(
                    claim_subject_tokens, title_tokens, headline_actions
                )
                if action_subject_match and not negates_claim:
                    matching.append(idx)
                else:
                    contradicting.append(idx)

            elif headline_commentary or _headline_negates_claim(
                claim_subject_tokens, title_tokens, set()
            ):
                # Headline has the subject but with a commentary verb
                # e.g., "Omar Abdullah questions..." vs claim "Omar Abdullah killed"
                contradicting.append(idx)
            else:
                # Has overlap but no clear action — mark neutral
                neutral.append(idx)
        else:
            # Non-serious claim (general news query) — overlap is sufficient
            if overlap_ratio >= 0.5:
                matching.append(idx)
            else:
                neutral.append(idx)

    # ── Step 3: Determine verdict ──
    if matching:
        return {
            "verified": True,
            "confidence": "high" if len(matching) >= 2 else "medium",
            "reason": f"{len(matching)} headline(s) semantically match the claim.",
            "matching_headlines": matching,
        }

    if contradicting and not matching:
        return {
            "verified": False,
            "confidence": "high" if has_serious_claim else "medium",
            "reason": (
                "Headlines contain the same names/keywords but describe a DIFFERENT event. "
                "The subject in the headlines is NOT the target of the claimed action."
            ),
            "matching_headlines": [],
        }

    return {
        "verified": False,
        "confidence": "low",
        "reason": "No headlines clearly confirm or deny this claim.",
        "matching_headlines": [],
    }


def _check_subject_action_alignment(
    claim_subjects: list, claim_actions: set,
    headline_tokens: list, headline_actions: set
) -> bool:
    """
    Check if the subject of the action is the same in both claim and headline.

    E.g., "omar abdullah killed" — subject is "omar abdullah", action is "killed".
    If headline says "terrorists killed in encounter... Omar Abdullah questions",
    the subject of "killed" in the headline is "terrorists", not "omar abdullah".
    """
    if not claim_subjects or not headline_tokens:
        return False

    subject_spans = _find_subject_spans(claim_subjects, headline_tokens)
    action_positions = [i for i, t in enumerate(headline_tokens) if t in headline_actions]
    if not action_positions or not subject_spans:
        return False

    for act_pos in action_positions:
        for span_start, span_end in subject_spans:
            if span_end < act_pos:
                bridge = headline_tokens[span_end + 1:act_pos]
                if len(bridge) <= 2 and all(t in _SERIOUS_CLAIM_BRIDGE_WORDS for t in bridge):
                    return True

            if act_pos < span_start:
                if act_pos + 1 >= len(headline_tokens) or headline_tokens[act_pos + 1] != "of":
                    continue
                bridge = headline_tokens[act_pos + 2:span_start]
                if len(bridge) <= 2 and all(t in _SERIOUS_CLAIM_BRIDGE_WORDS for t in bridge):
                    return True

    return False


def _headline_negates_claim(
    claim_subjects: list,
    headline_tokens: list,
    headline_actions: set,
) -> bool:
    if not claim_subjects or not headline_tokens:
        return False

    subject_spans = _find_subject_spans(claim_subjects, headline_tokens)
    if not subject_spans:
        return False

    negation_positions = [
        i for i, token in enumerate(headline_tokens) if token in _NEGATION_OR_RUMOR_CUES
    ]
    if not negation_positions:
        return False

    action_positions = [
        i for i, token in enumerate(headline_tokens) if token in headline_actions
    ] if headline_actions else []

    for span_start, span_end in subject_spans:
        context_start = max(0, span_start - 4)
        context_end = min(len(headline_tokens), span_end + 5)
        if any(context_start <= pos < context_end for pos in negation_positions):
            return True

        for act_pos in action_positions:
            context_start = max(0, min(span_start, act_pos) - 3)
            context_end = min(len(headline_tokens), max(span_end, act_pos) + 4)
            if any(context_start <= pos < context_end for pos in negation_positions):
                return True

    return False



def _google_news_rss_http_headers() -> dict:
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }


def _ask_ai_rss_query(user_text: str) -> str:
    """Turn user chat into a Google News ``q`` string (length-safe for URLs)."""
    q = re.sub(r"\s+", " ", (user_text or "").strip())
    q = q[:450].strip()
    return q


# ── Stop words to strip when building X/Twitter keyword queries ──
_X_STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "about", "above",
    "after", "again", "against", "all", "am", "and", "any", "at", "because",
    "before", "below", "between", "both", "but", "by", "down", "during",
    "each", "few", "for", "from", "further", "get", "got", "he", "her",
    "here", "hers", "herself", "him", "himself", "his", "how", "i", "if",
    "in", "into", "it", "its", "itself", "just", "me", "meets", "met",
    "more", "most", "my", "myself", "no", "nor", "not", "now", "of", "off",
    "on", "once", "only", "or", "other", "our", "ours", "ourselves", "out",
    "over", "own", "re", "same", "she", "so", "some", "such", "than",
    "that", "their", "theirs", "them", "themselves", "then", "there",
    "these", "they", "this", "those", "through", "to", "too", "under",
    "until", "up", "very", "we", "what", "when", "where", "which", "while",
    "who", "whom", "why", "with", "you", "your", "yours", "yourself",
    "delegation", "reportedly", "allegedly", "says", "said", "told",
    "according", "visit", "visits", "visiting", "visited",
    "news", "article", "headline", "spam", "fake", "check", "real",
    "true", "false", "whether", "please", "tell", "know",
})


def _extract_x_keywords(user_text: str) -> str:
    """Extract meaningful keywords from user text for X/Twitter search.

    Strips stop words, keeps proper nouns and significant terms.
    Returns a cleaned query that matches how people actually tweet.
    """
    text = re.sub(r"[\"'""''`]", " ", user_text or "")
    text = re.sub(r"[^\w\s@#]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    words = text.split()
    keywords = [w for w in words if w.lower() not in _X_STOP_WORDS and len(w) > 1]

    if not keywords and words:
        keywords = words[:5]

    return " ".join(keywords[:8])


def _google_news_rss_items_simple(search_query: str, limit: int = 15) -> list:
    """
    Fetch items from Google News RSS using the same endpoint/parameters as article search.
    Synchronous helper for Ask AI (Flask request thread).
    """
    if not search_query:
        return []
    rss_url = GOOGLE_NEWS_RSS_BASE + "?" + urlencode(
        {"q": search_query, "hl": "en", "gl": "IN", "ceid": "IN:en"}
    )
    try:
        r = requests.get(rss_url, headers=_google_news_rss_http_headers(), timeout=28)
        if r.status_code != 200:
            logger.warning("Ask AI Google News RSS status %s", r.status_code)
            return []
        root = ET.fromstring(r.text)
    except Exception as e:
        logger.warning("Ask AI Google News RSS failed: %s", e)
        return []

    rows = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        when = (item.findtext("pubDate") or "").strip() or "Recent"
        source_name = ""
        source_el = item.find("source")
        if source_el is not None:
            source_name = (source_el.text or "").strip()
        if not title:
            continue
        low = title.lower()
        if low.startswith(("page", "page-", "page ")) or "you searched for" in low:
            continue
        rows.append({"title": title, "link": link, "time": when, "source": source_name})
        if len(rows) >= limit:
            break
    return rows


def _apify_api_token() -> str:
    return (
        (os.environ.get("APIFY_TOKEN") or os.environ.get("APIFY_API_TOKEN") or os.environ.get("APIFY") or "")
        .strip()
    )


APIFY_TWEET_SCRAPER_ACT = os.environ.get(
    "APIFY_TWEET_SCRAPER_ACT",
    "kaitoeasyapi/twitter-x-data-tweet-scraper-pay-per-result-cheapest"
).replace("/", "~")


def _apify_run_single_search(client, query: str, max_items: int) -> list:
    """Run a single Apify tweet-scraper search and return items."""
    run_input = {
        "searchTerms": [query],
        "sort": "Top",
        "maxItems": max_items,
    }
    logger.info("Apify X search query: %r", query)

    run = client.actor(APIFY_TWEET_SCRAPER_ACT).call(run_input=run_input, wait_secs=120)

    if not run:
        raise RuntimeError("Apify actor run failed to return data")

    status = (run.get("status") or "").upper()
    if status in ("FAILED", "ABORTED", "TIMED-OUT"):
        err = run.get("statusMessage") or status
        raise RuntimeError(f"Apify run did not succeed: {err}")

    dataset_id = run.get("defaultDatasetId")
    if not dataset_id:
        return []

    items_list = client.dataset(dataset_id).list_items(clean=True)
    # Filter out placeholder items like {"noResults": true}
    return [it for it in items_list.items if not it.get("noResults")]


def _apify_run_tweet_scraper_search(search_term_parts: list) -> list:
    """
    Run ``apidojo/tweet-scraper`` via Apify API; return dataset items (raw dicts).
    ``search_term_parts`` become one Twitter search string (joined).

    Strategy:
    1. Extract keywords (stop-word-free) from the user query.
    2. Search with all keywords first.
    3. If zero results, retry with the top 3 keywords for broader matching.
    """
    token = _apify_api_token()
    if not token:
        raise ValueError("Apify API token not configured")
    raw_q = " ".join(p.strip() for p in search_term_parts if (p or "").strip())[:400]
    if not raw_q:
        raise ValueError("Empty search query for X")

    keywords_q = _extract_x_keywords(raw_q)
    if not keywords_q:
        keywords_q = raw_q[:200]

    max_items = min(int(os.environ.get("APIFY_TWEET_MAX_ITEMS", "35")), 100)
    client = ApifyClient(token)

    try:
        # Pass 1: search with extracted keywords
        items = _apify_run_single_search(client, keywords_q, max_items)
        if items:
            logger.info("Apify X search: %d items with query %r", len(items), keywords_q)
            return items

        # Pass 2: retry with top 3 keywords only (broader match)
        top_kw = " ".join(keywords_q.split()[:3])
        if top_kw != keywords_q and len(top_kw.split()) >= 2:
            logger.info("Apify X retry with broader query: %r", top_kw)
            items = _apify_run_single_search(client, top_kw, max_items)
            if items:
                logger.info("Apify X retry: %d items with query %r", len(items), top_kw)
                return items

        logger.info("Apify X search: 0 items after all attempts")
        return []
    except Exception as e:
        logger.error(f"Apify client search failed: {e}")
        raise


def _tweet_record_brief(raw: dict) -> dict:
    """Normalize a tweet-scraper row for display."""
    text = (raw.get("text") or raw.get("fullText") or "").strip()
    if not text and isinstance(raw.get("legacy"), dict):
        text = (raw["legacy"].get("full_text") or "").strip()
    url = (raw.get("url") or raw.get("twitterUrl") or raw.get("link") or "").strip()
    author = ""
    if isinstance(raw.get("author"), dict):
        author = (raw["author"].get("userName") or raw["author"].get("username") or "").strip()
    if not author and isinstance(raw.get("author"), str):
        author = raw["author"].strip()
    if not author and isinstance(raw.get("user"), dict):
        author = (raw["user"].get("username") or raw["user"].get("userName") or "").strip()
    if len(text) > 320:
        text = text[:317] + "..."
    return {"text": text, "url": url, "author": author}


def _format_x_com_search_reply(search_query: str, tweets: list, had_google_news_hits: bool = False) -> str:
    display_q = search_query if len(search_query) <= 200 else search_query[:197] + "..."
    
    if not tweets:
        status_para = ""
        if not had_google_news_hits:
            status_para = (
                "\n\n**STATUS: Fake**\n"
                "This news did not appear in Google News or X.com searches. "
                "Disclaimer: Still, there should be a chance we are wrong."
            )
        else:
            status_para = (
                "\n\n**STATUS: Unverified on X**\n"
                "No complementing posts found on X.com, though headlines were seen on Google News."
            )
            
        status_para_clean = status_para.strip()
        return (
            f"{status_para_clean}\n\n"
            f"Searched **X (Twitter)** via Apify for:\n\"{display_q}\"\n\n"
            "No posts were returned (empty result, blocked topic, or search limits). "
            "Try shorter keywords or check x.com/search directly."
        )

    lines = []
    for i, tw in enumerate(tweets[:12], 1):
        who = f"@{tw['author']} " if tw.get("author") else ""
        snippet = (tw.get("text") or "").replace("\n", " ")
        if len(snippet) > 200:
            snippet = snippet[:197] + "..."
        link = tw.get("url") or ""
        link_str = f" [Link]({link})" if link else ""
        lines.append(f"{i}. {who}{snippet}{link_str}")
    
    block = "\n".join(lines)

    # Semantic analysis on X tweets (convert to headline-like dicts for the engine)
    tweet_as_headlines = [{"title": tw.get("text", "")} for tw in tweets[:12]]
    x_verification = _semantic_verify_claim(search_query, tweet_as_headlines)

    if x_verification["verified"]:
        status_para = (
            "\n\n**STATUS: \u2705 Verified**\n"
            f"Semantic analysis of X posts confirms: {x_verification['reason']}"
        )
    else:
        status_para = (
            "\n\n**STATUS: \u2753 Unverified on X**\n"
            f"Semantic analysis: {x_verification['reason']} "
            "Posts found contain related keywords but may not confirm the specific claim."
        )


def _format_google_news_ask_ai_reply(
    user_question: str, search_query: str, items: list, offer_x_search: bool = False
) -> str:
    """Plain-text answer from Google News RSS only (no OpenAI)."""
    display_q = search_query if len(search_query) <= 200 else search_query[:197] + "..."
    if not items:
        return (
            f"We ran the same Google News RSS search the app uses for articles.\n\n"
            f"**Search used:** \"{display_q}\"\n\n"
            "No headlines were returned (or the feed could not be read). "
            "That often means the topic isn't indexed with those exact words yet, or it's very niche. "
            "Try adding a location, organization name, or year.\n\n"
            "**STATUS: Unverified**\n"
            "No corroboration from Google News in this search \u2014 searching on X.com might yield more info."
        )

    lines = []
    for i, it in enumerate(items[:10], 1):
        src = f" — {it['source']}" if it.get("source") else ""
        link = it.get("link") or ""
        link_str = f" [Article]({link})" if link else ""
        lines.append(f"{i}. {it['title']}{src}{link_str}")
    block = "\n".join(lines)

    # ── Semantic analysis ──
    verification = _semantic_verify_claim(user_question, items)

    if verification["verified"]:
        status_para = (
            "\n\n**STATUS: \u2705 Verified News**\n"
            f"Semantic analysis confirms: {verification['reason']} "
            f"(Confidence: {verification['confidence']})"
        )
    elif verification["confidence"] == "high" and not verification["verified"]:
        status_para = (
            "\n\n**STATUS: \u26a0\ufe0f Likely False / Misleading**\n"
            f"Semantic analysis: {verification['reason']} "
            "Headlines mention the same people/topics but describe a DIFFERENT event. "
            "Disclaimer: There is still a chance we are wrong."
        )
    else:
        status_para = (
            "\n\n**STATUS: \u2753 Unverified**\n"
            f"Semantic analysis: {verification['reason']} "
            "The headlines found don't clearly confirm your specific claim. "
            "Try searching on X.com for more info."
        )

    return (
        f"Using **Google News** (same feed type as “Get Briefing”), we searched:\n\"{display_q}\"\n\n"
        f"**Found {len(items)} headline(s).** Sample:\n\n{block}\n\n"
        "Headlines were analyzed using **semantic verification** to check if they actually "
        "confirm your specific claim (not just keyword overlap)."
        f"{status_para}"
    )


def _google_news_context_block(items: list) -> str:
    if not items:
        return "(Google News RSS returned no items for this query.)"
    parts = []
    for i, it in enumerate(items[:12], 1):
        src = f" [{it.get('source') or '?'}]"
        parts.append(f"{i}. {it['title']}{src}")
    return "Recent Google News RSS headlines:\n" + "\n".join(parts)


def _heuristic_news_reply(user_text: str) -> str:
    """Last resort if Google News RSS and optional OpenAI both fail."""
    return (
        "We couldn’t reach Google News just now. Try again in a moment.\n\n"
        "**Overall:** No automated check ran — verify on a trusted news site if the claim matters."
    )


def _openai_news_reply(
    user_message: str,
    headline: Optional[str],
    summary: Optional[str],
    google_news_block: str,
) -> str:
    api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")
    extra_parts = []
    if headline:
        extra_parts.append("Headline (optional context): " + headline.strip()[:800])
    if summary:
        extra_parts.append("Summary (optional context): " + summary.strip()[:1200])
    extra = ("\n".join(extra_parts) + "\n\n") if extra_parts else ""
    user_block = (
        extra
        + "User question / claim:\n"
        + user_message[:10000]
        + "\n\n---\n"
        + google_news_block
    )
    payload = {
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        "messages": [
            {"role": "system", "content": NEWS_ASSISTANT_SYSTEM},
            {"role": "user", "content": user_block[:12000]},
        ],
        "max_tokens": 700,
        "temperature": 0.45,
    }
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=75,
    )
    if resp.status_code != 200:
        logger.error("OpenAI API error %s: %s", resp.status_code, resp.text[:500])
        raise RuntimeError("AI service returned an error")
    data = resp.json()
    choice = (data.get("choices") or [{}])[0]
    msg = (choice.get("message") or {}).get("content") or ""
    return msg.strip() or "No response from the model."


def _gemini_news_reply(
    user_message: str,
    headline: Optional[str],
    summary: Optional[str],
    google_news_block: str,
) -> str:
    api_key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")

    extra_parts = []
    if headline:
        extra_parts.append("Headline (optional context): " + headline.strip()[:800])
    if summary:
        extra_parts.append("Summary (optional context): " + summary.strip()[:1200])
    extra = ("\n".join(extra_parts) + "\n\n") if extra_parts else ""
    user_block = (
        extra
        + "User question / claim:\n"
        + user_message[:10000]
        + "\n\n---\n"
        + google_news_block
    )

    payload = {
        "system_instruction": {
            "parts": [{"text": NEWS_ASSISTANT_SYSTEM}],
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": user_block[:12000]}],
            }
        ],
        "generationConfig": {
            "temperature": 0.45,
            "maxOutputTokens": 700,
        },
    }
    model = (os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash").strip()
    resp = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=75,
    )
    if resp.status_code != 200:
        logger.error("Gemini API error %s: %s", resp.status_code, resp.text[:500])
        raise RuntimeError("Gemini returned an error")

    data = resp.json()
    for candidate in data.get("candidates") or []:
        content = candidate.get("content") or {}
        parts = content.get("parts") or []
        texts = [part.get("text", "").strip() for part in parts if part.get("text")]
        reply = "\n".join(texts).strip()
        if reply:
            return reply

    logger.error("Gemini API returned no text payload: %s", json.dumps(data)[:500])
    raise RuntimeError("Gemini returned no text")


@app.route("/api/ask-ai", methods=["POST"])
def api_ask_ai():
    """Credibility helper using Google News RSS (same as article feed); optional OpenAI to summarize."""
    ip = get_client_ip()
    if is_rate_limited(ip):
        reset_time = request_counts[ip]["reset_time"]
        retry_after = (reset_time - datetime.now()).total_seconds()
        return jsonify({
            "success": False,
            "error": "Rate limit exceeded",
            "message": "Please wait and try again later.",
            "retry_after": retry_after,
        }), 429

    body = request.get_json(silent=True) or {}
    message = (body.get("message") or "").strip()
    if not message:
        return jsonify({"success": False, "message": "Please type a question or paste the news text."}), 400
    if len(message) > 10000:
        return jsonify({"success": False, "message": "Text is too long. Paste a shorter excerpt (under ~10k characters)."}), 400

    headline = (body.get("headline") or "").strip() or None
    summary = (body.get("summary") or "").strip() or None

    search_on_x = bool(body.get("search_on_x") or body.get("searchOnX"))
    if search_on_x:
        if not _apify_api_token():
            return jsonify({
                "success": False,
                "message": "Apify is not configured. Add APIFY or APIFY_TOKEN to your .env file.",
            }), 400
        try:
            raw_items = _apify_run_tweet_scraper_search([_ask_ai_rss_query(message)])
            briefs = []
            for r in raw_items:
                if isinstance(r, dict):
                    b = _tweet_record_brief(r)
                    if b.get("text"):
                        briefs.append(b)
            sq = _extract_x_keywords(_ask_ai_rss_query(message))
            had_gn = bool(body.get("had_google_news_hits") or body.get("hadGoogleNewsHits"))
            reply = _format_x_com_search_reply(sq, briefs, had_google_news_hits=had_gn)
            return jsonify({
                "success": True,
                "reply": reply,
                "mode": "x_com",
                "tweet_count": len(briefs),
                "headlines": briefs[:5]
            })
        except ValueError as e:
            return jsonify({"success": False, "message": str(e)}), 400
        except Exception as e:
            logger.exception("Apify X search failed")
            return jsonify({
                "success": False,
                "message": "X search could not complete. Try again or shorten your keywords.",
            }), 502

    try:
        search_q = _ask_ai_rss_query(message)
        items = _google_news_rss_items_simple(search_q, limit=15)
        google_block = _google_news_context_block(items)
        apify_ok = bool(_apify_api_token())
        offer_x = apify_ok
        headlines_count = len(items)

        try:
            if (os.environ.get("GEMINI_API_KEY") or "").strip():
                reply = _gemini_news_reply(message, headline, summary, google_block)
                return jsonify({
                    "success": True,
                    "reply": reply,
                    "mode": "google_news+ai",
                    "ai_provider": "gemini",
                    "offer_x_search": offer_x,
                    "headlines_count": headlines_count,
                    "x_search_available": apify_ok,
                    "search_query": search_q,
                    "headlines": items[:5] # Return top 5 headlines
                })
            if (os.environ.get("OPENAI_API_KEY") or "").strip():
                reply = _openai_news_reply(message, headline, summary, google_block)
                return jsonify({
                    "success": True,
                    "reply": reply,
                    "mode": "google_news+ai",
                    "ai_provider": "openai",
                    "offer_x_search": offer_x,
                    "headlines_count": headlines_count,
                    "x_search_available": apify_ok,
                    "search_query": search_q,
                    "headlines": items[:5] # Return top 5 headlines
                })
        except Exception as e:
            logger.warning("AI ask-ai failed, using Google News text only: %s", e)

        if search_q:
            reply = _format_google_news_ask_ai_reply(
                message, search_q, items
            )
            return jsonify({
                "success": True,
                "reply": reply,
                "mode": "google_news",
                "offer_x_search": offer_x,
                "headlines_count": headlines_count,
                "x_search_available": apify_ok,
                "search_query": search_q,
                "headlines": items[:5]
            })

        reply = _heuristic_news_reply(message)
        return jsonify({
            "success": True,
            "reply": reply,
            "mode": "fallback",
            "offer_x_search": False,
        })
    except Exception as e:
        logger.exception("FATAL error in api_ask_ai")
        return jsonify({"success": False, "message": "An internal error occurred. Please try again later."}), 500


@app.route("/api/news", methods=["GET"])
def api_news():
    """API endpoint for fetching news data as JSON"""
    ip = get_client_ip()
    if is_rate_limited(ip):
        reset_time = request_counts[ip]["reset_time"]
        retry_after = (reset_time - datetime.now()).total_seconds()
        return jsonify({
            'success': False,
            'error': 'Rate limit exceeded',
            'message': 'Please wait and try again later.',
            'status_code': 429,
            'retry_after': retry_after
        }), 429

    user_choice = request.args.get("filter", "rf")
    time_range = get_time_range(user_choice)
    city = sanitize_city(request.args.get("city"))
    
    # Clean up expired cache entries
    cleanup_cache()
    
    # Check cache first
    cache_key = f"{user_choice}_{time_range}_{city or ''}"
    if cache_key in news_cache:
        cache_time, cached_data = news_cache[cache_key]
        if (datetime.now() - cache_time).total_seconds() < cache_duration:
            return jsonify({
                'success': True,
                'data': cached_data,
                'cached': True,
                'city': city,
            })
    
    try:
        # Enable image extraction for better user experience
        news_data = asyncio.run(fetch_news(time_range, extract_images=True, city=city))
        
        # Cache the results
        news_cache[cache_key] = (datetime.now(), news_data)
        
        return jsonify({
            'success': True,
            'data': news_data,
            'cached': False,
            'city': city,
        })
    except Exception as e:
        logger.error(f"Error in API news endpoint: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch news',
            'message': str(e)
        }), 500

@app.route("/api/news/with-images", methods=["GET"])
def api_news_with_images():
    """API endpoint for fetching news data with full image extraction"""
    ip = get_client_ip()
    if is_rate_limited(ip):
        reset_time = request_counts[ip]["reset_time"]
        retry_after = (reset_time - datetime.now()).total_seconds()
        return jsonify({
            'success': False,
            'error': 'Rate limit exceeded',
            'message': 'Please wait and try again later.',
            'status_code': 429,
            'retry_after': retry_after
        }), 429

    user_choice = request.args.get("filter", "rf")
    time_range = get_time_range(user_choice)
    city = sanitize_city(request.args.get("city"))
    
    try:
        # Force image extraction for this endpoint
        news_data = asyncio.run(fetch_news(time_range, extract_images=True, city=city))
        
        return jsonify({
            'success': True,
            'data': news_data,
            'cached': False,
            'city': city,
        })
    except Exception as e:
        logger.error(f"Error in API news with images endpoint: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch news with images',
            'message': str(e)
        }), 500

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/results", methods=["GET", "POST"])
def results():
    ip = get_client_ip()
    if is_rate_limited(ip):
        reset_time = request_counts[ip]["reset_time"]
        retry_after = (reset_time - datetime.now()).total_seconds()
        return jsonify({
            'error': 'Rate limit exceeded',
            'message': 'Please wait and try again later. You can check the real-time limit status at /rate_limit_status',
            'status_code': 429,
            'retry_after': retry_after
        }), 429

    user_city = None
    if request.method == "POST":
        user_city = sanitize_city(request.form.get("city"))
        # Check if news_data is passed via AJAX
        news_data_json = request.form.get("news_data")
        if news_data_json:
            try:
                news_data = json.loads(news_data_json)
                user_choice = request.form.get("filter", "rf")
            except json.JSONDecodeError:
                # Fallback to fetching news if JSON parsing fails
                user_choice = request.form.get("filter", "rf")
                time_range = get_time_range(user_choice)
                news_data = asyncio.run(fetch_news(time_range, extract_images=True, city=user_city))
        else:
            # Traditional form submission
            user_choice = request.form.get("filter", "rf")
            time_range = get_time_range(user_choice)
            news_data = asyncio.run(fetch_news(time_range, extract_images=True, city=user_city))
    else:
        # GET request
        user_choice = "rf"
        time_range = get_time_range(user_choice)
        news_data = asyncio.run(fetch_news(time_range, extract_images=True))
    
    return render_template("results.html", news_data=news_data, user_city=user_city)

@app.route("/rate_limit_status")
def rate_limit_status():
    ip = get_client_ip()
    now = datetime.now()
    if ip in request_counts:
        reset_time = request_counts[ip]["reset_time"]
        if now >= reset_time:
            return jsonify({"message": "Rate limit has reset.", "time_remaining": "0 seconds"})
        else:
            time_remaining = reset_time - now
            return jsonify({"time_remaining": str(time_remaining)})
    else:
        return jsonify({"message": "No rate limit for this IP.", "time_remaining": "0 seconds"})
        
@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory('static', 'sitemap.xml')

@app.route('/robots.txt')
def robots():
    return send_from_directory('static', 'robots.txt')

@app.route('/googlef376e0fa7802dd19.html')
def googlverify():
    return send_from_directory('static', 'googlef376e0fa7802dd19.html')

# Admin Routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Simple admin authentication (you should use proper authentication)
        if username == 'geekyfaahad' and password == 'shaw666@?':  # Change these credentials
            session['admin_authenticated'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error='Invalid credentials')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_authenticated', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@require_admin_auth
def admin_dashboard():
    news_sources = get_news_sources()
    last_updated_str = datetime.now().strftime('%B %d, %Y, %I:%M:%S %p')
    return render_template('admin_dashboard.html', news_sources=news_sources, last_updated=last_updated_str)

@app.route('/admin/sources', methods=['GET', 'POST'])
@require_admin_auth
def admin_sources():
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'toggle':
            source_id = request.form.get('source_id')
            enabled = request.form.get('enabled') == 'true'
            
            # If Firestore available, try it; otherwise use local storage
            if db is not None:
                try:
                    db.collection('news_sources').document(source_id).update({'enabled': enabled})
                    return jsonify({'success': True, 'message': 'Source updated successfully'})
                except Exception as e:
                    logger.warning(f"Firestore update failed for toggle, falling back to local: {e}")
            # Local fallback
            if toggle_source_local(source_id, enabled):
                return jsonify({'success': True, 'message': 'Source updated successfully (local)'})
            return jsonify({'success': False, 'message': 'Error updating source'})
        
        elif action == 'add':
            domain = request.form.get('domain')
            name = request.form.get('name')
            
            if not domain or not name:
                return jsonify({'success': False, 'message': 'Domain and name are required'})
            
            if db is not None:
                try:
                    db.collection('news_sources').add({'domain': domain, 'name': name, 'enabled': True})
                    return jsonify({'success': True, 'message': 'Source added successfully'})
                except Exception as e:
                    logger.warning(f"Firestore add failed, falling back to local: {e}")
            if add_source_local(domain, name):
                return jsonify({'success': True, 'message': 'Source added successfully (local)'})
            return jsonify({'success': False, 'message': 'Error adding source (maybe duplicate domain?)'})
        
        elif action == 'delete':
            source_id = request.form.get('source_id')
            
            if db is not None:
                try:
                    db.collection('news_sources').document(source_id).delete()
                    return jsonify({'success': True, 'message': 'Source deleted successfully'})
                except Exception as e:
                    logger.warning(f"Firestore delete failed, falling back to local: {e}")
            if delete_source_local(source_id):
                return jsonify({'success': True, 'message': 'Source deleted successfully (local)'})
            return jsonify({'success': False, 'message': 'Error deleting source'})
    
    news_sources = get_news_sources()
    return render_template('admin_sources.html', news_sources=news_sources)

@app.route('/admin/api/sources', methods=['GET'])
@require_admin_auth
def api_sources():
    news_sources = get_news_sources()
    return jsonify(news_sources)

if __name__ == "__main__":
    # Initialize news sources on startup
    initialize_news_sources()
    app.run(debug=True, port=55100, host='0.0.0.0')
