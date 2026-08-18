import urllib.request
import json
import csv

url = "https://apirc.aareas.com/api/Manufacturers"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=15) as resp:
    res_json = json.loads(resp.read().decode('utf-8'))

manufacturers = res_json.get("responseObject", [])

with_url = []
without_url = []

for m in manufacturers:
    m_url = m.get("url")
    if m_url and isinstance(m_url, str) and m_url.strip():
        # normalize url if needed
        clean_url = m_url.strip()
        if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
            clean_url = "https://" + clean_url
        with_url.append({
            "id": m.get("id"),
            "name": (m.get("manufacturerName") or "").strip(),
            "url": clean_url,
            "type": m.get("type") or "",
            "category": m.get("category") or "",
            "contact": m.get("contact") or "",
            "email": m.get("eMail") or "",
            "logo": m.get("logo") or ""
        })
    else:
        without_url.append({
            "id": m.get("id"),
            "name": (m.get("manufacturerName") or "").strip(),
            "type": m.get("type") or ""
        })

# Sort by name
with_url.sort(key=lambda x: x["name"].lower())

# Export JSON
json_path = r"d:\Aareas\manufacturers_with_url.json"
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(with_url, f, indent=2, ensure_ascii=False)
print(f"Saved JSON to: {json_path} ({len(with_url)} records)")

# Export CSV
csv_path = r"d:\Aareas\manufacturers_with_url.csv"
with open(csv_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["id", "name", "url", "type", "category", "contact", "email", "logo"])
    writer.writeheader()
    for row in with_url:
        writer.writerow(row)
print(f"Saved CSV to: {csv_path}")

# Build interactive HTML viewer for manufacturers
html_content = f"""<!DOCTYPE html>
<html lang="en" class="h-full">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aareas Manufacturers Directory</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
</head>
<body class="h-full bg-slate-50 dark:bg-slate-950 text-slate-800 dark:text-slate-100 font-sans antialiased">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <!-- Header -->
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-slate-200 dark:border-slate-800">
            <div>
                <div class="flex items-center gap-2">
                    <h1 class="text-2xl font-bold text-slate-900 dark:text-white">Manufacturer Directory</h1>
                    <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300">
                        {len(with_url)} with URLs
                    </span>
                </div>
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">Source: https://apirc.aareas.com/api/Manufacturers (Total: {len(manufacturers)} | With URL: {len(with_url)} | Missing: {len(without_url)})</p>
            </div>
            <div class="flex items-center gap-3">
                <a href="manufacturers_with_url.csv" download class="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium bg-white dark:bg-slate-800 hover:bg-slate-50 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xs transition">
                    <i data-lucide="download" class="w-4 h-4 text-slate-500"></i> Download CSV
                </a>
                <a href="manufacturers_with_url.json" download class="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium bg-white dark:bg-slate-800 hover:bg-slate-50 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xs transition">
                    <i data-lucide="file-json" class="w-4 h-4 text-slate-500"></i> Download JSON
                </a>
            </div>
        </div>

        <!-- Search Bar -->
        <div class="my-6">
            <div class="relative max-w-md">
                <i data-lucide="search" class="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400"></i>
                <input 
                    type="text" 
                    id="filterInput" 
                    placeholder="Search by manufacturer name, URL, type, or ID..."
                    class="w-full pl-10 pr-4 py-2.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-amber-500 shadow-xs"
                >
            </div>
        </div>

        <!-- Results Table -->
        <div class="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-xs">
            <div class="overflow-x-auto">
                <table class="w-full text-left text-xs">
                    <thead class="bg-slate-50 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 font-semibold uppercase">
                        <tr>
                            <th class="p-3.5 w-16">ID</th>
                            <th class="p-3.5">Manufacturer Name</th>
                            <th class="p-3.5">Website URL</th>
                            <th class="p-3.5">Type</th>
                            <th class="p-3.5">Category</th>
                            <th class="p-3.5 text-right">Action</th>
                        </tr>
                    </thead>
                    <tbody id="tableBody" class="divide-y divide-slate-100 dark:divide-slate-800 text-slate-700 dark:text-slate-300">
                    </tbody>
                </table>
            </div>
        </div>

        <div id="footerStats" class="mt-4 text-xs text-slate-500 dark:text-slate-400">
            Showing {len(with_url)} manufacturers
        </div>
    </div>

    <script>
        const data = {json.dumps(with_url, ensure_ascii=False)};
        const tableBody = document.getElementById('tableBody');
        const filterInput = document.getElementById('filterInput');
        const footerStats = document.getElementById('footerStats');

        function render(list) {{
            tableBody.innerHTML = list.map(m => `
                <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition">
                    <td class="p-3.5 font-mono text-slate-400">${{m.id}}</td>
                    <td class="p-3.5 font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                        ${{m.logo ? `<img src="${{m.logo}}" alt="" class="w-5 h-5 object-contain rounded" onerror="this.remove()">` : ''}}
                        <span>${{m.name}}</span>
                    </td>
                    <td class="p-3.5">
                        <a href="${{m.url}}" target="_blank" class="text-amber-600 dark:text-amber-400 hover:underline font-mono text-[11px] truncate max-w-xs block">
                            ${{m.url}}
                        </a>
                    </td>
                    <td class="p-3.5"><span class="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 text-[11px]">${{m.type || '-'}}</span></td>
                    <td class="p-3.5 text-slate-500">${{m.category || '-'}}</td>
                    <td class="p-3.5 text-right">
                        <a href="${{m.url}}" target="_blank" class="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium bg-amber-50 hover:bg-amber-100 dark:bg-amber-950/50 dark:hover:bg-amber-900 text-amber-700 dark:text-amber-300 rounded-lg transition">
                            <span>Visit</span>
                            <i data-lucide="external-link" class="w-3 h-3"></i>
                        </a>
                    </td>
                </tr>
            `).join('');
            footerStats.innerText = `Showing ${{list.length}} of ${{data.length}} manufacturers with URLs`;
            if (window.lucide) lucide.createIcons();
        }}

        filterInput.addEventListener('input', (e) => {{
            const q = e.target.value.toLowerCase().trim();
            if (!q) return render(data);
            const filtered = data.filter(m => 
                m.name.toLowerCase().includes(q) || 
                m.url.toLowerCase().includes(q) || 
                m.type.toLowerCase().includes(q) ||
                (m.id && m.id.toString().includes(q))
            );
            render(filtered);
        }});

        render(data);
    </script>
</body>
</html>
"""

html_path = r"d:\Aareas\manufacturers.html"
with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_content)
print(f"Saved HTML viewer to: {html_path}")
