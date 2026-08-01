# Purpose

This doc is the **data contract** between modules. It says what each step produces and what the next step expects, so frontend, request stream, and action stream can plug together without guessing.

Use it when wiring `/chat`, `/decide`, draft store, or HITL buttons. Architecture diagrams live in `architecture-validation.md`; this file only tracks **shapes that move**.

# Two streams

Same user story in the examples: **“Cut cost on idle EC2”**.

## 1. Request (`POST /chat`) — draft only

No cloud action is executed here. Output is a **draft** the human must review.

```text
message
  → words
  → runbook paths
  → ec2_text
  → prompt (chat messages)
  → model_response (draft)
  → draft store[request_id]
  → UI payload
```

### Station snapshots

**1. UI → router**

```json
{ "message": "Cut cost on idle EC2" }
```

**2. After string breakdown** (`modules/string_breakdown.py`)

```python
["Cut", "cost", "on", "idle", "EC2"]
```

**3. After filter / request** (`modules/request_filter.py`)

```python
["runbook/idle-ec2.md", "runbook/cost-optimization.md"]
```

**4. After EC2 processor** (`modules/ec2_processor.py` via ingestor)

Plain text metrics blob (shape may vary; treat as `str`):

```text
instance_id=i-123456789 name=dev-api state=running env=development cpu_avg_24h=3 ...
```

**5. After prompt crafter** (`modules/prompt_crafter.py`)

```python
[
  { "role": "system", "content": "You provide recommendations only..." },
  { "role": "user", "content": "{...user_request, runbook_documents, ec2_records...}" }
]
```

**6. After LLM** (`modules/llm_server.py`) — draft JSON

```json
{
  "status": "success",
  "summary": "One development EC2 instance appears idle and may be optimized after human review.",
  "privacy_warning": null,
  "requires_human_review": true,
  "paths": [
    {
      "id": "path_1",
      "title": "Stop the idle development instance",
      "risk": "medium",
      "recommended": true,
      "reason": "…",
      "evidence": ["…"],
      "steps": ["…"],
      "pros": ["…"],
      "cons": ["…"],
      "requires_approval": true,
      "mock_action": {
        "action": "stop_instance",
        "instance_id": "i-123456789"
      }
    },
    { "id": "path_2", "title": "Resize the EC2 instance", "mock_action": { "action": "resize_instance", "instance_id": "i-123456789" } },
    { "id": "path_3", "title": "Continue monitoring before making a change", "mock_action": { "action": "monitor_instance", "instance_id": "i-123456789" } }
  ]
}
```

Allowlisted `mock_action.action` values: `stop_instance` | `start_instance` | `resize_instance` | `monitor_instance` | `no_action`.

**7. Draft store** (planned `modules/draft_store.py`)

```text
request_id  →  model_response (station 6)
```

Example key: `req_20260801_032454_1605`.

**8. `/chat` response to UI** (`run_request_stream`)

```json
{
  "request_id": "req_20260801_032454_1605",
  "readable_response": "One development EC2 instance appears idle…",
  "model_response": { "...full draft from station 6..." },
  "pii_warning": null,
  "words": ["Cut", "cost", "on", "idle", "EC2"],
  "paths": ["runbook/idle-ec2.md", "runbook/cost-optimization.md"],
  "ec2_text": "…",
  "steps": [],
  "meta": {
    "word_count": 5,
    "document_count": 2,
    "ec2_text_len": 617,
    "duration_ms": 42
  }
}
```

Frontend should keep `request_id` and render `model_response.paths` for HITL buttons.

---

## 2. Action (`POST /decide`) — no LLM re-entry

Human finalizes a stored draft. Approve may mock-execute; reject/edit only record a decision.

```text
decide body
  → draft_store.get(request_id)
  → (approve) path.mock_action
  → mock_executor
  → decision status + results
```

### Station snapshots

**9. UI → router (approve path_1)**

```json
{
  "request_id": "req_20260801_032454_1605",
  "decision": "approve",
  "path_id": "path_1"
}
```

**Reject**

```json
{
  "request_id": "req_20260801_032454_1605",
  "decision": "reject"
}
```

**Edit**

```json
{
  "request_id": "req_20260801_032454_1605",
  "decision": "edit"
}
```

**10. Handler resolves action from stored draft** (not from the browser)

From `paths` where `id == path_id`:

```json
{ "action": "stop_instance", "instance_id": "i-123456789" }
```

**11. Decision response (approve success)**

```json
{
  "status": "executed",
  "results": ["stop_instance has been accomplished for i-123456789"],
  "message": "…",
  "request_id": "req_20260801_032454_1605",
  "decision": "approve",
  "path_id": "path_1"
}
```

**Reject / edit (no execution)**

```json
{
  "status": "rejected",
  "results": [],
  "message": "Decision recorded as reject (no execution).",
  "request_id": "req_20260801_032454_1605",
  "decision": "reject",
  "path_id": null
}
```

```json
{
  "status": "edit_requested",
  "results": [],
  "message": "Decision recorded as edit (no execution; re-run via POST /chat).",
  "request_id": "req_20260801_032454_1605",
  "decision": "edit",
  "path_id": null
}
```

Other statuses: `not_found` (missing draft), `blocked` (bad decision / missing `path_id` on approve), `not_implemented` (placeholder until executor is wired).

Frontend: reject → clear input; edit → keep input; next AI pass is always a new `POST /chat`.

# Payload cheat sheet

| Field | Type | Produced by | Consumed by |
| --- | --- | --- | --- |
| `message` | `str` | UI | request orchestrator, breakdown, EC2 hint, prompt |
| `words` | `list[str]` | string breakdown | request filter |
| `paths` (runbooks) | `list[str]` | request filter | prompt crafter; also echoed in `/chat` JSON |
| `ec2_text` | `str` | EC2 processor / AWS ingestor | prompt crafter |
| prompt / chat messages | `list[{role, content}]` | prompt crafter | LLM server |
| `model_response` | `dict` | LLM (+ json handler validation) | draft store, UI, decision handler |
| `paths[]` (recommendations) | `list[dict]` | LLM draft | UI HITL buttons; decision handler |
| `paths[].id` | `str` | LLM | UI `path_id`; decision handler lookup |
| `paths[].mock_action` | `{ action, instance_id }` | LLM (allowlisted) | mock executor (via handler) |
| `request_id` | `str` | pipeline_log / orchestrator | draft store key; `/decide`; logs |
| `readable_response` | `str` | json handler | UI display |
| `pii_warning` | `str \| null` | request orchestrator | UI |
| decide `decision` | `approve \| reject \| edit` | UI | decision handler |
| decide `path_id` | `str \| null` | UI (approve only) | decision handler |
| `results` | `list[str]` | mock executor | UI |

# What not to do

- Do **not** run breakdown → filter → EC2 → LLM inside `/decide`.
- Do **not** trust the browser to supply `mock_action` for execution — load it from the **draft store** using `request_id` + `path_id`.
- Do **not** call real AWS from the mock executor.
- Do **not** treat a prompt that says “ask the user first” as the HITL gate — approve / reject / edit must be app endpoints.
- Do **not** auto-fire a new `/chat` from reject/edit on the server; the UI clears or keeps the input and the user sends `/chat` again when ready.
- Do **not** execute on `reject` or `edit`.
- Do **not** allow `BLOCKED_ACTIONS` (`terminate_instance`, `delete_production`, etc.) through validation or the executor.
