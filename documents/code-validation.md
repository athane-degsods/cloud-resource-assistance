# Code validation — final pass

**Pipeline verdict:** Backend routing works end-to-end (`/chat` → breakdown → runbook paths → EC2 text → prompt → LLM mock → json handler). LLM modules are acceptable to land with teammates (`USE_MOCK_LLM`, adapters present).

## Module status

| Module | Status | Notes |
|---|---|---|
| Processing (`app.py`) | OK | Orchestrates full chain; logs each step |
| String breakdown | OK | `breakdown(text) → list[str]` |
| Filter and request | OK (paths only) | Returns metadata `path`s; does **not** load file content into the prompt |
| AWS ingestor | OK | `ingest()` → EC2 text from `samples/ec2-cloudwatch.json` |
| EC2 processor | OK (pass-through) | `process_ec2` → `ingest()`; `request_hint` unused |
| Prompt crafter | OK | Builds chat messages |
| LLM server | OK for now | `call_llm` → mock/`generate_recommendations`; live API later |
| Json handler | OK for now | Validates; `handle_json` returns summary string |

## What you are still missing (vs `idea.md` + min requirements)

### Demo / product gaps (highest impact)

1. **User interface** — no HTML chat page; only curl/`/chat` JSON API.
2. **HITL loop** — `action: approve | edit | reject` is logged but does nothing; no mock cloud action after approval.
3. **Failure demo** — `"delete production"` still returns the mock *idle-dev success* recommendation (mock LLM ignores request). Need a real block / high-risk path for the scripted failure case.
4. **Runbook content not bundled** — prompt gets path strings only (`runbook/idle-ec2.md`), not the markdown body. LLM (and mock) cannot use runbook guidance unless paths are read into content.
5. **Document CRUD** — min requirement “user request and document CRUD”; no upload/update/list for runbooks beyond static files + `metadata.json`.

### Pipeline polish (medium)

6. **EC2 filtering** — processor does not use idle/prod/`request_hint`; always returns full snapshot.
7. **Structured HITL in response** — UI needs the 3 paths with risk/approve controls; `handle_json` currently flattens to a summary string (full structure still in `model_response`).
8. **PII gate** — `_pii_warning` only warns; does not block. Narrow keyword list.

### Cleanup (low, but confusing)

9. **Dead / duplicate trees** — `ec2_processing/`, `request_processor.py`, `prompt_crafting.py` (if present), `demo_ai_pipeline.py`, `test_fake_response.py`, old `data/metrics.csv` vs `samples/ec2-cloudwatch.json`.
10. **`idea.md` drift** — contracts still say RunbookDoc + EC2Record lists; code intentionally uses paths + EC2 text. Update `idea.md` so teammates don’t re-implement the old shapes.

## Not missing for your stated LLM plan

- Leaving `llm_server` on mock / `generate_recommendations` is fine to coordinate with teammates.
- `prompt_crafter` and `json_handler` are wired and usable as-is for the happy-path demo once mock responses match the user request (or live LLM is enabled).
