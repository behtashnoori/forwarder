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

## Running the backend locally

The backend is a Flask application that loads its configuration from environment
variables (via `python-dotenv`) and defaults to SQLite if a database URL is not
provided. Follow the steps below to bring it up locally:

1. **Create a virtual environment and install dependencies**

   ```sh
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment variables**

   Copy the provided template and adjust it for your environment. The backend
   automatically loads `.env` from the project root.

   ```sh
   cp ../.env.example ../.env
   # edit ../.env to set DATABASE_URL, CORS_ORIGIN, SLA_HOURS as needed
   ```

   * `DATABASE_URL` &mdash; optional. Defaults to `sqlite:///instance/forwarder.sqlite3`
     when omitted, so you can start without PostgreSQL.
   * `CORS_ORIGIN` &mdash; optional. Used by the app if your deployment needs specific
     origins.
   * `SLA_HOURS` &mdash; optional. Controls the service-level agreement message shown to
     users.

   The application creates the `instance/` folder automatically; make sure the
   process has write permissions if you rely on the SQLite fallback.

3. **Initialize the database schema**

   When running against a fresh database you can create the tables with:

   ```sh
   flask --app backend.wsgi shell -c "from backend.extensions import db; db.create_all()"
   ```

4. **Start the development server**

   ```sh
   flask --app backend.wsgi run --debug
   ```

   On startup the server prints a message indicating whether the database
   connection succeeded (e.g. `✅ Database connection successful.`). Visit
   `http://127.0.0.1:5000/api/shipment-request/ping` to verify the API is
   reachable.

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
