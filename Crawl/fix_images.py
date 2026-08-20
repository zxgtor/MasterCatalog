import json
import csv
import re
from urllib.parse import urlparse, urljoin

# Clean SVG placeholder data URI
FALLBACK_SVG = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 300' fill='%23f1f5f9'%3E%3Crect width='400' height='300' fill='%23f8fafc'/%3E%3Cpath d='M160 130a20 20 0 100-40 20 20 0 000 40zm-40 90h160l-50-65-35 45-25-30-50 50z' fill='%23cbd5e1'/%3E%3Ctext x='50%25' y='80%25' text-anchor='middle' fill='%2394a3b8' font-family='sans-serif' font-size='14'%3ENo Image Available%3C/text%3E%3C/svg%3E"

def fix_image_url(img_url, base_url="https://www.daltile.com"):
    if not img_url or not isinstance(img_url, str):
        return ""
    img = img_url.strip()
    if not img:
        return ""
        
    # Protocol-relative
    if img.startswith("//"):
        img = "https:" + img
    # Relative path
    elif img.startswith("/"):
        parsed = urlparse(base_url)
        domain = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else "https://www.daltile.com"
        img = urljoin(domain, img)

    # Convert .tif in DAM to web rendition
    if ".tif" in img.lower():
        if "digitalassets.daltile.com" in img and "/jcr:content/renditions/" not in img:
            img = img + "/jcr:content/renditions/cq5dam.web.570.570.jpeg"
        elif "s7d9.scene7.com" in img:
            img = re.sub(r'\.tif.*$', '', img, flags=re.I) + "?$PRODUCTIMAGE$"

    return img

def fix_dataset(json_path, csv_path):
    print(f"Fixing image links in {json_path}...")
    with open(json_path, "r", encoding="utf-8") as f:
        products = json.load(f)

    fixed_count = 0
    for p in products:
        base_u = p.get("url") or "https://www.daltile.com"
        old_primary = p.get("primary_image") or ""
        new_primary = fix_image_url(old_primary, base_u)
        if new_primary != old_primary:
            fixed_count += 1
            p["primary_image"] = new_primary

        # Fix all images in list
        if "images" in p and isinstance(p["images"], list):
            p["images"] = [fix_image_url(x, base_u) for x in p["images"] if fix_image_url(x, base_u)]

    print(f"Fixed {fixed_count:,} image URLs in {json_path}")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(products, f, indent=2, ensure_ascii=False)

    # Re-export CSV
    if products:
        fieldnames = list(products[0].keys())
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for p in products:
                row = dict(p)
                if isinstance(row.get("images"), list):
                    row["images"] = "; ".join(row["images"])
                if isinstance(row.get("applications"), list):
                    row["applications"] = "; ".join(row["applications"])
                writer.writerow(row)
    print(f"Updated CSV: {csv_path}")

def main():
    # 1. Fix Daltile Dataset
    fix_dataset(r"d:\Aareas\daltile_products.json", r"d:\Aareas\daltile_products.csv")

    # 2. Fix Master Dataset
    fix_dataset(r"d:\Aareas\master_products.json", r"d:\Aareas\master_products.csv")

    # 3. Regenerate HTML files with referrer policy & fallback SVG
    print("\nRegenerating HTML catalogs with no-referrer policy and fallback handlers...")
    import generate_html
    import generate_master_catalog
    
    generate_html.build_html_catalog()
    generate_master_catalog.build_master_html_catalog()
    print("\nAll image fixes applied successfully!")

if __name__ == "__main__":
    main()
