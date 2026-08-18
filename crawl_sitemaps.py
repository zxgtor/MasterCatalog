import json
import urllib.request
import xml.etree.ElementTree as ET
import re
import csv
import ssl
import time
import sys
from urllib.parse import urlparse, unquote
from html import unescape
from concurrent.futures import ThreadPoolExecutor, as_completed

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
MAX_WORKERS = 30
TIMEOUT = 10

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

PRODUCT_PATTERNS = [
    r'/products?/', r'/items?/', r'/collections?/', r'/tiles?/', r'/flooring/',
    r'/surfaces?/', r'/faucets?/', r'/fixtures?/', r'/catalog/', r'/shop/', r'/detail/'
]

def clean_text(s):
    if not s:
        return ""
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s)).strip()

def extract_products_from_sitemap(manufacturer):
    base_url = manufacturer["base_url"].rstrip("/")
    m_id = manufacturer["id"]
    m_name = manufacturer["name"]
    
    sitemap_urls = [
        f"{base_url}/sitemap.xml",
        f"{base_url}/sitemap_products_1.xml",
        f"{base_url}/product-sitemap.xml",
        f"{base_url}/sitemap_index.xml"
    ]
    
    extracted_products = []
    
    for s_url in sitemap_urls:
        try:
            req = urllib.request.Request(s_url, headers={'User-Agent': USER_AGENT})
            with urllib.request.urlopen(req, context=ctx, timeout=TIMEOUT) as resp:
                if resp.getcode() != 200:
                    continue
                content = resp.read()
                
                try:
                    root = ET.fromstring(content)
                except:
                    continue
                
                # If sitemap index, look for product sitemaps
                sub_sitemaps = []
                for sitemap_node in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap'):
                    loc = sitemap_node.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                    if loc is not None and loc.text:
                        sub_url = loc.text.strip()
                        if any(x in sub_url.lower() for x in ['product', 'item', 'tile', 'collection', 'catalog']):
                            sub_sitemaps.append(sub_url)
                
                # Parse sub-sitemaps (up to 3)
                all_roots = [root]
                for sub in sub_sitemaps[:3]:
                    try:
                        req_sub = urllib.request.Request(sub, headers={'User-Agent': USER_AGENT})
                        with urllib.request.urlopen(req_sub, context=ctx, timeout=TIMEOUT) as sresp:
                            all_roots.append(ET.fromstring(sresp.read()))
                    except:
                        pass
                
                # Extract URLs from all roots
                for r in all_roots:
                    for url_node in r.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                        loc = url_node.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                        if loc is not None and loc.text:
                            page_url = loc.text.strip()
                            path = urlparse(page_url).path.lower()
                            
                            # Filter for product pages
                            if any(re.search(pat, path) for pat in PRODUCT_PATTERNS) or len(path.strip('/').split('/')) >= 2:
                                images = []
                                for img_node in url_node.findall('.//{http://www.google.com/schemas/sitemap-image/1.1}image'):
                                    img_loc = img_node.find('{http://www.google.com/schemas/sitemap-image/1.1}loc')
                                    if img_loc is not None and img_loc.text:
                                        images.append(img_loc.text.strip())
                                
                                # Derive product name from slug
                                slug = path.strip('/').split('/')[-1].replace('-', ' ').replace('_', ' ')
                                if not slug or slug.isdigit() or len(slug) < 2:
                                    slug = path.strip('/').split('/')[-2].replace('-', ' ').title() if len(path.strip('/').split('/')) >= 2 else "Product"
                                else:
                                    slug = slug.title()
                                
                                # Derive category
                                parts = path.strip('/').split('/')
                                cat = parts[0].replace('-', ' ').title() if len(parts) > 1 else "Products"
                                
                                primary_img = images[0] if images else ""
                                
                                prod_id = f"mfg-{m_id}-{re.sub(r'[^a-zA-Z0-9]', '', path)[:40]}"
                                extracted_products.append({
                                    "id": prod_id,
                                    "manufacturer_id": m_id,
                                    "manufacturer_name": m_name,
                                    "name": slug,
                                    "collection": m_name,
                                    "category": cat,
                                    "sku": "",
                                    "price": "",
                                    "nominal_size": "",
                                    "finish": "",
                                    "primary_image": primary_img,
                                    "images": images,
                                    "image_count": len(images),
                                    "description": f"{slug} by {m_name}",
                                    "url": page_url
                                })
                                
                                if len(extracted_products) >= 150:
                                    break
                
                if extracted_products:
                    break
        except Exception:
            continue
            
    return m_name, extracted_products

def main():
    start_time = time.time()
    print("Loading discovery matrix...")
    matrix_path = r"d:\Aareas\manufacturer_feed_matrix.json"
    with open(matrix_path, "r", encoding="utf-8") as f:
        matrix = json.load(f)

    sitemap_mfgs = [m for m in matrix if m.get("feed_type") == "sitemap"]
    print(f"Found {len(sitemap_mfgs)} sitemap-enabled manufacturers.")

    # Load existing master products
    master_json_path = r"d:\Aareas\master_products.json"
    try:
        with open(master_json_path, "r", encoding="utf-8") as f:
            all_products = json.load(f)
        print(f"Loaded {len(all_products):,} existing products from master database.")
    except:
        all_products = []

    existing_urls = {p.get("url") for p in all_products if p.get("url")}
    new_products_count = 0
    brands_added = 0
    completed = 0
    total = len(sitemap_mfgs)

    print(f"\nStarting multi-threaded sitemap extraction across {total} manufacturers with {MAX_WORKERS} workers...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_m = {executor.submit(extract_products_from_sitemap, m): m for m in sitemap_mfgs}
        
        for future in as_completed(future_to_m):
            completed += 1
            m_name, prods = future.result()
            added_for_this = 0
            for p in prods:
                if p["url"] not in existing_urls:
                    existing_urls.add(p["url"])
                    all_products.append(p)
                    added_for_this += 1
                    new_products_count += 1
                    
            if added_for_this > 0:
                brands_added += 1

            if completed % 50 == 0 or completed == total:
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                print(f"Progress: {completed}/{total} ({(completed/total)*100:.1f}%) | New Products: {new_products_count:,} | New Brands: {brands_added} | Speed: {rate:.1f} sites/sec")

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
    print(f"Complete! Total Master Catalog now has {len(all_products):,} products in {time.time()-start_time:.1f}s.")

if __name__ == "__main__":
    main()
