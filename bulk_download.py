"""
Bulk Past Paper Downloader — ilmkidunya.com
=============================================
Ye script listing page se saare individual paper pages dhoondti hai,
har page khol kar full-size ("large") image ka URL nikalti hai,
aur seedha wahi asal image download karti hai (chhoti thumbnail nahi).

Requirements (install once):
    pip install requests beautifulsoup4

Usage:
    python bulk_download.py

Configure the CONFIG list below with your listing page URLs and
matching output folders before running.
"""

import os
import re
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Missing packages. Run: pip install requests beautifulsoup4")
    sys.exit(1)

# -----------------------------------------------------------------------
# Medium rule:
#   - For Pak Studies / Islamiat: keep Urdu-medium papers.
#   - For everything else: keep English-medium papers (skip Urdu ones).
# Detected automatically from the output_folder name below — no need to
# edit CONFIG.
# -----------------------------------------------------------------------
URDU_SUBJECT_KEYWORDS = ("islamiat", "pakistan-studies")

# How many papers to download at once, per subject. Higher = faster, but too
# high risks tripping the site's rate limiting / more timeouts. 5 is a safe,
# noticeably faster middle ground vs one-at-a-time.
MAX_WORKERS = 5

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

# Reuse a single session (connection pooling + keep-alive) instead of opening
# a brand new TCP/TLS connection on every request. Some listing pages (e.g.
# Chemistry, Mathematics) are heavy with ads/banners and are much more
# reliable over a warm, reused connection than a fresh one each time.
SESSION = requests.Session()
SESSION.headers.update(HEADERS)
_adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10, max_retries=0)
SESSION.mount("https://", _adapter)
SESSION.mount("http://", _adapter)

# -----------------------------------------------------------------------
# CONFIG: (listing_page_url, output_folder) pairs.
# Add/remove/edit rows here to match the subjects & grades you need.
# If a listing page URL 404s, double check the exact URL in your browser
# and fix it here.
# -----------------------------------------------------------------------
CONFIG = [
    # ---- Grade 9 ----
    ("https://www.ilmkidunya.com/past_papers/lahore-board-9th-physics.aspx", "data/past_papers/class_9/physics"),
    ("https://www.ilmkidunya.com/past_papers/lahore-board-9th-chemistry.aspx", "data/past_papers/class_9/chemistry"),
    ("https://www.ilmkidunya.com/past_papers/lahore-board-9th-mathematics.aspx", "data/past_papers/class_9/mathematics"),
    ("https://www.ilmkidunya.com/past_papers/lahore-board-9th-biology.aspx", "data/past_papers/class_9/biology"),
    ("https://www.ilmkidunya.com/past_papers/lahore-board-9th-computer-science.aspx", "data/past_papers/class_9/computer-science"),
    ("https://www.ilmkidunya.com/past_papers/lahore-board-9th-english.aspx", "data/past_papers/class_9/english"),
    ("https://www.ilmkidunya.com/past_papers/lahore-board-9th-urdu.aspx", "data/past_papers/class_9/urdu"),
    ("https://www.ilmkidunya.com/past_papers/lahore-board-9th-islamiat.aspx", "data/past_papers/class_9/islamiat"),
    ("https://www.ilmkidunya.com/past_papers/lahore-board-9th-pak-studies.aspx", "data/past_papers/class_9/pakistan-studies"),

    # ---- Grade 10 ----
    ("https://www.ilmkidunya.com/past_papers/lahore-board-10th-physics.aspx", "data/past_papers/class_10/physics"),
    ("https://www.ilmkidunya.com/past_papers/lahore-board-10th-chemistry.aspx", "data/past_papers/class_10/chemistry"),
    ("https://www.ilmkidunya.com/past_papers/lahore-board-10th-mathematics.aspx", "data/past_papers/class_10/mathematics"),
    ("https://www.ilmkidunya.com/past_papers/lahore-board-10th-biology.aspx", "data/past_papers/class_10/biology"),
    ("https://www.ilmkidunya.com/past_papers/lahore-board-10th-computer-science.aspx", "data/past_papers/class_10/computer-science"),
    ("https://www.ilmkidunya.com/past_papers/lahore-board-10th-english.aspx", "data/past_papers/class_10/english"),
    ("https://www.ilmkidunya.com/past_papers/lahore-board-10th-urdu.aspx", "data/past_papers/class_10/urdu"),
    ("https://www.ilmkidunya.com/past_papers/lahore-board-10th-islamiat.aspx", "data/past_papers/class_10/islamiat"),
    ("https://www.ilmkidunya.com/past_papers/lahore-board-10th-pak-studies.aspx", "data/past_papers/class_10/pakistan-studies"),

    # ---- Grade 11 (1st Year / FSc-ICS Part 1) ----
    ("https://www.ilmkidunya.com/past_papers/lahore-board-11th-physics.aspx", "data/past_papers/class_11/physics"),
    ("https://www.ilmkidunya.com/past_papers/lahore-board-11th-chemistry.aspx", "data/past_papers/class_11/chemistry"),
    ("https://www.ilmkidunya.com/past_papers/lahore-board-11th-mathematics.aspx", "data/past_papers/class_11/mathematics"),
    ("https://www.ilmkidunya.com/past_papers/lahore-board-11th-biology.aspx", "data/past_papers/class_11/biology"),
    ("https://www.ilmkidunya.com/past_papers/lahore-board-11th-computer-science.aspx", "data/past_papers/class_11/computer-science"),
    ("https://www.ilmkidunya.com/past_papers/lahore-board-11th-english.aspx", "data/past_papers/class_11/english"),
    ("https://www.ilmkidunya.com/past_papers/lahore-board-11th-urdu.aspx", "data/past_papers/class_11/urdu"),
    ("https://www.ilmkidunya.com/past_papers/lahore-board-11th-islamiat.aspx", "data/past_papers/class_11/islamiat"),

    # ---- Grade 12 (2nd Year / FSc-ICS Part 2) ----
    ("https://www.ilmkidunya.com/past_papers/lahore-board-12th-physics.aspx", "data/past_papers/class_12/physics"),
    ("https://www.ilmkidunya.com/past_papers/lahore-board-12th-chemistry.aspx", "data/past_papers/class_12/chemistry"),
    ("https://www.ilmkidunya.com/past_papers/lahore-board-12th-mathematics.aspx", "data/past_papers/class_12/mathematics"),
    ("https://www.ilmkidunya.com/past_papers/lahore-board-12th-biology.aspx", "data/past_papers/class_12/biology"),
    ("https://www.ilmkidunya.com/past_papers/lahore-board-12th-computer-science.aspx", "data/past_papers/class_12/computer-science"),
    ("https://www.ilmkidunya.com/past_papers/lahore-board-12th-english.aspx", "data/past_papers/class_12/english"),
    ("https://www.ilmkidunya.com/past_papers/lahore-board-12th-urdu.aspx", "data/past_papers/class_12/urdu"),
    ("https://www.ilmkidunya.com/past_papers/lahore-board-12th-pak-studies.aspx", "data/past_papers/class_12/pakistan-studies"),
]

