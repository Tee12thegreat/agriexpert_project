# AgriExpert — Agricultural AI Expert System

A Django web app implementing a hybrid AI-powered expert system for agriculture,
combining rule-based reasoning with certainty factors and a machine-learning
advisor, both of which adapt from user feedback.

## Components (mapped to the assignment brief)

| Requirement | Where it lives |
|---|---|
| Knowledge base | `core/models.py` (`Rule`, `Symptom`) + seed data in `core/management/commands/seed_kb.py` — 16 expert rules across 5 crops, plus 20 symptom facts |
| Inference engine | `core/inference.py` — forward-chaining rule matching |
| Intelligent reasoning | Certainty-factor combination (`combine_cf`) for the rule engine; RandomForest ensemble learning for the ML advisor (`core/ml_advisor.py`) |
| Learning / adaptive component | `inference.adapt_rule_confidence()` (EMA update to rule CFs from farmer feedback) and `ml_advisor.train_model()` folding confirmed `CropFeedback` cases back into training data |
| Uncertainty handling | Certainty factors (0–1) with partial symptom matching on the rule side; `predict_proba` confidence scores + ranked alternatives on the ML side |
| GUI | Django templates (Bootstrap) — see `templates/core/*.html` |

## Two advisory modules

1. **Pest & Disease Diagnosis** (`/diagnose/`) — pick a crop, tick observed
   symptoms, get ranked diagnoses with a certainty percentage and treatment
   advice. Give feedback (correct/incorrect) to adapt that rule's confidence
   for future users.
2. **Crop & Fertiliser-Fit Advisor** (`/crop-advisor/`) — enter soil (N, P, K,
   pH) and climate (temperature, humidity, rainfall) readings, get a
   best-fit crop prediction with a confidence score and runner-up options.
   Confirm/correct the outcome to add the case to the training pool.

`/model-health/` shows the rule confidence table and lets you trigger a
model retrain (folding in any confirmed crop feedback since the last training run).

## Setup

```bash
cd agriexpert_project
python -m venv venv && source venv/bin/activate   # optional but recommended
pip install -r requirements.txt

python manage.py migrate
python manage.py seed_kb          # loads the rule-based knowledge base
python manage.py createsuperuser  # optional, for /admin/

python manage.py shell -c "from core import ml_advisor; ml_advisor.train_model()"
# (or just start the server — the ML model auto-trains on first prediction if missing)

python manage.py runserver
```

Then open http://127.0.0.1:8000/

## Deploying to Render

This project ships with `build.sh`, `Procfile`, and `render.yaml` already set up.

**Quickest path (Blueprint):**
1. Push this project to a GitHub repo.
2. In Render, click **New → Blueprint**, point it at the repo — it reads
   `render.yaml` and creates the web service **and** a free Postgres database
   automatically, wiring `DATABASE_URL` and a random `SECRET_KEY` for you.
3. Click **Apply**. First deploy takes a few minutes (installs deps, runs
   migrations, seeds the knowledge base, trains the ML model).

**Manual path (New Web Service):**
1. Push to GitHub, then in Render click **New → Web Service** and connect the repo.
2. Runtime: Python 3. Build command: `./build.sh`. Start command:
   `gunicorn agriexpert_project.wsgi:application`.
3. Add a Postgres database (**New → PostgreSQL**, free tier is fine), then
   in the web service's **Environment** tab add `DATABASE_URL` (copy the
   Internal Connection String from the Postgres dashboard).
4. Add `SECRET_KEY` (any long random string) and `DEBUG=False`.
5. Deploy.

**Why Postgres, not SQLite, on Render:** Render's filesystem is ephemeral —
anything written to disk (including a SQLite file) is wiped on every
redeploy or restart. `settings.py` already falls back to SQLite locally but
picks up `DATABASE_URL` automatically when it's set, so once you attach the
Postgres add-on your diagnosis history, feedback, and admin users persist
across deploys. The trained `.joblib` ML model file itself is fine to lose
on redeploy — `build.sh` retrains it from `core/data/crop_dataset.csv` (plus
any feedback already in the database) every time.

## Notes

- The ML advisor's seed dataset (`core/data/crop_dataset.csv`) is synthetic,
  generated from typical agronomic N-P-K/pH/climate profiles per crop
  (`core/generate_dataset.py`) — a stand-in for historical case data. In a
  real deployment you'd replace/augment it with real soil-test and yield
  records.
- `ALLOWED_HOSTS = ['*']` and `DEBUG = True` are set for easy local demoing —
  tighten these before any real deployment.
- Each retrain creates a new `MLModelMeta` version row (v1, v2, ...) so you
  can see accuracy change as feedback accumulates.
