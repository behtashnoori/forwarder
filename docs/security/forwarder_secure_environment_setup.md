# Secure environment setup

Run `npm run setup:env` explicitly to copy `.env.example` to the ignored `.env`. The command refuses to overwrite an existing file unless `--force` is explicitly supplied. Even with that option it only recopies the safe template and never generates a credential.

Replace `change_me` placeholders locally. Development, CI, and production credentials must come from their approved process environments or secret managers. Never commit `.env`, credentials, database URLs, private keys, tokens, or real secrets in examples or fixtures.

The database values in `docker-compose.yml` are local-development placeholders only. They are not approved for production, staging, shared environments, or reuse outside the disposable local Compose stack. Supply every non-local credential through an environment variable or an approved secret manager.

Package installation, application startup, and migration commands are separate operations. `npm install` must not create environment files; database migration remains explicit.

When rotating a credential: revoke the old value, update authorized secret stores, restart only through the approved operational procedure, validate without printing the value, and record owner confirmation outside the repository.
