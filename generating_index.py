
#!/usr/bin/env python3
"""
FloodScience (pretty UI): generate index.html for all S3 folders, served via CloudFront.

Features:
- Clean folder URLs (CloudFront serves index.html automatically)
- File-type badges (ZIP, TIF, GDB, CSV, PDF, etc.)
- "Copy URL" buttons on folders and files
- Global search index (/search-index.json) + UI (/search/index.html)

Usage examples:
  # Rebuild all prefixes from the root (CloudFront default root object should be index.html)
  python generate_indexes.py --bucket floodsciencedata.twdb.texas.gov --full

  # Rebuild starting from a specific prefix only
  python generate_indexes.py --bucket floodsciencedata.twdb.texas.gov --prefix BLE_Delivered/11090102_PuntadeAgua_2025_09/

  # If you know your CloudFront base URL, you can provide it (optional, for absolute file links)
  python generate_indexes.py --bucket floodsciencedata.twdb.texas.gov --base-url https://d123abcd.cloudfront.net --full
"""

import argparse
import html
import json
from datetime import timezone
from urllib.parse import quote
import boto3

# Embed proper tags directly in the HTML
BOOTSTRAP_CSS_TAG = '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">'
BOOTSTRAP_JS_TAG  = '<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>'

FOLDER_ICON = '''
<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" class="me-2" fill="currentColor" viewBox="0 0 16 16" aria-hidden="true">
  <path d="M9.828 4a3 3 0 0 1 2.121.879l.172.172H14a2 2 0 0 1 2 2v4.5A2.5 2.5 0 0 1 13.5 14h-11A2.5 2.5 0 0 1 0 11.5V6a2 2 0 0 1 2-2h4.586l.707.707A3 3 0 0 0 9.828 4z"/>
</svg>
'''

FILE_ICON = '''
<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" class="me-2" fill="currentColor" viewBox="0 0 16 16" aria-hidden="true">
  <path d="M4 0a2 2 0 0 0-2 2v12c0 1.1.9 2 2 2h8a2 2 0 0 0 2-2V5.5L9.5 0H4z"/>
</svg>
'''


# ---------- S3 listing helpers ----------

def list_folder(s3, bucket: str, prefix: str):
    """Return (subfolders, files) under prefix using Delimiter='/'."""
    paginator = s3.get_paginator('list_objects_v2')
    subfolders, files = [], []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter='/'):
        subfolders += [p['Prefix'] for p in page.get('CommonPrefixes', [])]
        for obj in page.get('Contents', []):
            key = obj['Key']
            # Skip placeholder keys and previously generated index pages
            if key.endswith('/') or key.endswith('index.html'):
                continue
            files.append({
                'key': key,
                'size': obj.get('Size'),
                'last_modified': obj.get('LastModified'),
            })
    return sorted(subfolders), sorted(files, key=lambda x: x['key'])


def walk_prefixes(s3, bucket: str, start_prefix: str = ""):
    """Yield all folder prefixes reachable from start_prefix (including start)."""
    seen = set()
    stack = [start_prefix]
    while stack:
        pref = stack.pop()
        if pref in seen:
            continue
        seen.add(pref)
        yield pref
        subs, _ = list_folder(s3, bucket, pref)
        stack.extend(subs)


# ---------- Formatting helpers ----------

def human_size(n: int) -> str:
    """Format bytes into a human-readable size string."""
    if n is None:
        return ''
    n = float(n)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if n < 1024.0:
            return f"{n:3.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} PB"


def iso_utc(dt) -> str:
    if not dt:
        return ''
    return dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def breadcrumbs(prefix: str):
    """Return list of (name, href) crumb pairs. 'Home' goes to root '/'."""
    parts = [p for p in prefix.strip('/').split('/') if p]
    crumbs = [('Home', '/')]
    accum = []
    for p in parts:
        accum.append(p)
        crumbs.append((p, '/' + '/'.join(accum) + '/'))
    return crumbs


