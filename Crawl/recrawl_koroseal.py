"""Replace Koroseal sitemap stubs with real product pages + Akeneo images."""
import csv
import json
import re
import ssl
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(r"d:\Aareas")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
MAX_PRODUCTS = 300
WORKERS = 16

SKIP_PATH = re.compile(
    r"archived|faq|_archived|/about|/login|/checkout|/search-results|"
    r"page-not-found|/brand/?$|/valueprogram|/in-stock",
    re.I,
)
SKIP_IMG = re.compile(
    r"logo|icon|favicon|sprite|\.pdf|document|fact_sheet|hanging|"
    r"leed|hpd|epd|warranty|instruction|getmedia",
    re.I,
)


def fetch(url, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, context=CTX, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def sitemap_product_urls():
    xml = fetch("https://koroseal.com/sitemap.xml", timeout=40)
    locs = re.findall(r"<loc>(.*?)</loc>", xml)
    out = []
    seen = set()
    for loc in locs:
        path = urlparse(loc).path.lower()
        if "/products/" not in path:
            continue
        if SKIP_PATH.search(path):
            continue
        if loc in seen:
            continue
        seen.add(loc)
        out.append(loc)
    # Prefer shorter collection pages, then colorways
    out.sort(key=lambda u: (urlparse(u).path.count("/"), len(u)))
    return out


def extract_images(html, page_url):
    found = []
    patterns = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image',
        r'https?://koroseal\.asset\.akeneo\.cloud/[^"\'\s<>]+',
        r'<img[^>]+src=["\']([^"\']+)',
    ]
    for pat in patterns:
        for m in re.findall(pat, html, re.I):
            u = unescape(m.strip())
            if u.startswith("//"):
                u = "https:" + u
            elif u.startswith("/"):
                u = urljoin(page_url, u)
            if not u.startswith("http"):
                continue
            if SKIP_IMG.search(u):
                continue
            low = u.lower()
            if not any(x in low for x in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", "akeneo.cloud")):
                continue
            if u not in found:
                found.append(u)
    # Prefer product media over tiny thumbs
    found.sort(key=lambda u: (0 if "/images/media/" in u or "/thumbnails/media/" in u else 1, u))
    return found


def parse_product(url):
    html = fetch(url)
    images = extract_images(html, url)
    if not images:
        return None

    parts = [p for p in urlparse(url).path.strip("/").split("/") if p]
    name = unescape(parts[-1]).replace("-", " ").replace("_", " ").replace(",", "").title()
    title_m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.I | re.S)
    if title_m:
        t = re.sub(r"<[^>]+>", " ", title_m.group(1))
        t = re.sub(r"\s+", " ", unescape(t)).strip()
        if t:
            name = t
    h2_m = re.search(r"<h2[^>]*>(.*?)</h2>", html, re.I | re.S)
    color = ""
    if h2_m:
        color = re.sub(r"<[^>]+>", " ", h2_m.group(1))
        color = re.sub(r"\s+", " ", unescape(color)).strip()
        if color and color.lower() not in name.lower():
            name = f"{name} {color}"

    cat = parts[1].replace("-", " ").title() if len(parts) > 1 else "Products"
    sku_m = re.search(r"\b([A-Z]{2,}\d{2}(?:-\d{2})?)\b", html)
    sku = sku_m.group(1) if sku_m else ""

    from categorize import assign_category
    prod = {
        "id": "mfg-503-" + re.sub(r"[^a-zA-Z0-9]", "", urlparse(url).path)[:48],
        "manufacturer_id": 503,
        "manufacturer_name": "Koroseal",
        "name": name[:160],
        "collection": parts[2].replace("-", " ").title() if len(parts) > 2 else "Koroseal",
        "category": cat,
        "raw_category": cat,
        "sku": sku,
        "price": "",
        "nominal_size": "",
        "finish": color,
        "primary_image": images[0],
        "images": images[:8],
        "image_count": min(len(images), 8),
        "description": f"{name} by Koroseal",
        "url": url,
    }
    prod["category"] = assign_category(prod)
    return prod


def main():
    urls = sitemap_product_urls()
    print(f"Product URLs after filter: {len(urls)}")

    products = []
    seen_img = set()
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(parse_product, u): u for u in urls[:1200]}
        for fut in as_completed(futs):
            try:
                p = fut.result()
            except Exception:
                continue
            if not p:
                continue
            key = p["primary_image"]
            if key in seen_img:
                continue
            seen_img.add(key)
            products.append(p)
            if len(products) >= MAX_PRODUCTS:
                break

    products.sort(key=lambda x: (x["category"], x["name"]))
    print(f"Kept {len(products)} Koroseal products with images")
    if products:
        print(" sample:", products[0]["name"], products[0]["primary_image"][:90])

    master_path = ROOT / "master_products.json"
    master = json.loads(master_path.read_text(encoding="utf-8"))
    before = len(master)
    master = [p for p in master if (p.get("manufacturer_name") or "") != "Koroseal"]
    master.extend(products)
    master.sort(key=lambda x: (x.get("manufacturer_name") or "", x.get("name") or ""))
    master_path.write_text(json.dumps(master, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"master_products.json {before} -> {len(master)}")

    csv_path = ROOT / "master_products.csv"
    fields = [
        "id", "manufacturer_id", "manufacturer_name", "name", "collection",
        "category", "sku", "price", "nominal_size", "finish",
        "primary_image", "image_count", "url", "description",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(master)
    print("CSV updated")


if __name__ == "__main__":
    main()
