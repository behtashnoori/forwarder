# Initial administrator onboarding

Forwarder has no executable default account, shared password, reusable bcrypt, or mandatory user Seed.

After configuring an authorized non-Production database through protected environment configuration, run:

```bash
python manage.py create-admin
```

The interactive command requests the administrator's full name, username, password, confirmation, and final approval. It hashes the operator-supplied password, refuses duplicate usernames, creates exactly one active administrator atomically, and never prints the password or hash.

For Production or shared environments, follow the approved operator change procedure and secret-management policy. Do not place credentials in command history, scripts, documentation, fixtures, tickets, or repository files. Additional expert and supervisor accounts must be created individually through the authorized administration surface.

The legacy `backend/seed_experts.py` path is retained only as a compatibility refusal and creates no accounts.
