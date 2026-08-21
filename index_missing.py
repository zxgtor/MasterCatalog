"""Index manufacturers that have a URL but zero products. Sitemap + Shopify first."""
import json
import re
import ssl
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

from concurrent.futures import ThreadPoolExecutor, as_completed

from categorize import assign_category
from crawl_all_manufacturers import fetch_shopify_products
from crawl_custom_html_manufacturers import crawl_html_site
from db import connect, insert_product

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
NS = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "img": "http://www.google.com/schemas/sitemap-image/1.1",
}
SKIP_PATH = re.compile(
    r"/blog|/news|/about|/contact|/cart|/account|/login|/privacy|/terms|"
    r"/faq|/careers|/press|/search",
    re.I,
)
PRODUCT_HINT = re.compile(
    r"/products?/|/items?/|/collections?/|/catalog/|/shop/|/detail/|"
    r"/tiles?/|/flooring/|/surfaces?/|/faucets?/|/fixtures?/",
    re.I,
)

ROOT = Path(__file__).resolve().parent
SKIP = (
    "3dsky.org", "sketchup.com", "3dwarehouse", "aliexpress.com", "etsy.com",
    "aareas.com", "turbosquid.com", "facebook.com", "instagram.com",
)
MAX_SITEMAP = 150
MAX_SHOPIFY = 250
MAX_HTML = 60
WORKERS = 10


def targets(conn):
    have = {r[0] for r in conn.execute("SELECT DISTINCT manufacturer_id FROM products")}
    matrix = json.loads((ROOT / "manufacturer_feed_matrix.json").read_text(encoding="utf-8"))
    mx = {m.get("id"): m for m in matrix}
    out = []
    for row in conn.execute("SELECT id, name, url FROM manufacturers ORDER BY name"):
        if row["id"] in have:
            continue
        url = row["url"] or ""
        if any(s in url.lower() for s in SKIP):
            continue
        info = mx.get(row["id"]) or {}
        ft = info.get("feed_type") or "html_site"
        out.append({
            "id": row["id"],
            "name": row["name"],
            "url": url,
            "base_url": (info.get("base_url") or url).rstrip("/"),
            "feed_type": ft,
        })
    return out


def uniquify(conn, products):
    seen = {r[0] for r in conn.execute("SELECT id FROM products")}
    out = []
    for p in products:
        pid = str(p.get("id") or "")
        if not pid:
            continue
        if pid in seen:
            n = 2
            while f"{pid}-{n}" in seen:
                n += 1
            pid = f"{pid}-{n}"
        seen.add(pid)
        p = dict(p)
        p["id"] = pid
        p["raw_category"] = p.get("raw_category") or p.get("category") or ""
        p["category"] = assign_category(p)
        out.append(p)
    return out


def _fetch_xml(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, context=CTX, timeout=12) as resp:
        return ET.fromstring(resp.read())


def sitemap_products(m):
    base = m["base_url"]
    queue = [
        f"{base}/sitemap.xml",
        f"{base}/sitemap_index.xml",
        f"{base}/product-sitemap.xml",
        f"{base}/sitemap_products_1.xml",
    ]
    seen_maps, products, seen_urls = set(), [], set()
    while queue and len(products) < MAX_SITEMAP:
        sm_url = queue.pop(0)
        if sm_url in seen_maps:
            continue
        seen_maps.add(sm_url)
        try:
            root = _fetch_xml(sm_url)
        except Exception:
            continue
        for loc in root.findall(".//sm:sitemap/sm:loc", NS):
            if loc.text and loc.text.strip() not in seen_maps and len(queue) < 20:
                queue.append(loc.text.strip())
        for node in root.findall(".//sm:url", NS):
            loc = node.find("sm:loc", NS)
            if loc is None or not loc.text:
                continue
            page = loc.text.strip()
            path = urlparse(page).path
            if SKIP_PATH.search(path):
                continue
            if not (PRODUCT_HINT.search(path) or path.strip("/").count("/") >= 1):
                continue
            if page in seen_urls:
                continue
            seen_urls.add(page)
            images = []
            for img in node.findall(".//img:image/img:loc", NS):
                if img.text:
                    images.append(img.text.strip())
            slug = path.strip("/").split("/")[-1].replace("-", " ").replace("_", " ")
            if not slug or len(slug) < 2:
                slug = "Product"
            parts = path.strip("/").split("/")
            raw_cat = parts[0].replace("-", " ").title() if len(parts) > 1 else "Products"
            products.append({
                "id": f"mfg-{m['id']}-{re.sub(r'[^a-zA-Z0-9]', '', path)[:40]}",
                "manufacturer_id": m["id"],
                "manufacturer_name": m["name"],
                "name": slug.title(),
                "collection": m["name"],
                "category": raw_cat,
                "raw_category": raw_cat,
                "sku": "",
                "price": "",
                "primary_image": images[0] if images else "",
                "images": images,
                "image_count": len(images),
                "description": f"{slug.title()} by {m['name']}",
                "url": page,
            })
            if len(products) >= MAX_SITEMAP:
                break
    return products


def crawl_one(m):
    prods = []
    source = m.get("feed_type") or "html_site"
    if source == "shopify" or True:
        try:
            prods = fetch_shopify_products(m)[:MAX_SHOPIFY]
            if prods:
                return m, prods, "shopify"
        except Exception:
            prods = []
    try:
        prods = sitemap_products(m)
        if prods:
            return m, prods, "sitemap"
    except Exception:
        prods = []
    try:
        _name, prods = crawl_html_site(m)
        prods = (prods or [])[:MAX_HTML]
        if prods:
            return m, prods, "html"
    except Exception:
        prods = []
    return m, [], source


def main():
    conn = connect()
    todo = targets(conn)
    print(f"manufacturers still empty (excl. junk hosts): {len(todo)}")
    added_brands = 0
    added_products = 0
    empty = 0
    done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(crawl_one, m): m for m in todo}
        for fut in as_completed(futs):
            done += 1
            try:
                m, prods, source = fut.result()
            except Exception as e:
                m = futs[fut]
                print(f"[{done}/{len(todo)}] FAIL {m['name']}: {type(e).__name__}")
                empty += 1
                continue
            prods = uniquify(conn, prods)
            for p in prods:
                insert_product(conn, p)
            conn.commit()
            if prods:
                added_brands += 1
                added_products += len(prods)
                print(f"[{done}/{len(todo)}] {m['name']}: +{len(prods)} ({source})")
            else:
                empty += 1
                if done % 20 == 0 or done == len(todo):
                    print(f"[{done}/{len(todo)}] empty so far={empty} added_brands={added_brands}")
    still = conn.execute(
        """SELECT COUNT(*) FROM manufacturers m
           WHERE NOT EXISTS (SELECT 1 FROM products p WHERE p.manufacturer_id=m.id)"""
    ).fetchone()[0]
    print(f"done brands={added_brands} products={added_products} empty={empty}")
    print(f"manufacturers still without products: {still}")


if __name__ == "__main__":
    main()
