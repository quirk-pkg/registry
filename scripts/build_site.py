#!/usr/bin/env python3
"""
Build the static registry website from index.toml.

Output: site/index.html (and site/style.css inline-included for simplicity).
Used by the GitHub Pages workflow.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request

try:
    import tomllib
    def parse_toml(b: bytes):
        return tomllib.loads(b.decode("utf-8"))
except ImportError:
    # Same fallback as the validator
    def parse_toml(b: bytes):
        out = {}
        for raw in b.decode("utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or (line.startswith("[") and line.endswith("]")):
                continue
            if "=" not in line:
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip()
            if "#" in v:
                v = v.split("#", 1)[0].strip()
            if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                v = v[1:-1]
            out[k] = v
        return out


TIMEOUT = 10


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "quirk-registry-builder"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            if r.status != 200:
                return ""
            return r.read().decode("utf-8", errors="replace")
    except Exception:
        return ""


def fetch_json(url: str):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "quirk-registry-builder",
    })
    # Use GH_TOKEN if available (lifts API rate limits in CI).
    tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            if r.status != 200:
                return None
            return json.loads(r.read())
    except Exception:
        return None


def parse_manifest_field(content: str, field: str) -> str:
    m = re.search(rf'^\s*{re.escape(field)}\s*=\s*"([^"]*)"', content, flags=re.MULTILINE)
    return m.group(1) if m else ""


def gather_package_info(name: str, spec: str) -> dict:
    """Best-effort fetch of metadata. Missing fields just stay empty."""
    body = spec
    ref = ""
    if "@" in body:
        body, ref = body.rsplit("@", 1)
    info = {
        "name": name,
        "spec": spec,
        "host": body.split("/", 1)[0] if "/" in body else body,
        "owner_repo": body.split("/", 1)[1] if "/" in body else "",
        "ref": ref,
        "url": "https://" + body if "://" not in body else body,
        "description": "",
        "version": "",
        "license": "",
        "homepage": "",
        "latest_tag": "",
        "stars": None,
    }
    if info["host"] != "github.com" or not info["owner_repo"]:
        return info

    branch = ref or "HEAD"
    raw = f"https://raw.githubusercontent.com/{info['owner_repo']}/{branch}/quirk.toml"
    manifest = fetch_text(raw)
    if manifest:
        info["description"] = parse_manifest_field(manifest, "description")
        info["version"]     = parse_manifest_field(manifest, "version")
        info["license"]     = parse_manifest_field(manifest, "license")
        info["homepage"]    = parse_manifest_field(manifest, "homepage")

    # Latest tag + star count (one API call).
    repo = fetch_json(f"https://api.github.com/repos/{info['owner_repo']}")
    if repo:
        info["stars"] = repo.get("stargazers_count")
    tags = fetch_json(f"https://api.github.com/repos/{info['owner_repo']}/tags?per_page=1")
    if tags and isinstance(tags, list) and tags:
        info["latest_tag"] = tags[0].get("name", "")

    return info


PAGE_TMPL = """\
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Quirk Package Registry</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Official package registry for the Quirk programming language.">
<style>
:root {{
  --bg: #f7f7f8;
  --fg: #1f2328;
  --muted: #6e7681;
  --accent: #0969da;
  --card-bg: #fff;
  --border: #d0d7de;
  --code-bg: #f0f1f3;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --bg: #0d1117; --fg: #e6edf3; --muted: #9198a1;
    --accent: #58a6ff; --card-bg: #161b22; --border: #30363d;
    --code-bg: #1c2128;
  }}
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  background: var(--bg);
  color: var(--fg);
  line-height: 1.5;
}}
.wrap {{ max-width: 980px; margin: 0 auto; padding: 2rem 1.25rem 4rem; }}
header {{
  border-bottom: 1px solid var(--border);
  padding-bottom: 1.5rem;
  margin-bottom: 2rem;
}}
h1 {{
  margin: 0 0 .5rem;
  font-size: 1.8rem;
  display: inline-flex;
  align-items: baseline;
  gap: .6rem;
}}
h1 span.count {{
  font-size: .9rem;
  color: var(--muted);
  font-weight: 500;
}}
.tagline {{ color: var(--muted); margin: 0 0 1rem; }}
.install {{
  background: var(--code-bg);
  padding: .75rem 1rem;
  border-radius: 8px;
  border: 1px solid var(--border);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: .92rem;
  overflow-x: auto;
}}
.install em {{ color: var(--muted); font-style: normal; }}
#filter {{
  width: 100%;
  padding: .55rem .75rem;
  margin-bottom: 1rem;
  font: inherit;
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--fg);
}}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; }}
.card {{
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1rem 1.1rem;
  display: flex;
  flex-direction: column;
  transition: transform .08s ease, border-color .08s ease;
}}
.card:hover {{ border-color: var(--accent); }}
.card h2 {{
  margin: 0 0 .25rem;
  font-size: 1.1rem;
}}
.card h2 a {{ color: var(--fg); text-decoration: none; }}
.card h2 a:hover {{ color: var(--accent); text-decoration: underline; }}
.card .meta {{
  font-size: .8rem;
  color: var(--muted);
  display: flex;
  flex-wrap: wrap;
  gap: .35rem .75rem;
  margin-bottom: .55rem;
}}
.card .desc {{
  font-size: .92rem;
  color: var(--fg);
  margin: 0 0 .8rem;
  flex: 1;
}}
.card .install-cmd {{
  background: var(--code-bg);
  border-radius: 5px;
  padding: .35rem .5rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: .82rem;
  word-break: break-all;
}}
.tag {{
  display: inline-block;
  background: var(--code-bg);
  border: 1px solid var(--border);
  border-radius: 99px;
  padding: 0 .55rem;
  font-size: .72rem;
  color: var(--muted);
}}
.tag.version {{ color: var(--accent); border-color: var(--accent); }}
footer {{
  margin-top: 3rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--border);
  color: var(--muted);
  font-size: .85rem;
  display: flex;
  flex-wrap: wrap;
  gap: 1rem 2rem;
}}
footer a {{ color: var(--muted); }}
.empty {{
  text-align: center;
  color: var(--muted);
  padding: 2.5rem 0;
}}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>Quirk Package Registry <span class="count">{count} package{plural}</span></h1>
  <p class="tagline">Short-name index for <a href="https://github.com/AlexVachon/quirk">Quirk</a>.
     <a href="https://github.com/quirk-pkg/registry">Source</a> ·
     <a href="https://github.com/quirk-pkg/registry#adding-a-package">Add a package</a></p>
  <div class="install">
    <em># one-time setup</em><br>
    quirk pkg registry update<br>
    <em># then anywhere</em><br>
    quirk pkg install &lt;name&gt;
  </div>
