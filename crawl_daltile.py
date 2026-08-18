import urllib.request
import xml.etree.ElementTree as ET
import re
import json
import csv
import time
import sys
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape

SITEMAP_URL = "https://www.daltile.com/sitemap.xml"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
MAX_WORKERS = 18
TIMEOUT = 12

def get_sitemap_product_urls():
    print(f"Fetching sitemap from {SITEMAP_URL}...")
    req = urllib.request.Request(SITEMAP_URL, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        content = resp.read()
    root = ET.fromstring(content)
    
    product_urls = []
    for child in root:
        loc = child.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
        if loc is not None and loc.text:
            u = loc.text.strip()
            path = urlparse(u).path.strip('/')
            parts = path.split('/')
            # Target product variant pages (depth 4: products/category/collection/color)
            if len(parts) >= 4 and parts[0] == 'products':
                product_urls.append(u)

    # Deduplicate while preserving order
    seen = set()
    unique_urls = []
    for u in product_urls:
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)
            
    print(f"Found {len(unique_urls)} product variant URLs in sitemap.")
    return unique_urls

def extract_product_data(html, url):
    path_parts = url.replace("https://www.daltile.com/", "").strip("/").split("/")
    
    category_slug = path_parts[1] if len(path_parts) > 1 else ""
    collection_slug = path_parts[2] if len(path_parts) > 2 else ""
    color_slug = path_parts[3] if len(path_parts) > 3 else ""
    
    category_name = category_slug.replace("-", " ").title()
    collection_name = collection_slug.replace("-", " ").title()
    color_name = color_slug.replace("-", " ").title()

    # Product Title
    title = f"{collection_name} - {color_name}"
    t_match = re.search(r'<title>(.*?)</title>', html, re.I)
    if t_match:
        raw_title = unescape(t_match.group(1)).strip()
        if raw_title and "404" not in raw_title:
            title = raw_title

    # Description
    description = ""
    d_match = re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']*)["\']', html, re.I)
    if d_match and d_match.group(1).strip():
        description = unescape(d_match.group(1)).strip()
    if not description:
        # Fallback to series description paragraph
        p_match = re.search(r'class=["\'][^"\']*(?:product-desc|overview-description)[^"\']*["\'][^>]*>(.*?)</p>', html, re.I | re.DOTALL)
        if p_match:
            description = re.sub(r'<[^>]+>', '', p_match.group(1)).strip()

    # Hidden Form Inputs (Most reliable SKU and Size data)
    sku = ""
    sku_m = re.search(r'name=["\']sample\.EncodedSku["\']\s+value=["\']([^"\']+)["\']', html, re.I)
    if sku_m:
        sku = sku_m.group(1).strip()
    if not sku:
        sku_m2 = re.search(r'data-selling-sku=["\']([^"\']+)["\']', html, re.I)
        if sku_m2:
            sku = sku_m2.group(1).strip()

    nominal_size = ""
    size_m = re.search(r'name=["\']sample\.Product\.NominalSize["\']\s+value=["\']([^"\']+)["\']', html, re.I)
    if size_m:
        nominal_size = size_m.group(1).strip()

    finish = ""
    finish_m = re.search(r'name=["\']sample\.Product\.Finish["\']\s+value=["\']([^"\']+)["\']', html, re.I)
    if finish_m:
        finish = finish_m.group(1).strip()

    color_code = ""
    code_m = re.search(r'class=["\']sample-colorCode["\']\s+value=["\']([^"\']+)["\']', html, re.I)
    if code_m:
        color_code = code_m.group(1).strip()

    # Property Groups Helper
    def extract_property(label_name):
        patterns = [
            rf'<label[^>]*>{label_name}</label>\s*:\s*<span>([^<]+)</span>',
            rf'<label[^>]*>{label_name}</label>[\s:]*<span[^>]*>([^<]+)</span>',
            rf'<label[^>]*>{label_name}</label>\s*:\s*<span class="product-sku">([^<]+)</span>'
        ]
        for pat in patterns:
            m = re.search(pat, html, re.I)
            if m:
                return unescape(m.group(1)).strip()
        return ""

    thickness = extract_property("Thickness")
    shade_variation = extract_property("Shade Variation")
    country_of_origin = extract_property("Country of Origin")
    
    if not color_code:
        color_code = extract_property("Color Code")
    if not nominal_size:
        nominal_size = extract_property("Nominal Size")
    if not finish:
        finish = extract_property("Finish")

    # Images Extraction
    primary_image = ""
    gallery_images = []
    
    # 1. Main Zoom Image
    zoom_m = re.search(r'id=["\']responsive_zoom["\'][^>]+src=["\']([^"\']+)["\']', html, re.I)
    if zoom_m:
        primary_image = zoom_m.group(1).strip()
    
    # 2. Thumbnail Images
    thumb_matches = re.findall(r'<img[^>]+data-lrg-src=["\']([^"\']+)["\']', html)
    for t in thumb_matches:
        t_clean = t.strip()
        if t_clean and t_clean not in gallery_images:
            gallery_images.append(t_clean)

    # 3. Flyout High-Res Zoom Images
    flyout_matches = re.findall(r'data-zoom-image=["\']([^"\']+)["\']', html)
    for f in flyout_matches:
        f_clean = f.strip()
        if f_clean and f_clean not in gallery_images:
            gallery_images.append(f_clean)

    # 4. In-Situ / Room Scene Images on this page
    scene7_matches = re.findall(r'https?://s7d9\.scene7\.com/is/image/daltile/[^"\'\s<>?]+', html)
    for s in scene7_matches:
        s_lower = s.lower()
        if any(x in s_lower for x in ['logo', 'icon', 'arrow', 'banner', 'btn', 'social', 'flyout']):
            continue
        full_s = s + "?$PRODUCTIMAGE$"
        if full_s not in gallery_images:
            gallery_images.append(full_s)

    if not primary_image and gallery_images:
        primary_image = gallery_images[0]
    elif primary_image and primary_image not in gallery_images:
        gallery_images.insert(0, primary_image)

    # Applications
    applications = []
    app_section = re.search(r'Application</h2>(.*?)</table>', html, re.I | re.DOTALL)
    if app_section:
        app_rows = re.findall(r'<tr>(.*?)</tr>', app_section.group(1), re.DOTALL)
        for row in app_rows:
            if '&#10004;' in row or '✔' in row or 'suitable' in row.lower():
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
                if cells:
                    app_name = re.sub(r'<[^>]+>', '', cells[0]).strip()
                    if app_name and app_name not in applications:
                        applications.append(app_name)

    return {
        "id": f"{category_slug}-{collection_slug}-{color_slug}",
        "name": color_name,
        "full_title": title,
        "collection": collection_name,
        "category": category_name,
        "category_slug": category_slug,
        "color": color_name,
        "sku": sku,
        "color_code": color_code,
        "nominal_size": nominal_size,
        "thickness": thickness,
        "finish": finish,
        "shade_variation": shade_variation,
        "country_of_origin": country_of_origin,
        "primary_image": primary_image,
        "images": gallery_images,
        "image_count": len(gallery_images),
        "applications": applications,
        "description": description,
        "url": url
    }

