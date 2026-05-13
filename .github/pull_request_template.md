## Adding / updating a package

<!-- Fill in once. Delete sections that don't apply. -->

**Name** (what users will type in `quirk pkg install`):
`<name>`

**Repository URL** (as it appears in your `index.toml` entry):
`github.com/<owner>/<repo>`

**One-line description**:
<!-- e.g. "Convert strings to URL-safe slugs" -->

---

## Checklist

Please confirm each of these before requesting review.

- [ ] My repo has a valid `quirk.toml` at its root, with at minimum `name` and `version`
- [ ] My repo has at least one tagged release (e.g. `v0.1.0`)
- [ ] `quirk pkg check` passes locally inside my repo (no errors)
- [ ] I can install it via URL today:
  `quirk pkg install github.com/<owner>/<repo>@<tag>` works on a clean machine
- [ ] The `name` doesn't shadow an existing entry in `index.toml`
- [ ] The `name` matches `[a-zA-Z0-9_-]+` (no spaces, no slashes)
- [ ] I'm not squatting a name I don't intend to maintain

---

## What this package does

<!-- 2-3 sentences. What problem does it solve? -->

## Anything reviewers should know

<!-- e.g. "I took the name 'http' because the previous owner abandoned it" -->
