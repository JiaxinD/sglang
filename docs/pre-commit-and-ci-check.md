# Pre-commit and CI Check in SGLang

## Pre-commit (`.pre-commit-config.yaml`)

Pre-commit runs hooks **locally before each commit** (and optionally on push). The current hooks are:

| Hook | Purpose |
|---|---|
| **pre-commit-hooks** (v6.0.0) | Basic checks: trailing whitespace, end-of-file fixer, YAML/TOML/AST validation, large file detection, merge conflict markers, private key detection, `no-commit-to-branch` |
| **isort** (7.0.0) | Sort Python imports |
| **ruff** (v0.15.1) | Lint for unused imports (`F401`) and undefined names (`F821`), with auto-fix |
| **black** (26.1.0) | Python + Jupyter code formatting |
| **codespell** (v2.4.1) | Spell checking (configured via `.codespellrc`) |
| **clang-format** (v20.1.7) | C++/CUDA formatting |
| **nbstripout** (0.9.0) | Strip notebook metadata |
| **2 local hooks** | Check Chinese characters in `multimodal_gen/`, sort `CI_PERMISSIONS.json` |
| **lychee** (lychee-v0.22.0) | Offline docs link checks for local authoring issues |

Key details:

- **Excluded paths**: `multimodal_gen/csrc` and `flash_attention/cute` are globally excluded
- **Generated code** (grpc `_pb2` files) is excluded from isort, ruff, and black
- **Local docs links**: lychee runs in `offline = true` mode and excludes `docs/_build/`
- **Stages**: `pre-commit`, `pre-push`, and `manual`

## CI Lint Workflow (`.github/workflows/lint.yml`)

This runs **on every push to `main` and every PR targeting `main`**:

```yaml
- Install pre-commit
- Run: SKIP=no-commit-to-branch pre-commit run --all-files --show-diff-on-failure
- Run lychee online checks with .github/linters/lychee-ci.toml
- Run clang-format on sgl-kernel/ separately (via DoozyX/clang-format-lint-action)
```

It re-runs the pre-commit hooks in CI (skipping `no-commit-to-branch` since CI runs on branches), and adds a separate online lychee pass for external link availability. This acts as a safety net if a developer didn't have pre-commit installed locally and provides stronger URL validation than offline checks.

## Auto-Format Workflow (`.github/workflows/auto-format.yml`)

A convenience workflow triggered when the **`format` label** is added to a PR:

1. Checks out the PR branch
2. Runs `pre-commit run --all-files` (allowing failures)
3. If there are changes, commits and pushes them automatically
4. Removes the `format` label

This lets contributors fix formatting without running pre-commit locally.

## PR Gate (`.github/workflows/pr-gate.yml`)

Before the heavy CI tests run (`pr-test.yml`), this reusable workflow enforces:

1. **Block draft PRs** from running CI
2. **Require `run-ci` label** on the PR
3. **Rate-limit** low-permission users (default 120-min cooldown, configurable per-user via `.github/CI_PERMISSIONS.json`)

## How to Add a Broken-Link Checker

To add a docs link checker, follow the existing pattern:

1. **Add a hook in `.pre-commit-config.yaml`** — either use an existing repo like [`lychee`](https://github.com/lycheeverse/lychee) or a `local` hook (like the Chinese character checker at lines 68–83 of `.pre-commit-config.yaml`)
2. **It automatically runs in CI** — the `lint.yml` workflow runs `pre-commit run --all-files`, so any new hook is picked up with zero changes to CI config
3. **It automatically gets auto-format support** — the `auto-format.yml` workflow also runs pre-commit

The local hook pattern in the existing config (lines 68–83) shows how to add a custom script-based check if you need something tailored to the repo's doc structure.
