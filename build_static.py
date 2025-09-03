# build_static.py (robust paths, with Education)
import json, shutil
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).parent
TEMPLATE_DIR = ROOT / "app" / "templates"
OUT = ROOT / "docs"

# Where to look for static assets (merged)
STATIC_DIRS = [ROOT / "app" / "static", ROOT / "static"]

# Where to look for JSON content (merged)
PROJECT_DIRS   = [ROOT / "data" / "projects",   ROOT / "app" / "data" / "projects"]
EDUCATION_DIRS = [ROOT / "data" / "educations", ROOT / "app" / "data" / "educations"]

# Clean output
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True, exist_ok=True)

# Copy static/ -> docs/static (merge if both exist)
for s in STATIC_DIRS:
    if s.exists():
        shutil.copytree(s, OUT / "static", dirs_exist_ok=True)

# Copy data/ -> docs/data (merge if both exist)
for d in [ROOT / "data", ROOT / "app" / "data"]:
    if d.exists():
        shutil.copytree(d, OUT / "data", dirs_exist_ok=True)

# ---------- Loaders ----------
def load_items(dir_list):
    """Load and merge JSON files from the given directories, de-duping and sorting by 'order'."""
    items = []
    seen = set()
    for base in dir_list:
        if not base.exists():
            continue
        for p in base.rglob("*.json"):
            rp = p.resolve()
            if rp in seen:
                continue
            try:
                obj = json.loads(p.read_text(encoding="utf-8"))
                obj["_file"] = str(p.relative_to(ROOT))  # helpful for debugging
                items.append(obj)
                seen.add(rp)
            except Exception as e:
                print(f"[warn] skipping {p}: {e}")
    items.sort(key=lambda x: x.get("order", 1_000_000))
    return items

projects   = load_items(PROJECT_DIRS)
educations = load_items(EDUCATION_DIRS)

print(f"[build] loaded {len(projects)} project(s)")
for it in projects:
    print("  -", it.get("title"), "(", it.get("_file"), ")")
print(f"[build] loaded {len(educations)} education item(s)")

# ---------- Jinja ----------
env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"])
)

# Safety shim if a stray url_for remains
def _fake_url_for(endpoint, filename=None, **kwargs):
    if endpoint == "static" and filename:
        return f"static/{filename}"
    routing = {
        "pages.home": "index.html",
        "pages.projects": "projects.html",
        "pages.education": "education.html",
        "pages.contact": "contact.html",
    }
    return routing.get(endpoint, "")
env.globals["url_for"] = _fake_url_for

# ---------- Render ----------
pages = [
    ("home.html",      "index.html",    {}),
    ("projects.html",  "projects.html", {"projects": projects}),
    ("education.html", "education.html",{"educations": educations}),
    ("contact.html",   "contact.html",  {}),
]

for tpl_name, out_name, ctx in pages:
    tpl = env.get_template(tpl_name)
    (OUT / out_name).write_text(tpl.render(**ctx), encoding="utf-8")

# SPA-style 404 fallback (optional)
if (OUT / "index.html").exists():
    shutil.copy(OUT / "index.html", OUT / "404.html")

print("✅ Built static site to ./docs")
