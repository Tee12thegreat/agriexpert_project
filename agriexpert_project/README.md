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
