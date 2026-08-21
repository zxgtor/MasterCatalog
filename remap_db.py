"""Rematch products.category in SQLite using current categorize rules."""
from collections import Counter

from categorize import CATEGORIES, assign_category
from db import connect

CASES = [
    ({"name": "Anzea Concierge Tickets for Two Upholstery Fabric",
      "raw_category": "Upholstery Fabric",
      "url": "https://www.totofabrics.com/products/anzea-concierge-tickets-for-two-upholstery-fabric",
      "manufacturer_name": "Toto Fabrics"}, "Textiles"),
    ({"name": "Braemore Textiles Bamboo Vines Cotton Print Fabric",
      "raw_category": "Print Fabric",
      "url": "https://www.totofabrics.com/products/braemore-textiles-bamboo-vines-cotton-print",
      "manufacturer_name": "Toto Fabrics"}, "Textiles"),
    ({"name": "4/4 Round Dining Table",
      "raw_category": "Kitchen & Dining Room Tables",
      "url": "https://www.bludot.com/products/4-4-round-dining-table-sale",
      "manufacturer_name": "Blu Dot"}, "Furniture"),
    ({"name": "0 Degree Rail Gasket Pack Horizontal",
      "raw_category": "Products",
      "url": "https://www.trex.com/products/railing/transcend/0-degree-rail-gasket-pack-horizontal.wt00hgask/",
      "manufacturer_name": "Trex"}, "Other"),
    ({"name": "Trex Transcend Decking",
      "raw_category": "Products",
      "url": "https://www.trex.com/products/decking/transcend/spiced-rum/",
      "manufacturer_name": "Trex"}, "Flooring"),
    ({"name": "Bone Ceramic",
      "raw_category": "Sample",
      "url": "https://cedarandmoss.com/products/bone-sample",
      "manufacturer_name": "Cedar & Moss"}, "Lighting"),
    ({"name": "12x12 Murals Blend Bright White Glossy Wall Tile",
      "raw_category": "Sample",
      "url": "https://www.architecturalceramics.com/products/s-w63463464129",
      "manufacturer_name": "Architectural Ceramics"}, "Tile & Stone"),
    ({"name": "Zaft Weave Basalt ZF21-04",
      "raw_category": "Wallcoverings",
      "url": "https://koroseal.com/products/wallcoverings/zaft-weave",
      "manufacturer_name": "Koroseal"}, "Wallcoverings"),
    ({"name": "Interior Lighting Guide",
      "raw_category": "Company Said Blog",
      "url": "https://www.curreyandcompany.com/company-said-blog/2025/september/interior-lighting-g",
      "manufacturer_name": "Currey & Company"}, "Other"),
    ({"name": "Acre",
      "raw_category": "Wood Look",
      "url": "https://www.daltile.com/products/wood-look/bellamy-place/acre",
      "manufacturer_name": "Daltile"}, "Tile & Stone"),
    ({"name": '12" X 24" Geostone matte natural beige floor or wall tile',
      "raw_category": "Ceramic Tile",
      "url": "https://albertahardwood.com/products/12-x-24-geostone-matte-natural-beige-floor-or-wall-ti",
      "manufacturer_name": "Alberta Hardwood Flooring"}, "Tile & Stone"),
    ({"name": "Appalachian Hard Maple Travertine",
      "raw_category": "Product",
      "url": "https://www.aafloors.ca/product/appalachian-hard-maple-travertine/",
      "manufacturer_name": "AA Floors"}, "Flooring"),
    ({"name": "Bfc07Ss Stainless Steel Baffle Filter",
      "raw_category": "Product",
      "url": "https://cyclonerangehoods.com/product/bfc07ss-stainless-steel-baffle-filter/",
      "manufacturer_name": "Cyclone"}, "Other"),
    ({"name": "6084 4",
      "raw_category": "Handrail Fittings",
      "url": "https://houseofforgings.net/handrail-fittings/6084-4/",
      "manufacturer_name": "HF Stair and Railing"}, "Other"),
    ({"name": "Brett Lamp Table",
      "raw_category": "Side Tables",
      "url": "https://franceandson.ca/products/brett-lamp-table",
      "manufacturer_name": "CFC Furniture"}, "Furniture"),
    ({"name": "Astrid 4 Light Chandelier",
      "raw_category": "Chandeliers",
      "url": "https://franceandson.ca/products/astrid-4-light-chandelier-aged-brass-black46054",
      "manufacturer_name": "CFC Furniture"}, "Lighting"),
    ({"name": "Kalief Olive Solid Area Rug",
      "raw_category": "Rugs",
      "url": "https://boutiquerugs.com/products/kalief-olive-solid-area-rug",
      "manufacturer_name": "Boutique Rugs"}, "Rugs"),
    ({"name": "516 Locura",
      "raw_category": "Fr",
      "url": "https://www.caesarstone.ca/fr/countertops/516-locura/",
      "manufacturer_name": "Caesarstone"}, "Surfaces"),
    ({"name": "Kitchen With Peninsula",
      "raw_category": "En",
      "url": "https://www.lagodesign.com/en/kitchen-with-peninsula/",
      "manufacturer_name": "Lago"}, "Bath & Kitchen"),
    ({"name": "2026 Kitchen Design Trends",
      "raw_category": "Design Inspirations",
      "url": "https://1951cabinetry.com/design-inspirations/articles/2026-kitchen-design-trends",
      "manufacturer_name": "1951 Cabinetry"}, "Other"),
    ({"name": "Arc-Com Ceramica Jungle Upholstery Vinyl",
      "raw_category": "Upholstery Fabric",
      "url": "https://www.totofabrics.com/products/arc-com-ceramica-jungle-upholstery-vinyl",
      "manufacturer_name": "Toto Fabrics"}, "Textiles"),
    ({"name": "2 Doors Wardrobe Black (Glass Door)",
      "raw_category": "Dolaplar",
      "url": "https://cilekworld.com/products/2-doors-wardrobe-black",
      "manufacturer_name": "CILEK"}, "Furniture"),
    ({"name": "Adurapro Rigid",
      "raw_category": "Residential",
      "url": "https://www.mannington.com/residential/products/luxury-vinyl/adurapro-rigid",
      "manufacturer_name": "Mannington"}, "Flooring"),
    ({"name": "Cherner Wood Leg Stool Upholstered Seat",
      "raw_category": "Pages",
      "url": "https://hivemodern.com/pages/product3773/cherner-wood-leg-stool-upholstered-seat",
      "manufacturer_name": "Hive Modern"}, "Furniture"),
]