def _basename_folder(pref: str) -> str:
    s = pref.strip('/')
    return s.split('/')[-1] if s else 'Home'


def guess_ext(name: str) -> str:
    """Guess extension including common double-ext like .tar.gz, .tif.tfw (ignored)"""
    n = name.lower()
    # Double extensions
    for dbl in ['.tar.gz', '.tar.bz2', '.tar.xz']:
        if n.endswith(dbl):
            return dbl[1:]
    # Single extension
    parts = n.rsplit('.', 1)
    return parts[1] if len(parts) == 2 else ''


def ext_badge(name: str) -> str:
    ext = guess_ext(name)
    label = ext.upper() if ext else 'FILE'
    # Map common GIS/data types to Bootstrap colors
    color = 'secondary'
    if ext in ['zip']:
        color = 'primary'
        label = 'ZIP'
    elif ext in ['tif', 'tiff', 'geotiff']:
        color = 'info'
        label = 'GeoTIFF' if ext == 'geotiff' else 'TIF'
    elif ext in ['csv']:
        color = 'success'
        label = 'CSV'
    elif ext in ['pdf']:
        color = 'danger'
        label = 'PDF'
    elif ext in ['json', 'geojson']:
        color = 'dark'
        label = 'GEOJSON' if ext == 'geojson' else 'JSON'
    elif ext in ['xml']:
        color = 'secondary'
        label = 'XML'
    elif ext in ['shp', 'dbf', 'prj', 'shx']:
        color = 'warning'
        label = ext.upper()
    elif ext in ['jpg', 'jpeg', 'png']:
        color = 'info'
        label = 'IMG'
    elif ext in ['gz', 'bz2', 'xz', 'tar.gz', 'tar.bz2', 'tar.xz']:
        color = 'primary'
        label = ext.upper()
    elif ext in ['gdb', 'fgdb']:
        color = 'warning'
        label = 'GDB'
    return f'<span class="badge bg-{color} ms-2">{html.escape(label)}</span>'


# ---------- Page renderers ----------

