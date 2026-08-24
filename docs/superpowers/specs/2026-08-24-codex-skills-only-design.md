# Codex Skills-Only Integration Design

**Goal:** Support OpenAI Codex as a first-class consumer of this meta-plugin through native skills discovery, without symlinks, fallback installers, apps, MCPs, or hook emulation.

## Context

This repository already acts as a cross-CLI plugin catalog. Claude Code and OpenCode have distinct integration surfaces, but the reusable unit we want Codex to consume is the shared skills library. OpenAI's current Codex plugin model describes plugins as containers for skills, apps, and app templates, and the Superpowers project shows a clean Codex pattern centered on `.codex-plugin/plugin.json` with `skills: "./skills/"`.

The user explicitly wants:

- no symlink-based Codex setup
- no fallback install path
- no apps or MCP plumbing in this repository
- one shared skills catalog that stays reusable across all supported CLIs

## Non-goals

- Do not add Codex hooks.
- Do not add MCP servers, apps, or app templates.
- Do not change OpenCode installation docs as part of the Codex work.
- Do not introduce a secondary Codex install strategy or a “backup” path.

## Design

### 1. Codex is treated as a native plugin consumer

Codex support should be documented and maintained as a native plugin integration that discovers skills from the plugin package itself. The repository already has `.codex-plugin/plugin.json`; the design keeps that as the authoritative Codex manifest and documents the expected Codex workflow alongside it.

### 2. The shared unit remains `skills/`

All reusable behavior continues to live in the shared skills tree. That keeps the catalog consistent across Claude Code, OpenCode, and Codex. The Codex integration should point at the same skills source instead of materializing a separate skills directory or maintaining symlink overlays.

### 3. Codex-specific docs describe the native path only

A Codex installation guide should explain:

- that Codex reads the plugin manifest natively
- that the plugin is skills-only for this repo
- that no hooks, apps, or templates are required
- how to refresh/restart Codex so it picks up manifest or skill changes

### 4. Legacy symlink language is removed from Codex-facing docs and helper scripts

Any repo text or helper script that still implies “Codex needs a symlinked skills directory” should be revised. The goal is to make Codex documentation consistent with the Superpowers pattern and with the user’s preference to avoid filesystem clutter.

## Files in scope

- `README.md` — add a Codex section that points to the Codex-specific install guide and clarifies skills-only support.
- `AGENTS.md` — add a short Codex note in the plugin mode section so agents know Codex is skills-only and does not use the OpenCode hook path.
- `.codex/INSTALL.md` — new Codex-specific install guide.
- `bin/install-skills.sh` — remove Codex from the symlink installer and clarify that it is not part of the Codex flow.
- `features/multi-cli-compat/README.md` — update Codex wording so it matches the native skills-only model.
- `features/multi-cli-compat/files/install-skills.sh` — keep the template aligned with the new Codex stance.

## Validation

The design is correct when:

- Codex is described only as a native skills consumer.
- No doc or helper script recommends symlinking into `~/.codex/skills`.
- OpenCode documentation stays untouched.
- All Codex-facing references point to the same shared `skills/` catalog.
