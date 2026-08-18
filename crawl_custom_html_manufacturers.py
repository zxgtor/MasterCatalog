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
TIMEOUT = 8

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

CATALOG_KEYWORDS = [
    'products', 'collection', 'catalog', 'catalogue', 'shop', 'gallery', 
    'furniture', 'lighting', 'tile', 'flooring', 'doors', 'appliances', 'portfolio'
]

def clean_html_text(s):
    if not s:
        return ""
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s)).strip()

def crawl_html_site(manufacturer):
    base_url = manufacturer["base_url"].rstrip("/")
    m_id = manufacturer["id"]
    m_name = manufacturer["name"]
    
    extracted_products = []
    
    # 1. Fetch homepage
    try:
        req = urllib.request.Request(base_url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, context=ctx, timeout=TIMEOUT) as resp:
            if resp.getcode() != 200:
                return m_name, []
            html = resp.read().decode('utf-8', errors='ignore')
    except:
        return m_name, []

    # 2. Find product / catalog links on the homepage
    links = re.findall(r'<a[^>]+href=["\']([^"\']+)["\']', html, re.I)
    target_urls = set()
    
    for l in links:
        if l.startswith('#') or l.startswith('javascript:') or l.startswith('mailto:') or l.startswith('tel:'):
            continue
        full_url = urljoin(base_url, l).split('?')[0].split('#')[0]
        parsed = urlparse(full_url)
        if parsed.netloc == urlparse(base_url).netloc:
            path_lower = parsed.path.lower()
            if any(k in path_lower for k in CATALOG_KEYWORDS) and path_lower != '/':
                target_urls.add(full_url)

    # If no catalog subpages found, search homepage for product items directly
    pages_to_scan = list(target_urls)[:4]
    if not pages_to_scan:
        pages_to_scan = [base_url]

    # Scan pages for product cards
    for p_url in pages_to_scan:
        try:
            req = urllib.request.Request(p_url, headers={'User-Agent': USER_AGENT})
            with urllib.request.urlopen(req, context=ctx, timeout=TIMEOUT) as resp:
                if resp.getcode() != 200:
                    continue
                p_html = resp.read().decode('utf-8', errors='ignore')
                
                # Check for Schema.org JSON-LD Products
                json_lds = re.findall(r'<script type=["\']application/ld\+json["\']>(.*?)</script>', p_html, re.DOTALL | re.I)
                for jld in json_lds:
                    try:
                        data = json.loads(jld)
                        items = []
                        if isinstance(data, dict):
                            if data.get("@type") == "Product":
                                items = [data]
                            elif "itemListElement" in data:
                                items = data["itemListElement"]
                        elif isinstance(data, list):
                            items = [x for x in data if isinstance(x, dict) and x.get("@type") == "Product"]
                            
                        for item in items:
                            p_name = item.get("name")
                            if p_name:
                                p_img = item.get("image")
                                if isinstance(p_img, list):
                                    p_img = p_img[0] if p_img else ""
                                elif isinstance(p_img, dict):
                                    p_img = p_img.get("url", "")
                                    
                                extracted_products.append({
                                    "id": f"mfg-{m_id}-{re.sub(r'[^a-zA-Z0-9]', '', p_name)[:30]}",
                                    "manufacturer_id": m_id,
                                    "manufacturer_name": m_name,
                                    "name": p_name,
                                    "collection": m_name,
                                    "category": item.get("category", "Products"),
                                    "sku": item.get("sku", ""),
                                    "price": str(item.get("offers", {}).get("price", "")) if isinstance(item.get("offers"), dict) else "",
                                    "nominal_size": "",
                                    "finish": "",
                                    "primary_image": p_img or "",
                                    "images": [p_img] if p_img else [],
                                    "image_count": 1 if p_img else 0,
                                    "description": clean_html_text(item.get("description", ""))[:300],
                                    "url": item.get("url", p_url)
                                })
                    except:
                        pass
                
                # Fallback: Extract image & heading cards
                if len(extracted_products) < 5:
                    # Find cards with <img> and heading/link
                    cards = re.findall(r'(<(?:div|article|li)[^>]*class=["\'][^"\']*(?:product|item|card|grid-item|gallery-item)[^"\']*["\'][^>]*>.*?</(?:div|article|li)>)', p_html, re.DOTALL | re.I)
                    for c in cards[:25]:
                        # Image
                        img_m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', c, re.I)
                        # Title / Text
                        h_m = re.search(r'<(?:h2|h3|h4|span|a)[^>]*class=["\'][^"\']*(?:title|name|heading)[^"\']*["\'][^>]*>(.*?)</', c, re.DOTALL | re.I)
                        if not h_m:
                            h_m = re.search(r'<(?:h2|h3|h4)[^>]*>(.*?)</(?:h2|h3|h4)>', c, re.DOTALL | re.I)
                            
                        # Link
                        a_m = re.search(r'<a[^>]+href=["\']([^"\']+)["\']', c, re.I)
                        
                        if img_m and h_m:
                            card_img = urljoin(base_url, img_m.group(1))
                            card_title = clean_html_text(h_m.group(1))
                            card_link = urljoin(base_url, a_m.group(1)) if a_m else p_url
                            
                            if card_title and len(card_title) > 2 and not any(x in card_title.lower() for x in ['cookie', 'privacy', 'menu', 'search', 'cart']):
                                extracted_products.append({
                                    "id": f"mfg-{m_id}-{re.sub(r'[^a-zA-Z0-9]', '', card_title)[:30]}",
                                    "manufacturer_id": m_id,
                                    "manufacturer_name": m_name,
                                    "name": card_title,
                                    "collection": m_name,
                                    "category": "Products",
                                    "sku": "",
                                    "price": "",
                                    "nominal_size": "",
                                    "finish": "",
                                    "primary_image": card_img,
                                    "images": [card_img],
                                    "image_count": 1,
                                    "description": f"{card_title} by {m_name}",
                                    "url": card_link
                                })
        except:
            continue

    return m_name, extracted_products

def main():
    start_time = time.time()
    matrix_path = r"d:\Aareas\manufacturer_feed_matrix.json"
    with open(matrix_path, "r", encoding="utf-8") as f:
        matrix = json.load(f)

    html_mfgs = [m for m in matrix if m.get("feed_type") == "html_site"]
    print(f"Found {len(html_mfgs)} custom HTML manufacturer websites.")

    master_json_path = r"d:\Aareas\master_products.json"
    with open(master_json_path, "r", encoding="utf-8") as f:
        all_products = json.load(f)
    print(f"Loaded {len(all_products):,} existing products from master database.")

    existing_urls = {p.get("url") for p in all_products if p.get("url")}
    new_products = 0
    brands_added = 0
    completed = 0
    total = len(html_mfgs)

    print(f"\nStarting deep HTML crawling across {total} sites with {MAX_WORKERS} workers...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_m = {executor.submit(crawl_html_site, m): m for m in html_mfgs}
        
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

            if completed % 50 == 0 or completed == total:
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
    print(f"Complete! Master Catalog now has {len(all_products):,} products in {time.time()-start_time:.1f}s.")

if __name__ == "__main__":
    main()
