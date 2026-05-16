# Quirk Package Registry

Maps short names to git sources, consumed by `quirk pkg install <name>`.

> **Publishing a package?** This README documents the *registry mechanics*.
> The full end-to-end walkthrough — from `quirk new` to a merged PR — is in
> **[PUBLISHING.md](PUBLISHING.md)**.

## Using the registry (as a consumer)

```bash
# One-time, per user
quirk pkg registry update

# Then everywhere
quirk pkg install slug
quirk pkg install slug@v0.1.0
quirk pkg install slug@'>=0.1,<1.0'
```

## Adding a package (TL;DR)

For the full walkthrough see **[PUBLISHING.md](PUBLISHING.md)**. The
registry-mechanic summary:

1. Fork this repo
2. Add one line to [`index.toml`](index.toml):

   ```toml
   your-name = "github.com/you/your-pkg"
   ```

   Optionally pin a default version:

   ```toml
   your-name = "github.com/you/your-pkg@v0.1.0"
   ```
3. Open a PR

PRs are validated automatically — see [Validation rules](#validation-rules) below.

## Requirements

Your package must have:

- **A valid `quirk.toml` at the repo root** with at minimum `name` and `version`.
  The `name` must equal the key you're adding to `index.toml`.
- **At least one tagged release** (e.g. `v0.1.0`) — without tags, users can
  only install HEAD of the default branch.

## Validation rules

Every PR runs [`scripts/validate.py`](scripts/validate.py), which checks:

| Check | Behavior |
|-------|----------|
| `index.toml` parses as TOML | error |
| Each value is a string | error |
| Each key matches `[a-zA-Z][a-zA-Z0-9_-]*` | error |
| Key is not in the reserved list (stdlib namespaces) | error |
| Value is `host/owner/repo[@ref]` shape | error |
| GitHub repo exists | error |
| Repo has a `quirk.toml` at the referenced ref (or default branch) | error |
| Manifest's `name` field equals the registry key | warning |

A PR with any **error** cannot be merged. **Warnings** still merge but get a
heads-up comment from the bot.

## Reserved names

The following names are reserved for the official standard library and
related infrastructure — third-party PRs claiming them will be rejected:

- `typing`, `console`, `sys`, `io`, `math`, `fs`, `time`, `regex`, `test`,
  `crypto`, `argparse`, `url`, `csv`, `net`, `encoding`, `json`, `http`, `https`
- `quirk`, `quirk-lang`, `core`, `std`, `stdlib`

## Security advisories

Known issues in published packages (broken builds, security flaws, data
corruption) are tracked in [`advisories.toml`](advisories.toml). Users see
them via `quirk pkg audit`:

```bash
quirk pkg audit
# Audited 1 package(s) against 1 advisor(ies).
#
# 1 issue(s) found:
#
#   ⚠ [moderate] slug 0.1.0  (QSA-0001)
#       Compilation fails on Quirk 0.2.0+
#       fix:  Upgrade to v0.1.1 or later
```

To report a problem with a published package, open a PR adding an
`[[advisory]]` entry. Severity values: `low`, `moderate`, `high`, `critical`.
Required fields: `id`, `package`, `versions`, `severity`.

## License

The registry index (this repo's contents) is MIT-licensed — see
[LICENSE](LICENSE). Individual packages listed here are distributed under
their own licenses; check each package's `quirk.toml` and repository.
