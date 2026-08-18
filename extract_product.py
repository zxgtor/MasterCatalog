"""Pull SKU, color, overview, specs, and downloads from a product HTML page."""
import json
import re
from html import unescape
from urllib.parse import urljoin

_SKIP_DL = re.compile(
    r"privacy|terms|cookie|login|cart|account|facebook|instagram|pinterest|twitter|linkedin|youtube",
    re.I,
)


def _text(html):
    t = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", unescape(t)).strip()


def _json_ld_products(html):
    out = []
    for block in re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.I | re.S,
    ):
        try:
            data = json.loads(block.strip())
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        if isinstance(data, dict) and "@graph" in data:
            items = data["@graph"]
        for item in items:
            if isinstance(item, dict) and item.get("@type") in ("Product", ["Product"]):
                out.append(item)
    return out


def _trex_variant(html, sku):
    if not sku:
        return {}
    decoded = unescape(html)
    needle = f'"sku":"{sku}"'
    idx = decoded.find(needle)
    if idx < 0:
        return {}
    start = decoded.rfind("{", 0, idx)
    # walk to matching close, cheap
    chunk = decoded[start:start + 4000]
    specs = {}
    for attr in re.findall(
        r'"attributeId":"([^"]+)".*?"value":"([^"]*)"',
        chunk,
    ):
        key, val = attr
        if val and not key.startswith("trex."):
            specs[key.replace("_", " ").title()] = val
    color_m = re.search(r'"colorText":"([^"]+)"', chunk)
    price_m = re.search(r'"formattedFinalPrice":"([^"]+)"', chunk)
    return {
        "specs": specs,
        "color": color_m.group(1) if color_m else "",
        "price": price_m.group(1) if price_m else "",
    }


def extract_page_details(html, page_url):
    details = {
        "sku": "",
        "price": "",
        "color": "",
        "colors": [],
        "description": "",
        "specs": {},
        "downloads": [],
        "primary_image": "",
        "images": [],
    }

    ld = _json_ld_products(html)
    if ld:
        p = ld[0]
        details["sku"] = str(p.get("sku") or "")
        details["description"] = _text(str(p.get("description") or ""))
        img = p.get("image")
        if isinstance(img, list) and img:
            details["primary_image"] = img[0] if isinstance(img[0], str) else ""
            details["images"] = [x for x in img if isinstance(x, str)]
        elif isinstance(img, str):
            details["primary_image"] = img
            details["images"] = [img]
        offers = p.get("offers") or {}
        if isinstance(offers, list) and offers:
            offers = offers[0]
        if isinstance(offers, dict) and offers.get("price"):
            cur = offers.get("priceCurrency") or "USD"
            details["price"] = f"{offers['price']} {cur}".strip()

    sku_m = re.search(r'id=["\']multiSkuValue["\']>\s*([^<]+)', html, re.I)
    if sku_m:
        details["sku"] = sku_m.group(1).strip() or details["sku"]
    if not details["sku"]:
        sku_m = re.search(r"SKU:\s*([A-Z0-9][A-Z0-9\-]{2,})", html, re.I)
        if sku_m:
            details["sku"] = sku_m.group(1).strip()

    color_m = re.search(r'id=["\']color-name["\'][^>]*>\s*([^<]+)', html, re.I)
    if color_m:
        details["color"] = color_m.group(1).strip()
    colors = []
    for name in re.findall(r'data-name=["\']([^"\']+)["\']', html, re.I):
        if name and name not in colors and len(name) < 40:
            colors.append(name)
    details["colors"] = colors[:20]
    if not details["color"] and colors:
        details["color"] = colors[0]

    if not details["description"]:
        og = re.search(r'property=["\']og:description["\'][^>]+content=["\']([^"\']+)', html, re.I)
        if not og:
            og = re.search(r'content=["\']([^"\']+)["\'][^>]+property=["\']og:description', html, re.I)
        if og:
            details["description"] = unescape(og.group(1)).strip()
    short = re.search(r'id=["\']short_description["\'][^>]*>(.*?)</span></span>', html, re.I | re.S)
    if short:
        t = _text(short.group(1))
        if t and len(t) > len(details["description"]):
            details["description"] = t.lstrip("| ").strip()

    variant = _trex_variant(html, details["sku"])
    if variant.get("specs"):
        details["specs"].update(variant["specs"])
    if variant.get("color") and not details["color"]:
        details["color"] = variant["color"]
    if variant.get("price"):
        details["price"] = variant["price"]

    # generic spec tables / definition lists
    for dt, dd in re.findall(r"<dt[^>]*>(.*?)</dt>\s*<dd[^>]*>(.*?)</dd>", html, re.I | re.S):
        k, v = _text(dt), _text(dd)
        if k and v and len(k) < 40 and len(v) < 120 and k.lower() not in details["specs"]:
            details["specs"][k] = v

    downloads = []
    seen = set()
    for href, text in re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.I | re.S):
        label = _text(text)
        href = unescape(href).strip()
        if not href or href.startswith("#") or _SKIP_DL.search(href):
            continue
        low = href.lower()
        if not (low.endswith(".pdf") or ".pdf?" in low or "flippingbook.com" in low):
            continue
            continue
        full = urljoin(page_url, href)
        if full in seen:
            continue
        seen.add(full)
        downloads.append({"name": label or "Download", "url": full})
    details["downloads"] = downloads[:12]
    if details["description"]:
        details["description"] = details["description"].lstrip("| ").strip()
    return details
