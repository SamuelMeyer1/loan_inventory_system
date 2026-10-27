# Software integrations

Third-party software and protocol integrations live here. Business rules,
database access, and API routes remain in `backend/`.

- `communications/`: SMTP transport and the Teams-over-SMTP adapter.
- Future SMS support belongs in `communications/sms.py`; no SMS transport is
  implemented today.
- A future System Q client can live in `system_q.py` once its API and
  authentication are approved. No System Q connection exists today.

Transport code must keep simulation and external-send safeguards at the
backend service boundary. Do not store credentials in source files.