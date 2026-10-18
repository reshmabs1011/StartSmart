# Personalized Procrastination Management Platform

A beginner-friendly Flask starter project for a university hackathon. It includes a self-reflection assessment, rule-based recommendations, tasks and subtasks, mini-deadline fields, a focus-session logger, behavioral event logs, and a progress dashboard.

## Important scope note

This is a **starter prototype**, not a clinically validated assessment or production-ready service. The questionnaire is an illustrative self-reflection tool, not a diagnostic instrument. Focus sessions are logged when the user submits the form; this version does not verify continuous attention or run a server-side timer. Review the security and deployment checklist before publishing it.

## Requirements

- Python 3.10 or newer
- Visual Studio Code (recommended) or another editor
- PowerShell or CMD
- A modern browser

## Run on Windows (PowerShell)

1. Extract the ZIP file.
2. Open the extracted `procrastination_platform` folder in VS Code.
3. Open Terminal → New Terminal.
4. Run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

5. Open `http://127.0.0.1:5000` in your browser.
6. Register an account, take the assessment, create a task, try a focus session, and open Progress.

If PowerShell blocks activation, use CMD:

```cmd
py -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python app.py
```

Or run the virtual environment Python directly without activation:
`.\.venv\Scripts\python.exe -m pip install -r requirements.txt`
then `.\.venv\Scripts\python.exe app.py`.

## Included features

- Registration and login with password hashing
- Brief self-reflection assessment
- Rule-based recommendations
- Task creation and starter subtasks
- Planned start and due-date fields
- Recording actual task starts
- Subtask completion and task completion
- Focus-session participation logging
- Progress summary and recent activity
- Per-user task access checks

## Current limitations / next improvements

- Assessment questions and scoring are examples, not validated psychological measures.
- Subtask templates are generic; students can adapt them conceptually, but editing/deleting individual subtasks is not implemented yet.
- Mini-deadline date is stored as a field, but there is no automatic reminder service.
- Focus-session form logs a session; a live countdown and reliable completion tracking should be added.
- No password reset, email verification, rate limiting, or account deletion workflow yet.
- Uses SQLite by default; choose PostgreSQL for production multi-user deployment.
- `SECRET_KEY` has a development fallback. Set a strong environment variable before deployment.
- Debug mode defaults to on for local learning. Never run with debug enabled in production.
- No AI model is required; personalization is transparent rule-based logic.

## Lovable integration

Lovable is an AI-powered app builder, not a Flask library. You have two options:
1. **Simplest:** Use the HTML templates included here and build on Flask.
2. **Separate frontend:** Build/export a React frontend from Lovable, then call Flask API endpoints. This starter is primarily server-rendered and does not yet expose all features as JSON APIs. Add API routes, configure CORS only if needed, and use secure authentication before connecting a separate frontend.

## Before deployment

1. Replace the development secret with a strong `SECRET_KEY` environment variable.
2. Set `FLASK_DEBUG=0`.
3. Use HTTPS and a production WSGI server such as Gunicorn on a compatible host.
4. Configure a production database and migrations.
5. Review privacy, consent, retention, authorization, CSRF protection, logging, and backup requirements.
6. Test that users cannot access other users' records.
7. Pilot-test with consent and report outcomes honestly; do not claim effectiveness without evidence.
