"""Re-fetch Trex product pages and store SKU, color, specs, downloads."""
import csv
import json
import ssl
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from categorize import assign_category
from extract_product import extract_page_details

ROOT = Path(r"d:\Aareas")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, context=CTX, timeout=16) as resp:
        return resp.read().decode("utf-8", errors="ignore"), resp.geturl()


def merge(product):
    url = product.get("url") or ""
    if not url:
        return product, False
    html, final = fetch(url)
    d = extract_page_details(html, final)
    changed = False
    if d["sku"]:
        product["sku"] = d["sku"]
        changed = True
    if d["price"]:
        product["price"] = d["price"]
        changed = True
    if d["color"]:
        product["color"] = d["color"]
        if not product.get("finish"):
            product["finish"] = d["color"]
        changed = True
    if d["colors"]:
        product["colors"] = d["colors"]
    if d["description"]:
        product["description"] = d["description"]
        changed = True
    if d["specs"]:
        product["specs"] = d["specs"]
        changed = True
    if d["downloads"]:
        product["downloads"] = d["downloads"]
        changed = True
    # keep existing good Scene7 image; only fill if empty
    if d["primary_image"] and not product.get("primary_image"):
        product["primary_image"] = d["primary_image"]
        product["images"] = d["images"][:8]
        product["image_count"] = len(product["images"])
        changed = True
    if d["name"] if False else None:
        pass
    product["category"] = assign_category(product)
    return product, changed


def main():
    path = ROOT / "master_products.json"
    products = json.loads(path.read_text(encoding="utf-8"))
    idx = [i for i, p in enumerate(products) if p.get("manufacturer_name") == "Trex"]
    print("Trex", len(idx))
    ok = 0
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(merge, products[i]): i for i in idx}
        for fut in as_completed(futs):
            i = futs[fut]
            try:
                p, changed = fut.result()
            except Exception as e:
                print("fail", products[i].get("url"), type(e).__name__)
                continue
            products[i] = p
            if changed:
                ok += 1
    path.write_text(json.dumps(products, indent=2, ensure_ascii=False), encoding="utf-8")
    fields = [
        "id", "manufacturer_id", "manufacturer_name", "name", "collection",
        "category", "raw_category", "sku", "price", "color", "finish",
        "primary_image", "image_count", "url", "description",
    ]
    with (ROOT / "master_products.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(products)
    g = next(p for p in products if "0-degree-rail-gasket-pack-horizontal" in (p.get("url") or ""))
    print(f"enriched {ok}/{len(idx)}")
    print("gasket sku", g.get("sku"), "color", g.get("color"), "price", g.get("price"))
    print("desc", (g.get("description") or "")[:100])
    print("specs", g.get("specs"))
    print("downloads", g.get("downloads"))


if __name__ == "__main__":
    main()
