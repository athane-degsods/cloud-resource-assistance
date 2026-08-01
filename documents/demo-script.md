# Demo video plan (≤ 10 minutes)

**Track 3 — Human-in-the-Loop AI Assistant**  
**App:** Cloud Resource Assistant (`http://127.0.0.1:5000`)  
**Before recording:** hard-refresh the UI, mock LLM on, no secrets on screen, `/logs` tab ready.

---

## 0:00–0:45 — Hook + problem

**Say:**
> Hi — we’re Track 3, Human-in-the-Loop. Our user is a junior cloud or ops engineer. Cloud metrics are overwhelming, and a wrong action — like stopping or deleting the wrong machine — can hurt the app or create a security risk. So we built an assistant that **recommends** cloud actions but **never finalizes** them without a human.

**Show:** Home UI (conversation + composer).

---

## 0:45–1:30 — Architecture in one breath

**Say:**
> The backend has two streams. **Request stream** — `POST /chat` — builds a draft only: runbooks, mock EC2 metrics, LLM recommendations. **Action stream** — `POST /decide` — is the real gate: approve, reject, or edit. We also keep an action log. Architecture diagrams are in our docs; what matters is: AI proposes, the app enforces human control.

**Show (optional):** briefly flash `architecture-validation.md` diagram or request/action stream docs — 10–15 seconds max.

---

## 1:30–3:30 — Success path (core demo)

**Do:**
1. Type: `Cut cost on idle EC2`
2. Send
3. Point at summary + 3 paths with **risk** labels
4. Click **Approve** on “Stop the idle development instance”
5. Show decision line: `stop_instance has been accomplished for i-…`
6. Show you can keep typing in the composer under the chat

**Say:**
> Here’s a normal request. The system pulls mock CloudWatch-style EC2 data and matching runbooks, then returns three options — each with risk, reason, and a normalized mock action. I’m approving path one. The action stream looks up the **stored draft** — it does not trust the browser for the action — and runs a **mock** stop. No real AWS. The result is appended to the conversation so I can keep chatting.

---

## 3:30–4:30 — Action log

**Do:** Open `/logs` (and optionally the specific `request_id` detail).

**Say:**
> Track 3 asks for a simple action log. Here you see the pipeline steps for that request — breakdown, filter, EC2, LLM, draft store — and the human decision step. That’s our audit trail.

---

## 4:30–5:45 — Reject / Edit (HITL is real)

**Do:**
1. New chat: `Cut cost on idle EC2` again (or similar)
2. Click **Reject** → show “rejected”, cards clear, no accomplishment string
3. Or: **Edit** → show edit recorded, input still usable → tweak message → Send again

**Say:**
> Reject records the decision and executes nothing. Edit also does not execute — I stay in control and can send a new chat. A prompt that says “please ask first” would not be enough; these buttons hit `/decide` in the application.

---

## 5:45–7:00 — Failure A: PII prevention

**Do:** Type `my password is` (or `my pass is`) → Send

**Say:**
> Safety layer one: private-information check. If the user pastes password-like content, we **block before the LLM**. You see a privacy warning and a blocked message — no recommendation cards, no draft to approve.

---

## 7:00–8:15 — Failure B: prohibited production action

**Do:** Type `delete production please` → Send

**Say:**
> Safety layer two: approval policy on the LLM route. Destructive production intent — delete or terminate production — is hard-blocked in both mock and live paths. Status is blocked, paths are empty. We also allowlist mock actions so terminate/delete can never be executed even if a model tried to suggest them.

---

## 8:15–9:15 — Trust summary + limits

**Say:**
> So trust is built into the workflow: evidence and risk on each path, PII block, prohibited-action policy, human approve/reject/edit, allowlisted mock executor, and an action log. Limits: we use synthetic EC2 data and mock actions — no live AWS — and we intentionally skipped role-based approval and undo to keep the prototype focused.

**Show:** One more glance at a successful decision line + empty blocked response if useful.

---

## 9:15–10:00 — Close

**Say:**
> To wrap up: we help a junior ops engineer decide safer cloud actions. AI drafts three options; the human finalizes; dangerous or private requests are stopped by the app. Thanks for watching — repo and README have setup and demo steps.

---

## Quick checklist while recording

| Beat | Prompt / click | Must appear on screen |
| --- | --- | --- |
| Success | `Cut cost on idle EC2` → Approve | 3 paths + accomplishment line |
| Log | `/logs` | Step trail + decision |
| Reject/Edit | Reject or Edit | No fake AWS execute |
| PII | `my password is` | Privacy warning + blocked |
| Policy | `delete production please` | Blocked, no Approve cards |

## Speaking tips

- Prefer “draft” vs “execute” language — that’s the Track 3 story.
- Say **mock** once clearly so judges don’t think you deleted real prod.
- Don’t read the architecture doc aloud; point and move on.
- If something glitches, narrate the intended behavior and continue — keep under 10 minutes.
