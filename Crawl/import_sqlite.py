"""Load manufacturers + products JSON into aareas.db."""
import json
from pathlib import Path

from db import connect, init_db, product_to_row

ROOT = Path(__file__).resolve().parent


def main():
    conn = connect()
    init_db(conn)
    cur = conn.cursor()

    mfgs = json.loads((ROOT / "manufacturers_with_url.json").read_text(encoding="utf-8"))
    cur.execute("DELETE FROM products")
    cur.execute("DELETE FROM manufacturers")
    cur.executemany(
        """INSERT OR REPLACE INTO manufacturers
           (id, name, url, type, logo, contact, email)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                int(m["id"]),
                m.get("name") or "",
                m.get("url") or "",
                m.get("type") or "",
                m.get("logo") or "",
                m.get("contact") or "",
                m.get("email") or "",
            )
            for m in mfgs
        ],
    )

    products = json.loads((ROOT / "master_products.json").read_text(encoding="utf-8"))
    have = {r[0] for r in cur.execute("SELECT id FROM manufacturers")}
    missing = {}
    for p in products:
        mid = int(p.get("manufacturer_id") or 0)
        name = p.get("manufacturer_name") or f"mfg-{mid}"
        if mid and mid not in have:
            missing[mid] = name
    for mid, name in missing.items():
        cur.execute(
            "INSERT OR IGNORE INTO manufacturers (id, name) VALUES (?, ?)",
            (mid, name),
        )
        have.add(mid)

    rows = []
    skipped = 0
    seen_ids = set()
    for p in products:
        mid = int(p.get("manufacturer_id") or 0)
        if not mid or mid not in have:
            skipped += 1
            continue
        pid = str(p.get("id") or "")
        if not pid:
            skipped += 1
            continue
        if pid in seen_ids:
            n = 2
            while f"{pid}-{n}" in seen_ids:
                n += 1
            pid = f"{pid}-{n}"
        seen_ids.add(pid)
        p = dict(p)
        p["id"] = pid
        rows.append(product_to_row(p))

    cur.executemany(
        """INSERT OR REPLACE INTO products (
            id, manufacturer_id, name, collection, category, raw_category,
            sku, price, color, description, url, primary_image, image_count,
            images, downloads, attrs
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )
    conn.commit()

    n_p = cur.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    n_m = cur.execute("SELECT COUNT(*) FROM manufacturers").fetchone()[0]
    n_t = cur.execute(
        "SELECT COUNT(*) FROM products p JOIN manufacturers m ON m.id=p.manufacturer_id WHERE m.name='Trex'"
    ).fetchone()[0]
    print(f"manufacturers {n_m}")
    print(f"products {n_p} (skipped {skipped})")
    print(f"trex {n_t}")
    assert n_p > 80000, n_p
    assert n_t > 100, n_t
    conn.close()


if __name__ == "__main__":
    main()