def self_check():
    failed = 0
    for product, expect in CASES:
        got = assign_category(product)
        if got != expect:
            failed += 1
            print(f"  FAIL {expect!r} != {got!r}  {product['name'][:50]}")
    print(f"self-check {len(CASES) - failed}/{len(CASES)} passed")
    return failed == 0


def main():
    if not self_check():
        raise SystemExit("rules failed self-check; not writing db")

    conn = connect()
    before = Counter(
        r[0] for r in conn.execute("SELECT category FROM products")
    )
    rows = conn.execute(
        """SELECT p.id, p.name, p.collection, p.category, p.raw_category, p.url,
                  m.name AS manufacturer_name
           FROM products p JOIN manufacturers m ON m.id = p.manufacturer_id"""
    ).fetchall()

    flipped = Counter()
    updates = []
    for r in rows:
        product = {
            "name": r["name"],
            "collection": r["collection"],
            "category": r["category"],
            "raw_category": r["raw_category"],
            "url": r["url"],
            "manufacturer_name": r["manufacturer_name"],
        }
        new = assign_category(product)
        if new != r["category"]:
            updates.append((new, r["id"]))
            flipped[(r["category"] or "", new)] += 1

    for i in range(0, len(updates), 2000):
        conn.executemany(
            "UPDATE products SET category=? WHERE id=?",
            updates[i:i + 2000],
        )
    conn.commit()

    after = Counter(
        r[0] for r in conn.execute("SELECT category FROM products")
    )
    print(f"updated {len(updates)} / {len(rows)}")
    print("\ncounts:")
    for label in CATEGORIES:
        print(f"  {after.get(label, 0):6}  {label}   ({after.get(label, 0) - before.get(label, 0):+d})")
    print("\ntop flips:")
    for (old, new), n in flipped.most_common(20):
        print(f"  {n:5}  {old} -> {new}")
    conn.close()


if __name__ == "__main__":
    main()
