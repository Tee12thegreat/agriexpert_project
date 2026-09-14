#!/usr/bin/env bash
# Render build command. Set this as the service's Build Command:
#   ./build.sh
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# Idempotent: get_or_create-based, safe to run on every deploy.
python manage.py seed_kb

# Train the ML model if it doesn't exist yet on this instance's disk
# (ephemeral on Render's free tier, so this reruns after every deploy —
# harmless, just retrains from the seed dataset + any DB feedback).
python manage.py shell -c "
from core import ml_advisor
from pathlib import Path
if not ml_advisor.MODEL_PATH.exists():
    meta = ml_advisor.train_model(notes='auto-trained on deploy')
    print('Trained', meta)
else:
    print('Model already present, skipping training')
"
