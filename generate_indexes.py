

#!/usr/bin/env python3
import argparse, html, json
from datetime import timezone
from urllib.parse import quote
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

BOOTSTRAP_CSS = '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">'
BOOTSTRAP_JS  = '<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>'

# ---------- Region & S3 client ----------
def discover_bucket_region(bucket):
    c = boto3.client('s3', config=Config(s3={'addressing_style':'path'}))
    try:
        r = c.head_bucket(Bucket=bucket)
        return r['ResponseMetadata']['HTTPHeaders'].get('x-amz-bucket-region') or 'us-east-1'
    except ClientError:
        try:
            r = c.get_bucket_location(Bucket=bucket)
            return r.get('LocationConstraint') or 'us-east-1'  # us-east-1 => null
        except ClientError:
            return 'us-east-1'

def s3_client_for_bucket(bucket):
    region = discover_bucket_region(bucket)
    cfg = Config(s3={'addressing_style':'path'})
    return boto3.client('s3', region_name=region, config=cfg)

# ---------- S3 listing ----------
def list_folder(s3, bucket, prefix):
    p = s3.get_paginator('list_objects_v2')
    subs, files = [], []
    for page in p.paginate(Bucket=bucket, Prefix=prefix, Delimiter='/'):
        subs += [c['Prefix'] for c in page.get('CommonPrefixes', [])]
        for o in page.get('Contents', []):
            k = o['Key']
            if k.endswith('/') or k.endswith('index.html'): continue
            files.append({'key': k, 'size': o.get('Size'), 'last_modified': o.get('LastModified')})
    return sorted(subs), sorted(files, key=lambda x: x['key'])

def walk_prefixes(s3, bucket, start=""):
    seen, stack = set(), [start]
    while stack:
        pref = stack.pop()
        if pref in seen: continue
        seen.add(pref); yield pref
        subs, _ = list_folder(s3, bucket, pref)
        stack.extend(subs)

# ---------- helpers ----------
def human_size(n):
    if n is None: return ''
    n = float(n)
    for u in ['B','KB','MB','GB','TB']:
        if n < 1024: return f'{n:3.1f} {u}'
        n /= 1024
    return f'{n:.1f} PB'

def iso_utc(dt): return '' if not dt else dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def crumbs(prefix):
    parts = [p for p in prefix.strip('/').split('/') if p]
    out, acc = [('Home','/')], []
    for p in parts:
        acc.append(p); out.append((p, '/' + '/'.join(acc) + '/'))
    return out
def base_folder(pref):
    s = pref.strip('/')
    return s.split('/')[-1] if s else 'Home'

BADGE_MAP = {
    'zip':'primary','tif':'info','tiff':'info','geotiff':'info','csv':'success','pdf':'danger',
    'json':'dark','geojson':'dark','xml':'secondary','gdb':'warning','fgdb':'warning',
    'shp':'warning','dbf':'warning','prj':'warning','shx':'warning','jpg':'info','jpeg':'info','png':'info',
}
def ext_label(name):
    n = name.lower()
    ext = n.rsplit('.',1)[1] if '.' in n else ''
    lbl = {'tif':'TIF','tiff':'TIFF','geotiff':'GeoTIFF','geojson':'GEOJSON'}.get(ext, (ext.upper() if ext else 'FILE'))
    color = BADGE_MAP.get(ext, 'secondary')
    return f'<span class="badge bg-{color} ms-2">{html.escape(lbl)}</span>'

FOLDER_ICON = '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" class="me-2" fill="currentColor" viewBox="0 0 16 16" aria-hidden="true"><path d="M9.828 4a3 3 0 0 1 2.121.879l.172.172H14a2 2 0 0 1 2 2v4.5A2.5 2.5 0 0 1 13.5 14h-11A2.5 2.5 0 0 1 0 11.5V6a2 2 0 0 1 2-2h4.586l.707.707A3 3 0 0 0 9.828 4z"/></svg>'
FILE_ICON   = '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" class="me-2" fill="currentColor" viewBox="0 0 16 16" aria-hidden="true"><path d="M4 0a2 2 0 0 0-2 2v12c0 1.1.9 2 2 2h8a2 2 0 0 0 2-2V5.5L9.5 0H4z"/></svg>'

# ---------- HTML ----------


