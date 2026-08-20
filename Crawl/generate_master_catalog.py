import json
import os

FALLBACK_SVG = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 300' fill='%23f1f5f9'%3E%3Crect width='400' height='300' fill='%23f8fafc'/%3E%3Cpath d='M160 130a20 20 0 100-40 20 20 0 000 40zm-40 90h160l-50-65-35 45-25-30-50 50z' fill='%23cbd5e1'/%3E%3Ctext x='50%25' y='80%25' text-anchor='middle' fill='%2394a3b8' font-family='sans-serif' font-size='14'%3ENo Image Available%3C/text%3E%3C/svg%3E"

def build_master_html_catalog():
    json_path = r"d:\Aareas\master_products.json"
    if not os.path.exists(json_path):
        print(f"Error: {json_path} does not exist yet.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        products = json.load(f)

    try:
        from categorize import assign_category
        for p in products:
            p["category"] = assign_category(p)
    except ImportError:
        pass

    print(f"Loaded {len(products)} products from {json_path}. Generating master_catalog.html...")

    brands = {}
    categories = {}

    for p in products:
        b = p.get("manufacturer_name") or "Unknown"
        brands[b] = brands.get(b, 0) + 1
        
        c = p.get("category") or "General"
        categories[c] = categories.get(c, 0) + 1

    products_json_str = json.dumps(products, ensure_ascii=False)

    html_template = f"""<!DOCTYPE html>
<html lang="en" class="h-full">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="referrer" content="no-referrer">
    <title>Master Multi-Manufacturer Product Catalog</title>
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {{
            darkMode: 'class',
            theme: {{
                extend: {{
                    colors: {{
                        brand: {{
                            50: '#f0fdfa',
                            100: '#ccfbf1',
                            500: '#14b8a6',
                            600: '#0d9488',
                            700: '#0f766e',
                            900: '#134e4a'
                        }}
                    }}
                }}
            }}
        }}
    </script>
    <!-- Lucide Icons -->
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        .custom-scrollbar::-webkit-scrollbar {{
            width: 6px;
            height: 6px;
        }}
        .custom-scrollbar::-webkit-scrollbar-track {{
            background: rgba(0,0,0,0.03);
        }}
        .custom-scrollbar::-webkit-scrollbar-thumb {{
            background: rgba(0,0,0,0.2);
            border-radius: 4px;
        }}
        .card-zoom-img {{
            transition: transform 0.35s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        .product-card:hover .card-zoom-img {{
            transform: scale(1.06);
        }}
    </style>
</head>
<body class="h-full bg-slate-50 dark:bg-slate-950 text-slate-800 dark:text-slate-100 font-sans antialiased transition-colors duration-200">

    <div id="app" class="min-h-full flex flex-col">

        <!-- Top Header Navigation -->
        <header class="sticky top-0 z-40 bg-white/95 dark:bg-slate-900/95 backdrop-blur border-b border-slate-200 dark:border-slate-800 shadow-sm">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div class="flex items-center justify-between h-16 gap-4">
                    <div class="flex items-center gap-3">
                        <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-teal-600 to-emerald-800 flex items-center justify-center text-white shadow-md">
                            <i data-lucide="boxes" class="w-5 h-5"></i>
                        </div>
                        <div>
                            <div class="flex items-center gap-2">
                                <h1 class="text-lg font-bold tracking-tight text-slate-900 dark:text-white">Master Catalog</h1>
                                <span class="px-2 py-0.5 text-xs font-semibold rounded-full bg-teal-100 text-teal-800 dark:bg-teal-900/50 dark:text-teal-300">Multi-Brand</span>
                            </div>
                            <p class="text-xs text-slate-500 dark:text-slate-400">Unified Manufacturer Product Database</p>
                        </div>
                    </div>

                    <div class="flex-1 max-w-xl hidden md:block">
                        <div class="relative">
                            <i data-lucide="search" class="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400"></i>
                            <input 
                                type="text" 
                                id="searchInput" 
                                placeholder="Search by product name, brand, SKU, category, collection..."
                                class="w-full pl-10 pr-9 py-2 bg-slate-100 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:bg-white dark:focus:bg-slate-800 transition"
                            >
                            <button id="clearSearchBtn" class="hidden absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">
                                <i data-lucide="x" class="w-4 h-4"></i>
                            </button>
                        </div>
                    </div>

                    <div class="flex items-center gap-2">
                        <button id="exportBtn" class="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-lg border border-slate-200 dark:border-slate-700 transition">
                            <i data-lucide="download" class="w-4 h-4"></i>
                            <span class="hidden sm:inline">Export CSV</span>
                        </button>
                        <button id="themeToggle" class="p-2 text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition" title="Toggle Theme">
                            <i data-lucide="sun" class="w-5 h-5 hidden dark:block"></i>
                            <i data-lucide="moon" class="w-5 h-5 block dark:hidden"></i>
                        </button>
                    </div>
                </div>

                <div class="pb-3 md:hidden">
                    <div class="relative">
                        <i data-lucide="search" class="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400"></i>
                        <input 
                            type="text" 
                            id="mobileSearchInput" 
                            placeholder="Search products, brands, SKUs..."
                            class="w-full pl-10 pr-4 py-2 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                        >
                    </div>
                </div>
            </div>
        </header>

        <!-- Stats Bar -->
        <div class="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2.5">
                <div class="flex flex-wrap items-center justify-between gap-3 text-xs">
                    <div class="flex items-center gap-4 text-slate-500 dark:text-slate-400">
                        <span><strong class="text-slate-900 dark:text-white font-semibold">{len(products):,}</strong> Total Products</span>
                        <span>•</span>
                        <span><strong class="text-slate-900 dark:text-white font-semibold">{len(brands):,}</strong> Brands</span>
                        <span>•</span>
                        <span><strong class="text-slate-900 dark:text-white font-semibold">{len(categories):,}</strong> Categories</span>
                    </div>

                    <div class="flex items-center gap-3">
                        <div class="flex items-center gap-1 bg-slate-100 dark:bg-slate-800 p-0.5 rounded-lg border border-slate-200 dark:border-slate-700">
                            <button id="viewGridBtn" class="p-1.5 rounded-md text-teal-700 dark:text-teal-400 bg-white dark:bg-slate-700 shadow-xs" title="Grid View">
                                <i data-lucide="grid" class="w-4 h-4"></i>
                            </button>
                            <button id="viewTableBtn" class="p-1.5 rounded-md text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200" title="Table View">
                                <i data-lucide="list" class="w-4 h-4"></i>
                            </button>
                        </div>

                        <select id="sortSelect" class="bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-teal-500">
                            <option value="name_asc">Name (A-Z)</option>
                            <option value="name_desc">Name (Z-A)</option>
                            <option value="brand_asc">Brand (A-Z)</option>
                            <option value="category_asc">Category</option>
                            <option value="photos_desc">Most Photos</option>
                        </select>
                    </div>
                </div>
            </div>
        </div>

        <!-- Main Content -->
        <div class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 flex gap-6">

            <!-- Sidebar -->
            <aside class="w-64 flex-shrink-0 hidden lg:block">
                <div class="sticky top-24 space-y-6">
                    <div class="flex items-center justify-between">
                        <h2 class="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                            <i data-lucide="filter" class="w-3.5 h-3.5"></i> Filter By Brand
                        </h2>
                        <button id="resetFiltersBtn" class="text-xs text-teal-600 dark:text-teal-400 hover:underline font-medium">Reset All</button>
                    </div>

                    <div class="bg-white dark:bg-slate-900 p-4 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xs">
                        <h3 class="text-xs font-semibold text-slate-900 dark:text-white mb-3">Manufacturers</h3>
                        <input id="brandSearchInput" type="text" placeholder="Find brand…"
                            class="w-full mb-2 px-2.5 py-1.5 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-teal-500">
                        <div id="brandFilterList" class="space-y-1 max-h-64 overflow-y-auto custom-scrollbar pr-1"></div>
                    </div>

                    <div class="bg-white dark:bg-slate-900 p-4 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xs">
                        <h3 class="text-xs font-semibold text-slate-900 dark:text-white mb-3">Category</h3>
                        <div id="categoryFilterList" class="space-y-1 max-h-56 overflow-y-auto custom-scrollbar pr-1"></div>
                    </div>
                </div>
            </aside>

            <!-- Products Grid/Table -->
            <main class="flex-1 min-w-0">

                <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
                    <span id="resultCountText" class="text-sm font-semibold text-slate-800 dark:text-slate-200">Showing products...</span>
                    <div id="activeFilterTags" class="flex flex-wrap items-center gap-1.5"></div>
                </div>

                <div id="productGridView" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3 gap-5"></div>

                <div id="productTableView" class="hidden bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-xs">
                    <div class="overflow-x-auto">
                        <table class="w-full text-left text-xs">
                            <thead class="bg-slate-50 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 uppercase font-semibold">
                                <tr>
                                    <th class="p-3 w-16">Preview</th>
                                    <th class="p-3">Product Name</th>
                                    <th class="p-3">Manufacturer</th>
                                    <th class="p-3">Category</th>
                                    <th class="p-3">SKU</th>
                                    <th class="p-3">Price / Specs</th>
                                    <th class="p-3 text-right">Action</th>
                                </tr>
                            </thead>
                            <tbody id="productTableBody" class="divide-y divide-slate-100 dark:divide-slate-800 text-slate-700 dark:text-slate-300"></tbody>
                        </table>
                    </div>
                </div>

                <div id="emptyState" class="hidden text-center py-16 px-4 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xs">
                    <i data-lucide="package-x" class="w-12 h-12 mx-auto text-slate-400 mb-3"></i>
                    <h3 class="text-base font-semibold text-slate-900 dark:text-white">No products match your criteria</h3>
                    <button id="emptyResetBtn" class="mt-4 px-4 py-2 text-xs font-semibold bg-teal-600 hover:bg-teal-700 text-white rounded-xl shadow-xs transition">
                        Clear Filters
                    </button>
                </div>

                <div id="paginationContainer" class="mt-8 flex flex-col sm:flex-row items-center justify-between gap-4 border-t border-slate-200 dark:border-slate-800 pt-4 text-xs">
                    <div class="flex items-center gap-2 text-slate-500 dark:text-slate-400">
                        <span>Items per page:</span>
                        <select id="pageSizeSelect" class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg px-2 py-1 focus:ring-1 focus:ring-teal-500">
                            <option value="24">24</option>
                            <option value="48">48</option>
                            <option value="96">96</option>
                            <option value="all">Show All</option>
                        </select>
                    </div>
                    <div id="paginationControls" class="flex items-center gap-1"></div>
                </div>

            </main>
        </div>

        <!-- Quick View Modal -->
        <div id="quickViewModal" class="fixed inset-0 z-50 hidden bg-slate-950/70 backdrop-blur-xs flex items-center justify-center p-4">
            <div class="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
                <div class="flex items-center justify-between p-5 border-b border-slate-100 dark:border-slate-800">
                    <div>
                        <span id="modalBrandBadge" class="px-2 py-0.5 text-xs font-semibold rounded-md bg-teal-100 text-teal-800 dark:bg-teal-900/40 dark:text-teal-300"></span>
                        <h3 id="modalTitle" class="text-lg font-bold text-slate-900 dark:text-white mt-1"></h3>
                    </div>
                    <button id="closeModalBtn" class="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 transition">
                        <i data-lucide="x" class="w-5 h-5"></i>
                    </button>
                </div>

                <div class="flex-1 overflow-y-auto p-6 grid grid-cols-1 md:grid-cols-2 gap-6 custom-scrollbar">
                    <div class="space-y-3">
                        <div class="relative aspect-square rounded-2xl overflow-hidden bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-center justify-center">
                            <img id="modalMainImg" src="" alt="" class="w-full h-full object-contain p-2" onerror="this.src='{FALLBACK_SVG}'">
                        </div>
                        <div id="modalThumbnails" class="flex items-center gap-2 overflow-x-auto custom-scrollbar pb-2"></div>
                    </div>

                    <div class="space-y-4 text-xs">
                        <div>
                            <h4 class="font-semibold text-slate-900 dark:text-white text-sm mb-1">Product Description</h4>
                            <p id="modalDescription" class="text-slate-600 dark:text-slate-300 leading-relaxed"></p>
                        </div>

                        <div class="border-t border-slate-100 dark:border-slate-800 pt-3">
                            <h4 class="font-semibold text-slate-900 dark:text-white text-sm mb-2">Specifications</h4>
                            <dl class="grid grid-cols-2 gap-2 bg-slate-50 dark:bg-slate-800/50 p-3.5 rounded-xl border border-slate-200/60 dark:border-slate-800">
                                <div>
                                    <dt class="text-slate-400">Manufacturer</dt>
                                    <dd id="modalMfgName" class="font-semibold text-slate-800 dark:text-slate-200"></dd>
                                </div>
                                <div>
                                    <dt class="text-slate-400">Category</dt>
                                    <dd id="modalCategory" class="font-semibold text-slate-800 dark:text-slate-200"></dd>
                                </div>
                                <div>
                                    <dt class="text-slate-400">SKU / Code</dt>
                                    <dd id="modalSku" class="font-semibold text-slate-800 dark:text-slate-200 font-mono"></dd>
                                </div>
                                <div>
                                    <dt class="text-slate-400">Price / Format</dt>
                                    <dd id="modalPriceOrFormat" class="font-semibold text-slate-800 dark:text-slate-200"></dd>
                                </div>
                            </dl>
                        </div>

                        <div id="modalSpecsExtraWrap" class="hidden border-t border-slate-100 dark:border-slate-800 pt-3">
                            <h4 class="font-semibold text-slate-900 dark:text-white text-sm mb-2">More specifications</h4>
                            <dl id="modalSpecsExtra" class="grid grid-cols-2 gap-2 bg-slate-50 dark:bg-slate-800/50 p-3.5 rounded-xl border border-slate-200/60 dark:border-slate-800"></dl>
                        </div>
                        <div id="modalDownloadsWrap" class="hidden border-t border-slate-100 dark:border-slate-800 pt-3">
                            <h4 class="font-semibold text-slate-900 dark:text-white text-sm mb-2">Downloads</h4>
                            <div id="modalDownloads" class="flex flex-col gap-1.5"></div>
                        </div>
                        <div class="pt-2">
                            <a id="modalProductLink" href="#" target="_blank" class="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-teal-600 hover:bg-teal-700 text-white font-medium rounded-xl shadow-xs transition">
                                <span>Visit Product Website</span>
                                <i data-lucide="external-link" class="w-4 h-4"></i>
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <footer class="mt-auto border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 py-6 text-center text-xs text-slate-500 dark:text-slate-400">
            <p>Master Multi-Manufacturer Product Catalog • Powered by Automated Discovery Pipeline</p>
        </footer>

    </div>

    <script>
        window.MASTER_PRODUCTS = {products_json_str};
        window.FALLBACK_IMG = "{FALLBACK_SVG}";
    </script>
    <script>
        (function() {{
            const products = window.MASTER_PRODUCTS || [];
            let currentView = 'grid';
            let currentPage = 1;
            let pageSize = 24;
            let currentSort = 'name_asc';
            
            let searchQuery = '';
            let selectedBrand = '';
            let selectedCategory = '';
            let brandQuery = '';

            const searchInput = document.getElementById('searchInput');
            const mobileSearchInput = document.getElementById('mobileSearchInput');
            const clearSearchBtn = document.getElementById('clearSearchBtn');
            const productGridView = document.getElementById('productGridView');
            const productTableView = document.getElementById('productTableView');
            const productTableBody = document.getElementById('productTableBody');
            const emptyState = document.getElementById('emptyState');
            const resultCountText = document.getElementById('resultCountText');
            const activeFilterTags = document.getElementById('activeFilterTags');
            const paginationControls = document.getElementById('paginationControls');
            const pageSizeSelect = document.getElementById('pageSizeSelect');
            const sortSelect = document.getElementById('sortSelect');
            const viewGridBtn = document.getElementById('viewGridBtn');
            const viewTableBtn = document.getElementById('viewTableBtn');
            const themeToggle = document.getElementById('themeToggle');
            const resetFiltersBtn = document.getElementById('resetFiltersBtn');
            const emptyResetBtn = document.getElementById('emptyResetBtn');
            const exportBtn = document.getElementById('exportBtn');

            const quickViewModal = document.getElementById('quickViewModal');
            const closeModalBtn = document.getElementById('closeModalBtn');
            const modalMainImg = document.getElementById('modalMainImg');
            const modalThumbnails = document.getElementById('modalThumbnails');
            const modalTitle = document.getElementById('modalTitle');
            const modalBrandBadge = document.getElementById('modalBrandBadge');
            const modalDescription = document.getElementById('modalDescription');
            const modalMfgName = document.getElementById('modalMfgName');
            const modalCategory = document.getElementById('modalCategory');
            const modalSku = document.getElementById('modalSku');
            const modalPriceOrFormat = document.getElementById('modalPriceOrFormat');
            const modalProductLink = document.getElementById('modalProductLink');

            function refreshIcons() {{
                if (window.lucide) window.lucide.createIcons();
            }}

            function populateSidebar() {{
                const brandCounts = {{}};
                const catCounts = {{}};

                products.forEach(p => {{
                    const b = p.manufacturer_name || 'Unknown';
                    brandCounts[b] = (brandCounts[b] || 0) + 1;
                    const c = p.category || 'General';
                    catCounts[c] = (catCounts[c] || 0) + 1;
                }});

                const brandList = document.getElementById('brandFilterList');
                brandList.innerHTML = `<button data-brand="" class="w-full text-left px-2.5 py-1.5 rounded-lg text-xs flex items-center justify-between font-medium ${{selectedBrand === '' ? 'bg-teal-100 dark:bg-teal-900/40 text-teal-900 dark:text-teal-300' : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'}}"><span>All Brands</span><span class="text-slate-400">${{products.length}}</span></button>`;
                
                const bq = brandQuery.toLowerCase().trim();
                Object.keys(brandCounts).sort((a,b) => brandCounts[b] - brandCounts[a]).filter(brand => !bq || brand.toLowerCase().includes(bq)).forEach(brand => {{
                    const active = selectedBrand === brand;
                    const btn = document.createElement('button');
                    btn.className = `w-full text-left px-2.5 py-1.5 rounded-lg text-xs flex items-center justify-between font-medium ${{active ? 'bg-teal-100 dark:bg-teal-900/40 text-teal-900 dark:text-teal-300' : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'}}`;
                    btn.innerHTML = `<span class="truncate">${{brand}}</span><span class="text-slate-400 font-mono text-[11px]">${{brandCounts[brand]}}</span>`;
                    btn.onclick = () => {{
                        selectedBrand = selectedBrand === brand ? '' : brand;
                        currentPage = 1;
                        populateSidebar();
                        render();
                    }};
                    brandList.appendChild(btn);
                }});

                const catList = document.getElementById('categoryFilterList');
                catList.innerHTML = `<button data-cat="" class="w-full text-left px-2.5 py-1.5 rounded-lg text-xs flex items-center justify-between font-medium ${{selectedCategory === '' ? 'bg-teal-100 dark:bg-teal-900/40 text-teal-900 dark:text-teal-300' : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'}}"><span>All Categories</span></button>`;
                
                Object.keys(catCounts).sort((a,b) => a.localeCompare(b)).forEach(cat => {{
                    const active = selectedCategory === cat;
                    const btn = document.createElement('button');
                    btn.className = `w-full text-left px-2.5 py-1.5 rounded-lg text-xs flex items-center justify-between font-medium ${{active ? 'bg-teal-100 dark:bg-teal-900/40 text-teal-900 dark:text-teal-300' : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'}}`;
                    btn.innerHTML = `<span class="truncate">${{cat}}</span><span class="text-slate-400 font-mono text-[11px]">${{catCounts[cat]}}</span>`;
                    btn.onclick = () => {{
                        selectedCategory = selectedCategory === cat ? '' : cat;
                        currentPage = 1;
                        populateSidebar();
                        render();
                    }};
                    catList.appendChild(btn);
                }});
            }}

            function getFilteredProducts() {{
                const q = searchQuery.toLowerCase().trim();
                const terms = q.split(/\\s+/).filter(Boolean);

                return products.filter(p => {{
                    if (selectedBrand && p.manufacturer_name !== selectedBrand) return false;
                    if (selectedCategory && p.category !== selectedCategory) return false;

                    if (terms.length > 0) {{
                        const fullText = `${{p.name}} ${{p.manufacturer_name}} ${{p.collection}} ${{p.category}} ${{p.sku}} ${{p.nominal_size}} ${{p.finish}} ${{p.price}}`.toLowerCase();
                        return terms.every(t => fullText.includes(t));
                    }}
                    return true;
                }}).sort((a, b) => {{
                    switch (currentSort) {{
                        case 'name_desc': return b.name.localeCompare(a.name);
                        case 'brand_asc': return (a.manufacturer_name || '').localeCompare(b.manufacturer_name || '');
                        case 'category_asc': return (a.category || '').localeCompare(b.category || '');
                        case 'photos_desc': return (b.image_count || 0) - (a.image_count || 0);
                        case 'name_asc':
                        default: return a.name.localeCompare(b.name);
                    }}
                }});
            }}

            function render() {{
                const filtered = getFilteredProducts();
                const totalFiltered = filtered.length;

                resultCountText.innerHTML = `Showing <span class="font-bold text-slate-900 dark:text-white">${{totalFiltered.toLocaleString()}}</span> of <span class="text-slate-500 dark:text-slate-400">${{products.length.toLocaleString()}}</span> products`;

                activeFilterTags.innerHTML = '';
                if (searchQuery) addTag(`Search: "${{searchQuery}}"`, () => {{ searchQuery = ''; searchInput.value = ''; mobileSearchInput.value = ''; clearSearchBtn.classList.add('hidden'); render(); }});
                if (selectedBrand) addTag(`Brand: ${{selectedBrand}}`, () => {{ selectedBrand = ''; populateSidebar(); render(); }});
                if (selectedCategory) addTag(`Category: ${{selectedCategory}}`, () => {{ selectedCategory = ''; populateSidebar(); render(); }});

                function addTag(label, onRemove) {{
                    const tag = document.createElement('span');
                    tag.className = 'inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-teal-100 dark:bg-teal-950/70 text-teal-900 dark:text-teal-200 border border-teal-200 dark:border-teal-800/60';
                    tag.innerHTML = `<span>${{label}}</span><button class="hover:text-teal-700 ml-0.5"><i data-lucide="x" class="w-3 h-3"></i></button>`;
                    tag.querySelector('button').onclick = onRemove;
                    activeFilterTags.appendChild(tag);
                }}

                if (totalFiltered === 0) {{
                    productGridView.classList.add('hidden');
                    productTableView.classList.add('hidden');
                    emptyState.classList.remove('hidden');
                    paginationContainer.classList.add('hidden');
                    refreshIcons();
                    return;
                }}

                emptyState.classList.add('hidden');
                paginationContainer.classList.remove('hidden');

                const effectivePageSize = pageSize === 'all' ? totalFiltered : parseInt(pageSize, 10);
                const totalPages = Math.ceil(totalFiltered / effectivePageSize);
                if (currentPage > totalPages) currentPage = 1;
                
                const startIndex = (currentPage - 1) * effectivePageSize;
                const pageProducts = filtered.slice(startIndex, startIndex + effectivePageSize);

                if (currentView === 'grid') {{
                    productGridView.classList.remove('hidden');
                    productTableView.classList.add('hidden');
                    renderGrid(pageProducts);
                }} else {{
                    productGridView.classList.add('hidden');
                    productTableView.classList.remove('hidden');
                    renderTable(pageProducts);
                }}

                renderPagination(totalPages);
                refreshIcons();
            }}

            function renderGrid(items) {{
                productGridView.innerHTML = items.map(p => {{
                    const imgUrl = p.primary_image || window.FALLBACK_IMG;
                    return `
                    <div class="product-card group bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-xs hover:shadow-xl transition-all duration-300 flex flex-col">
                        <div class="relative aspect-[4/3] bg-slate-100 dark:bg-slate-800 overflow-hidden cursor-pointer" onclick="openQuickView('${{p.id}}')">
                            <img 
                                src="${{imgUrl}}" 
                                alt="${{p.name}}" 
                                loading="lazy" 
                                class="card-zoom-img w-full h-full object-contain p-3"
                                onerror="this.onerror=null; this.src='${{window.FALLBACK_IMG}}'"
                            >
                            <div class="absolute top-2.5 left-2.5">
                                <span class="px-2 py-0.5 text-[10px] font-bold rounded-md bg-teal-600/90 text-white backdrop-blur">${{p.manufacturer_name}}</span>
                            </div>
                            <div class="absolute top-2.5 right-2.5">
                                <span class="px-2 py-0.5 text-[10px] font-semibold rounded-md bg-slate-900/70 text-white backdrop-blur flex items-center gap-1">
                                    <i data-lucide="image" class="w-3 h-3"></i> ${{p.image_count || 1}}
                                </span>
                            </div>
                        </div>

                        <div class="p-4 flex-1 flex flex-col justify-between">
                            <div>
                                <div class="text-[11px] uppercase tracking-wider text-teal-700 dark:text-teal-400 font-semibold mb-0.5">${{p.category}}</div>
                                <h3 class="text-sm font-bold text-slate-900 dark:text-white group-hover:text-teal-600 transition line-clamp-1">${{p.name}}</h3>
                                
                                <div class="mt-2 flex flex-wrap gap-1.5 text-[11px]">
                                    ${{p.price ? `<span class="px-2 py-0.5 rounded-md bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 font-semibold">${{p.price}}</span>` : ''}}
                                    ${{p.nominal_size ? `<span class="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 font-mono">${{p.nominal_size}}</span>` : ''}}
                                    ${{p.finish ? `<span class="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">${{p.finish}}</span>` : ''}}
                                </div>
                            </div>

                            <div class="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs">
                                <span class="font-mono text-slate-400 text-[11px]">${{p.sku || 'SKU N/A'}}</span>
                                <button onclick="openQuickView('${{p.id}}')" class="inline-flex items-center gap-1 text-teal-600 dark:text-teal-400 font-semibold hover:underline">
                                    <span>Details</span>
                                    <i data-lucide="arrow-right" class="w-3.5 h-3.5"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                    `;
                }}).join('');
            }}

            function renderTable(items) {{
                productTableBody.innerHTML = items.map(p => `
                    <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition cursor-pointer" onclick="openQuickView('${{p.id}}')">
                        <td class="p-3">
                            <div class="w-10 h-10 rounded-lg bg-slate-100 dark:bg-slate-800 overflow-hidden border border-slate-200 dark:border-slate-700 flex items-center justify-center">
                                <img src="${{p.primary_image || window.FALLBACK_IMG}}" alt="${{p.name}}" class="w-full h-full object-contain p-0.5" loading="lazy" onerror="this.onerror=null; this.src='${{window.FALLBACK_IMG}}'">
                            </div>
                        </td>
                        <td class="p-3 font-semibold text-slate-900 dark:text-white">${{p.name}}</td>
                        <td class="p-3 text-slate-600 dark:text-slate-400 font-medium">${{p.manufacturer_name}}</td>
                        <td class="p-3"><span class="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">${{p.category}}</span></td>
                        <td class="p-3 font-mono text-[11px] text-slate-500">${{p.sku || '-'}}</td>
                        <td class="p-3 font-semibold text-emerald-600 dark:text-emerald-400">${{p.price || p.nominal_size || '-'}}</td>
                        <td class="p-3 text-right">
                            <a href="${{p.url}}" target="_blank" onclick="event.stopPropagation()" class="p-1.5 text-slate-400 hover:text-teal-600 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 inline-flex" title="Open page">
                                <i data-lucide="external-link" class="w-4 h-4"></i>
                            </a>
                        </td>
                    </tr>
                `).join('');
            }}

            function renderPagination(totalPages) {{
                if (totalPages <= 1) {{
                    paginationControls.innerHTML = '';
                    return;
                }}

                let html = `
                    <button id="prevPageBtn" class="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 font-medium ${{currentPage === 1 ? 'opacity-50 cursor-not-allowed' : 'hover:bg-slate-50 dark:hover:bg-slate-800'}}" ${{currentPage === 1 ? 'disabled' : ''}}>
                        Previous
                    </button>
                    <span class="px-3 py-1.5 text-slate-500">Page ${{currentPage}} of ${{totalPages}}</span>
                    <button id="nextPageBtn" class="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 font-medium ${{currentPage === totalPages ? 'opacity-50 cursor-not-allowed' : 'hover:bg-slate-50 dark:hover:bg-slate-800'}}" ${{currentPage === totalPages ? 'disabled' : ''}}>
                        Next
                    </button>
                `;
                paginationControls.innerHTML = html;

                document.getElementById('prevPageBtn').onclick = () => {{
                    if (currentPage > 1) {{ currentPage--; render(); window.scrollTo({{top: 0, behavior: 'smooth'}}); }}
                }};
                document.getElementById('nextPageBtn').onclick = () => {{
                    if (currentPage < totalPages) {{ currentPage++; render(); window.scrollTo({{top: 0, behavior: 'smooth'}}); }}
                }};
            }}

            window.openQuickView = function(productId) {{
                const p = products.find(x => x.id === productId);
                if (!p) return;

                modalBrandBadge.innerText = p.manufacturer_name;
                modalTitle.innerText = p.name;
                modalDescription.innerText = p.description || 'No detailed description available.';
                modalMfgName.innerText = p.manufacturer_name;
                modalCategory.innerText = p.category;
                modalSku.innerText = p.sku || 'N/A';
                modalPriceOrFormat.innerText = p.price || p.color || p.finish || p.nominal_size || 'N/A';
                modalProductLink.href = p.url;
                const extra = p.specs || {{}};
                const extraWrap = document.getElementById('modalSpecsExtraWrap');
                const extraDl = document.getElementById('modalSpecsExtra');
                const extraKeys = Object.keys(extra).filter(k => extra[k]);
                extraWrap.classList.toggle('hidden', extraKeys.length === 0);
                extraDl.innerHTML = extraKeys.map(k => `<div><dt class="text-slate-400">${{k}}</dt><dd class="font-semibold text-slate-800 dark:text-slate-200">${{extra[k]}}</dd></div>`).join('');
                const dls = p.downloads || [];
                const dlWrap = document.getElementById('modalDownloadsWrap');
                const dlBox = document.getElementById('modalDownloads');
                dlWrap.classList.toggle('hidden', dls.length === 0);
                dlBox.innerHTML = dls.map(d => `<a href="${{d.url}}" target="_blank" rel="noopener" class="text-teal-700 dark:text-teal-400 hover:underline">${{d.name || 'Download'}}</a>`).join('');

                const allImgs = p.images && p.images.length ? p.images : [p.primary_image || window.FALLBACK_IMG];
                modalMainImg.src = allImgs[0] || window.FALLBACK_IMG;

                modalThumbnails.innerHTML = allImgs.map((img, idx) => `
                    <button class="thumb-btn flex-shrink-0 w-14 h-14 rounded-xl border-2 ${{idx === 0 ? 'border-teal-600' : 'border-transparent'}} overflow-hidden bg-slate-100 dark:bg-slate-800 p-0.5 transition" onclick="selectModalImg(this, '${{img}}')">
                        <img src="${{img}}" alt="" class="w-full h-full object-contain" onerror="this.onerror=null; this.src='${{window.FALLBACK_IMG}}'">
                    </button>
                `).join('');

                quickViewModal.classList.remove('hidden');
                refreshIcons();
            }};

            window.selectModalImg = function(btn, src) {{
                modalMainImg.src = src;
                document.querySelectorAll('.thumb-btn').forEach(b => b.classList.replace('border-teal-600', 'border-transparent'));
                btn.classList.replace('border-transparent', 'border-teal-600');
            }};

            closeModalBtn.onclick = () => quickViewModal.classList.add('hidden');
            quickViewModal.onclick = (e) => {{
                if (e.target === quickViewModal) quickViewModal.classList.add('hidden');
            }};

            viewGridBtn.onclick = () => {{
                currentView = 'grid';
                viewGridBtn.className = 'p-1.5 rounded-md text-teal-700 dark:text-teal-400 bg-white dark:bg-slate-700 shadow-xs';
                viewTableBtn.className = 'p-1.5 rounded-md text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200';
                render();
            }};
            viewTableBtn.onclick = () => {{
                currentView = 'table';
                viewTableBtn.className = 'p-1.5 rounded-md text-teal-700 dark:text-teal-400 bg-white dark:bg-slate-700 shadow-xs';
                viewGridBtn.className = 'p-1.5 rounded-md text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200';
                render();
            }};

            function handleSearch(val) {{
                searchQuery = val;
                currentPage = 1;
                clearSearchBtn.classList.toggle('hidden', !val);
                render();
            }}

            const brandSearchInput = document.getElementById('brandSearchInput');
            if (brandSearchInput) {{
                brandSearchInput.addEventListener('input', (e) => {{
                    brandQuery = e.target.value;
                    populateSidebar();
                }});
            }}

            searchInput.addEventListener('input', (e) => handleSearch(e.target.value));
            mobileSearchInput.addEventListener('input', (e) => {{
                searchInput.value = e.target.value;
                handleSearch(e.target.value);
            }});
            clearSearchBtn.onclick = () => {{
                searchInput.value = '';
                mobileSearchInput.value = '';
                handleSearch('');
            }};

            sortSelect.onchange = (e) => {{
                currentSort = e.target.value;
                render();
            }};
            pageSizeSelect.onchange = (e) => {{
                pageSize = e.target.value;
                currentPage = 1;
                render();
            }};

            function resetAll() {{
                searchQuery = '';
                selectedBrand = '';
                selectedCategory = '';
                brandQuery = '';
                searchInput.value = '';
                mobileSearchInput.value = '';
                if (brandSearchInput) brandSearchInput.value = '';
                clearSearchBtn.classList.add('hidden');
                currentPage = 1;
                populateSidebar();
                render();
            }}
            resetFiltersBtn.onclick = resetAll;
            emptyResetBtn.onclick = resetAll;

            exportBtn.onclick = () => {{
                const filtered = getFilteredProducts();
                const headers = ["ID", "Manufacturer", "Product Name", "Category", "SKU", "Price", "URL", "Primary Image"];
                const rows = filtered.map(p => [
                    p.id, p.manufacturer_name, p.name, p.category, p.sku, p.price, p.url, p.primary_image
                ]);
                let csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map(e => e.map(x => `"${{(x||'').toString().replace(/"/g, '""')}}"`).join(","))].join("\\n");
                const encodedUri = encodeURI(csvContent);
                const link = document.createElement("a");
                link.setAttribute("href", encodedUri);
                link.setAttribute("download", `master_catalog_export_${{Date.now()}}.csv`);
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }};

            themeToggle.onclick = () => {{
                document.documentElement.classList.toggle('dark');
                localStorage.setItem('theme', document.documentElement.classList.contains('dark') ? 'dark' : 'light');
                refreshIcons();
            }};
            if (localStorage.getItem('theme') === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {{
                document.documentElement.classList.add('dark');
            }}

            const brandParam = new URLSearchParams(location.search).get('brand');
            if (brandParam) selectedBrand = brandParam;

            populateSidebar();
            render();
        }})();
    </script>
</body>
</html>
"""

    out_path = r"d:\Aareas\master_catalog.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_template)
    print(f"Successfully generated {out_path} ({len(html_template)} bytes)")

if __name__ == "__main__":
    build_master_html_catalog()
