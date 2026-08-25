# Feedback Dedup + Deferred Status Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `deferred` as a formal feedback status and deduplication logic to prevent duplicate feedbacks from being created.

**Architecture:** Two small, independent changes to `bin/lib/gateway.py` (the persistence layer) + CLI wiring + tests. No new files, no new hooks. The dedup check happens at save time: before creating a feedback, check if one with the same slug already exists and act accordingly. Deferred is a 4th status that sits alongside pending/applied/discarded — it means "valid but not now".

**Tech Stack:** Python 3.10+, bash tests (existing test-cpt-feedback.sh pattern)

---

## File Structure

- Modify: `bin/lib/gateway.py` — add `deferred` to FEEDBACK_STATUSES, add dedup logic to `feedback_save`
- Modify: `bin/cpt` — add `defer` subcommand wired to `feedback_set_status`
- Modify: `bin/test-cpt-feedback.sh` — add tests for both features

---

### Task 1: Add `deferred` status to FEEDBACK_STATUSES

**Files:**
- Modify: `bin/lib/gateway.py:229`

- [ ] **Step 1: Add `deferred` to the tuple**

```python
# bin/lib/gateway.py line 229
FEEDBACK_STATUSES = ("pending", "applied", "discarded", "deferred")
```

- [ ] **Step 2: Verify existing tests still pass**

Run: `bash bin/test-cpt-feedback.sh`
Expected: all existing tests PASS

---

### Task 2: Add `defer` CLI subcommand

**Files:**
- Modify: `bin/cpt` (CLI dispatch)

- [ ] **Step 1: Find where `apply` and `discard` are wired in `cpt`**

Run: `grep -n "apply\|discard" bin/cpt`

- [ ] **Step 2: Add `defer` subcommand following the same pattern**

The `defer` subcommand calls `feedback_set_status(plugin, slug, "deferred")`. Follow the exact same pattern as `apply` and `discard`.

- [ ] **Step 3: Verify `cpt feedback defer` works**

Run: `bash bin/test-cpt-feedback.sh`
Expected: all tests PASS (no breakage)

---

### Task 3: Add dedup logic to `feedback_save`

**Files:**
- Modify: `bin/lib/gateway.py:180-217` (feedback_save function)

- [ ] **Step 1: Add dedup check at the start of `feedback_save`**

Before the existing upsert logic, check if a feedback with the same slug already exists. If it does:

| Existing status | Action |
|---|---|
| `pending` | Skip save, return existing path with a message |
| `deferred` | Skip save, return existing path with a message |
| `applied` | Overwrite with status `pending` (re-activation) |
| `discarded` | Overwrite with status `pending` (re-activation) |

```python
def feedback_save(plugin: str, slug: str, content: str) -> str:
    # ... existing docstring ...
    path = paths.feedbacks_dir(plugin) / f"feedback_{paths.slugify(slug)}.md"
    prev = _read(path)
    if prev:
        existing_status = _state_of(prev)
        if existing_status in ("pending", "deferred"):
            # Dedup: already active or deferred, don't recreate
            return f"exists:{existing_status}:{path}"
        # applied/discarded → re-activate as pending
    # ... rest of existing logic unchanged ...
```

The return value changes from `str` to `str | dict` — or better, keep it as `str` and use a prefix convention (`exists:`) so callers don't break. The CLI layer can parse this and print a human message.

- [ ] **Step 2: Update CLI layer to handle the `exists:` prefix**

In `bin/cpt`, where `feedback save` is dispatched, check if the result starts with `exists:` and print a message like "Feedback ya existe con status <X>, no se creó duplicado."

- [ ] **Step 3: Run existing tests**

Run: `bash bin/test-cpt-feedback.sh`
Expected: the "re-save preserva created y status" test (line 37-56) will need updating — that test creates a feedback with `status: applied` then re-saves with `status: pending`. With dedup, the second save should succeed (re-activation from applied → pending). Verify behavior is correct.

---

### Task 4: Tests for dedup and deferred

**Files:**
- Modify: `bin/test-cpt-feedback.sh`

- [ ] **Step 1: Test — save new feedback creates it**

