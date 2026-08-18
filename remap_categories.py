"""Rewrite product.category onto the 12-item materials list."""
import csv
import json
from collections import Counter
from pathlib import Path

from categorize import CATEGORIES, assign_category

ROOT = Path(r"d:\Aareas")


def main():
    path = ROOT / "master_products.json"
    products = json.loads(path.read_text(encoding="utf-8"))
    before = Counter((p.get("category") or "") for p in products)

    for p in products:
        if "raw_category" not in p:
            p["raw_category"] = p.get("category") or ""
        p["category"] = assign_category(p)

    after = Counter((p.get("category") or "") for p in products)
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

    print(f"products {len(products)}")
    print("before unique", len(before), "-> after", len(after))
    for label in CATEGORIES:
        print(f"  {after.get(label, 0):6}  {label}")
    leftover = set(after) - set(CATEGORIES)
    if leftover:
        print("unexpected", leftover)


if __name__ == "__main__":
    main()
