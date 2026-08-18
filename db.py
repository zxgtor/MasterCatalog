"""SQLite access. One products table; manufacturer extras live in attrs JSON."""
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "aareas.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS manufacturers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    url TEXT,
    type TEXT,
    logo TEXT,
    contact TEXT,
    email TEXT
);

CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    manufacturer_id INTEGER NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    collection TEXT DEFAULT '',
    category TEXT DEFAULT '',
    raw_category TEXT DEFAULT '',
    sku TEXT DEFAULT '',
    price TEXT DEFAULT '',
    color TEXT DEFAULT '',
    description TEXT DEFAULT '',
    url TEXT DEFAULT '',
    primary_image TEXT DEFAULT '',
    image_count INTEGER DEFAULT 0,
    images TEXT DEFAULT '[]',
    downloads TEXT DEFAULT '[]',
    attrs TEXT DEFAULT '{}',
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(id)
);

CREATE INDEX IF NOT EXISTS idx_products_mfg ON products(manufacturer_id);
CREATE INDEX IF NOT EXISTS idx_products_cat ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
"""

CORE = {
    "id", "manufacturer_id", "manufacturer_name", "name", "collection",
    "category", "raw_category", "sku", "price", "color", "description",
    "url", "primary_image", "image_count", "images", "downloads",
}


def connect(path=None):
    conn = sqlite3.connect(str(path or DB_PATH), check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db(conn=None):
    own = conn is None
    conn = conn or connect()
    conn.executescript(SCHEMA)
    conn.commit()
    if own:
        conn.close()


def product_to_row(p):
    attrs = {}
    for k, v in p.items():
        if k not in CORE and k != "attrs":
            attrs[k] = v
    extra = p.get("attrs")
    if isinstance(extra, dict):
        attrs.update(extra)
    return (
        str(p.get("id") or ""),
        int(p.get("manufacturer_id") or 0),
        p.get("name") or "",
        p.get("collection") or "",
        p.get("category") or "",
        p.get("raw_category") or "",
        p.get("sku") or "",
        p.get("price") or "",
        p.get("color") or "",
        p.get("description") or "",
        p.get("url") or "",
        p.get("primary_image") or "",
        int(p.get("image_count") or 0),
        json.dumps(p.get("images") or [], ensure_ascii=False),
        json.dumps(p.get("downloads") or [], ensure_ascii=False),
        json.dumps(attrs, ensure_ascii=False),
    )


def row_to_product(row):
    p = dict(row)
    p["images"] = json.loads(p.get("images") or "[]")
    p["downloads"] = json.loads(p.get("downloads") or "[]")
    attrs = json.loads(p.pop("attrs", None) or "{}")
    if isinstance(attrs, dict):
        for k, v in attrs.items():
            if k not in p or p[k] in (None, "", [], {}):
                p[k] = v
        p["attrs"] = attrs
    return p
