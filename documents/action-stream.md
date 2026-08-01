# Action stream

**Endpoint:** `POST /decide`  
**Entry:** `app.py` → `modules/decision_handler.py` (`handle_decision`)  
**Job:** Apply a **human** decision (approve / reject / edit) to a **stored** draft. Mock-execute only on approve. **Never re-run the LLM pipeline.**

Sister doc: [`request-stream.md`](./request-stream.md) · data shapes: [`data-flow.md`](./data-flow.md) · full system: [`architecture-validation.md`](./architecture-validation.md)

---

## 1. Where it sits in the system

```mermaid
flowchart LR
    UI[HTML chat UI]
    R[Router app.py]
    REQ[Request stream]
    S[(Draft store)]
    ACT[Action stream]
    X[Mock executor]

    UI -->|"1 POST /chat"| R --> REQ
    REQ -->|"put draft"| S
    REQ -->|"draft cards"| UI
    UI -->|"2 POST /decide"| R --> ACT
    ACT -->|"get draft"| S
    ACT -->|"approve only"| X
    ACT -->|"status + results"| UI
```

Track 3 rule: a prompt that says “ask first” is not enough — **this stream is the real gate**.

---

## 2. End-to-end flow

```mermaid
flowchart TD
    A["UI: Approve / Reject / Edit"] --> B["POST /decide"]
    B --> C["Router checks request_id + decision"]
    C --> D["handle_decision(...)"]
    D --> E{decision valid?}
    E -->|no| B1[status blocked]
    E -->|approve without path_id| B2[status blocked]
    E -->|ok| F["draft_store.get(request_id)"]
    F --> G{draft found?}
    G -->|no| NF[status not_found]
    G -->|yes| H{branch}
    H -->|reject| RJ[log only → rejected<br/>clear draft]
    H -->|edit| ED[log only → edit_requested]
    H -->|approve| AP[find path by path_id]
    AP --> I{path + mock_action OK?}
    I -->|no| B3[status blocked]
    I -->|yes| J["mock_executor.execute"]
    J --> K{ok?}
    K -->|no| B4[status blocked]
    K -->|yes| EX[status executed + results<br/>clear draft]
    B1 & B2 & NF & RJ & ED & B3 & B4 & EX --> L[JSON back to UI]
    L --> M[Append decision at end of conversation]
```

---

## 3. Sequence diagrams

### Approve (happy path)

```mermaid
sequenceDiagram
    actor User
    participant UI as HTML UI
    participant App as app.py
    participant DH as decision_handler
    participant DS as draft_store
    participant MX as mock_executor
    participant Log as pipeline_log

    User->>UI: click Approve on path_1
    UI->>App: POST /decide {request_id, decision:approve, path_id}
    App->>DH: handle_decision(...)
    DH->>Log: step info
    DH->>DS: get(request_id)
    DS-->>DH: model_response draft
    DH->>DH: find path_1.mock_action
    DH->>MX: execute(action, instance_id)
    MX-->>DH: {ok:true, results:[...]}
    DH->>DS: clear(request_id)
    DH->>Log: step exit executed
    DH-->>App: status executed + results
    App-->>UI: 200 JSON
    UI-->>User: decision line at end of chat
```

### Reject

```mermaid
sequenceDiagram
    actor User
    participant UI
    participant App
    participant DH as decision_handler
    participant DS as draft_store

    User->>UI: Reject
    UI->>App: POST /decide {request_id, decision:reject}
    App->>DH: handle_decision
    DH->>DS: get(request_id)
    DH->>DS: clear(request_id)
    Note over DH: no mock_executor call
    DH-->>App: status rejected
    App-->>UI: 200
    UI->>UI: clear recommendations + keep chatting
```

### Edit

