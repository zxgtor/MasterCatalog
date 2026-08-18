"""Fill empty Trex images from product pages (images.trex.com / og:image)."""
import csv
import json
import re
import ssl
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from pathlib import Path
from urllib.parse import urljoin

from categorize import assign_category

ROOT = Path(r"d:\Aareas")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
SKIP = re.compile(r"icon|logo|flag|social|favicon|sprite|storefront", re.I)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, context=CTX, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="ignore"), resp.geturl()


def extract_images(html, page_url):
    found = []
    pats = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image',
        r'https?://images\.trex\.com/is/image/trexcompany/[^"\'\s<>)]+',
        r'<img[^>]+src=["\']([^"\']+)',
    ]
    for pat in pats:
        for m in re.findall(pat, html, re.I):
            u = unescape(m.strip())
            if u.startswith("//"):
                u = "https:" + u
            elif u.startswith("/"):
                u = urljoin(page_url, u)
            if not u.startswith("http"):
                continue
            if SKIP.search(u):
                continue
            if "images.trex.com/is/image/" not in u and not re.search(r"\.(jpe?g|png|webp)(\?|$)", u, re.I):
                continue
            u = u.split("?")[0]
            if u not in found:
                found.append(u)
    # Prefer product SKU shots over swatches / social
    found.sort(key=lambda u: (0 if "SKU_" in u or "Primary" in u else 1 if "swatch" not in u.lower() else 2, u))
    return found


def enrich(product):
    url = product.get("url") or ""
    if not url:
        return product, False
    html, final = fetch(url)
    images = extract_images(html, final)
    if not images:
        return product, False
    product["primary_image"] = images[0]
    product["images"] = images[:8]
    product["image_count"] = min(len(images), 8)
    sku_m = re.search(r"SKU:\s*([A-Z0-9\-]+)", html, re.I)
    if sku_m and not product.get("sku"):
        product["sku"] = sku_m.group(1)
    product["category"] = assign_category(product)
    return product, True


def main():
    path = ROOT / "master_products.json"
    products = json.loads(path.read_text(encoding="utf-8"))
    idx = [i for i, p in enumerate(products) if p.get("manufacturer_name") == "Trex"]
    print(f"Trex products: {len(idx)}")

    filled = 0
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(enrich, products[i]): i for i in idx}
        for fut in as_completed(futs):
            i = futs[fut]
            try:
                p, ok = fut.result()
            except Exception as e:
                print(" fail", products[i].get("url"), type(e).__name__)
                continue
            products[i] = p
            if ok:
                filled += 1

    path.write_text(json.dumps(products, indent=2, ensure_ascii=False), encoding="utf-8")
    fields = [
        "id", "manufacturer_id", "manufacturer_name", "name", "collection",
        "category", "raw_category", "sku", "price", "nominal_size", "finish",
        "primary_image", "image_count", "url", "description",
    ]
    with (ROOT / "master_products.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(products)
    print(f"filled {filled}/{len(idx)}")
    sample = next((products[i] for i in idx if products[i].get("primary_image")), None)
    if sample:
        print("sample", sample["name"], sample["primary_image"][:110])


if __name__ == "__main__":
    main()
