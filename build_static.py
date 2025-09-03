# build_static.py (robust paths)
import json, shutil
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).parent
TEMPLATE_DIR = ROOT / "app" / "templates"     # your templates live here
OUT = ROOT / "docs"

# candidates for static dirs (copy whichever exist)
STATIC_DIRS = [ROOT / "app" / "static", ROOT / "static"]

# candidates for project JSON roots (load from both)
PROJECT_DIRS = [ROOT / "data" / "projects", ROOT / "app" / "data" / "projects"]

# clean output
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True, exist_ok=True)

# copy static/ into docs/static (merge if both exist)
for s in STATIC_DIRS:
    if s.exists():
        shutil.copytree(s, OUT / "static", dirs_exist_ok=True)

# copy data/ into docs/data (merge if both exist)
for d in [ROOT / "data", ROOT / "app" / "data"]:
    if d.exists():
        shutil.copytree(d, OUT / "data", dirs_exist_ok=True)

def load_projects(paths):
    items = []
    seen = set()
    for pdir in paths:
        if not pdir.exists():
            continue
        for p in pdir.rglob("*.json"):
            if p.resolve() in seen:
                continue
            try:
                obj = json.loads(p.read_text(encoding="utf-8"))
                obj["_file"] = str(p.relative_to(ROOT))
                items.append(obj)
                seen.add(p.resolve())
            except Exception as e:
                print(f"[warn] skipping {p}: {e}")
    items.sort(key=lambda x: x.get("order", 1_000_000))
    return items

projects = load_projects(PROJECT_DIRS)
print(f"[build] loaded {len(projects)} project(s)")
for it in projects:
    print("  -", it.get("title"), "(", it.get("_file"), ")")

env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"])
)

# tiny safety shim if a stray url_for remains
def _fake_url_for(endpoint, filename=None, **kwargs):
    if endpoint == "static" and filename:
        return f"static/{filename}"
    routing = {
        "pages.home": "index.html",
        "pages.projects": "projects.html",
        "pages.contact": "contact.html",
    }
    return routing.get(endpoint, "")
env.globals["url_for"] = _fake_url_for

pages = [
    ("home.html", "index.html", {}),
    ("projects.html", "projects.html", {"projects": projects}),
    ("contact.html", "contact.html", {}),
]

for tpl_name, out_name, ctx in pages:
    tpl = env.get_template(tpl_name)
    (OUT / out_name).write_text(tpl.render(**ctx), encoding="utf-8")

# optional: SPA fallback
if (OUT / "index.html").exists():
    shutil.copy(OUT / "index.html", OUT / "404.html")

print("✅ Built static site to ./docs")
