import json
import urllib.request
import xml.etree.ElementTree as ET
import re
import csv
import ssl
import time
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
MAX_WORKERS = 20
TIMEOUT = 10

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def clean_html(raw_html):
    if not raw_html:
        return ""
    clean = re.sub(r'<[^>]+>', ' ', raw_html)
    return " ".join(clean.split())

def fetch_shopify_products(manufacturer):
    base_url = manufacturer["base_url"].rstrip("/")
    products = []
    page = 1
    max_pages = 5 # Up to 1,250 products per manufacturer
    
    while page <= max_pages:
        endpoint = f"{base_url}/products.json?limit=250&page={page}"
        try:
            req = urllib.request.Request(endpoint, headers={'User-Agent': USER_AGENT})
            with urllib.request.urlopen(req, context=ctx, timeout=TIMEOUT) as resp:
                if resp.getcode() != 200:
                    break
                data = json.loads(resp.read().decode('utf-8'))
                raw_prods = data.get("products", [])
                if not raw_prods:
                    break
                
                for p in raw_prods:
                    # Get primary image and all images
                    imgs = [img["src"] for img in p.get("images", []) if "src" in img]
                    primary_img = imgs[0] if imgs else ""
                    
                    variants = p.get("variants", [])
                    sku = variants[0].get("sku", "") if variants else ""
                    price = variants[0].get("price", "") if variants else ""
                    
                    handle = p.get("handle", "")
                    prod_url = f"{base_url}/products/{handle}" if handle else base_url
                    
                    products.append({
                        "id": f"mfg-{manufacturer['id']}-{p.get('id', handle)}",
                        "manufacturer_id": manufacturer["id"],
                        "manufacturer_name": manufacturer["name"],
                        "name": p.get("title", "").strip(),
                        "collection": p.get("vendor", manufacturer["name"]).strip(),
                        "category": p.get("product_type", "Product").strip() or "Product",
                        "sku": sku,
                        "price": f"${price}" if price else "",
                        "nominal_size": "",
                        "finish": "",
                        "primary_image": primary_img,
                        "images": imgs,
                        "image_count": len(imgs),
                        "description": clean_html(p.get("body_html", ""))[:300],
                        "url": prod_url
                    })
                
                if len(raw_prods) < 250:
                    break
                page += 1
        except Exception:
            break
            
    return products

def main():
    start_time = time.time()
    print("Loading discovery matrix...")
    matrix_path = r"d:\Aareas\manufacturer_feed_matrix.json"
    with open(matrix_path, "r", encoding="utf-8") as f:
        matrix = json.load(f)

    all_products = []

    # 1. Load Daltile products (already scraped in detail)
    daltile_json = r"d:\Aareas\daltile_products.json"
    try:
        with open(daltile_json, "r", encoding="utf-8") as f:
            dal_prods = json.load(f)
            for dp in dal_prods:
                all_products.append({
                    "id": f"mfg-28-{dp.get('id')}",
                    "manufacturer_id": 28,
                    "manufacturer_name": "Daltile",
                    "name": dp.get("name"),
                    "collection": dp.get("collection"),
                    "category": dp.get("category"),
                    "sku": dp.get("sku") or dp.get("color_code"),
                    "price": "",
                    "nominal_size": dp.get("nominal_size"),
                    "finish": dp.get("finish"),
                    "primary_image": dp.get("primary_image"),
                    "images": dp.get("images", []),
                    "image_count": dp.get("image_count", 1),
                    "description": dp.get("description", "")[:300],
                    "url": dp.get("url")
                })
        print(f"Loaded {len(dal_prods)} products from Daltile.")
    except Exception as e:
        print("Daltile load error:", e)

    # 2. Extract Shopify stores
    shopify_mfgs = [m for m in matrix if m.get("feed_type") == "shopify"]
    print(f"Extracting products from {len(shopify_mfgs)} Shopify-enabled manufacturers...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_m = {executor.submit(fetch_shopify_products, m): m for m in shopify_mfgs}
        for future in as_completed(future_to_m):
            m = future_to_m[future]
            try:
                prods = future.result()
                if prods:
                    all_products.extend(prods)
                    print(f"  + Extracted {len(prods)} products from {m['name']}")
            except Exception as e:
                print(f"  - Failed {m['name']}: {e}")

    # Sort all products
    all_products.sort(key=lambda x: (x["manufacturer_name"], x["name"]))

    # Save to master JSON
    master_json_path = r"d:\Aareas\master_products.json"
    with open(master_json_path, "w", encoding="utf-8") as f:
        json.dump(all_products, f, indent=2, ensure_ascii=False)
    print(f"\nSaved Master JSON to: {master_json_path} ({len(all_products)} total products)")

    # Save to master CSV
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
    print(f"Saved Master CSV to: {master_csv_path}")

if __name__ == "__main__":
    main()
