# LLM Server — how `modules/llm_server.py` works

This module turns crafted chat messages into a **recommendation JSON** object (summary + 3 paths). It can run in **mock mode** (no API cost) or **live mode** (OpenAI).

## Place in the pipeline

```mermaid
flowchart LR
    A[app.py process_request] --> B[prompt_crafter.craft_prompt]
    B -->|messages list| C[llm_server.generate_recommendations]
    C -->|model_response_json dict| D[json_handler]
    D --> E[readable response / UI]
```



**Input:** `messages: list[{ "role": str, "content": str }]`  
(usually system + user messages from `prompt_crafter`)

**Output:** `dict` with at least:

- `status`
- `summary`
- `privacy_warning`
- `paths` (list of recommendation paths)
- `requires_human_review`

---



## High-level decision flow

```mermaid
flowchart TD
    Start([generate_recommendations messages]) --> Empty{messages empty?}
    Empty -->|yes| Err1[llm_error_response<br/>validation_error]
    Empty -->|no| Mock{USE_MOCK_LLM == True?}

    Mock -->|yes| MockOut[mock_recommendation_response]
    Mock -->|no| Key{OPENAI_API_KEY set?}

    Key -->|no| Err2[llm_error_response<br/>configuration_error]
    Key -->|yes| Call[OpenAI chat.completions.create<br/>json_object + temperature 0.1]

    Call --> Content{content non-empty?}
    Content -->|no| Err3[llm_error_response<br/>empty_response]
    Content -->|yes| Parse[json.loads content]
    Parse --> OK([return model dict])

    Call -.->|exceptions| ErrMap[mapped llm_error_response]
    Parse -.->|JSONDecodeError| ErrJSON[invalid_json]

    Err1 --> End([return error dict])
    Err2 --> End
    Err3 --> End
    ErrMap --> End
    ErrJSON --> End
    MockOut --> End2([return success mock dict])
    OK --> End2
```



---



## Mock vs live mode

```mermaid
flowchart TB
    subgraph config [Configuration]
        F1["USE_MOCK_LLM = True  ← default for hackathon"]
        F2["USE_MOCK_LLM = False ← needs OPENAI_API_KEY in .env"]
        F3["LLM_MODEL env or DEFAULT_MODEL gpt-4.1-mini"]
    end

    subgraph mock [Mock path]
        M1[Ignore message content for generation]
        M2[Return fixed idle-EC2 demo with 3 paths]
        M3[stop / resize / monitor]
    end

    subgraph live [Live path]
        L1[Create OpenAI client timeout 30s]
        L2[Send messages as chat completion]
        L3[Force JSON object response_format]
        L4[Parse content string to dict]
    end

    F1 --> mock
    F2 --> live
    F3 --> live
```




| Mode      | When                             | Behavior                                                  |
| --------- | -------------------------------- | --------------------------------------------------------- |
| Mock      | `USE_MOCK_LLM = True`            | Always returns the same demo recommendation               |
| Live      | `USE_MOCK_LLM = False` + API key | Calls OpenAI; returns model JSON                          |
| Safe fail | Missing key / API errors         | Returns `llm_error_response(...)` — never crashes the app |


---



## Success response shape (mock / expected live)

```mermaid
flowchart TB
    R[Recommendation JSON]
    R --> S[status: success]
    R --> Sum[summary: string]
    R --> PW[privacy_warning: null or string]
    R --> RH[requires_human_review: true]
    R --> P[paths: array of 3]

    P --> P1[path_1 recommended]
    P --> P2[path_2]
    P --> P3[path_3]

    P1 --> Fields["id, title, risk, recommended, reason,<br/>evidence[], steps[], pros[], cons[],<br/>requires_approval, mock_action"]
```



Each `mock_action` is a **suggestion only** (e.g. `stop_instance` + `instance_id`). The LLM server does **not** execute cloud changes.

---



## Error handling map

All failures go through `llm_error_response(message, error_type)`:

```mermaid
flowchart LR
    subgraph errors [Error types]
        E1[validation_error]
        E2[configuration_error]
        E3[empty_response]
        E4[authentication_error]
        E5[timeout_error]
        E6[connection_error]
        E7[quota_error / rate_limit_error]
        E8[api_error]
        E9[invalid_json]
        E10[llm_error]
    end

    Out["status = error_type<br/>summary = message<br/>paths = []<br/>requires_human_review = true"]
    errors --> Out
```




| Exception / case         | `status` returned      |
| ------------------------ | ---------------------- |
| Empty `messages`         | `validation_error`     |
| No `OPENAI_API_KEY`      | `configuration_error`  |
| Empty model content      | `empty_response`       |
| `AuthenticationError`    | `authentication_error` |
| `APITimeoutError`        | `timeout_error`        |
| `APIConnectionError`     | `connection_error`     |
| `RateLimitError` (quota) | `quota_error`          |
| `RateLimitError` (other) | `rate_limit_error`     |
| `APIStatusError`         | `api_error`            |
| Bad JSON from model      | `invalid_json`         |
| Anything else            | `llm_error`            |


Downstream `json_handler` treats these statuses as safe/error responses for the UI.

---



## Functions in this file

```mermaid
flowchart TB
    subgraph public [Public helpers]
        GR[generate_recommendations]
        MER[mock_recommendation_response]
        LER[llm_error_response]
    end

    GR -->|mock branch| MER
    GR -->|failure| LER
    GR -->|live success| JSON[parsed OpenAI JSON]
```




| Function                       | Role                                           |
| ------------------------------ | ---------------------------------------------- |
| `llm_error_response`           | Build a uniform error dict                     |
| `mock_recommendation_response` | Hardcoded 3-path demo payload                  |
| `generate_recommendations`     | Main entry: validate → mock or live API → dict |


---



## How `app.py` uses it today

```mermaid
sequenceDiagram
    participant App as app.py
    participant PC as prompt_crafter
    participant LLM as llm_server
    participant JH as json_handler

    App->>PC: craft_prompt(request, paths, ec2_text)
    PC-->>App: messages[{role, content}, ...]
    App->>LLM: generate_recommendations(messages)
    Note over LLM: USE_MOCK_LLM True → mock<br/>False → OpenAI
    LLM-->>App: model_response_json
    App->>JH: handle_json / handle_model_response
    JH-->>App: readable summary (+ validated structure)
```



> Note: Some branches expose an adapter named `call_llm` that wraps `generate_recommendations`. If your local `app.py` imports `call_llm`, that adapter should call this same flow.

---



## Enabling live LLM (checklist)

1. Put `OPENAI_API_KEY=...` in a local `.env` (**do not commit**).
2. Optionally set `LLM_MODEL=...`.
3. Set `USE_MOCK_LLM = False` in `llm_server.py`.
4. Restart Flask and send a `/chat` request.
5. If the key/quota fails, you still get an error-shaped JSON (app stays up).

---



## Design intent (hackathon)

- **AI recommends only** — paths include `requires_approval` and `mock_action`; humans decide later.
- **Mock-first** — full demo without billing.
- **Fail closed on tra*n*sport** — API problems become structured errors, not stack traces to the UI.

