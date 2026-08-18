"""Map messy crawl categories onto a fixed materials-library list."""
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
    "us", "uk", "ca", "en-us", "en-ca", "en-gb", "de-de", "es-ar", "fr-fr", "it-it",
}
_JUNK_SEG = {
    "product", "products", "catalog", "catalogue", "shop", "store",
    "collection", "collections", "blog", "news", "page", "pages",
    "item", "items", "prodotto", "produits", "produkt", "category",
    "product-category", "p", "post", "all-products", "sample", "samples",
}

# First match wins. More specific groups first.
_RULES = [
    ("Acoustics", (
        "acoustic", "acoustics", "sound design", "sound-design",
        "baffle", "felt panel",
    )),
    ("Wall Protection", (
        "wall protection", "wall-protection", "korogard",
        "corner guard", "kick plate", "rub strip", "crash rail",
        "handrail",
    )),
    ("Wallcoverings", (
        "wallcovering", "wall-covering", "wall covering",
        "wallpaper", "wall paper", "mural", "korographics",
        "digital lab", "digital-lab",
    )),
    ("Rugs", (
        "area rug", "area rugs", "rugs", "rug sample",
        "/rugs/", "carpet tile",
    )),
    ("Lighting", (
        "lighting", "light fixture", "chandelier", "sconce",
        "pendant", "luminaire", "lamp", "ceiling light",
        "table lamp", "floor lamp", "ceiling fan",
    )),
    ("Bath & Kitchen", (
        "bathroom", "bath ", "faucet", "lavatory", "toilet",
        "bathtub", "shower", "vanity", "kitchen", "appliance",
        "sink", "tub filler", "bidet",
    )),
    ("Tile & Stone", (
        "tile", "mosaic", "porcelain", "ceramic", "terrazzo",
        "stone look", "wood look", "concrete look", "marble look",
        "fabric look", "metallic look", "natural stone", "travertine",
        "quarry", "paver", "daltile",
    )),
    ("Flooring", (
        "flooring", "hardwood", "engineered wood", "lvp",
        "vinyl plank", "laminate floor", "parquet",
        "wood floor", "floors",
    )),
    ("Furniture", (
        "furniture", "sofa", "sectional", "loveseat", "armchair",
        "lounge", "dining", "nightstand", "dresser", "credenza",
        "cabinet", "sideboard", "ottoman", "stool", "bench",
        "desk", "bookcase", "bed ", "beds", "mobili", "divan",
        "chaise",
    )),
    ("Textiles", (
        "upholstery", "fabric", "textile", "drapery", "curtain",
        "leather", "sunbrella",
    )),
    ("Surfaces", (
        "countertop", "quartz", "solid surface", "hpl",
        "reatec", "veneer", "decorative film",
        "surface material",
    )),
]

_BRAND = {
    "daltile": "Tile & Stone",
    "artistic tile": "Tile & Stone",
    "architectural ceramics": "Tile & Stone",
    "adex usa": "Tile & Stone",
    "centura tile": "Tile & Stone",
    "koroseal": "Wallcoverings",
    "elitis": "Wallcoverings",
    "wall and wall": "Wallcoverings",
    "boutique rugs": "Rugs",
    "benjamin rugs & furniture": "Rugs",
    "toto fabrics": "Textiles",
    "alberta hardwood flooring": "Flooring",
    "coretec floors": "Flooring",
    "kahrs": "Flooring",
    "uniboard": "Flooring",
    "trex": "Flooring",
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
    "cedar & moss": "Lighting",
    "bella figura": "Lighting",
    "arlight": "Lighting",
    "lightstar": "Lighting",
    "kutek mood": "Lighting",
    "casablanca": "Lighting",
    "allen brau": "Bath & Kitchen",
    "abber": "Bath & Kitchen",
    "siemens": "Bath & Kitchen",
}


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


def assign_category(product):
    original = product.get("raw_category")
    if original is None:
        original = product.get("category") or ""
    original = (original or "").strip()
    if original in CATEGORIES:
        return original

    hay = " ".join([
        original,
        product.get("name") or "",
        product.get("collection") or "",
        product.get("url") or "",
        _path_tokens(product.get("url") or ""),
        product.get("manufacturer_name") or "",
    ]).lower()

    for label, keys in _RULES:
        if any(k in hay for k in keys):
            return label

    brand = (product.get("manufacturer_name") or "").strip().lower()
    if brand in _BRAND:
        return _BRAND[brand]
    return "Other"
