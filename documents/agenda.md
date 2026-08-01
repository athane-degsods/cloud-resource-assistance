# Next agenda — HITL gate (Track 3)

Architecture is locked in `documents/architecture-validation.md`: **Router** splits traffic into a **request stream** (draft only, already mostly done) and an **action stream** (human decide → mock execute). Live LLM is **optional / later** — Track 3 does not require it. Priority is approve / reject / edit in the app.

## Shared expectations

- Follow contracts in **Code component** (`architecture-validation.md`). Params/returns below are the source of truth.
- Do **not** re-run the LLM pipeline inside `/decide`.
- Approve executes a **normalized** `mock_action` from the **stored draft**, not free text from the browser.
- Log human decisions (use `pipeline_log` where you can).
- Keep PRs small; leave stubs/TODO if blocked on Duy’s router wiring.
- **Done when** we can demo: chat → 3 paths → approve one → “action accomplished”; reject clears prompt; edit keeps prompt for a new `/chat`.

---



## Akshita — Frontend + Draft store



### 1. Frontend (`templates/index.html`, `static/script.js`)

Extend the current chat boilerplate.


| Expectation   | Detail                                                                                                                                 |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| After `/chat` | Show `readable_response` **and** the 3 paths from `model_response.paths` (title, risk, short reason). Keep `request_id` in page state. |
| HITL controls | **3 Approve buttons** (one per path) + **Reject** + **Edit**.                                                                          |
| Approve       | `POST /decide` with `{ request_id, decision: "approve", path_id }`. Show `results` (e.g. action accomplished).                         |
| Reject        | `POST /decide` with `{ request_id, decision: "reject" }`. Clear the input. Do **not** auto-call `/chat`.                               |
| Edit          | `POST /decide` with `{ request_id, decision: "edit" }`. Keep the input text. User edits → Send → new `/chat`.                          |
| Logging       | Keep request/response visible in the on-page log.                                                                                      |


**Out of scope:** fancy styling, document upload, live AWS.

### 2. Draft store — new `modules/draft_store.py`


|               |                                                                                                                                     |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| **Role**      | In-memory map `request_id → model_response` so `/decide` does not trust the client for `mock_action`.                               |
| **Functions** | `put(request_id, model_response)`, `get(request_id) → dict | None`, optional `clear(request_id)`.                                   |
| **Done when** | Unit-smokeable: put → get returns same draft; missing id → `None`. Duy will call `put` after chat and Mrunali will `get` on decide. |


---



## Mrunali — Action stream modules

Build the modules Duy will call from `POST /decide`. **No LLM calls** here.

### 1. Mock executor — `modules/mock_executor.py`


|               |                                                                                                                                |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **Role**      | Fake cloud actions only; never real AWS.                                                                                       |
| **params**    | `action: str`, `instance_id: str | None`                                                                                       |
| **Allowlist** | `stop_instance`, `start_instance`, `resize_instance`, `monitor_instance`, `no_action` (same as `json_handler.ALLOWED_ACTIONS`) |
| **return**    | `results: list[str]` e.g. `["stop_instance has been accomplished for i-0abc"]`                                                 |
| **Rules**     | Unknown / blocked actions → refuse (raise or return an error-shaped result). Called **only** after approve.                    |




### 2. Decision / action handler — `modules/decision_handler.py`


|            |                                                                                                                                                                                          |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Role**   | HITL gate: load draft → branch on decision → execute only on approve.                                                                                                                    |
| **params** | `request_id`, `decision: "approve"|"reject"|"edit"`, `path_id` (required for approve)                                                                                                    |
| **Flow**   | `draft_store.get(request_id)` → if missing: `status: "not_found"`. **approve:** find path by `path_id`, read `mock_action`, call mock executor. **reject / edit:** log only, no execute. |
| **return** | `{ status: "executed"|"rejected"|"edit_requested"|"blocked"|"not_found", results: list[str], message: str, … }`                                                                          |


**Done when:** given a fake stored draft, approve returns accomplishment strings; reject/edit return status with empty/no execution; bad `path_id` / missing draft handled cleanly.

**Not your focus this pass:** live OpenAI wiring (nice-to-have only if HITL is done early).

---



## Duy — Router + data-state documentation



### 1. Router (`app.py`)

- Keep `/chat` on the request stream (draft only).
- After a successful chat: `draft_store.put(request_id, model_response)`.
- Add `POST /decide` → call `decision_handler` → return JSON to UI. **Do not** run breakdown/LLM on decide.
- Wire logging for human decisions.



### 2. Document data states

Short note (can live under `documents/` or in architecture-validation) of what each module passes next, especially:

`message` → `words` → `paths` → `ec2_text` → prompt → `model_response` → **draft store** → decide body → `mock_action` → `results`

Goal: one place the team can check contracts so frontend + action stream plug in without guessing.

---



## Integration order

1. Akshita: `draft_store` API stable
2. Mrunali: handler + executor against that store (you can mock that store when Akshita is working)
3. Duy: `/decide` + `put` after `/chat`
4. Akshita: wire HITL buttons to live `/decide`
5. Smoke demo together (success approve + reject/edit)

Questions → reply on this thread; contracts stay in `architecture-validation.md`.