def render_index_html(base_url, prefix, subfolders, files):
    b = (base_url or '').rstrip('/')
    p = (prefix or '').strip('/')
    t = "Texas Water Development Board | Flood DataScience"
    og = b + ('/' + p if p else '/')
    # CloudFront logo URL
    logo_url = (b or '') + '/twdblogo/twdblogo.png'
    #Fixed logo dimensions
    LOGO_W = 160
    LOGO_H = 55

    #Exclude the Logo Folder 
    excluded_folder = "twdblogo"
    filtered_subfolders = [sf for sf in subfolders if base_folder(sf) != excluded_folder]

    # Breadcrumbs
    ca = [(n, (b + h) if b else h) for n, h in crumbs(p)]
    bc_items = []
    for i, (n, h) in enumerate(ca):
        if i < len(ca) - 1:
            bc_items.append(
                '<li class="breadcrumb-item"><a href="' + html.escape(h) + '">' +
                html.escape(n) + '</a></li>'
            )
        else:
            bc_items.append(
                '<li class="breadcrumb-item active" aria-current="page">' +
                html.escape(n) + '</li>'
            )
    bc = ''.join(bc_items)

    # Links
    fL = lambda s: b + '/' + quote(s, safe='/')
    
    folders = ''.join([
        '<li class="list-group-item d-flex justify-content-between">'
        '<div class="d-flex align-items-center">' + FOLDER_ICON +
        '<a href="' + html.escape(fL(sf)) + '">' + html.escape(base_folder(sf)) + '/</a></div>'
        '<button class="btn btn-sm btn-outline-secondary copy" data-u="' + html.escape(fL(sf)) + '">Copy</button>'
        '</li>'
        for sf in filtered_subfolders
    ]) or '<li class="list-group-item text-muted">(no subfolders)</li>'

    filesh = ''.join([
        (lambda u, n, sz, lm:
         '<li class="list-group-item d-flex justify-content-between">'
         '<div class="d-flex align-items-center">' + FILE_ICON +
         '<a href="' + html.escape(u) + '">' + html.escape(n) + '</a>' + ext_label(n) +
         '<small class="text-muted ms-2">' + html.escape(human_size(sz)) + ' • ' + html.escape(iso_utc(lm)) + '</small></div>'
         '<button class="btn btn-sm btn-outline-secondary copy" data-u="' + html.escape(u) + '">Copy</button>'
         '</li>'
         )(fL(f["key"]), f["key"].split('/')[-1], f.get("size"), f.get("last_modified"))
        for f in files
    ]) or '<li class="list-group-item text-muted">(no files)</li>'

    # Safe JS string injections
    pj = json.dumps(p)
    IF = json.dumps(FOLDER_ICON)  # icon html strings as JS consts
    IA = json.dumps(FILE_ICON)
   
    html_out = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<title>' + html.escape(t) + '</title>'
        # Open Graph
        '<meta property="og:title" content="Texas Water Development Board">'
        '<meta property="og:type" content="website">'
        '<meta property="og:url" content="' + html.escape(og) + '">'
        '<meta property="og:description" content="The mission of the Texas Water Development Board (TWDB) is to lead the state\'s efforts in ensuring a secure water future for Texas and its citizens.">'
        '<meta property="og:image" content="' + html.escape(logo_url) + '">'
        '<meta property="og:image:alt" content="Logo of the Texas Water Development Board">'
        