```mermaid
sequenceDiagram
    actor User
    participant UI
    participant App
    participant DH as decision_handler

    User->>UI: Edit
    UI->>App: POST /decide {request_id, decision:edit}
    App->>DH: handle_decision
    Note over DH: log only — no execute
    DH-->>UI: status edit_requested
    UI->>User: focus composer — next Send is new POST /chat
```

---

## 4. Modules and responsibilities

```mermaid
flowchart TB
    subgraph Router["app.py"]
        DCD[POST /decide]
    end

    subgraph Handler["decision_handler.py"]
        HD[handle_decision]
        AP[_approve]
        FP[_find_path]
        RS[_response]
    end

    subgraph Store["draft_store.py"]
        GET[get]
        CLR[clear]
    end

    subgraph Exec["mock_executor.py"]
        EX[execute]
        AL[ALLOWED_ACTIONS dispatch]
    end

    DCD --> HD
    HD --> GET
    HD --> AP
    AP --> FP
    AP --> EX
    EX --> AL
    AP --> CLR
    HD --> RS
```

| Module | File | Role |
| --- | --- | --- |
| Router | `app.py` | Validate body; map status → HTTP code |
| Decision handler | `decision_handler.py` | HITL gate + logging |
| Draft store | `draft_store.py` | Trusted source of `mock_action` |
| Mock executor | `mock_executor.py` | Fake allowlisted cloud actions |
| Pipeline log | `pipeline_log.py` | Record human decision steps |
| Frontend | `static/script.js` | Buttons → `/decide`; append results to conversation |

**Dependency direction (keep one-way):**

```mermaid
flowchart LR
    app --> decision_handler
    decision_handler --> draft_store
    decision_handler --> mock_executor
    decision_handler --> pipeline_log
    mock_executor --> json_handler
```

`mock_executor` reuses `ALLOWED_ACTIONS` / `BLOCKED_ACTIONS` from `json_handler` so draft validation and execution stay aligned.

---

## 5. Decision branches

```mermaid
stateDiagram-v2
    [*] --> Received: POST /decide
    Received --> Blocked: bad decision / missing path_id
    Received --> Lookup: valid decision
    Lookup --> NotFound: no draft
    Lookup --> Rejected: reject
    Lookup --> EditRequested: edit
    Lookup --> ApprovePath: approve
    ApprovePath --> Blocked: unknown path / bad mock_action
    ApprovePath --> Executing: mock_executor
    Executing --> Executed: ok
    Executing --> Blocked: refused / blocked action
    Rejected --> [*]
    EditRequested --> [*]
    Executed --> [*]
    NotFound --> [*]
    Blocked --> [*]
```

### HTTP mapping

```mermaid
flowchart LR
    S1[executed / rejected / edit_requested] --> H200[200]
    S2[blocked] --> H400[400]
    S3[not_found] --> H404[404]
```

---

## 6. Data shapes

### Request body

```mermaid
flowchart TD
    B[POST /decide body]
    B --> RID[request_id: str]
    B --> DEC["decision: approve | reject | edit"]
    B --> PID["path_id: str | null<br/>(required for approve)"]
```

### Resolve action from store (not from browser)

```mermaid
flowchart LR
    RID[request_id] --> DS[(draft_store)]
    DS --> DRAFT[model_response]
    DRAFT --> PATHS[paths[]]
    PID[path_id] --> FIND[find matching id]
    PATHS --> FIND
    FIND --> MA["mock_action<br/>{ action, instance_id }"]
    MA --> EX[mock_executor]
```

### Response body

```mermaid
flowchart TD
    R[Decision response]
    R --> ST["status"]
    R --> RS["results: list[str]"]
    R --> MSG[message]
    R --> META[request_id / decision / path_id]
```

Example approve success:

```json
{
  "status": "executed",
  "results": ["stop_instance has been accomplished for i-123456789"],
  "message": "Mock action completed.",
  "request_id": "req_…",
  "decision": "approve",
  "path_id": "path_1"
}
```

---

## 7. Mock executor internals