def fetch_and_parse(url, retries=2):
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                if resp.getcode() == 200:
                    html = resp.read().decode('utf-8', errors='ignore')
                    return extract_product_data(html, url)
                return None
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if attempt < retries:
                time.sleep(1.0)
            else:
                return None
        except Exception:
            if attempt < retries:
                time.sleep(1.0)
            else:
                return None
    return None

def main():
    start_time = time.time()
    urls = get_sitemap_product_urls()
    total_urls = len(urls)
    
    print(f"\nStarting multi-threaded crawl of {total_urls} product pages with {MAX_WORKERS} workers...")
    
    products = []
    completed = 0
    failed = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_url = {executor.submit(fetch_and_parse, url): url for url in urls}
        
        for future in as_completed(future_to_url):
            completed += 1
            res = future.result()
            if res:
                products.append(res)
            else:
                failed += 1
                
            if completed % 100 == 0 or completed == total_urls:
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                percent = (completed / total_urls) * 100
                sys.stdout.write(f"\rProgress: {completed}/{total_urls} ({percent:.1f}%) | Success: {len(products)} | Speed: {rate:.1f} pages/sec")
                sys.stdout.flush()

    total_time = time.time() - start_time
    print(f"\n\nCrawl Complete in {total_time:.1f} seconds!")
    print(f"Successfully scraped {len(products)} products ({failed} 404/skipped).")

    # Sort products alphabetically by category and collection
    products.sort(key=lambda x: (x["category"], x["collection"], x["name"]))

    # Save to JSON
    json_path = r"d:\Aareas\daltile_products.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(products, f, indent=2, ensure_ascii=False)
    print(f"Saved JSON catalog to: {json_path}")

    # Save to CSV
    csv_path = r"d:\Aareas\daltile_products.csv"
    fieldnames = [
        "id", "name", "full_title", "collection", "category", "color",
        "sku", "color_code", "nominal_size", "thickness", "finish",
        "shade_variation", "country_of_origin", "primary_image",
        "image_count", "applications", "url", "description"
    ]
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for p in products:
            p_copy = dict(p)
            p_copy["applications"] = "; ".join(p["applications"])
            writer.writerow(p_copy)
    print(f"Saved CSV catalog to: {csv_path}")

if __name__ == "__main__":
    main()
