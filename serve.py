"""Local Aareas site. Product data comes from aareas.db."""
import json
import os
import http.server
import socketserver
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from db import connect, init_db, row_to_product

PORT = int(os.environ.get("MASTER_CATALOG_PORT", "8765"))
ROOT = Path(__file__).resolve().parent
DB = connect()
init_db(DB)


def _json(handler, payload, status=200):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _q(qs, key, default=""):
    vals = qs.get(key) or [default]
    return vals[0]


def stats():
    products = DB.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    brands = DB.execute(
        "SELECT COUNT(DISTINCT manufacturer_id) FROM products"
    ).fetchone()[0]
    manufacturers = DB.execute("SELECT COUNT(*) FROM manufacturers").fetchone()[0]
    return {"products": products, "brands": brands, "manufacturers": manufacturers}


def brands():
    rows = DB.execute(
        """SELECT m.name, COUNT(p.id) AS n
           FROM manufacturers m
           JOIN products p ON p.manufacturer_id = m.id
           GROUP BY m.id
           ORDER BY n DESC, m.name"""
    ).fetchall()
    return [{"name": r["name"], "count": r["n"]} for r in rows]


def categories():
    rows = DB.execute(
        """SELECT category, COUNT(*) AS n FROM products
           GROUP BY category ORDER BY category COLLATE NOCASE"""
    ).fetchall()
    return [{"name": r["category"] or "Other", "count": r["n"]} for r in rows]


def house_payload(brand):
    m = DB.execute(
        "SELECT id, name, url FROM manufacturers WHERE name = ?", (brand,)
    ).fetchone()
    if not m:
        return {"brand": brand, "url": "", "products": []}
    rows = DB.execute(
        """SELECT p.*, m.name AS manufacturer_name
           FROM products p JOIN manufacturers m ON m.id = p.manufacturer_id
           WHERE p.manufacturer_id = ?
           ORDER BY p.name""",
        (m["id"],),
    ).fetchall()
    return {
        "brand": m["name"],
        "url": m["url"] or "",
        "products": [row_to_product(r) for r in rows],
    }


def search_products(qs):
    brand = _q(qs, "brand")
    category = _q(qs, "category")
    q = _q(qs, "q").strip()
    sort = _q(qs, "sort", "name_asc")
    try:
        page = max(1, int(_q(qs, "page", "1")))
        page_size = _q(qs, "page_size", "24")
        page_size = 10_000 if page_size == "all" else max(1, min(200, int(page_size)))
    except ValueError:
        page, page_size = 1, 24

    where = ["1=1"]
    args = []
    if brand:
        where.append("m.name = ?")
        args.append(brand)
    if category:
        where.append("p.category = ?")
        args.append(category)
    if q:
        like = f"%{q}%"
        where.append(
            "(p.name LIKE ? OR p.sku LIKE ? OR p.collection LIKE ? OR p.description LIKE ? OR m.name LIKE ?)"
        )
        args.extend([like, like, like, like, like])

    order = {
        "name_desc": "p.name DESC",
        "brand_asc": "m.name ASC, p.name ASC",
        "category_asc": "p.category ASC, p.name ASC",
        "photos_desc": "p.image_count DESC, p.name ASC",
    }.get(sort, "p.name ASC")

    where_sql = " AND ".join(where)
    total = DB.execute(
        f"""SELECT COUNT(*) FROM products p
            JOIN manufacturers m ON m.id = p.manufacturer_id
            WHERE {where_sql}""",
        args,
    ).fetchone()[0]
    offset = (page - 1) * page_size
    rows = DB.execute(
        f"""SELECT p.*, m.name AS manufacturer_name
            FROM products p JOIN manufacturers m ON m.id = p.manufacturer_id
            WHERE {where_sql}
            ORDER BY {order}
            LIMIT ? OFFSET ?""",
        args + [page_size, offset],
    ).fetchall()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "products": [row_to_product(r) for r in rows],
    }


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def translate_path(self, path):
        if path == "/":
            path = "/home.html"
        elif path == "/master_catalog.html":
            path = "/catalog.html"
        return super().translate_path(path)

    def send_head(self):
        path = urlparse(self.path).path
        if path not in {"/", "/home.html", "/catalog.html", "/master_catalog.html",
                        "/house.html", "/manufacturers.html", "/logo.svg",
                        "/manufacturers_with_url.json", "/manufacturers_with_url.csv"}:
            self.send_error(404)
            return None
        return super().send_head()

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        if parsed.path == "/api/stats":
            return _json(self, stats())
        if parsed.path == "/api/brands":
            return _json(self, brands())
        if parsed.path == "/api/categories":
            return _json(self, categories())
        if parsed.path == "/api/house":
            return _json(self, house_payload(_q(qs, "brand")))
        if parsed.path == "/api/products":
            return _json(self, search_products(qs))
        return super().do_GET()


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    s = stats()
    print(f"SQLite {s['products']:,} products / {s['brands']:,} brands")
    url = f"http://127.0.0.1:{PORT}/"
    with Server(("127.0.0.1", PORT), Handler) as httpd:
        print(f"Aareas library at {url}")
        if os.environ.get("MASTER_CATALOG_NO_BROWSER") != "1":
            webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