# Regex for individual paper detail page links on a listing page.
# Matches both absolute (https://www.ilmkidunya.com/...) and relative (/past_papers/...) hrefs.
DETAIL_LINK_RE = re.compile(
    r'(?:https?://(?:www\.)?ilmkidunya\.com)?/past_papers/past-papers?-[^"\'<>\s]+?-\d+\.aspx',
    re.IGNORECASE,
)

# Regex for the full-size ("large") image URL on a detail page.
# NOTE: newer (2024/2025) papers have literal spaces in the filename
# (e.g. ".../Past Paper 2024 ... Subjective.jpg"), so we must NOT exclude
# whitespace from the match — only quotes/angle-brackets/newlines, which
# mark the real end of the HTML attribute value.
LARGE_IMG_RE = re.compile(
    r'https://pastpapers\.ilmkidunya\.com/past_papers/Images/[^"\'<>\r\n]+?/large/[^"\'<>\r\n]+?\.(?:jpg|jpeg|png)',
    re.IGNORECASE,
)

# Fallback: any past-paper image on the CDN, even if it's not under a
# "/large/" folder. Some subjects/pages (e.g. certain Chemistry papers)
# serve the full image without that folder segment. We prefer the
# LARGE_IMG_RE match when available and only fall back to this.
ANY_IMG_RE = re.compile(
    r'https://pastpapers\.ilmkidunya\.com/past_papers/Images/[^"\'<>\r\n]+?\.(?:jpg|jpeg|png)',
    re.IGNORECASE,
)


def fetch_with_retry(url: str, max_retries: int = 5, timeout: int = 60):
    """GET a URL with retries and exponential backoff for temporary network issues."""
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = SESSION.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt < max_retries:
                wait = 3 * attempt
                print(f"    (retry {attempt}/{max_retries} in {wait}s: {e})")
                time.sleep(wait)
    raise last_error