# Explicit OG image size for scrapers
        f'<meta property="og:image:width" content="{LOGO_W}">'
        f'<meta property="og:image:height" content="{LOGO_H}">'

        # Head
        '<meta name="viewport" content="width=device-width,initial-scale=1">' + BOOTSTRAP_CSS +
        '<style>body{padding:2rem ;background-color:#f5f7fa;}.search-input{max-width:640px}</style></head><body class="container">'
        # Navbar with visible logo
        '<nav class="navbar mb-3"><div class="container-fluid px-0">'
        '<img src="' + html.escape(logo_url) + '" alt="TWDB Logo" style="height:130px;margin-right:40px;background-color:#f5f7fa;filter:brightness(96%);">'
        '<span class="navbar-brand">' + html.escape(t) + '</span>'
        '<div class="d-flex gap-2"><a class="btn btn-sm btn-outline-primary" href="' + (b + '/search/') + '">Search</a>'
        '<a class="btn btn-sm btn-outline-secondary" href="' + (b or '/') + '">Home</a></div>'
        '</div></nav>'
        # Body
        '<nav aria-label="breadcrumb"><ol class="breadcrumb">' + bc + '</ol></nav>'
        '<input id="s" type="search" class="form-control mb-3 search-input" placeholder="Search folders/files">'
        '<h6>Subfolders</h6><ul id="f1" class="list-group">' + folders + '</ul>'
        '<h6 class="mt-4">Files</h6><ul id="f2" class="list-group">' + filesh + '</ul>'
        '<section id="r" style="display:none"><h6>Search results</h6><ul id="rs" class="list-group"></ul>'
        '<p id="em" class="text-muted mt-3" style="display:none">(no matches)</p></section>'
        # JS
        + BOOTSTRAP_JS +
        '<script>'
        'const P=' + pj + ',IF=' + IF + ',IA=' + IA + ';let D=null;'
        'const I=document.getElementById("s"),S1=document.getElementById("f1"),S2=document.getElementById("f2"),'
        'R=document.getElementById("r"),UL=document.getElementById("rs"),E=document.getElementById("em");'
        'function n(s){return (s||"").toLowerCase()}'
        'async function ld(){if(D)return;try{D=await (await fetch("/search-index.json")).json()}catch(e){D=null}}'
        'function m(r,q){let a=n(r.name),b=n(r.path);return a.includes(q)||b.includes(q)}'
        'function rk(r,q){let a=n(r.name),b=n(r.path);return (a.startsWith(q)?2:0)+(b.startsWith(q)?1:0)}'
        'function row(r){var ic=r.type==="folder"?IF:IA,h=(r.url||r.path),nm=(r.name||r.path);'
        'return "<li class=\\"list-group-item d-flex justify-content-between\\"><div class=\\"d-flex align-items-center\\">"+ic+"<a href=\\""+h+"\\">"+nm+"</a></div><button class=\\"btn btn-sm btn-outline-secondary copy\\" data-u=\\""+h+"\\">Copy</button></li>"}'
        'function rend(L){UL.innerHTML=L.map(row).join("");E.style.display=L.length?"none":""}'
        'async function s(q){q=n(q);if(!q){R.style.display="none";S1.style.display="";S2.style.display="";return}'
        'await ld();if(!D)return;const pref="/"+P+(P?"/":"");'
        'const L=D.filter(r=>((r.path||"").startsWith(pref))).filter(r=>m(r,q)).sort((a,b)=>rk(b,q)-rk(a,q));'
        'rend(L);R.style.display="";S1.style.display="none";S2.style.display="none"}'
        'I && (I.oninput=e=>s(e.target.value));'
        'document.addEventListener("click",e=>{const b=e.target.closest(".copy");if(!b)return;const u=b.getAttribute("data-u");'
        'navigator.clipboard.writeText(u).then(()=>{const o=b.textContent;b.textContent="Copied!";'
        'b.classList.replace("btn-outline-secondary","btn-success");'
        'setTimeout(()=>{b.textContent=o;b.classList.replace("btn-success","btn-outline-secondary")},900)})})'
        '</script></body></html>'
    )
    return html_out


def render_search_page():
    h=(
        '<!doctype html><html><head><meta charset=utf-8><title>FloodScience • Global Search</title>'+BOOTSTRAP_CSS+
        '</head><body class=container><nav class="navbar mb-3"><span class=navbar-brand>Global Search</span>'
        '<a class="btn btn-sm btn-outline-secondary" href="/">Home</a></nav>'
        '<input id="q" type="search" class="form-control mb-3" placeholder="Search all files">'
        '<ul id="r" class="list-group"></ul><p id="e" class="text-muted" style="display:none">(no results)</p>'+BOOTSTRAP_JS+
        '<script>let D=[];const R=document.getElementById("r"),E=document.getElementById("e"),Q=document.getElementById("q");'
        'const IF='+json.dumps(FOLDER_ICON)+',IA='+json.dumps(FILE_ICON)+';'
        'function row(x){var ic=x.type==="folder"?IF:IA,h=(x.url||x.path),n=(x.name||x.path);return "<li class=\\"list-group-item d-flex justify-content-between\\"><div class=\\"d-flex align-items-center\\">"+ic+"<a href=\\""+h+"\\">"+n+"</a></div><button class=\\"btn btn-sm btn-outline-secondary copy\\" data-u=\\""+h+"\\">Copy</button></li>"}'
        'function render(L){R.innerHTML=L.map(row).join("");E.style.display=L.length?"none":""}'
        'fetch("/search-index.json").then(r=>r.json()).then(j=>{D=j;render(D)}).catch(()=>{R.innerHTML="<li class=\\"list-group-item text-danger\\">Failed to load search index.</li>"})'
        'Q&&Q.addEventListener("input",e=>{var s=(e.target.value||"").toLowerCase();render(s?D.filter(r=>(((r.name||"")+(r.path||"")+(r.ext||"")).toLowerCase().includes(s))):D)})'
        'document.addEventListener("click",e=>{var b=e.target.closest(".copy");if(!b)return;var u=b.getAttribute("data-u");navigator.clipboard.writeText(u).then(()=>{var o=b.textContent;b.textContent="Copied!";b.classList.replace("btn-outline-secondary","btn-success");setTimeout(()=>{b.textContent=o;b.classList.replace("btn-success","btn-outline-secondary")},900)})})'
        '</script></body></html>'
    )
    return h




