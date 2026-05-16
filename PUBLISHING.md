# Publishing a Quirk package

End-to-end guide: from empty directory to `quirk pkg install your-pkg` working
for everyone.

The flow has five steps:

1. [Scaffold](#1-scaffold) the package
2. [Write](#2-write-code-and-tests) code + tests
3. [Validate](#3-validate) locally
4. [Release](#4-release) to GitHub (tag + push)
5. [Register](#5-register-in-the-central-registry) the short name

A minimal example (the `slug` package) is referenced throughout.

---

## 1. Scaffold

```bash
quirk new my-pkg
cd my-pkg
```

This creates:

```
my-pkg/
├── quirk.toml            ← manifest
├── .gitignore
├── src/
│   └── index.qk          ← package entry point
└── tests/
    └── my-pkg_test.qk
```

Then make it a git repo and push an empty initial commit:

```bash
git init
git add .
git commit -m "init"
gh repo create my-pkg --public --source=. --remote=origin --push
```

> **Reserved names.** Some names (`typing`, `math`, `fs`, `net`, `crypto`,
> `quirk`, `std`, etc.) belong to the standard library and cannot be used.
> The full list is in [README.md](README.md#reserved-names).

---

## 2. Write code and tests

### `quirk.toml`

The manifest declares your package. Minimum required fields are `name` and
`version`; the rest are strongly recommended.

```toml
name        = "my-pkg"
version     = "0.1.0"
description = "One-line summary of what the package does"
author      = "Your Name <you@example.com>"
license     = "MIT"
repository  = "https://github.com/you/my-pkg.git"
homepage    = "https://github.com/you/my-pkg"

# Pin the minimum Quirk compiler version your package needs.
quirk-version = ">=0.2.0"

# Runtime deps — installed when someone runs `quirk pkg install my-pkg`.
[deps]
# slug = "slug@>=1.0,<2.0"

# Dev deps — only installed when running `quirk pkg install --dev` (CI, tests).
[dev-deps]
# test-helpers = "github.com/you/test-helpers"

# Named scripts — run via `quirk run <name>`. List with `quirk run --list`.
[scripts]
test = "quirk run tests/my-pkg_test.qk"
```

Both `name` and the short name you'll register in `index.toml` **must match**.
Otherwise the registry validator rejects the PR.

### Code layout

| Path                           | Purpose                                                     |
|--------------------------------|-------------------------------------------------------------|
| `src/index.qk`                 | Entry point. `quirk pkg install` exposes this as `my-pkg`. |
| `src/anything-else.qk`         | Submodules. Importable as `from my-pkg use { … }`.         |
| `tests/`                       | Local-only. **Stripped at install time** — consumers never see it. |
| `.git/`, `.github/`, `.vscode/`, `.idea/` | Also stripped at install time. |

The pruning is automatic — there's no manifest setting to configure.
[See the test below to confirm.](#tests-not-shipped)

### Docstrings

Place a `---` block directly above any `define` / `struct` for it to appear in
hover tooltips and tooling.

```quirk
---
Convert a free-form string into a URL-safe slug.

Letters are lowercased; runs of any non-alphanumeric characters
collapse into a single `-`; leading and trailing dashes are trimmed.

@example
print(slug("Hello, World!"))     // "hello-world"
print(slug("  C++ & Quirk  "))   // "c-quirk"
---
define slug(s: String) -> String { … }
```

**Important:** the closing `---` must be *directly* above the definition.
A blank line between the closing `---` and the definition makes the block a
*module-level* docstring instead of attaching it to the symbol.

### Tests

```quirk
// tests/my-pkg_test.qk
from my-pkg use { my_function }

define main() -> void {
    print(my_function("hello"))
}
```

Run them locally:

```bash
quirk run tests/my-pkg_test.qk
# or, if you defined [scripts]:
quirk run test
```

---

## 3. Validate

`quirk pkg check` runs a pre-flight pipeline — the same checks the registry
validator runs on your PR, plus a few more:

```bash
quirk pkg check
```

Common findings:

| Finding | Meaning | Severity |
|---------|---------|----------|
| `no `quirk-version` constraint` | Manifest doesn't say which compiler versions are supported | warning |
| `working tree is dirty` | Uncommitted changes | warning |
| `latest git tag (v0.1.0) doesn't match manifest version (0.1.1)` | You bumped `version` but haven't tagged the release | warning |
| `name in registry-key form (kebab-case)` | Helps registry lookup work uniformly | info |
| `type-check passed` | Compiler accepted `src/index.qk` | ok |

Fix every error; warnings are advisory but reviewers will ask about them.

### Tests not shipped

To confirm `tests/` is stripped before consumers see the package, install your
own package locally into a sandbox:

```bash
mkdir /tmp/sandbox && cd /tmp/sandbox
quirk init --yes
quirk pkg install /path/to/my-pkg
ls packages/my-pkg/        # should NOT contain tests/, .git/, etc.
```

---

## 4. Release

The release command bumps the version, tags the commit, validates, and pushes.

```bash
# Bumps 0.1.0 → 0.1.1, tags v0.1.1, pushes both
quirk pkg release --bump patch

# Bumps 0.1.1 → 0.2.0
quirk pkg release --bump minor

# Manually-edited version: skip --bump, just tag what's in quirk.toml
quirk pkg release

# Tag locally only (debug push problems first)
quirk pkg release --bump patch --no-push
```

If `quirk pkg release` reports issues, it aborts before tagging — fix and
re-run.

### Versioning

Use [semver](https://semver.org). Quirk's resolver understands range syntax:

| Spec | Matches |
|------|---------|
| `1.0.0`            | exactly `1.0.0` |
| `^1.0.0`           | `>=1.0.0,<2.0.0` |
| `~1.0.0`           | `>=1.0.0,<1.1.0` |
| `>=1.0,<2.0`       | explicit range |
| `*` or empty       | any version |

Bump rules:

| Change | Bump |
|--------|------|
| Bug fix, no API change | patch (`0.1.0` → `0.1.1`) |
| New feature, backwards compatible | minor (`0.1.0` → `0.2.0`) |
| Breaking API change | major (`0.1.0` → `1.0.0`) |

Pre-1.0 the rules are softer — many authors treat any change as a minor bump
until the API stabilizes.

### Tag conventions

Quirk accepts both `v1.0.0` and `1.0.0`. `quirk pkg release` writes the
`v`-prefixed form (matching git/GitHub convention). Consumers can install
either form regardless:

```bash
quirk pkg install slug@1.0.0    # works
quirk pkg install slug@v1.0.0   # also works
```

---

## 5. Register in the central registry

Without this step, your package is still installable — by URL:

```bash
quirk pkg install github.com/you/my-pkg
```

Registering gives it a short name (`quirk pkg install my-pkg`).

1. **Fork** [quirk-pkg/registry](https://github.com/quirk-pkg/registry).
2. **Add one line** to [`index.toml`](index.toml):

   ```toml
   my-pkg = "github.com/you/my-pkg"
   ```

   Optionally pin a default version:

   ```toml
   my-pkg = "github.com/you/my-pkg@v0.1.0"
   ```

3. **Open a PR.** The validator runs automatically and comments on failure.

Once merged, anyone can:

```bash
quirk pkg registry update    # one-time, refreshes the local cache
quirk pkg install my-pkg
```

---

## Maintaining a released package

### Cutting a new release

```bash
# Make changes, commit
git commit -am "fix: foo"

# Bump + tag + push in one command
quirk pkg release --bump patch
```

Existing consumers automatically pick up the new tag on their next
`quirk pkg upgrade my-pkg` (or `quirk pkg install my-pkg@latest`). Lockfiles
pin specific versions, so they only upgrade when the user runs `upgrade`.

### Reporting a known issue

If a published version has a serious bug, security flaw, or data-corruption
problem, file an advisory:

1. Fork [quirk-pkg/registry](https://github.com/quirk-pkg/registry).
2. Add an entry to [`advisories.toml`](advisories.toml):

   ```toml
   [[advisory]]
   id          = "QSA-0042"
   package     = "my-pkg"
   versions    = "<0.1.1"
   severity    = "moderate"
   title       = "Off-by-one in slug() trims final char"
   description = "When the input ends in a non-alphanumeric char, slug() returns an empty string."
   fix         = "Upgrade to v0.1.1 or later"
   url         = "https://github.com/you/my-pkg/issues/3"
   ```

3. Open a PR.

Users will then see the advisory via `quirk pkg audit`.

### Unpublishing

Quirk's registry is index-only — it doesn't host code, it just points at your
GitHub repo. To "unpublish":

- Delete the GitHub repo (or the tag), and
- Open a PR removing the line from `index.toml`.

Filing an advisory with `severity = "critical"` and a clear `fix` is usually
the better choice than unpublishing — it preserves history for users pinned
to the old version.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `release: tag 'v0.1.1' already exists` | You already released this version | Bump again: `quirk pkg release --bump patch` |
| `install: no tag of github.com/you/my-pkg satisfies '>=1.0'` | No matching git tag pushed | `git push --tags` |
| Validator: `repo has a quirk.toml … warning: name mismatch` | `quirk.toml [name]` differs from the registry key | Make them identical (kebab-case is the convention) |
| `quirk pkg release` push fails | git auth not set up | Run `git push` once manually to confirm, then retry |
| Consumer says `not in registry or cache` | Their registry cache is stale | They run `quirk pkg registry update` |

---

## Reference

- [`README.md`](README.md) — registry overview, validation rules, reserved names
- [`scripts/validate.py`](scripts/validate.py) — what the PR validator actually checks
- [`advisories.toml`](advisories.toml) — known issues in published packages
- Quirk CLI: `quirk help`, `quirk pkg help`
