# Welcome to your Lovable project

## Project info

**URL**: https://lovable.dev/projects/6537ffc1-88ab-4c2a-8eb9-82b3b1bc9f4f

## How can I edit this code?

There are several ways of editing your application.

**Use Lovable**

Simply visit the [Lovable Project](https://lovable.dev/projects/6537ffc1-88ab-4c2a-8eb9-82b3b1bc9f4f) and start prompting.

Changes made via Lovable will be committed automatically to this repo.

**Use your preferred IDE**

If you want to work locally using your own IDE, you can clone this repo and push changes. Pushed changes will also be reflected in Lovable.

The only requirement is having Node.js & npm installed - [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating)

Follow these steps:

```sh
# Step 1: Clone the repository using the project's Git URL.
git clone <YOUR_GIT_URL>

# Step 2: Navigate to the project directory.
cd <YOUR_PROJECT_NAME>

# Step 3: Install the necessary dependencies.
npm i

# Step 4: Start the development server with auto-reloading and an instant preview.
npm run dev
```

**Edit a file directly in GitHub**

- Navigate to the desired file(s).
- Click the "Edit" button (pencil icon) at the top right of the file view.
- Make your changes and commit the changes.

**Use GitHub Codespaces**

- Navigate to the main page of your repository.
- Click on the "Code" button (green button) near the top right.
- Select the "Codespaces" tab.
- Click on "New codespace" to launch a new Codespace environment.
- Edit files directly within the Codespace and commit and push your changes once you're done.

## Running the backend locally (Windows PowerShell)

The Flask backend reads configuration from the project root `.env` file using
`python-dotenv`. If `DATABASE_URL` is missing, it falls back to a SQLite file in
`instance/forwarder.sqlite3`, so the service can start without PostgreSQL.

1. **Create a virtual environment and install dependencies**

   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r backend/requirements.txt
   ```

2. **Configure environment variables**

   Copy the template and adjust it for your environment. The application
   automatically loads `.env` from the repository root on startup.

   ```powershell
   Copy-Item .env.example .env
   # Edit .env and set DATABASE_URL, CORS_ORIGIN, and SLA_HOURS as needed
   ```

   * `DATABASE_URL` &mdash; optional. When omitted, the backend uses
     `sqlite:///instance/forwarder.sqlite3`.
   * `CORS_ORIGIN` &mdash; optional. Lets you define which frontend origin is allowed.
   * `SLA_HOURS` &mdash; optional. Controls the SLA message exposed by the API.

   The application creates the `instance/` directory automatically; ensure your
   shell has permission to write to it if you rely on the SQLite fallback.

3. **Initialize the database schema**

   Create the tables for a fresh environment (works for SQLite or PostgreSQL):

   ```powershell
   flask --app backend.wsgi shell -c "from backend.extensions import db; db.create_all()"
   ```

4. **Start the development server**

   ```powershell
   $env:FLASK_APP = "backend.wsgi"
   $env:FLASK_ENV = "development"
   flask run
   ```

   When the server starts it prints a connectivity check (for example,
   `✅ Database connection successful.`). Browse to
   `http://127.0.0.1:5000/api/shipment-request/ping` to confirm the API responds.

## What technologies are used for this project?

This project is built with:

- Vite
- TypeScript
- React
- shadcn-ui
- Tailwind CSS

## How can I deploy this project?

Simply open [Lovable](https://lovable.dev/projects/6537ffc1-88ab-4c2a-8eb9-82b3b1bc9f4f) and click on Share -> Publish.

## Can I connect a custom domain to my Lovable project?

Yes, you can!

To connect a domain, navigate to Project > Settings > Domains and click Connect Domain.

Read more here: [Setting up a custom domain](https://docs.lovable.dev/features/custom-domain#custom-domain)
