# Codex Skills-Only Integration Implementation Plan

> **Estado: ejecutado** (verificado 2026-08-27) — evidencia: `.codex-plugin/plugin.json`.
> Los checkboxes de abajo quedaron sin tildar: en este repo el estado real de una
> tarea vive en `DONE.md` del store central, no en el plan. No los leas como pendientes.


> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Codex a first-class, native, skills-only consumer of this plugin catalog, with docs and helper scripts aligned to that model.

**Architecture:** Codex will keep using the existing `.codex-plugin/plugin.json` manifest and the shared `skills/` tree. The implementation will remove symlink-oriented Codex guidance from helper scripts and replace it with Codex-specific documentation that mirrors the Superpowers pattern: native discovery, skills-only, no hooks/apps/templates, no fallback path.

**Tech Stack:** Markdown docs, shell scripts, existing plugin manifests.

---

### Task 1: Add a Codex-specific installation guide

**Files:**
- Create: `.codex/INSTALL.md`

- [ ] **Step 1: Write the new Codex install guide**

```md
# Installing cli-plugin-template in Codex

## What Codex gets

Codex consumes this repository as a native plugin with shared skills. For this project, Codex support is skills-only:

- no symlinks
- no MCP servers
- no apps or app templates
- no hook emulation

## Install

1. Open Codex.
2. Add or install the `cli-plugin-template` plugin through the Codex plugin flow.
3. Restart Codex if the new plugin does not appear immediately.

## Verify

Ask Codex to use a skill from this catalog, for example:

> use the `plugin-dev` skill

or ask for one of the catalog workflows such as auditing or recommending features.

## Updating

If Codex does not show the latest plugin version, refresh the plugin data or restart Codex, then re-open the plugin.
```

- [ ] **Step 2: Validate the file exists and contains the expected sections**

Run:
```bash
grep -nE '^(# Installing|## What Codex gets|## Install|## Verify|## Updating)' .codex/INSTALL.md
```
Expected: five matching headings.

- [ ] **Step 3: Commit**

```bash
git add .codex/INSTALL.md
git commit -m "docs: add Codex skills-only install guide"
```

### Task 2: Update the top-level docs to describe Codex correctly

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: Add a Codex section to README.md**

Add a short section after OpenCode that says Codex is supported as a native skills-only plugin, points to `.codex/INSTALL.md`, and explicitly says there is no symlink-based setup in this repo for Codex.

- [ ] **Step 2: Add a Codex note to AGENTS.md**

Add one compact note in the plugin mode section:

```md
Codex usa `.codex-plugin/plugin.json` y consume `skills/` de forma nativa; en este repo no hay hooks, apps ni symlinks para Codex.
```

- [ ] **Step 3: Check the docs mention the new Codex guide**

Run:
```bash
grep -n "\.codex/INSTALL.md\|Codex" README.md AGENTS.md
```
Expected: README links the guide and AGENTS includes the Codex note.

- [ ] **Step 4: Commit**

```bash
git add README.md AGENTS.md
git commit -m "docs: describe Codex as native skills-only plugin"
```

### Task 3: Remove Codex from the symlink installer path

**Files:**
- Modify: `bin/install-skills.sh`
- Modify: `features/multi-cli-compat/files/install-skills.sh`

- [ ] **Step 1: Remove Codex from the repo installer**

Change the comment in `bin/install-skills.sh` so it no longer lists Codex as a target for symlink installation, and delete the `codex` row from `PLATFORMS`.

- [ ] **Step 2: Keep the shared feature template aligned**

Update `features/multi-cli-compat/files/install-skills.sh` so its platform list also omits Codex from symlink targets and keeps Codex out of the “manual setup” path.

- [ ] **Step 3: Verify Codex is no longer advertised as a symlink target**

Run:
```bash
grep -n "codex" bin/install-skills.sh features/multi-cli-compat/files/install-skills.sh
```
Expected: no Codex symlink target remains in either script.

- [ ] **Step 4: Commit**

```bash
git add bin/install-skills.sh features/multi-cli-compat/files/install-skills.sh
git commit -m "docs: remove Codex from symlink skill installer"
```

### Task 4: Align multi-CLI compatibility docs with the Codex-native model

**Files:**
- Modify: `features/multi-cli-compat/README.md`

- [ ] **Step 1: Rewrite the Codex installation wording**

Replace the older “sync copies `skills/` + `.codex-plugin/` to the Codex fork” phrasing with a native-plugin explanation:

```md
- **Codex**: consume the plugin natively via `.codex-plugin/plugin.json`; skills load from the shared `skills/` tree and hooks are not part of this path.
```

- [ ] **Step 2: Confirm the doc no longer recommends a Codex symlink flow**

Run:
```bash
grep -n "symlink\|copy.*Codex\|fork of plugins of Codex" features/multi-cli-compat/README.md
```
Expected: no Codex symlink recommendation remains.

- [ ] **Step 3: Commit**

```bash
git add features/multi-cli-compat/README.md
git commit -m "docs: align multi-cli compat with native Codex skills"
```

### Task 5: Final validation pass

**Files:**
- No new files

- [ ] **Step 1: Check that Codex-facing docs are consistent**

Run:
```bash
grep -RIn "codex" README.md AGENTS.md .codex bin features/multi-cli-compat | sed -n '1,200p'
```

- [ ] **Step 2: Confirm there are no OpenCode doc changes in this branch**

Run:
```bash
git diff -- .opencode/INSTALL.md
```
Expected: no diff.

- [ ] **Step 3: Sanity-check the repo status**

Run:
```bash
git status --short
```
Expected: only the intended Codex-doc and installer-script files show up.
