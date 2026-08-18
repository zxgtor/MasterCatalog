import json
import urllib.request
import re
import csv
import ssl
import time
from urllib.parse import urlparse, urljoin
from html import unescape
from concurrent.futures import ThreadPoolExecutor, as_completed

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
MAX_WORKERS = 30
TIMEOUT = 7

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

KEYWORDS = [
    'product', 'collection', 'item', 'catalog', 'series', 'furniture', 'chair',
    'table', 'light', 'lamp', 'tile', 'bath', 'faucet', 'floor', 'decor', 'rug',
    'sofa', 'cabinet', 'door', 'mirror', 'sink', 'vanity', 'model', 'gallery'
]

EXCLUDE_PATTERNS = [
    'privacy', 'terms', 'cookie', 'login', 'cart', 'account', 'checkout',
    'contact', 'about-us', 'careers', 'blog', 'news', 'press', 'faq', 'help',
    'facebook', 'instagram', 'twitter', 'linkedin', 'youtube', 'pinterest'
]

def clean_text(s):
    if not s:
        return ""
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s)).strip()

def deep_spider_site(manufacturer):
    base_url = manufacturer["base_url"].rstrip("/")
    m_id = manufacturer["id"]
    m_name = manufacturer["name"]
    
    # Skip non-manufacturer domains (like 3dsky model links, sketchup, aliexpress, dam.aareas)
    if any(x in base_url.lower() for x in ['3dsky.org', 'sketchup.com', 'aliexpress.com', 'aareas.com', 'turbosquid.com']):
        return m_name, []

    visited = set()
    to_visit = [base_url]
    products = []
    
    domain = urlparse(base_url).netloc

    while to_visit and len(visited) < 8 and len(products) < 60:
        curr_url = to_visit.pop(0)
        if curr_url in visited:
            continue
        visited.add(curr_url)
        
        try:
            req = urllib.request.Request(curr_url, headers={'User-Agent': USER_AGENT})
            with urllib.request.urlopen(req, context=ctx, timeout=TIMEOUT) as resp:
                if resp.getcode() != 200:
                    continue
                html = resp.read().decode('utf-8', errors='ignore')
        except:
            continue

        # 1. Discover more internal links
        for a_href in re.findall(r'<a[^>]+href=["\']([^"\']+)["\']', html, re.I):
            if a_href.startswith('#') or a_href.startswith('javascript:') or a_href.startswith('mailto:'):
                continue
            full_u = urljoin(base_url, a_href).split('?')[0].split('#')[0].rstrip('/')
            parsed_u = urlparse(full_u)
            
            if parsed_u.netloc == domain and full_u not in visited and full_u not in to_visit:
                path_l = parsed_u.path.lower()
                if any(k in path_l for k in KEYWORDS) and not any(ex in path_l for ex in EXCLUDE_PATTERNS):
                    to_visit.append(full_u)

        # 2. Check if current page is a single product page (OpenGraph / Title / Image)
        og_type = re.search(r'<meta\s+property=["\']og:type["\']\s+content=["\']([^"\']+)["\']', html, re.I)
        og_title = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']*)["\']', html, re.I)
        og_img = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']*)["\']', html, re.I)
        og_desc = re.search(r'<meta\s+property=["\']og:description["\']\s+content=["\']([^"\']*)["\']', html, re.I)

        if og_title and og_img:
            p_title = clean_text(unescape(og_title.group(1)))
            p_image = urljoin(base_url, og_img.group(1).strip())
            p_desc = clean_text(unescape(og_desc.group(1))) if og_desc else ""
            
            if len(p_title) > 2 and not any(ex in p_title.lower() for ex in ['home', 'welcome', 'login', 'cart', 'error', 'page not found', '404', 'cookies']):
                # Verify image is valid
                if p_image.startswith('http') and not any(x in p_image.lower() for x in ['logo', 'icon', 'arrow', 'banner', 'favicon', 'pixel']):
                    prod_id = f"mfg-{m_id}-{re.sub(r'[^a-zA-Z0-9]', '', p_title)[:30]}"
                    products.append({
                        "id": prod_id,
                        "manufacturer_id": m_id,
                        "manufacturer_name": m_name,
                        "name": p_title,
                        "collection": m_name,
                        "category": "Products",
                        "sku": "",
                        "price": "",
                        "nominal_size": "",
                        "finish": "",
                        "primary_image": p_image,
                        "images": [p_image],
                        "image_count": 1,
                        "description": p_desc or f"{p_title} by {m_name}",
                        "url": curr_url
                    })

        # 3. Extract Grid/List items on this page
        # Find images with alt text or adjacent headings
        img_tags = re.findall(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*alt=["\']([^"\']+)["\']', html, re.I)
        img_tags += re.findall(r'<img[^>]+alt=["\']([^"\']+)["\'][^>]*src=["\']([^"\']+)["\']', html, re.I)
        
        for item in img_tags:
            src, alt = (item[0], item[1]) if item[0].startswith('http') or '/' in item[0] else (item[1], item[0])
            alt_clean = clean_text(alt)
            img_clean = urljoin(base_url, src)
            
            if len(alt_clean) > 3 and len(alt_clean) < 60 and not any(ex in alt_clean.lower() for ex in EXCLUDE_PATTERNS + ['logo', 'banner', 'icon', 'header', 'footer', 'slide', 'image', 'photo', 'daltile']):
                if img_clean.startswith('http') and not any(x in img_clean.lower() for x in ['logo', 'icon', 'arrow', 'banner', 'favicon', 'pixel', 'sprite']):
                    prod_id = f"mfg-{m_id}-{re.sub(r'[^a-zA-Z0-9]', '', alt_clean)[:30]}"
                    if not any(p["id"] == prod_id for p in products):
                        products.append({
                            "id": prod_id,
                            "manufacturer_id": m_id,
                            "manufacturer_name": m_name,
                            "name": alt_clean,
                            "collection": m_name,
                            "category": "Products",
                            "sku": "",
                            "price": "",
                            "nominal_size": "",
                            "finish": "",
                            "primary_image": img_clean,
                            "images": [img_clean],
                            "image_count": 1,
                            "description": f"{alt_clean} by {m_name}",
                            "url": curr_url
                        })

    return m_name, products

def main():
    start_time = time.time()
    matrix_path = r"d:\Aareas\manufacturer_feed_matrix.json"
    with open(matrix_path, "r", encoding="utf-8") as f:
        matrix = json.load(f)

    # Load master products
    master_json_path = r"d:\Aareas\master_products.json"
    with open(master_json_path, "r", encoding="utf-8") as f:
        all_products = json.load(f)

    scraped_brands = set(p.get("manufacturer_name") for p in all_products)
    unscraped_sites = [m for m in matrix if m["name"] not in scraped_brands and m.get("accessible", False)]
    print(f"Deep spidering {len(unscraped_sites)} remaining accessible manufacturer websites...")

    existing_urls = {p.get("url") for p in all_products if p.get("url")}
    new_products = 0
    brands_added = 0
    completed = 0
    total = len(unscraped_sites)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_m = {executor.submit(deep_spider_site, m): m for m in unscraped_sites}
        
        for future in as_completed(future_to_m):
            completed += 1
            m_name, prods = future.result()
            added_this = 0
            for p in prods:
                if p["url"] not in existing_urls:
                    existing_urls.add(p["url"])
                    all_products.append(p)
                    new_products += 1
                    added_this += 1
                    
            if added_this > 0:
                brands_added += 1

            if completed % 25 == 0 or completed == total:
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                print(f"Progress: {completed}/{total} ({(completed/total)*100:.1f}%) | New Products: {new_products:,} | New Brands: {brands_added} | Speed: {rate:.1f} sites/sec")

    # Sort master catalog
    all_products.sort(key=lambda x: (x.get("manufacturer_name", ""), x.get("name", "")))

    # Save to JSON
    with open(master_json_path, "w", encoding="utf-8") as f:
        json.dump(all_products, f, indent=2, ensure_ascii=False)
    print(f"\nSaved updated Master JSON to: {master_json_path} ({len(all_products):,} total products)")

    # Save to CSV
    master_csv_path = r"d:\Aareas\master_products.csv"
    fieldnames = [
        "id", "manufacturer_id", "manufacturer_name", "name", "collection",
        "category", "sku", "price", "nominal_size", "finish",
        "primary_image", "image_count", "url", "description"
    ]
    with open(master_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for p in all_products:
            writer.writerow(p)
    print(f"Saved updated Master CSV to: {master_csv_path}")

    # Rebuild Master HTML Portal
    print("\nRebuilding master_catalog.html...")
    import subprocess
    subprocess.run(["python", r"d:\Aareas\generate_master_catalog.py"], check=True)
    print(f"Complete! Master Catalog now has {len(all_products):,} products across all brands in {time.time()-start_time:.1f}s.")

if __name__ == "__main__":
    main()
