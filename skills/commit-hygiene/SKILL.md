---
name: commit-hygiene
description: >
  Trunk-based Git branching, fast-forward merging, conventional commit formatting,
  and runtime artifact exclusion rules for ocr-engine.
  Trigger: Creating branches, staging files, crafting commits, or merging into development.
version: 1.0.0
---

# Commit Hygiene

Enforces trunk-based workflow and clean history across `ocr-engine`.

## When to Use

- Starting a new branch from `development`
- Staging files and writing commit messages
- Merging completed work back into `development`

---

## Critical Rules

1. **Never commit directly to `main` or `development`:** Always branch from `development` and merge back with `git merge --ff-only`.
2. **Branch naming format:** `<prefix>/<area>-<short-slug>` where prefix is `feat | fix | chore | docs | refactor | test` and area is `core | api | cli | mcp | web | supabase | repo`.
3. **Conventional Commit format:** `<type>(<scope>[,<scope>...]): <imperative description>` where type is `feat | fix | refactor | docs | test | chore | perf | style | ci` and scope is `core | api | cli | mcp | web | supabase | repo`.
4. **One logical change per commit:** Never mix refactors with new features. Stage explicitly by path (`git add <paths>`) or `git add -p`, never blind `git add .`.
5. **Only commit with explicit user authorization:** Repository scripts and automated steps never stage or commit without authorization.
6. **Never commit out-of-scope artifacts:** Exclude `runs/`, `outputs/`, `dataset/results*`, `.env*` (except `.env*.example`), `.server/`, `.server-token`, `.cloud-token`, `.cloud-image`, `.venv/`, `.graphify-venv/`, `node_modules/`, `.next/`, `.codex/`, `.devin/`, `.agents/`, and `~/.engram/engram.db`.

---

## Cookbook: Branch & Merge Flow

```bash
git switch -c feat/api-my-change development
# ... work and atomic commits ...
git diff --staged
git switch development
git merge --ff-only feat/api-my-change
git branch -d feat/api-my-change
```

If `development` advanced in the meantime, run `git rebase development` on the feature branch rather than merging `development` into it.

---

## Verification Checklist

- [ ] Branch name matches `<prefix>/<area>-<short-slug>`.
- [ ] Commit message matches `<type>(<scope>): <imperative description>`.
- [ ] `git status --short` contains zero secrets, `.env` files, or `runs/`/`outputs/` artifacts.
- [ ] Only the intended logical change is staged.
