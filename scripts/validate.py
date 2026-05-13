#!/usr/bin/env python3
"""
Validate index.toml entries in the Quirk package registry.

Run from the repo root:
    python scripts/validate.py

Used by the GitHub Actions workflow to gate PRs.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request

try:
    import tomllib  # 3.11+
    def parse_toml(b: bytes):
        return tomllib.loads(b.decode("utf-8"))
except ImportError:
    try:
        import tomli  # 3.8-3.10 with `pip install tomli`
        def parse_toml(b: bytes):
            return tomli.loads(b.decode("utf-8"))
    except ImportError:
        # Hand-rolled fallback so `python scripts/validate.py` works on any
        # Python 3 even without tomllib/tomli. We only support the subset
        # the registry uses: flat `key = "value"` pairs and `# comments`.
        def parse_toml(b: bytes):
            out = {}
            for raw in b.decode("utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("[") and line.endswith("]"):
                    # Sections aren't part of index.toml's flat format
                    continue
                if "=" not in line:
                    raise ValueError(f"unparseable line: {raw!r}")
                k, _, v = line.partition("=")
                k = k.strip()
                v = v.strip()
                # Strip trailing inline-comment, then quotes.
                if "#" in v:
                    v = v.split("#", 1)[0].strip()
                if (v.startswith('"') and v.endswith('"')) \
                   or (v.startswith("'") and v.endswith("'")):
                    v = v[1:-1]
                else:
                    raise ValueError(f"value must be quoted: {raw!r}")
                out[k] = v
            return out

NAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{0,63}$")
URL_RE  = re.compile(
    r"^(?:github\.com|gitlab\.com|bitbucket\.org)"
    r"/[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+"
    r"(?:@[\w./-]+)?$"
)

# Names we never want third-parties to take — reserved for stdlib/official use.
RESERVED = {
    "typing", "console", "sys", "io", "math", "fs", "time",
    "regex", "test", "crypto", "argparse", "url", "csv", "net",
    "encoding", "json", "http", "https",
    "quirk", "quirk-lang", "core", "std", "stdlib",
}

TIMEOUT = 10  # seconds


def fetch_json(url: str) -> tuple[int, dict | None]:
    """GET a URL, return (status, parsed-json-or-none)."""
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "quirk-registry-validator",
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return 0, None


def fetch_text(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "quirk-registry-validator"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return 0, ""


def parse_entry(value: str) -> tuple[str, str, str | None]:
    """Return (host, owner_repo, ref-or-None) from `github.com/foo/bar@v1`."""
    ref = None
    if "@" in value:
        body, ref = value.rsplit("@", 1)
    else:
        body = value
    host, _, path = body.partition("/")
    return host, path, ref


def check_github_repo(owner_repo: str, ref: str | None) -> list[str]:
    """Verify the repo exists, has a quirk.toml, and the manifest name matches."""
    errs: list[str] = []
    status, _ = fetch_json(f"https://api.github.com/repos/{owner_repo}")
    if status == 404:
        errs.append(f"repo not found: github.com/{owner_repo}")
        return errs
    if status != 200:
        errs.append(f"GitHub API returned {status} for {owner_repo} (rate limit?)")
        # Don't fail PR on rate limit — just warn
        return errs

    # Verify quirk.toml exists at the (optional) ref, default branch otherwise.
    branch = ref if ref else "HEAD"
    raw = f"https://raw.githubusercontent.com/{owner_repo}/{branch}/quirk.toml"
    status, body = fetch_text(raw)
    if status != 200:
        errs.append(f"no quirk.toml at github.com/{owner_repo}@{branch}")
        return errs
    return errs


def check_manifest_name(owner_repo: str, ref: str | None,
                       expected_name: str) -> list[str]:
    branch = ref if ref else "HEAD"
    raw = f"https://raw.githubusercontent.com/{owner_repo}/{branch}/quirk.toml"
    status, body = fetch_text(raw)
    if status != 200:
        return []  # already reported by check_github_repo
    # Tiny TOML scan: `name = "..."` at the top level
    m = re.search(r'^\s*name\s*=\s*"([^"]+)"', body, flags=re.MULTILINE)
    if not m:
        return [f"package's quirk.toml has no `name = ...` field"]
    found = m.group(1)
    if found != expected_name:
        return [
            f"registry key '{expected_name}' doesn't match the package's "
            f"manifest name '{found}'"
        ]
    return []


def validate(entries: dict[str, str]) -> tuple[int, int]:
    """Return (error-count, warning-count)."""
    errs = 0
    warns = 0
    print(f"Validating {len(entries)} registry entries\n")
    for name, value in entries.items():
        prefix = f"  {name}:"
        if not isinstance(value, str):
            print(f"{prefix} ✗ value must be a string")
            errs += 1
            continue
        if not NAME_RE.match(name):
            print(f"{prefix} ✗ invalid name (use [a-zA-Z][a-zA-Z0-9_-]*)")
            errs += 1
        if name.lower() in RESERVED:
            print(f"{prefix} ✗ '{name}' is reserved for the official stdlib")
            errs += 1
        if not URL_RE.match(value):
            print(f"{prefix} ✗ malformed URL '{value}' "
                  f"(want host/owner/repo[@ref])")
            errs += 1
            continue
        host, owner_repo, ref = parse_entry(value)
        if host == "github.com":
            repo_errs = check_github_repo(owner_repo, ref)
            for e in repo_errs:
                print(f"{prefix} ✗ {e}")
                errs += 1
            if not repo_errs:
                name_errs = check_manifest_name(owner_repo, ref, name)
                for e in name_errs:
                    print(f"{prefix} ⚠ {e}")
                    warns += 1
        if errs == 0 and warns == 0:
            print(f"{prefix} ✓ {value}")
    return errs, warns


def main() -> int:
    try:
        with open("index.toml", "rb") as f:
            data = parse_toml(f.read())
    except FileNotFoundError:
        print("index.toml not found (run from repo root)", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"index.toml is not valid TOML: {e}", file=sys.stderr)
        return 2

    # Flat name = "url" only (no sections expected).
    entries = {k: v for k, v in data.items() if not isinstance(v, dict)}
    errs, warns = validate(entries)
    print(f"\n{len(entries)} entries, {errs} error(s), {warns} warning(s)")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
