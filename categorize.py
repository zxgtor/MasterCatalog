"""Map messy crawl categories onto a fixed materials-library list."""
import re
from urllib.parse import urlparse

CATEGORIES = [
    "Acoustics",
    "Bath & Kitchen",
    "Flooring",
    "Furniture",
    "Lighting",
    "Other",
    "Rugs",
    "Surfaces",
    "Textiles",
    "Tile & Stone",
    "Wall Protection",
    "Wallcoverings",
]

_LOCALES = {
    "en", "fr", "de", "it", "es", "pt", "nl", "pl", "ru", "ja", "zh",
    "us", "uk", "ca", "nz", "en-us", "en-ca", "en-gb", "de-de", "es-ar",
    "fr-fr", "it-it", "fr-ch", "fr-ca", "en-nz",
}
_JUNK_SEG = {
    "product", "products", "catalog", "catalogue", "katalog", "shop", "store",
    "collection", "collections", "blog", "news", "page", "pages",
    "item", "items", "prodotto", "produits", "produkt", "category",
    "product-category", "p", "post", "all-products", "sample", "samples",
    "vare",
}

# Content / non-product pages. First-match category rules must not run on these.
_CONTENT_RAW = {
    "blog", "news", "press", "pressd", "journal", "stories", "articles",
    "inspiration", "insights", "gallery", "about", "careers", "career",
    "faq", "faqs", "support", "contact", "resources", "locations",
    "company said blog", "news events", "ideas inspiration",
    "partner spotlights", "design inspirations", "project planning",
    "our mission", "new blog 1",
}
_CONTENT_PATH = re.compile(
    r"/(blog|news|press|careers?|about|faq|faqs|inspiration|stories|"
    r"journal|articles|insights|gallery|locations|support|contact|"
    r"resources|privacy|login|cart|account)(/|$)",
    re.I,
)

# Word-or-phrase rules. More specific groups first. Phrases with spaces/slashes
# are substring matches; single tokens use word boundaries (tile ≠ textile).
_RULES = [
    ("Acoustics", (
        "acoustic", "acoustics", "sound design", "sound-design",
        "felt panel", "acoustic panel",
    )),
    ("Wall Protection", (
        "wall protection", "wall-protection", "korogard",
        "corner guard", "kick plate", "rub strip", "crash rail",
    )),
    ("Tile & Stone", (
        "tile", "tiles", "mosaic", "mosaics", "porcelain",
        "terrazzo", "stone look", "wood look", "concrete look",
        "marble look", "fabric look", "metallic look",
        "natural stone", "ceramic tile", "porcelain tile",
        "quarry tile", "daltile",
    )),
    ("Wallcoverings", (
        "wallcovering", "wallcoverings", "wall-covering", "wall covering",
        "wallpaper", "wall paper", "mural", "murals", "korographics",
        "digital lab", "digital-lab",
    )),
    ("Rugs", (
        "area rug", "area rugs", "rug", "rugs", "rug sample",
        "/rugs/", "carpet tile",
    )),
    ("Furniture", (
        "furniture", "sofa", "sofas", "sectional", "loveseat",
        "armchair", "lounge", "nightstand", "dresser", "credenza",
        "sideboard", "ottoman", "bookcase", "chaise", "mobili", "divan",
        "dining table", "dining chair", "dining bench",
        "coffee table", "side table", "lamp table",
        "kitchen & dining", "kitchen and dining",
        "bed", "beds", "daybed", "stool", "stools",
        "bench", "benches", "desk", "desks",
        "cabinet", "cabinets", "wardrobe", "wardrobes",
        "mattress",
    )),
    ("Lighting", (
        "lighting", "light fixture", "chandelier", "sconce",
        "pendant", "luminaire", "lamp", "lamps", "ceiling light",
        "table lamp", "floor lamp", "ceiling fan", "sconces",
    )),
    ("Bath & Kitchen", (
        "bathroom", "bathrooms", "faucet", "faucets", "lavatory",
        "toilet", "bathtub", "shower", "vanity", "appliance",
        "sink", "sinks", "tub filler", "bidet",
        "kitchen faucet", "kitchen sink", "kitchen appliance",
    )),
    ("Flooring", (
        "flooring", "hardwood", "engineered wood", "lvp",
        "vinyl plank", "luxury vinyl", "vinyl flooring",
        "laminate", "parquet", "rigid core",
        "wood floor", "decking", "composite deck",
    )),
    ("Textiles", (
        "upholstery", "fabric", "fabrics", "textile", "textiles",
        "drapery", "curtain", "curtains", "sunbrella",
    )),
    ("Surfaces", (
        "countertop", "countertops", "solid surface", "hpl",
        "reatec", "decorative film", "surface material",
        "quartz counter", "quartz surface",
    )),
]

# Extra Bath signal: bare "kitchen" / "bath" only when not furniture dining.
_KITCHEN_OK = re.compile(r"\b(kitchen|kitchens|bath)\b")
_KITCHEN_BLOCK = re.compile(
    r"\b(dining|table|tables|chair|chairs|bench|benches|sofa|stool|stools)\b"
)

# lamp table is furniture; table lamp is lighting. Checked before Lighting.
_LAMP_TABLE = re.compile(r"\blamp tables?\b")
_TABLE_LAMP = re.compile(r"\btable lamps?\b")

