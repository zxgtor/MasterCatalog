import json
import urllib.request
import urllib.parse
import re
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://apirc.aareas.com/api/Manufacturers"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
    res_json = json.loads(resp.read().decode('utf-8'))

manufacturers = res_json.get("responseObject", [])
missing = [m for m in manufacturers if not m.get("url") or not str(m.get("url")).strip()]

print(f"Total manufacturers with missing URL: {len(missing)}")

# Well known domain heuristics for missing manufacturers
resolved = []
for m in missing:
    name = (m.get("manufacturerName") or "").strip()
    clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', name).lower().strip()
    words = clean_name.split()
    
    # Generate candidate domain names
    candidates = []
    if len(words) == 1:
        candidates.append(f"https://www.{words[0]}.com")
    elif len(words) >= 2:
        candidates.append(f"https://www.{''.join(words)}.com")
        candidates.append(f"https://www.{'-'.join(words)}.com")
        candidates.append(f"https://www.{words[0]}.com")

    found_url = ""
    for cand in candidates:
        try:
            req_c = urllib.request.Request(cand, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req_c, context=ctx, timeout=4) as cresp:
                if cresp.getcode() in [200, 301, 302]:
                    found_url = cand
                    break
        except:
            continue
            
    if found_url:
        print(f"  + Resolved [{m.get('id')}] '{name}' -> {found_url}")
        resolved.append({
            "id": m.get("id"),
            "name": name,
            "url": found_url,
            "type": m.get("type") or "manufactory",
            "category": m.get("category") or "",
            "contact": m.get("contact") or "",
            "email": m.get("eMail") or "",
            "logo": m.get("logo") or ""
        })
    else:
        print(f"  - Could not auto-resolve: '{name}'")

print(f"\nSuccessfully resolved {len(resolved)} / {len(missing)} missing URLs.")

# Update manufacturers_with_url.json
json_path = r"d:\Aareas\manufacturers_with_url.json"
with open(json_path, "r", encoding="utf-8") as f:
    current_with_url = json.load(f)

existing_ids = {x["id"] for x in current_with_url}
for r in resolved:
    if r["id"] not in existing_ids:
        current_with_url.append(r)

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(current_with_url, f, indent=2, ensure_ascii=False)
print(f"Updated {json_path} to {len(current_with_url)} total manufacturers with URLs.")