def render_index_html(base_url: str, prefix: str, subfolders, files):
    """Build the HTML for a single index page under `prefix`."""
    title = f"Index of /{prefix}" if prefix else "Index of /"
    base_url = (base_url or '').rstrip('/')

    # Breadcrumbs
    crumbs = breadcrumbs(prefix)
    bc_html_parts = []
    for i, (name, href) in enumerate(crumbs):
        if i < len(crumbs) - 1:
            bc_html_parts.append(
                f'<li class="breadcrumb-item"><a href="{html.escape(href)}">{html.escape(name)}</a></li>'
            )
        else:
            bc_html_parts.append(
                f'<li class="breadcrumb-item active" aria-current="page">{html.escape(name)}</li>'
            )
    bc_html = ''.join(bc_html_parts)

    # Subfolders (clean URLs: /prefix/subfolder/)
    folder_items = ''.join([
        f'''
        <li class="list-group-item d-flex align-items-center justify-content-between">
          <div class="d-flex align-items-center">
            {FOLDER_ICON}
            <a class="folder-link" href="/{html.escape(sf)}">{html.escape(_basename_folder(sf))}/</a>
          </div>
          <button class="btn btn-sm btn-outline-secondary copy-btn" data-url="/{html.escape(sf)}" aria-label="Copy folder URL">Copy URL</button>
        </li>
        ''' for sf in subfolders
    ]) or '<li class="list-group-item text-muted">(no subfolders)</li>'

    # Files (clickable anchors + badges + copy URL)
    file_items = ''
    for f in files:
        key   = f['key']
        name  = key.split('/')[-1]
        size  = human_size(f.get('size'))
        lm_str = iso_utc(f.get('last_modified'))
        file_url = (f"{base_url}/{quote(key)}" if base_url else f"/{quote(key)}")
        file_items += f'''
        <li class="list-group-item d-flex align-items-center justify-content-between">
          <div class="d-flex align-items-center">
            {FILE_ICON}
            <a class="file-link" href="{html.escape(file_url)}">{html.escape(name)}</a>
            {ext_badge(name)}
            <small class="text-muted ms-2">{html.escape(size)} • {html.escape(lm_str)}</small>
          </div>
          <button class="btn btn-sm btn-outline-secondary copy-btn" data-url="{html.escape(file_url)}" aria-label="Copy file URL">Copy URL</button>
        </li>
        '''
    if not file_items:
        file_items = '<li class="list-group-item text-muted">(no files)</li>'

    # Final HTML
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  {BOOTSTRAP_CSS_TAG}
  <style>
    body {{ padding: 2rem; }}
    .file-link {{ word-break: break-all; }}
    .folder-link {{ font-weight: 600; }}
    .search-input {{ max-width: 480px; }}
    .navbar-brand small {{ font-weight: 400; color: #6c757d; }}
  </style>
</head>
<body class="container">
  <nav class="navbar mb-3">
    <div class="container-fluid px-0">
      <span class="navbar-brand mb-0 h5">FloodScience <small>Data Browser</small></span>
      <div class="d-flex gap-2">
        <a class="btn btn-sm btn-outline-primary" href="/search/">Global Search</a>
        <a class="btn btn-sm btn-outline-secondary" href="/">Home</a>
      </div>
    </div>
  </nav>

  <header class="mb-3">
    <h1 class="h5">{html.escape(title)}</h1>
    <p class="text-muted mb-0">Browse subfolders and files. Use the search box to filter within this folder.</p>
  </header>

  <nav aria-label="breadcrumb" class="mb-3">
    <ol class="breadcrumb">{bc_html}</ol>
  </nav>

  <div class="mb-3">
    <input id="search" type="search" class="form-control search-input" placeholder="Filter folders/files in this page (type to search)">
  </div>

  <section class="mb-4">
    <h2 class="h6">Subfolders</h2>
    <ul id="folders" class="list-group">
      {folder_items}
    </ul>
  </section>

  <section>
    <h2 class="h6">Files</h2>
    <ul id="files" class="list-group">
      {file_items}
    </ul>
  </section>

  <footer class="mt-4">
    <small class="text-muted">Served via CloudFront • FloodScience</small>
  </footer>

  {BOOTSTRAP_JS_TAG}
  <script>
    // Local filter
    const search = document.getElementById('search');
    function filterList(list, query) {{
      const items = list.querySelectorAll('li');
      items.forEach(li => {{
        const text = li.textContent.toLowerCase();
        li.style.display = text.includes(query) ? '' : 'none';
      }});
    }}
    search.addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase();
      filterList(document.getElementById('folders'), q);
      filterList(document.getElementById('files'), q);
    }});

    // Copy URL buttons
    document.addEventListener('click', (e) => {{
      const btn = e.target.closest('.copy-btn');
      if (!btn) return;
      const url = btn.getAttribute('data-url');
      if (!url) return;
      navigator.clipboard.writeText(url).then(() => {{
        const original = btn.textContent;
        btn.textContent = 'Copied!';
        btn.classList.remove('btn-outline-secondary');
        btn.classList.add('btn-success');
        setTimeout(() => {{
          btn.textContent = original;
          btn.classList.add('btn-outline-secondary');
          btn.classList.remove('btn-success');
        }}, 1200);
      }}).catch(() => {{
        alert('Copy failed. Please copy manually: ' + url);
      }});
    }});
  </script>