</header>

<input id="filter" placeholder="Search by name, description, or repo…" autofocus>

<div class="grid" id="grid">
{cards}
</div>
<p class="empty" id="empty" style="display:none">No packages match your search.</p>

<footer>
  <span>Generated {generated_at}</span>
  <a href="https://github.com/quirk-pkg/registry/blob/main/index.toml">View raw index.toml</a>
</footer>
</div>

<script>
// Tiny client-side filter — no framework needed.
const input = document.getElementById('filter');
const empty = document.getElementById('empty');
const cards = Array.from(document.querySelectorAll('.card'));
input.addEventListener('input', () => {{
  const q = input.value.trim().toLowerCase();
  let shown = 0;
  for (const c of cards) {{
    const hit = q === '' || c.dataset.search.includes(q);
    c.style.display = hit ? '' : 'none';
    if (hit) shown++;
  }}
  empty.style.display = shown ? 'none' : 'block';
}});
</script>
</body>
</html>
"""


CARD_TMPL = """\
<div class="card" data-search="{search_blob}">
  <h2><a href="{url}">{name}</a></h2>
  <div class="meta">
    {version_tag}{license_tag}<span class="tag">{owner_repo}</span>{stars_tag}
  </div>
  <p class="desc">{description}</p>
  <code class="install-cmd">quirk pkg install {name}{ref_suffix}</code>
</div>
"""


def render_card(info: dict) -> str:
    desc = info["description"] or '<em style="color: var(--muted)">No description.</em>'
    version_tag = f'<span class="tag version">v{html.escape(info["version"])}</span>' \
        if info["version"] else ""
    license_tag = f'<span class="tag">{html.escape(info["license"])}</span>' \
        if info["license"] else ""
    stars_tag = ""
    if info["stars"] is not None:
        stars_tag = f'<span class="tag">★ {info["stars"]}</span>'
    ref_suffix = f"@{info['ref']}" if info["ref"] else ""
    search_blob = " ".join([
        info["name"].lower(),
        info["description"].lower(),
        info["owner_repo"].lower(),
    ])
    return CARD_TMPL.format(
        name=html.escape(info["name"]),
        url=html.escape(info["url"]),
        owner_repo=html.escape(info["owner_repo"] or info["host"]),
        version_tag=version_tag,
        license_tag=license_tag,
        stars_tag=stars_tag,
        description=html.escape(desc) if not desc.startswith("<em") else desc,
        ref_suffix=html.escape(ref_suffix),
        search_blob=html.escape(search_blob, quote=True),
    )


def main() -> int:
    try:
        with open("index.toml", "rb") as f:
            data = parse_toml(f.read())
    except FileNotFoundError:
        print("index.toml not found (run from repo root)", file=sys.stderr)
        return 2

    entries = sorted(
        ((k, v) for k, v in data.items() if isinstance(v, str)),
        key=lambda kv: kv[0].lower(),
    )
    print(f"Building site for {len(entries)} package(s)…")

    cards = []
    for name, spec in entries:
        print(f"  · {name}")
        info = gather_package_info(name, spec)
        cards.append(render_card(info))

    page = PAGE_TMPL.format(
        count=len(entries),
        plural="" if len(entries) == 1 else "s",
        cards="\n".join(cards) if cards else "",
        generated_at=dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    )

    os.makedirs("site", exist_ok=True)
    with open("site/index.html", "w", encoding="utf-8") as f:
        f.write(page)
    print(f"Wrote site/index.html ({len(page)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
