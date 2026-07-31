# Idle EC2 handling

When an EC2 instance shows low average CPU (for example under 5%) for an extended window:

1. Confirm environment (prefer non-production first).
2. Check for scheduled jobs or overnight batch work.
3. Prefer stop over terminate for idle development instances.
4. Require human approval before any mock stop action.