</body>
</html>"""


def render_search_page():
    """Global search UI (fetches /search-index.json)."""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>FloodScience • Global Search</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  {BOOTSTRAP_CSS_TAG}
  <style>
    body {{ padding: 2rem; }}
    .result-link {{ word-break: break-all; }}
    .search-input {{ max-width: 640px; }}
    .navbar-brand small {{ font-weight: 400; color: #6c757d; }}
  </style>
</head>
<body class="container">
  <nav class="navbar mb-3">
    <div class="container-fluid px-0">
      <span class="navbar-brand mb-0 h5">FloodScience <small>Global Search</small></span>
      <div class="d-flex gap-2">
        <a class="btn btn-sm btn-outline-secondary" href="/">Home</a>
      </div>
    </div>
  </nav>

  <header class="mb-3">
    <h1 class="h5">Search across all folders & files</h1>
    <p class="text-muted mb-2">Type to filter; click to open. Use Copy URL to share a direct link.</p>
    <input id="q" type="search" class="form-control search-input" placeholder="Search by name, path, or extension (e.g., tif, zip, gdb)">
  </header>

  <section>
    <ul id="results" class="list-group"></ul>
    <p id="empty" class="text-muted mt-3" style="display:none">(no results)</p>
  </section>

  {BOOTSTRAP_JS_TAG}
  <script>
    const resultsEl = document.getElementById('results');
    const emptyEl = document.getElementById('empty');
    const qEl = document.getElementById('q');
    let DATA = [];

    function badgeFor(rec) {{
      const label = (rec.ext || (rec.type === 'folder' ? 'FOLDER' : 'FILE')).toUpperCase();
      let color = 'secondary';
      if (label === 'ZIP') color = 'primary';
      if (['TIF','TIFF','GEOTIFF'].includes(label)) color = 'info';
      if (label === 'CSV') color = 'success';
      if (label === 'PDF') color = 'danger';
      if (['JSON','GEOJSON'].includes(label)) color = 'dark';
      if (['SHP','DBF','PRJ','SHX','GDB','FGDB'].includes(label)) color = 'warning';
      if (['JPG','JPEG','PNG','IMG'].includes(label)) color = 'info';
      return `<span class="badge bg-${{color}} ms-2">${{label}}</span>`;
    }}

    function row(rec) {{
      const icon = rec.type === 'folder'
        ? `{FOLDER_ICON}`
        : `{FILE_ICON}`;
      const href = rec.url || rec.path;
      const name = rec.name || rec.path;
      const meta = [];
      if (rec.size) meta.push(rec.size);
      if (rec.last_modified) meta.push(rec.last_modified);
      const metaStr = meta.length ? ` <small class="text-muted ms-2">${{meta.join(' • ')}}</small>` : '';
      return `
        <li class="list-group-item d-flex align-items-center justify-content-between">
          <div class="d-flex align-items-center">
            ${icon}
            <a class="result-link" href="${{href}}">${{name}}</a>
            ${badgeFor(rec)}
            ${metaStr}
          </div>
          <button class="btn btn-sm btn-outline-secondary copy-btn" data-url="${{href}}" aria-label="Copy URL">Copy URL</button>
        </li>
      `;
    }}

    function render(list) {{
      resultsEl.innerHTML = list.map(row).join('');
      emptyEl.style.display = list.length ? 'none' : '';
    }}

    function matches(rec, q) {{
      const t = (rec.name + ' ' + rec.path + ' ' + (rec.ext || '')).toLowerCase();
      return t.includes(q);
    }}

    // Copy URL
    document.addEventListener('click', (e) => {{
      const btn = e.target.closest('.copy-btn');
      if (!btn) return;
      const url = btn.getAttribute('data-url');
      navigator.clipboard.writeText(url).then(() => {{
        const original = btn.textContent;
        btn.textContent = 'Copied!';
        btn.classList.remove('btn-outline-secondary');
        btn.classList.add('btn-success');
        setTimeout(() => {{
          btn.textContent = original;
          btn.classList.add('btn-outline-secondary');
          btn.classList.remove('btn-success');
        }}, 1200);
      }}).catch(() => {{
        alert('Copy failed. Please copy manually: ' + url);
      }});
    }});

    // Load data
    fetch('/search-index.json')
      .then(r => r.json())
      .then(json => {{
        DATA = json;
        render(DATA);
      }})
      .catch(err => {{
        console.error('Failed to load search-index.json', err);
        resultsEl.innerHTML = '<li class="list-group-item text-danger">Failed to load search index.</li>';
      }});

    // Filter
    qEl.addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase();
      const list = q ? DATA.filter(rec => matches(rec, q)) : DATA;
      render(list);
    }});
  </script>
</body>
</html>"""


