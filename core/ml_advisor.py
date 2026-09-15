"""
Machine-learning half of the hybrid expert system: a crop/fertiliser-fit
advisor. Given soil (N, P, K, pH) and climate (temperature, humidity,
rainfall) readings, a RandomForestClassifier predicts the best-fit crop.

Intelligent reasoning: ensemble learning over agronomic feature space.
Uncertainty handling: predict_proba gives a calibrated-ish confidence
score per class, so the GUI can show "62% confident: Maize" rather
than a bare label, and can surface runner-up crops.
Learning/adaptive component: confirmed farmer feedback (CropFeedback)
is appended to the training set and the model is retrained, so
recommendation accuracy is meant to improve as real cases accumulate
on top of the synthetic seed dataset.
"""
import json
from pathlib import Path

import joblib
import pandas as pd
from django.conf import settings
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
SEED_CSV = Path(__file__).resolve().parent / "data" / "crop_dataset.csv"
MODEL_PATH = Path(settings.ML_MODEL_DIR) / "crop_model.joblib"
LABELS_PATH = Path(settings.ML_MODEL_DIR) / "crop_labels.json"


def _load_seed_dataframe() -> pd.DataFrame:
    return pd.read_csv(SEED_CSV)


def _load_feedback_dataframe() -> pd.DataFrame:
    """
    Pull confirmed CropFeedback rows and turn them into extra training
    rows, using the original session's sensor inputs as features and
    the farmer-confirmed crop as the label. This is what lets the
    model adapt to local conditions over time instead of staying
    frozen at its seed-dataset behaviour.
    """
    from .models import CropFeedback  # local import: avoid app-loading issues

    rows = []
    for fb in CropFeedback.objects.select_related("session").filter(was_helpful=True):
        s = fb.session
        rows.append({
            "N": s.n, "P": s.p, "K": s.k,
            "temperature": s.temperature, "humidity": s.humidity,
            "ph": s.ph, "rainfall": s.rainfall,
            "label": fb.actual_best_crop.strip().lower(),
        })
    # Corrections (was_helpful=False) still carry a true label -> also useful signal
    for fb in CropFeedback.objects.select_related("session").filter(was_helpful=False):
        s = fb.session
        rows.append({
            "N": s.n, "P": s.p, "K": s.k,
            "temperature": s.temperature, "humidity": s.humidity,
            "ph": s.ph, "rainfall": s.rainfall,
            "label": fb.actual_best_crop.strip().lower(),
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=FEATURES + ["label"])


def train_model(notes: str = "") -> "MLModelMeta":
    """Train (or retrain) the RandomForest on seed + accumulated feedback data."""
    from .models import MLModelMeta  # local import

    seed_df = _load_seed_dataframe()
    feedback_df = _load_feedback_dataframe()
    full_df = pd.concat([seed_df, feedback_df], ignore_index=True)

    X = full_df[FEATURES]
    y = full_df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y if y.nunique() > 1 else None
    )

    clf = RandomForestClassifier(n_estimators=200, max_depth=8, random_state=42)
    clf.fit(X_train, y_train)
    acc = accuracy_score(y_test, clf.predict(X_test)) if len(X_test) else float("nan")

    joblib.dump(clf, MODEL_PATH)
    LABELS_PATH.write_text(json.dumps(sorted(y.unique().tolist())))

    prior_versions = MLModelMeta.objects.count()
    version = f"v{prior_versions + 1}"
    meta = MLModelMeta.objects.create(
        version=version,
        accuracy=0.0 if pd.isna(acc) else float(acc),
        n_training_samples=len(full_df),
        notes=notes or f"seed={len(seed_df)}, feedback={len(feedback_df)}",
    )
    return meta


def _ensure_model():
    if not MODEL_PATH.exists():
        train_model(notes="initial training on seed dataset")


def predict(features: dict) -> dict:
    """
    features: {"N":.., "P":.., "K":.., "temperature":.., "humidity":..,
               "ph":.., "rainfall":..}
    Returns {"predicted_crop", "confidence", "alternatives": [(crop, prob), ...]}
    """
    _ensure_model()
    clf = joblib.load(MODEL_PATH)
    row = pd.DataFrame([[features[f] for f in FEATURES]], columns=FEATURES)

    proba = clf.predict_proba(row)[0]
    classes = clf.classes_
    ranked = sorted(zip(classes, proba), key=lambda t: t[1], reverse=True)

    top_crop, top_conf = ranked[0]
    alternatives = [{"crop": c, "confidence": round(float(p) * 100, 1)} for c, p in ranked[1:4]]

    return {
        "predicted_crop": top_crop,
        "confidence": round(float(top_conf) * 100, 1),
        "alternatives": alternatives,
    }


def current_meta():
    from .models import MLModelMeta
    return MLModelMeta.objects.first()  # ordered by -trained_at
