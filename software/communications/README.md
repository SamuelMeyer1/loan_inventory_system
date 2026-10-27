# Communications

- `smtp.py`: TLS-required SMTP message transport.
- `teams.py`: formats the existing Teams relay over the approved SMTP route.

Notification policy, configuration, recipient selection, simulation routing,
and audit logging remain in `backend/services/notifications.py`.

SMS is not implemented; add it here only after its provider, consent rules,
credentials, and tests are approved.