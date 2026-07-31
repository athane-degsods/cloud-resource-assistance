# Production safety

High-risk language (delete, terminate, production) requires extra care:

1. Mark the path as high risk.
2. Block destructive actions without explicit human approval.
3. Prefer monitor or no_action when evidence is weak.
4. Log every decision step for audit.
