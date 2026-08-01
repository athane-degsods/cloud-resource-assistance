# Request stream

**Endpoint:** `POST /chat`  
**Entry:** `app.py` → `modules/request_orchestrator.py` (`run_request_stream`)  
**Job:** Turn a user message into an AI **draft** (recommendations only). **No cloud action is executed here.**

Sister doc: [`action-stream.md`](./action-stream.md) · data shapes: [`data-flow.md`](./data-flow.md) · full system: [`architecture-validation.md`](./architecture-validation.md)

---

## 1. Where it sits in the system

```mermaid
flowchart LR
    UI[HTML chat UI]
    R[Router app.py]
    REQ[Request stream]
    S[(Draft store)]
    ACT[Action stream]

    UI -->|"POST /chat message"| R
    R --> REQ
    REQ -->|"draft + request_id"| UI
    REQ -->|"put model_response"| S
    UI -.->|"later POST /decide"| ACT
    S -.-> ACT
```

The request stream **proposes**. The action stream **finalizes** (after a human clicks).

---

## 2. End-to-end flow

```mermaid
flowchart TD
    A["UI: user types message"] --> B["POST /chat"]
    B --> C["Router validates body"]
    C --> D["run_request_stream(message)"]
    D --> E[PII check]
    E --> F[String breakdown]
    F --> G[Filter and request<br/>runbook match]
    G --> H[EC2 processor<br/>+ AWS ingestor]
    H --> I[Prompt crafter]
    I --> J[LLM server<br/>mock or live]
    J --> K[Json handler<br/>validate draft]
    K --> L[Draft store put]
    L --> M["Return JSON to UI"]
    M --> N["UI shows summary + 3 path cards"]
```

---

## 3. Sequence (who calls whom)

```mermaid
sequenceDiagram
    actor User
    participant UI as HTML UI
    participant App as app.py
    participant Orch as request_orchestrator
    participant BD as string_breakdown
    participant RF as request_filter
    participant EC2 as ec2_processor
    participant PC as prompt_crafter
    participant LLM as llm_server
    participant JH as json_handler
    participant DS as draft_store
    participant Log as pipeline_log

    User->>UI: type + Send
    UI->>App: POST /chat {message}
    App->>Orch: run_request_stream(message)
    Orch->>Log: start(request_id)
    Orch->>Orch: PII warning check
    Orch->>BD: breakdown(message)
    BD-->>Orch: words[]
    Orch->>RF: filter_and_request(words)
    RF-->>Orch: runbook paths[]
    Orch->>EC2: process_ec2(hint)
    EC2-->>Orch: ec2_text
    Orch->>PC: craft_prompt(...)
    PC-->>Orch: chat messages[]
    Orch->>LLM: call_llm(messages)
    LLM-->>Orch: raw model JSON
    Orch->>JH: handle_model_response(...)
    JH-->>Orch: validated model_response
    Orch->>DS: put(request_id, model_response)
    Orch->>Log: finish(ok)
    Orch-->>App: draft payload
    App-->>UI: JSON
    UI-->>User: summary + Approve / Reject / Edit
```

---

## 4. Modules and responsibilities

```mermaid
flowchart TB
    subgraph Orchestrator["request_orchestrator.py"]
        O[run_request_stream]
    end

    subgraph Steps["Downstream callables"]
        PII[_pii_warning]
        SB[string_breakdown.breakdown]
        RF[request_filter.filter_and_request]
        EP[ec2_processor.process_ec2]
        AI[aws_ingestor.ingest]
        PC[prompt_crafter.craft_prompt]
        LLM[llm_server.call_llm]
        JH[json_handler.handle_model_response]
        DS[draft_store.put]
        PL[pipeline_log.*]
    end

    O --> PII
    O --> SB
    O --> RF
    O --> EP
    EP --> AI
    O --> PC
    O --> LLM
    O --> JH
    O --> DS
    O --> PL
```

| Module | File | Input | Output |
| --- | --- | --- | --- |
| Router | `app.py` | `{ message }` | HTTP JSON draft |
| Orchestrator | `request_orchestrator.py` | `message`, optional `request_id` | full draft payload |
| String breakdown | `string_breakdown.py` | `str` | `list[str]` words |
| Filter / request | `request_filter.py` | words | runbook path list |
| EC2 processor | `ec2_processor.py` | hint | `ec2_text` |
| AWS ingestor | `aws_ingestor.py` | JSON sample path | EC2 text |
| Prompt crafter | `prompt_crafter.py` | request + paths + EC2 | chat messages |
| LLM server | `llm_server.py` | messages | raw recommendation JSON |
| Json handler | `json_handler.py` | raw JSON | validated draft |
| Draft store | `draft_store.py` | `request_id`, draft | persisted for `/decide` |
| Pipeline log | `pipeline_log.py` | steps | `/logs` trail |

