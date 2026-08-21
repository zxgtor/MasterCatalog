"""Fetch product URLs, fill missing fields, write SQLite.

  python enrich_db.py --report
  python enrich_db.py --brand Trex
  python enrich_db.py --limit 50
  python enrich_db.py --brand Koroseal --force
"""
import argparse
import re
import ssl
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

from categorize import assign_category
from db import connect, row_to_product, update_product
from extract_product import extract_page_details

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def missing_fields(p):
    specs = p.get("specs") or {}
    downloads = p.get("downloads") or []
    images = p.get("images") or []
    gaps = []
    if not p.get("sku"):
        gaps.append("sku")
    if not p.get("primary_image"):
        gaps.append("image")
    if not (p.get("description") or "").strip():
        gaps.append("description")
    if not p.get("color") and not p.get("finish"):
        gaps.append("color")
    if not p.get("price"):
        gaps.append("price")
    if not specs:
        gaps.append("specs")
    if not downloads:
        gaps.append("downloads")
    if not images and p.get("primary_image"):
        gaps.append("images")
    return gaps


def fill_empty(product, extracted, force=False):
    changed = []

    def take(key, dest=None, value=None):
        dest = dest or key
        val = extracted.get(key) if value is None else value
        if not val:
            return
        cur = product.get(dest)
        empty = cur in (None, "", [], {})
        if force or empty:
            if cur != val:
                product[dest] = val
                changed.append(dest)

    take("sku")
    take("price")
    take("color")
    take("description")
    if extracted.get("color") and (force or not product.get("finish")):
        product["finish"] = extracted["color"]
        changed.append("finish")
    if extracted.get("colors"):
        take("colors")
    if extracted.get("specs"):
        if force or not product.get("specs"):
            product["specs"] = extracted["specs"]
            changed.append("specs")
        else:
            merged = dict(product["specs"])
            for k, v in extracted["specs"].items():
                if v and not merged.get(k):
                    merged[k] = v
            if merged != product["specs"]:
                product["specs"] = merged
                changed.append("specs")
    if extracted.get("downloads") and (force or not product.get("downloads")):
        product["downloads"] = extracted["downloads"]
        changed.append("downloads")
    if extracted.get("primary_image") and (force or not product.get("primary_image")):
        product["primary_image"] = extracted["primary_image"]
        imgs = extracted.get("images") or [extracted["primary_image"]]
        product["images"] = imgs[:8]
        product["image_count"] = len(product["images"])
        changed.append("image")
    if changed:
        product["category"] = assign_category(product)
    return list(dict.fromkeys(changed))


SKIP_URL = re.compile(
    r"/blog/|/news/|/press/|/about|/contact|/privacy|/login|/cart|/account|"
    r"/faq|/careers|/cookie|/terms|/search\?",
    re.I,
)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, context=CTX, timeout=10) as resp:
        return resp.read().decode("utf-8", errors="ignore"), resp.geturl()


def select_targets(conn, brand=None, limit=0, offset=0, all_rows=False):
    sql = """SELECT p.*, m.name AS manufacturer_name
             FROM products p
             JOIN manufacturers m ON m.id = p.manufacturer_id
             WHERE p.url != '' AND p.url NOT LIKE '%/blog/%' AND p.url NOT LIKE '%/news/%'"""
    args = []
    if brand:
        sql += " AND m.name = ?"
        args.append(brand)
    if not all_rows:
        sql += """ AND (p.sku = '' OR p.primary_image = '' OR p.description = ''
                        OR p.color = '' OR p.price = '' OR p.downloads = '[]')"""
    sql += " ORDER BY CASE WHEN p.primary_image = '' THEN 0 ELSE 1 END, m.name, p.name"
    if limit:
        sql += " LIMIT ?"
        args.append(limit)
        if offset:
            sql += " OFFSET ?"
            args.append(offset)
    return [row_to_product(r) for r in conn.execute(sql, args)]


def enrich_one(product, force=False):
    url = product.get("url") or ""
    if SKIP_URL.search(url):
        return product, []
    html, final = fetch(url)
    extracted = extract_page_details(html, final)
    changed = fill_empty(product, extracted, force=force)
    return product, changed


def report(conn, brand=None):
    extra = " AND m.name = ?" if brand else ""
    args = (brand,) if brand else ()
    row = conn.execute(
        f"""SELECT COUNT(*) total,
                   SUM(p.sku='') sku,
                   SUM(p.primary_image='') image,
                   SUM(p.description='') description,
                   SUM(p.color='' AND json_extract(p.attrs,'$.finish') IS NULL) color,
                   SUM(p.price='') price,
                   SUM(p.downloads='[]') downloads
            FROM products p JOIN manufacturers m ON m.id=p.manufacturer_id
            WHERE 1=1 {extra}""",
        args,
    ).fetchone()
    print("brand:", brand or "(all)")
    print(f"  {'total':12} {row['total']}")
    for k in ("sku", "image", "description", "color", "price", "downloads"):
        print(f"  {k:12} {row[k] or 0}")
    return dict(row)


def main():
    ap = argparse.ArgumentParser(description="Fill missing product fields from live URLs into SQLite.")
    ap.add_argument("--brand", default="", help="Only this manufacturer name")
    ap.add_argument("--limit", type=int, default=0, help="Max products to fetch")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--force", action="store_true", help="Overwrite existing fields")
    ap.add_argument("--report", action="store_true", help="Count gaps, do not fetch")
    args = ap.parse_args()

    conn = connect()
    if args.report:
        report(conn, args.brand or None)
        return

    WAVE = 200
    updated = failed = skipped = 0
    extra = " AND m.name = ?" if args.brand else ""
    qargs = [args.brand] if args.brand else []
    miss = "" if args.force else """ AND (p.sku = '' OR p.primary_image = '' OR p.description = ''
                    OR p.color = '' OR p.price = '' OR p.downloads = '[]')"""
    ids = [
        r[0]
        for r in conn.execute(
            f"""SELECT p.id FROM products p
                JOIN manufacturers m ON m.id = p.manufacturer_id
                WHERE p.url != '' AND p.url NOT LIKE '%/blog/%' AND p.url NOT LIKE '%/news/%'
                {extra} {miss}
                ORDER BY CASE WHEN p.primary_image = '' THEN 0 ELSE 1 END, m.name, p.name""",
            qargs,
        )
    ]
    if args.limit:
        ids = ids[: args.limit]
    print(f"to fetch: {len(ids)}" + (f" ({args.brand})" if args.brand else ""), flush=True)
    for i in range(0, len(ids), WAVE):
        chunk = ids[i : i + WAVE]
        ph = ",".join("?" * len(chunk))
        batch = [
            row_to_product(r)
            for r in conn.execute(
                f"""SELECT p.*, m.name AS manufacturer_name
                    FROM products p JOIN manufacturers m ON m.id = p.manufacturer_id
                    WHERE p.id IN ({ph})""",
                chunk,
            )
        ]
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = [ex.submit(enrich_one, p, args.force) for p in batch]
            for fut in as_completed(futs):
                try:
                    product, changed = fut.result()
                except Exception:
                    failed += 1
                    continue
                if changed:
                    update_product(conn, product)
                    updated += 1
                else:
                    skipped += 1
        conn.commit()
        print(f" {min(i + WAVE, len(ids))}/{len(ids)} updated={updated} failed={failed} no-new-data={skipped}", flush=True)
    print(f"done updated={updated} failed={failed} no-new-data={skipped}", flush=True)


if __name__ == "__main__":
    sys.exit(main() or 0)
