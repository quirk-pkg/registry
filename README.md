# Quirk Package Registry

Maps short names to git sources, consumed by `quirk pkg install <name>`.

## Using the registry

```bash
# One-time, per user
quirk pkg registry update

# Then everywhere
quirk pkg install slug
quirk pkg install slug@v0.1.0
```

## Adding a package

1. Fork this repo
2. Add one line to [`index.toml`](index.toml):

   ```toml
   your-name = "github.com/you/your-pkg"
   ```

3. Open a PR

Your package must have:

- A valid `quirk.toml` at the repo root (with `name` and `version`)
- At least one tagged release (e.g. `v0.1.0`)

PRs are reviewed for name collisions and obviously-broken entries. The
package code itself stays under your own control — this registry only
stores the name-to-URL mapping.

## What's a Quirk package?

See the main Quirk documentation:
[Quirk Packages Guide](https://github.com/AlexVachon/quirk/blob/main/PACKAGES.md)
