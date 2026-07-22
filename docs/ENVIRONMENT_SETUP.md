# Environment setup

Package installation does not create or modify environment files. Create a local file explicitly:

```bash
npm run setup:env
```

The command copies `.env.example` to the ignored `.env` file and refuses to overwrite an existing file. Use `npm run setup:env -- --force` only when replacement is intentional. The generated file contains placeholders, not usable production credentials.

Example database setting:

```env
DATABASE_URL=postgresql+psycopg2://<user>:<password>@<host>:5432/<database>
```

Replace placeholders only in the local ignored file. Production credentials must be supplied through the approved secret manager or process environment and must never be committed, pasted into documentation, or stored in fixtures.

`SECRET_KEY` and `JWT_SECRET_KEY` in `.env.example` are development placeholders. Generate environment-specific values outside the repository. If a credential is exposed, revoke or rotate it before updating authorized services.

The repository ignores `.env`, `.env.production`, and `.env.docker`. Copying the template is a development convenience and is not production configuration or a deployment procedure.