def get_detail_links(listing_url: str, want_urdu: bool) -> list:
    """Fetch a listing page and return matching individual paper page URLs (absolute).

    If want_urdu is True, keep only links whose slug mentions "urdu"
    (Urdu-medium papers). If False, keep only links that do NOT mention
    "urdu" (English-medium / unmarked papers, which are English by default
    on ilmkidunya's compulsory-subject listing pages).
    """
    resp = fetch_with_retry(listing_url)
    raw_links = set(DETAIL_LINK_RE.findall(resp.text))
    # Resolve any relative links (e.g. "/past_papers/...") to absolute URLs
    absolute_links = sorted(urljoin(listing_url, link) for link in raw_links)

    if want_urdu:
        return [link for link in absolute_links if "urdu" in link.lower()]
    return [link for link in absolute_links if "urdu" not in link.lower()]


def get_large_image_url(detail_url: str) -> str | None:
    """Fetch a paper detail page and return the full-size image URL, if found."""
    resp = fetch_with_retry(detail_url)

    match = LARGE_IMG_RE.search(resp.text)
    if match:
        return match.group(0)

    # Fallback: try any CDN image on the page (thumbnail-sized folders
    # excluded where possible by preferring the LAST match, which tends
    # to be the higher-res one when multiple appear).
    fallback_matches = ANY_IMG_RE.findall(resp.text)
    if fallback_matches:
        return fallback_matches[-1]

    # Nothing found at all — print a bit of diagnostic info so it's easy
    # to see *why* (page blocked/redirected/changed layout, etc).
    print(f"    DEBUG: status={resp.status_code}, page length={len(resp.text)} chars, "
          f"final url={resp.url}")
    return None


def download_image(image_url: str, output_folder: str) -> str:
    """Download an image to output_folder, keeping its original filename."""
    os.makedirs(output_folder, exist_ok=True)
    filename = image_url.rsplit("/", 1)[-1]
    filepath = os.path.join(output_folder, filename)

    if os.path.exists(filepath) and os.path.getsize(filepath) > 20_000:
        return f"SKIPPED (already downloaded): {filename}"

    # Some newer image URLs contain literal (unencoded) spaces, which HTTP
    # requests can't send as-is — encode them before making the request.
    safe_url = image_url.replace(" ", "%20")
    resp = fetch_with_retry(safe_url)
    with open(filepath, "wb") as f:
        f.write(resp.content)

    size_kb = len(resp.content) / 1024
    return f"OK ({size_kb:.0f} KB): {filename}"


def process_listing(listing_url: str, output_folder: str) -> bool:
    """Returns True if the listing page was fetched successfully, False if it
    failed outright (e.g. repeated timeouts) so the caller can report it."""
    folder_lower = output_folder.lower().rstrip("/")
    is_urdu_subject = folder_lower.endswith("/urdu") or folder_lower.endswith("\\urdu")
    want_urdu = is_urdu_subject or any(kw in folder_lower for kw in URDU_SUBJECT_KEYWORDS)
    medium_label = "Urdu medium" if want_urdu else "English medium"
    print(f"\n=== {listing_url}  [{medium_label}] ===")
    try:
        detail_links = get_detail_links(listing_url, want_urdu)
    except Exception as e:
        print(f"  ERROR fetching listing page: {e}")
        return False

    print(f"  Found {len(detail_links)} paper pages.")

    def handle_one(i_url):
        i, detail_url = i_url
        try:
            img_url = get_large_image_url(detail_url)
            if not img_url:
                return f"  [{i}/{len(detail_links)}] No large image found: {detail_url}"
            result = download_image(img_url, output_folder)
            return f"  [{i}/{len(detail_links)}] {result}"
        except Exception as e:
            return f"  [{i}/{len(detail_links)}] ERROR on {detail_url}: {e}"

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(handle_one, (i, url)) for i, url in enumerate(detail_links, 1)]
        for future in as_completed(futures):
            print(future.result())

    return True


if __name__ == "__main__":
    failed = []
    for listing_url, output_folder in CONFIG:
        ok = process_listing(listing_url, output_folder)
        if not ok:
            failed.append(listing_url)
        time.sleep(2)  # pause between subjects so the server doesn't rate-limit us

    print("\nAll done! Check the folders under data/past_papers/ for downloaded images.")
    if failed:
        print(f"\n{len(failed)} listing page(s) FAILED (likely timeouts) — just re-run the")
        print("script and these will be retried; everything already downloaded is skipped:")
        for url in failed:
            print(f"  - {url}")