```bash
python3 "$CPT" feedback save test-plugin "new-feature" - >/dev/null <<'EOF'
---
name: feedback-new-feature
plugin: test-plugin
---
nuevo feedback
EOF
f="$DATA/test-plugin/feedbacks/feedback_new-feature.md"
[ -f "$f" ] && _pass "save creates new feedback" || _fail "save: no existe $f"
```

- [ ] **Step 2: Test — re-save with same slug and pending status → skip (dedup)**

```bash
out=$(python3 "$CPT" feedback save test-plugin "new-feature" - <<< "duplicado" 2>&1)
echo "$out" | grep -q "exists:pending" && _pass "dedup: pending feedback not duplicated" \
    || _fail "dedup: should have returned exists:pending, got: $out"
```

- [ ] **Step 3: Test — defer a feedback**

```bash
python3 "$CPT" feedback defer test-plugin "new-feature" >/dev/null
grep -q "^status: deferred" "$f" && _pass "defer: status changes to deferred" \
    || _fail "defer: '$(cat "$f")'"
```

- [ ] **Step 4: Test — re-save with same slug while deferred → skip (dedup)**

```bash
out=$(python3 "$CPT" feedback save test-plugin "new-feature" - <<< "duplicado" 2>&1)
echo "$out" | grep -q "exists:deferred" && _pass "dedup: deferred feedback not duplicated" \
    || _fail "dedup: should have returned exists:deferred, got: $out"
```

- [ ] **Step 5: Test — apply then re-save → re-activate as pending**

```bash
python3 "$CPT" feedback apply test-plugin "new-feature" >/dev/null
python3 "$CPT" feedback save test-plugin "new-feature" - >/dev/null <<'EOF'
---
name: feedback-new-feature
plugin: test-plugin
---
reactivado
EOF
grep -q "^status: pending" "$f" && grep -q "reactivado" "$f" \
    && _pass "re-activate: applied feedback → pending on re-save" \
    || _fail "re-activate: '$(cat "$f")'"
```

- [ ] **Step 6: Test — discard then re-save → re-activate as pending**

```bash
python3 "$CPT" feedback discard test-plugin "new-feature" >/dev/null
python3 "$CPT" feedback save test-plugin "new-feature" - >/dev/null <<'EOF'
---
name: feedback-new-feature
plugin: test-plugin
---
reactivado2
EOF
grep -q "^status: pending" "$f" && grep -q "reactivado2" "$f" \
    && _pass "re-activate: discarded feedback → pending on re-save" \
    || _fail "re-activate: '$(cat "$f")'"
```

- [ ] **Step 7: Run full test suite**

Run: `bash bin/test-cpt-feedback.sh`
Expected: all PASS

---

### Task 5: Update `feedback list` to support deferred filtering

**Files:**
- Modify: `bin/lib/gateway.py:253-282` (feedback_list function)
- Modify: `bin/cpt` (CLI dispatch for `feedback list`)

- [ ] **Step 1: Add `--deferred` flag to `feedback_list`**

Following the same pattern as `pending_only`, add a `deferred_only` parameter. When set, only return feedbacks with `status: deferred`.

- [ ] **Step 2: Wire `--deferred` in CLI**

Add `--deferred` flag to `cpt feedback list`.

- [ ] **Step 3: Test deferred list filter**

```bash
python3 "$CPT" feedback save test-plugin "deferred-test" - >/dev/null <<'EOF'
---
name: feedback-deferred-test
plugin: test-plugin
---
para deferir
EOF
python3 "$CPT" feedback defer test-plugin "deferred-test" >/dev/null
out=$(python3 "$CPT" feedback list --deferred)
echo "$out" | grep -q "test-plugin/deferred-test" \
    && _pass "list --deferred shows deferred feedback" \
    || _fail "list --deferred: '$out'"
```

- [ ] **Step 4: Run full test suite**

Run: `bash bin/test-cpt-feedback.sh`
Expected: all PASS

---

## Self-Review

1. **Spec coverage:** Both requirements (dedup + deferred status) have tasks. ✅
2. **Placeholder scan:** All steps have concrete code. ✅
3. **Type consistency:** `feedback_save` return type stays `str`, uses `exists:` prefix convention. `FEEDBACK_STATUSES` tuple updated. ✅
4. **Backward compatibility:** Existing `applied`/`discarded` feedbacks continue to work. The `feedback_set_status` function already validates against `FEEDBACK_STATUSES`, so adding `deferred` there is automatic. ✅