# ---------- S3 writers ----------

def put_index(s3, bucket: str, prefix: str, html_doc: str):
    """Upload index.html to the given prefix in S3 with short cache TTL."""
    key = f"{prefix}index.html"
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=html_doc.encode('utf-8'),
        ContentType='text/html; charset=utf-8',
        CacheControl='public, max-age=60'
    )
    return key


def put_json(s3, bucket: str, key: str, obj):
    body = json.dumps(obj, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType='application/json; charset=utf-8',
        CacheControl='public, max-age=300'
    )
    return key


# ---------- Global search index ----------

def build_search_index(s3, bucket: str, start_prefix: str, base_url: str):
    """Build list of records for global search."""
    base_url = (base_url or '').rstrip('/')
    records = []
    for pref in walk_prefixes(s3, bucket, start_prefix):
        # Folder record
        folder_path = f"/{pref}"
        folder_url = f"{base_url}{folder_path}" if base_url else folder_path
        records.append({
            "type": "folder",
            "name": _basename_folder(pref) if pref else "Home",
            "path": folder_path,
            "url": folder_url
        })

        subs, files = list_folder(s3, bucket, pref)
        for f in files:
            key = f['key']
            name = key.split('/')[-1]
            size = human_size(f.get('size'))
            lm   = iso_utc(f.get('last_modified'))
            ext  = guess_ext(name)
            path = f"/{key}"
            url  = f"{base_url}{path}" if base_url else path
            records.append({
                "type": "file",
                "name": name,
                "path": path,
                "url": url,
                "size": size,
                "last_modified": lm,
                "ext": ext.upper() if ext else ""
            })
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bucket', required=True)
    parser.add_argument('--base-url', default='', help='Optional absolute base (e.g., https://d123abcd.cloudfront.net). If omitted, links are site-relative.')
    parser.add_argument('--prefix', default='', help='Start prefix (e.g., BLE_Delivered/). Default = root.')
    parser.add_argument('--full', action='store_true', help='Rebuild all reachable prefixes from --prefix')
    parser.add_argument('--with-search', action='store_true', help='Also (re)build global search index and page at root.')
    args = parser.parse_args()

    s3 = boto3.client('s3')

    # Generate folder index pages
    prefixes = walk_prefixes(s3, args.bucket, args.prefix) if args.full else [args.prefix]
    updated = []
    for pref in prefixes:
        subs, files = list_folder(s3, args.bucket, pref)
        html_doc = render_index_html(args.base_url, pref, subs, files)
        key = put_index(s3, args.bucket, pref, html_doc)
        updated.append('/' + key)
        print(f"Updated {key} with {len(subs)} subfolders, {len(files)} files")

    # Global search index + UI at root (recommended)
    if args.with_search or args.full:
        print("Building global search index...")
        records = build_search_index(s3, args.bucket, args.prefix if args.full else args.prefix, args.base_url)
        jkey = put_json(s3, args.bucket, 'search-index.json', records)
        print(f"Updated /{jkey} with {len(records)} records")

        search_html = render_search_page()
        skey = put_index(s3, args.bucket, 'search/', search_html)
        print(f"Updated /{skey} (global search UI)")

    print('\nDone. Updated:')
    for u in sorted(updated):
        print(u)


if __name__ == '__main__':
    main()