# ---------- S3 put & index ----------
def put_obj(s3, bucket, key, body, ctype, cache='public, max-age=60'):
    s3.put_object(Bucket=bucket, Key=key, Body=body.encode('utf-8'), ContentType=ctype, CacheControl=cache)
    return key

def build_search_index(s3, bucket, start_prefix, base_url):
    base_url = (base_url or '').rstrip('/'); recs=[] ; excluded_folder = "twdblogo"  # Folder to exclude
    for pref in walk_prefixes(s3, bucket, start_prefix):
         # Skip the excluded folder
        if base_folder(pref) == excluded_folder:
            continue

        path=f'/{pref}'; url=f'{base_url}{path}' if base_url else path
        recs.append({'type':'folder','name':base_folder(pref) if pref else 'Home','path':path,'url':url})
        subs, files = list_folder(s3, bucket, pref)
        for f in files:
            key=f['key']
# Skip files inside the excluded folder
            if key.startswith(excluded_folder + '/'):
                continue
          
            name=key.split('/')[-1]
            ext=(name.lower().rsplit('.',1)[1].upper() if '.' in name else '')
            path=f'/{key}'; url=f'{base_url}{path}' if base_url else path
            recs.append({
                'type':'file','name':name,'path':path,'url':url,
                'size':human_size(f.get('size')),'last_modified':iso_utc(f.get('last_modified')),'ext':ext
            })
    return recs

# ---------- CLI ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bucket', default='floodsciencedata.twdb.texas.gov')
    ap.add_argument('--base-url', default='https://floodsciencedata.twdb.texas.gov', help='e.g., https://floodsciencedata.twdb.texas.gov (optional)')
    ap.add_argument('--prefix', default='', help='Start prefix (default root)')
    ap.add_argument('--full', action='store_true', help='Rebuild all reachable prefixes from --prefix')
    ap.add_argument('--with-search', action='store_true', help='Also build global search index + UI')
    args = ap.parse_args()

    s3 = s3_client_for_bucket(args.bucket)
    prefixes = walk_prefixes(s3, args.bucket, args.prefix) if args.full else [args.prefix]
    updated=[]
    for pref in prefixes:
        subs, files = list_folder(s3, args.bucket, pref)
        html_doc = render_index_html(args.base_url, pref, subs, files)
        updated.append('/'+put_obj(s3, args.bucket, f'{pref}index.html', html_doc, 'text/html; charset=utf-8'))
        print(f'Updated {pref}index.html ({len(subs)} subfolders, {len(files)} files)')

    if args.with_search or args.full:
        print('Building global search index...')
        recs = build_search_index(s3, args.bucket, args.prefix if args.full else args.prefix, args.base_url)
        sidx = json.dumps(recs, ensure_ascii=False, separators=(',',':'))
        put_obj(s3, args.bucket, 'search-index.json', sidx, 'application/json; charset=utf-8', cache='public, max-age=300')
        put_obj(s3, args.bucket, 'search/index.html', render_search_page(), 'text/html; charset=utf-8')
        print(f'Global search: /search-index.json ({len(recs)} records), /search/index.html')

    print('\nDone. Updated:')
    for u in sorted(updated): print(u)

if __name__ == '__main__':
    main()
