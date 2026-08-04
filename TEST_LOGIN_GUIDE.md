# Login verification guide

No test or shared login credentials are distributed with Forwarder.

1. Create an individual administrator using `python manage.py create-admin` against an authorized disposable or local environment.
2. Create any additional test user through the authorized administration flow.
3. Supply credentials at runtime through the test runner's protected environment or interactive prompt.
4. Remove the disposable database and any temporary credential material after verification.

Never commit a usable password, reusable password hash, shared bootstrap account, database URL, or captured authenticated session. The retired `backend/seed_experts.py` entry point refuses execution and exists only to explain the supported onboarding path.