```mermaid
flowchart TD
    IN["execute(action, instance_id)"] --> N[normalize action]
    N --> BL{in BLOCKED_ACTIONS?}
    BL -->|yes| FAIL1[ok:false]
    BL -->|no| AL{in ALLOWED_ACTIONS?}
    AL -->|no| FAIL2[ok:false]
    AL -->|yes| NEED{needs instance_id?}
    NEED -->|yes and missing| FAIL3[ok:false]
    NEED -->|ok| H[handler dispatch]
    H --> OK["ok:true + results message"]
```

```mermaid
flowchart LR
    subgraph Allowlist
        stop[stop_instance]
        start[start_instance]
        resize[resize_instance]
        mon[monitor_instance]
        none[no_action]
    end
    subgraph Blocked
        term[terminate_instance]
        del[delete_production]
        more[...]
    end
```

Handlers only return accomplishment **strings**. There is no real AWS SDK call.

---

## 8. Frontend contract

```mermaid
flowchart TD
    CHAT[POST /chat success] --> CARDS[Render 3 Approve cards]
    CARDS --> A[Approve path_id]
    CARDS --> R[Reject]
    CARDS --> E[Edit]
    A --> D1["POST /decide approve"]
    R --> D2["POST /decide reject"]
    E --> D3["POST /decide edit"]
    D1 --> L[Append decision at end of conversation]
    D2 --> L
    D3 --> L
    L --> C[Clear recommendation cards]
    C --> IN[Focus composer — keep chatting]
```

UI layout (conversation → recommendations → composer at bottom) keeps the human in a continuous chat loop after each decision.

---

## 9. Safety rules

```mermaid
flowchart TD
    Q[Can we execute?] --> T1{Came from draft store?}
    T1 -->|no| NO[Refuse]
    T1 -->|yes| T2{Human approved?}
    T2 -->|no| NO
    T2 -->|yes| T3{action allowlisted?}
    T3 -->|no| NO
    T3 -->|yes| T4{blocked list?}
    T4 -->|yes| NO
    T4 -->|no| YES[Mock execute only]
```

| Rule | Why |
| --- | --- |
| No LLM on `/decide` | Gate must be application code, not a prompt |
| Trust store, not client `mock_action` | Prevents forged execute payloads |
| Allowlist + blocklist | Limits blast radius of bad model output |
| Clear draft after approve/reject | Avoid double-executing the same draft |
| Log every decision | Track 3 action-log requirement |

---

## 10. How the two streams hand off

```mermaid
sequenceDiagram
    participant REQ as Request stream
    participant DS as Draft store
    participant UI as UI
    participant ACT as Action stream

    REQ->>DS: put(request_id, draft)
    REQ->>UI: paths + request_id
    Note over UI: Human reviews
    UI->>ACT: decide(request_id, decision, path_id?)
    ACT->>DS: get(request_id)
    ACT->>UI: executed / rejected / edit_requested
```

```mermaid
flowchart LR
    subgraph Request["Request stream"]
        M[message] --> D[draft]
    end
    subgraph Bridge["Shared"]
        ID[request_id]
        ST[(draft_store)]
    end
    subgraph Action["Action stream"]
        DEC[decision] --> RES[results / status]
    end
    D --> ST
    ID --> ST
    ST --> DEC
```

---

## 11. Demo story (action half)

```mermaid
journey
    title Action stream demo beat
    section After draft
      Read three options: 5: User
      Approve stop idle instance: 5: User
    section Gate
      Lookup stored mock_action: 4: System
      Mock execute stop_instance: 5: System
      Log decision: 4: System
    section Continue
      See accomplishment in chat: 5: User
      Type another request: 5: User
```

**Failure demo (optional):** ask something that yields `blocked` / empty paths in the request stream, or approve a missing `request_id` → `not_found`.

**Done signal for this stream:** Approve returns `executed` with a non-empty `results` list; Reject/Edit never call the executor; conversation can continue with a new `/chat`.