---

## 5. Data shape at each station

Example user message: **“Cut cost on idle EC2”**.

```mermaid
flowchart LR
    A["message: str"] --> B["words: list[str]"]
    B --> C["runbook paths: list[str]"]
    C --> D["ec2_text: str"]
    D --> E["prompt: messages[]"]
    E --> F["model_response: dict"]
    F --> G["draft_store[request_id]"]
    F --> H["UI payload + readable_response"]
```

```mermaid
flowchart TD
    subgraph S1["1. HTTP body"]
        M["{ message: 'Cut cost on idle EC2' }"]
    end
    subgraph S2["2. Words"]
        W["['Cut','cost','on','idle','EC2']"]
    end
    subgraph S3["3. Runbooks"]
        P["['runbook/idle-ec2.md', ...]"]
    end
    subgraph S4["4. Metrics text"]
        E["instance_id=i-… cpu_avg_24h=3 …"]
    end
    subgraph S5["5. Prompt"]
        PR["[{role:system},{role:user}]"]
    end
    subgraph S6["6. Draft"]
        DR["status + summary + 3 paths<br/>each with mock_action"]
    end

    S1 --> S2 --> S3 --> S4 --> S5 --> S6
```

### Draft path shape (what HITL will approve later)

```mermaid
flowchart TB
    MR[model_response]
    MR --> ST[status: success]
    MR --> SU[summary]
    MR --> PATHS[paths: exactly 3]

    PATHS --> P1[path_1]
    PATHS --> P2[path_2]
    PATHS --> P3[path_3]

    P1 --> T[title / risk / reason]
    P1 --> EV[evidence / steps / pros / cons]
    P1 --> MA["mock_action<br/>{ action, instance_id }"]
```

Allowlisted `mock_action.action` values (validated here, executed only in the action stream):

`stop_instance` · `start_instance` · `resize_instance` · `monitor_instance` · `no_action`

---

## 6. Safety inside the request stream

```mermaid
flowchart TD
    MSG[User message] --> PII{PII markers?}
    PII -->|yes| WARN[pii_warning string on response]
    PII -->|no| CLEAN[warning = null]
    WARN --> PIPE[Continue pipeline]
    CLEAN --> PIPE

    PIPE --> LLM[LLM draft]
    LLM --> VAL{json_handler validate}
    VAL -->|blocked / invalid| SAFE[safe_response<br/>empty paths]
    VAL -->|success| OK[3 paths + requires_human_review]
    SAFE --> STORE[Still stored + returned]
    OK --> STORE
```

Important: even a successful draft is **not** an execution. The prompt and product rule are: recommendations only until `/decide`.

---

## 7. Logging spine

```mermaid
flowchart LR
    start[pipeline_log.start] --> s1[pii_check]
    s1 --> s2[string_breakdown]
    s2 --> s3[request_filter]
    s3 --> s4[ec2_processor]
    s4 --> s5[prompt_crafter]
    s5 --> s6[llm_server]
    s6 --> s7[json_handler]
    s7 --> s8[draft_store]
    s8 --> fin[pipeline_log.finish]
    fin --> logs["GET /logs /logs/request_id"]
```

Every step shares one `request_id` so demos can show the full trail.

---

## 8. What this stream does **not** do

```mermaid
flowchart LR
    REQ[Request stream]
    X1[Call mock_executor]
    X2[Approve / reject / edit]
    X3[Change real AWS]
    X4[Trust browser mock_action]

    REQ -.->|no| X1
    REQ -.->|no| X2
    REQ -.->|no| X3
    REQ -.->|no| X4
```

Those belong to the [action stream](./action-stream.md).

---

## 9. Demo story (request half)

```mermaid
journey
    title Request stream demo beat
    section User asks
      Type idle EC2 cost question: 5: User
      Send POST /chat: 5: User
    section System drafts
      Match runbooks + load EC2 mock: 4: System
      LLM returns 3 paths: 5: System
      Store draft by request_id: 4: System
    section UI
      Show summary and cards: 5: User
      Wait for human decision: 3: User
```

**Done signal for this stream:** UI receives `request_id`, `readable_response`, and `model_response.paths` with three options — and `draft_store.get(request_id)` returns the same draft.
