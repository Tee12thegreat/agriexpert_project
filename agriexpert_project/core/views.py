from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse

from . import inference, ml_advisor
from .forms import DiagnosisForm, CropInputForm, DiagnosisFeedbackForm, CropFeedbackForm
from .models import (
    Rule, DiagnosisSession, DiagnosisFeedback,
    CropRecommendationSession, CropFeedback, MLModelMeta,
)


def home(request):
    return render(request, "core/home.html", {
        "n_rules": Rule.objects.count(),
        "n_diagnoses": DiagnosisSession.objects.count(),
        "n_crop_sessions": CropRecommendationSession.objects.count(),
        "model_meta": ml_advisor.current_meta(),
    })


# ---------------------------------------------------------------------------
# Rule-based diagnosis (symptoms -> pest/disease, with certainty factors)
# ---------------------------------------------------------------------------

def diagnose_view(request):
    if request.method == "POST":
        form = DiagnosisForm(request.POST)
        if form.is_valid():
            crop = form.cleaned_data["crop"]
            symptoms = form.cleaned_data["symptoms"]
            results = inference.diagnose(crop, symptoms)
            session = DiagnosisSession.objects.create(
                crop=crop, symptoms_selected=symptoms, results=results
            )
            return redirect("diagnosis_result", session_id=session.id)
    else:
        form = DiagnosisForm()
    return render(request, "core/diagnose_form.html", {"form": form})


def diagnosis_result_view(request, session_id):
    session = get_object_or_404(DiagnosisSession, id=session_id)

    if request.method == "POST":
        fb_form = DiagnosisFeedbackForm(request.POST)
        if fb_form.is_valid():
            rule = get_object_or_404(Rule, id=fb_form.cleaned_data["rule_id"])
            is_correct = fb_form.cleaned_data["is_correct"] == "yes"
            DiagnosisFeedback.objects.create(session=session, rule=rule, is_correct=is_correct)
            new_cf = inference.adapt_rule_confidence(rule, is_correct)
            messages.success(
                request,
                f"Thanks! Recorded your feedback on '{rule.conclusion}'. "
                f"Rule confidence adapted to {new_cf * 100:.0f}%."
            )
            return redirect("diagnosis_result", session_id=session.id)
    else:
        fb_form = DiagnosisFeedbackForm()

    already_rated_ids = set(session.feedback.values_list("rule_id", flat=True))
    return render(request, "core/diagnose_result.html", {
        "session": session,
        "fb_form": fb_form,
        "already_rated_ids": already_rated_ids,
    })


# ---------------------------------------------------------------------------
# ML-based crop / fertiliser-fit advisor
# ---------------------------------------------------------------------------

def crop_advisor_view(request):
    if request.method == "POST":
        form = CropInputForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            features = {
                "N": cd["n"], "P": cd["p"], "K": cd["k"],
                "temperature": cd["temperature"], "humidity": cd["humidity"],
                "ph": cd["ph"], "rainfall": cd["rainfall"],
            }
            result = ml_advisor.predict(features)
            meta = ml_advisor.current_meta()
            session = CropRecommendationSession.objects.create(
                n=cd["n"], p=cd["p"], k=cd["k"],
                temperature=cd["temperature"], humidity=cd["humidity"],
                ph=cd["ph"], rainfall=cd["rainfall"],
                predicted_crop=result["predicted_crop"],
                confidence=result["confidence"],
                alternatives=result["alternatives"],
                model_version=meta.version if meta else "v1",
            )
            return redirect("crop_result", session_id=session.id)
    else:
        form = CropInputForm()
    return render(request, "core/crop_form.html", {"form": form})


def crop_result_view(request, session_id):
    session = get_object_or_404(CropRecommendationSession, id=session_id)

    if request.method == "POST":
        fb_form = CropFeedbackForm(request.POST)
        if fb_form.is_valid():
            CropFeedback.objects.create(
                session=session,
                actual_best_crop=fb_form.cleaned_data["actual_best_crop"],
                was_helpful=fb_form.cleaned_data["was_helpful"] == "yes",
            )
            messages.success(
                request,
                "Thanks — this case has been added to the training pool. "
                "Retrain the model from the Model Health page to fold it in."
            )
            return redirect("crop_result", session_id=session.id)
    else:
        fb_form = CropFeedbackForm(initial={"session_id": session.id})

    already_gave_feedback = session.feedback.exists()
    return render(request, "core/crop_result.html", {
        "session": session, "fb_form": fb_form,
        "already_gave_feedback": already_gave_feedback,
    })


# ---------------------------------------------------------------------------
# Model / knowledge-base health & retraining
# ---------------------------------------------------------------------------

def model_health_view(request):
    if request.method == "POST" and request.POST.get("action") == "retrain":
        meta = ml_advisor.train_model(notes="manual retrain via GUI")
        messages.success(
            request,
            f"Retrained model {meta.version}: accuracy {meta.accuracy * 100:.1f}% "
            f"on {meta.n_training_samples} samples."
        )
        return redirect("model_health")

    rules = Rule.objects.all().order_by("crop", "-base_cf")
    model_history = MLModelMeta.objects.all()[:10]
    pending_feedback = CropFeedback.objects.count()
    return render(request, "core/model_health.html", {
        "rules": rules,
        "model_history": model_history,
        "pending_feedback": pending_feedback,
    })


def history_view(request):
    diagnoses = DiagnosisSession.objects.order_by("-created_at")[:25]
    crop_sessions = CropRecommendationSession.objects.order_by("-created_at")[:25]
    return render(request, "core/history.html", {
        "diagnoses": diagnoses, "crop_sessions": crop_sessions,
    })
