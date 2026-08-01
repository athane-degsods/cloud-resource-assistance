# Cloud Resource Assistance

**Secure AI Hackathon — Track 3: Human-in-the-Loop AI Assistant**

A Flask chat app that helps a junior cloud/ops engineer decide what to do with AWS-style EC2 metrics. The AI **drafts** up to three recommendation paths (with risk, evidence, and a normalized mock action). A human must **approve, reject, or edit** before anything is finalized. Mock execution never calls real AWS.

---

## Problem and users

- **User:** Junior cloud / ops engineer managing a small AWS account  
- **Problem:** Metrics and runbooks are overwhelming; a wrong action can cause outages or security issues  
- **Approach:** Mock CloudWatch EC2 data + runbook docs + LLM recommendations → human gate → mock action + audit log  

---

## Features

- **Request stream** (`POST /chat`): draft-only pipeline (breakdown → runbook filter → EC2 ingest → prompt → LLM → validation → draft store)  
- **Action stream** (`POST /decide`): approve / reject / edit; execute **only** on approve via allowlisted mock actions  
- **Trust / safety**
  - PII / secret markers block the request before the LLM  
  - Prohibited production intent (e.g. “delete production”) blocked on the LLM route  
  - Risk labels on recommendation paths  
  - Allowlisted mock actions; blocked destructive actions cannot execute  
  - Pipeline / decision logging at `/logs`  
- **UI:** chat conversation, recommendation cards, composer under the thread  

---

## Architecture (short)

```text
UI ──POST /chat──► Router (app.py) ──► Request orchestrator ──► draft store
UI ──POST /decide─► Router           ──► Decision handler ──► mock executor
```

Diagrams and contracts:

- `documents/architecture-validation.md` — system diagram + checklist  
- `documents/request-stream.md` — request stream  
- `documents/action-stream.md` — action stream / HITL  
- `documents/data-flow.md` — payload shapes  
- `documents/demo-script.md` — video narration plan  

Presentation deck: `Cloud_Resource_Assistance_hackathon_Team50.pptx`

---

## Requirements

- Python 3.10+ recommended  
- Dependencies in `requirements.txt` (Flask, openai, python-dotenv, pandas, pytest)  

---

## Setup

```bash
git clone <your-public-repo-url>
cd cloud-resource-assistance

python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### Environment (optional for live LLM)

By default the app uses a **mock LLM** (`USE_MOCK_LLM = True` in `modules/llm_server.py`). No API key is required for the demo.

To try a live model later:

1. Copy env vars into a local `.env` (never commit secrets):

```env
OPENAI_API_KEY=your_key_here
LLM_MODEL=gpt-4.1-mini
```

2. Set `USE_MOCK_LLM = False` in `modules/llm_server.py`.

`.env` is gitignored. Do not commit API keys, tokens, or credentials.

---

## Run

```bash
python app.py
```

Or:

```bash
flask --app app run --debug
```

Open: [http://127.0.0.1:5000](http://127.0.0.1:5000)

Useful routes:

| Route | Purpose |
| --- | --- |
| `GET /` | Chat UI |
| `POST /chat` | Request stream (draft) |
| `POST /decide` | Action stream (HITL) |
| `GET /logs` | Readable action / pipeline log |
| `GET /health` | Health check |

---

## Demo instructions

### Success path

1. Open the UI.  
2. Enter: `Cut cost on idle EC2` → **Send**.  
3. Review three paths (title, risk, reason).  
4. Click **Approve** on the stop-idle recommendation.  
5. Confirm a decision line such as `stop_instance has been accomplished for i-…`.  
6. Open `/logs` to show the pipeline and human decision trail.

### Human-in-the-loop controls

- **Reject** — records reject, does **not** execute, clears cards.  
- **Edit** — records edit, does **not** execute; adjust the prompt and **Send** again (`POST /chat`).

### Safety / failure demos

| Prompt | Expected |
| --- | --- |
| `my password is` | Privacy warning; request blocked before LLM; no Approve cards |
| `delete production please` | Approval-policy block on LLM route; empty paths |

---

## Data and APIs

| Asset | Location / note |
| --- | --- |
| Synthetic EC2 / CloudWatch-style JSON | `samples/ec2-cloudwatch.json` |
| Runbook documents + keyword index | `runbook/*.md`, `runbook/metadata.json` |
| Draft store (runtime) | `modules/draft_store.json` (gitignored) |
| Optional LLM API | OpenAI-compatible chat completions when mock is off |

Data is **synthetic / participant-owned sample content** for the hackathon. No confidential customer data. Mock executor does **not** call AWS.

Reference sample used while designing mocks: [Mockoon AWS CloudWatch Logs sample](https://mockoon.com/mock-samples/amazonawscom-logs/) (inspiration only; app uses local JSON).

---

## Project layout

```text
app.py                 # Router
modules/               # Request + action stream modules
templates/             # HTML UI + logs pages
static/                # Frontend JS
samples/               # Mock metrics
runbook/               # Ops guidance docs
documents/             # Architecture, streams, demo script
tests/                 # Pytest
```

---

## Tests

```bash
pytest -q
```

---

## Team / submission notes

- **Hackathon track:** Track 3 — Human-in-the-Loop AI Assistant  
- **Substantial work** built during the event; disclose any pre-existing snippets and third-party libraries in this README  
- **Third-party:** Flask, OpenAI Python SDK, python-dotenv, pandas, pytest  
- **Out of scope for this prototype:** live AWS, role-based approval, undo/rollback timers  

For a timed walkthrough of the recorded demo, see `documents/demo-script.md`.
