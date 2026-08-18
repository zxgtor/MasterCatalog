import json
import urllib.request
import ssl
import time
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
MAX_WORKERS = 35
TIMEOUT = 6

# Load manufacturers
with open(r"d:\Aareas\manufacturers_with_url.json", "r", encoding="utf-8") as f:
    manufacturers = json.load(f)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def probe_manufacturer(m):
    url = m["url"].rstrip("/")
    # Clean base domain
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    
    result = {
        "id": m["id"],
        "name": m["name"],
        "url": url,
        "base_url": base_url,
        "category": m.get("category"),
        "type": m.get("type"),
        "logo": m.get("logo"),
        "feed_type": "none",
        "feed_url": "",
        "product_count_estimate": 0,
        "accessible": False
    }

    # 1. Test Shopify endpoint
    try:
        shopify_endpoint = f"{base_url}/products.json?limit=5"
        req = urllib.request.Request(shopify_endpoint, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, context=ctx, timeout=TIMEOUT) as resp:
            if resp.getcode() == 200:
                body = resp.read()
                data = json.loads(body.decode('utf-8'))
                if "products" in data and isinstance(data["products"], list) and len(data["products"]) > 0:
                    result["feed_type"] = "shopify"
                    result["feed_url"] = f"{base_url}/products.json"
                    result["product_count_estimate"] = len(data["products"])
                    result["accessible"] = True
                    return result
    except:
        pass

    # 2. Test XML Sitemap
    try:
        sitemap_endpoint = f"{base_url}/sitemap.xml"
        req = urllib.request.Request(sitemap_endpoint, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, context=ctx, timeout=TIMEOUT) as resp:
            if resp.getcode() == 200:
                content = resp.read(2048)
                if b'<urlset' in content or b'<sitemapindex' in content:
                    result["feed_type"] = "sitemap"
                    result["feed_url"] = sitemap_endpoint
                    result["accessible"] = True
                    return result
    except:
        pass

    # 3. Test basic reachability
    try:
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, context=ctx, timeout=TIMEOUT) as resp:
            if resp.getcode() in [200, 301, 302]:
                result["feed_type"] = "html_site"
                result["accessible"] = True
    except:
        result["accessible"] = False

    return result

def main():
    start_time = time.time()
    total = len(manufacturers)
    print(f"Starting discovery probe across {total} manufacturer domains with {MAX_WORKERS} workers...")

    results = []
    completed = 0
    shopify_count = 0
    sitemap_count = 0
    accessible_count = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_m = {executor.submit(probe_manufacturer, m): m for m in manufacturers}
        for future in as_completed(future_to_m):
            completed += 1
            res = future.result()
            results.append(res)

            if res["feed_type"] == "shopify":
                shopify_count += 1
            elif res["feed_type"] == "sitemap":
                sitemap_count += 1
            if res["accessible"]:
                accessible_count += 1

            if completed % 100 == 0 or completed == total:
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                print(f"Progress: {completed}/{total} ({(completed/total)*100:.1f}%) | Shopify: {shopify_count} | Sitemaps: {sitemap_count} | Accessible: {accessible_count} | Speed: {rate:.1f} sites/sec")

    # Save discovery matrix
    out_path = r"d:\Aareas\manufacturer_feed_matrix.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nProbe Complete in {time.time()-start_time:.1f}s!")
    print(f"Saved discovery matrix to: {out_path}")

if __name__ == "__main__":
    main()