# leather seating is furniture, not textiles.
_LEATHER_FURN = re.compile(
    r"\b(sofa|sofas|sectional|armchair|lounge|ottoman|chair|chairs)\b"
)

_BRAND = {
    "daltile": "Tile & Stone",
    "artistic tile": "Tile & Stone",
    "architectural ceramics": "Tile & Stone",
    "adex usa": "Tile & Stone",
    "centura tile": "Tile & Stone",
    "interceramic": "Tile & Stone",
    "american olean": "Tile & Stone",
    "koroseal": "Wallcoverings",
    "elitis": "Wallcoverings",
    "wall and wall": "Wallcoverings",
    "maya romanoff": "Wallcoverings",
    "murals wallpaper": "Wallcoverings",
    "boutique rugs": "Rugs",
    "benjamin rugs & furniture": "Rugs",
    "toto fabrics": "Textiles",
    "mayer fabrics": "Textiles",
    "alberta hardwood flooring": "Flooring",
    "coretec floors": "Flooring",
    "kahrs": "Flooring",
    "uniboard": "Flooring",
    "shaw flooring": "Flooring",
    "kentwood floors": "Flooring",
    "aa floors": "Flooring",
    "ambassador flooring": "Flooring",
    "mannington": "Flooring",
    "caracole": "Furniture",
    "blu dot": "Furniture",
    "bludot": "Furniture",
    "cfc furniture": "Furniture",
    "cane line": "Furniture",
    "cane-line": "Furniture",
    "croft house": "Furniture",
    "baxter": "Furniture",
    "globewest": "Furniture",
    "gramercy home": "Furniture",
    "kastel": "Furniture",
    "scab design": "Furniture",
    "depadova": "Furniture",
    "cazarina": "Furniture",
    "cofur": "Furniture",
    "dovlet house": "Furniture",
    "turri": "Furniture",
    "arketipo": "Furniture",
    "porada": "Furniture",
    "alf dafre": "Furniture",
    "baltus": "Furniture",
    "divan boss": "Furniture",
    "inspire q": "Furniture",
    "1920r": "Furniture",
    "cilek": "Furniture",
    "cedar & moss": "Lighting",
    "bella figura": "Lighting",
    "arlight": "Lighting",
    "lightstar": "Lighting",
    "kutek mood": "Lighting",
    "casablanca": "Lighting",
    "progress electric": "Lighting",
    "allen brau": "Bath & Kitchen",
    "abber": "Bath & Kitchen",
    "siemens": "Bath & Kitchen",
    "caesarstone": "Surfaces",
    "cambria": "Surfaces",
}

_WORD_RE = {}


def _word_re(token):
    compiled = _WORD_RE.get(token)
    if compiled is None:
        compiled = re.compile(r"\b" + re.escape(token) + r"\b")
        _WORD_RE[token] = compiled
    return compiled


def _has(hay, keys):
    for key in keys:
        if " " in key or "/" in key or "-" in key:
            if key in hay:
                return True
        elif _word_re(key).search(hay):
            return True
    return False


def _path_tokens(url):
    if not url:
        return ""
    parts = urlparse(url).path.lower().strip("/").replace("_", "-").split("/")
    kept = []
    for part in parts:
        token = part.replace("-", " ")
        if token in _LOCALES or token in _JUNK_SEG:
            continue
        kept.append(token)
    return " ".join(kept)


def _is_content_page(url, raw):
    raw_l = (raw or "").strip().lower()
    if raw_l in _CONTENT_RAW:
        return True
    if not url:
        return False
    path = urlparse(url).path or ""
    if _CONTENT_PATH.search(path):
        return True
    return False


def _raw_hint(product):
    """Use site category only if it is not already one of our 12 labels.

    Assigned labels must not lock in a previous bad rematch.
    """
    raw = (product.get("raw_category") or "").strip()
    if raw:
        return raw
    cat = (product.get("category") or "").strip()
    if cat and cat not in CATEGORIES:
        return cat
    return ""


def assign_category(product):
    raw = _raw_hint(product)
    url = product.get("url") or ""
    if _is_content_page(url, raw):
        return "Other"

    brand = (product.get("manufacturer_name") or "").strip().lower()
    path = urlparse(url).path.lower() if url else ""

    # Trex is mixed (decking vs railing). Do not brand-dump everything to Flooring.
    if brand == "trex":
        if "rail" in path or "railing" in (product.get("name") or "").lower():
            return "Other"
        return "Flooring"

    hay = " ".join([
        raw,
        product.get("name") or "",
        product.get("collection") or "",
        url,
        _path_tokens(url),
    ]).lower()
    hay = hay.replace("_", " ").replace("-", " ")

    if _LAMP_TABLE.search(hay) and not _TABLE_LAMP.search(hay):
        if not _has(hay, ("chandelier", "sconce", "pendant", "luminaire")):
            return "Furniture"

    if _word_re("leather").search(hay) and _LEATHER_FURN.search(hay):
        return "Furniture"

    for label, keys in _RULES:
        if _has(hay, keys):
            return label

    if _KITCHEN_OK.search(hay) and not _KITCHEN_BLOCK.search(hay):
        return "Bath & Kitchen"

    if brand in _BRAND:
        return _BRAND[brand]
    return "Other"
