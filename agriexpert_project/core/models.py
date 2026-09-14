from django.db import models


class Rule(models.Model):
    """
    A single knowledge-base rule for the rule-based diagnosis engine.

    IF (crop = self.crop) AND (a sufficient subset of self.symptoms are observed)
    THEN (conclusion = self.conclusion) WITH certainty self.base_cf

    base_cf is a Certainty Factor in [0, 1] representing the expert's initial
    confidence in this rule. It is adapted over time by the feedback loop in
    core.inference.adapt_rule_confidence(), which is the system's
    data-driven / adaptive learning component for the rule-based side.
    """
    CROP_CHOICES = [
        ("maize", "Maize"),
        ("tomato", "Tomato"),
        ("beans", "Beans"),
        ("cabbage", "Cabbage"),
        ("potato", "Potato"),
        ("general", "General / Any crop"),
    ]

    crop = models.CharField(max_length=32, choices=CROP_CHOICES, default="general")
    conclusion = models.CharField(max_length=120, help_text="e.g. 'Fall Armyworm infestation'")
    symptoms = models.JSONField(help_text="List of symptom codes this rule looks for")
    base_cf = models.FloatField(default=0.6, help_text="Certainty factor, 0..1")
    advice = models.TextField(help_text="Recommended action shown to the farmer")
    times_confirmed = models.PositiveIntegerField(default=0)
    times_rejected = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"[{self.crop}] {self.conclusion} (cf={self.base_cf:.2f})"


class Symptom(models.Model):
    """Reference list of symptom codes usable in the diagnosis GUI."""
    code = models.SlugField(unique=True)
    label = models.CharField(max_length=200)
    crop = models.CharField(max_length=32, default="general")

    def __str__(self):
        return self.label


class DiagnosisSession(models.Model):
    """One run of the rule-based inference engine (a 'case')."""
    crop = models.CharField(max_length=32)
    symptoms_selected = models.JSONField()
    results = models.JSONField(help_text="Ranked list of {rule_id, conclusion, cf, advice}")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Diagnosis #{self.pk} ({self.crop})"


class DiagnosisFeedback(models.Model):
    """Farmer confirms/rejects a diagnosis result -> drives CF adaptation."""
    session = models.ForeignKey(DiagnosisSession, on_delete=models.CASCADE, related_name="feedback")
    rule = models.ForeignKey(Rule, on_delete=models.CASCADE)
    is_correct = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)


class CropRecommendationSession(models.Model):
    """One run of the ML-based crop/fertilizer advisor."""
    n = models.FloatField()
    p = models.FloatField()
    k = models.FloatField()
    temperature = models.FloatField()
    humidity = models.FloatField()
    ph = models.FloatField()
    rainfall = models.FloatField()
    predicted_crop = models.CharField(max_length=64)
    confidence = models.FloatField()
    alternatives = models.JSONField(default=list)
    model_version = models.CharField(max_length=32, default="v1")
    created_at = models.DateTimeField(auto_now_add=True)


class CropFeedback(models.Model):
    """
    Ground-truth outcome supplied later by the farmer/agronomist
    (what was actually the best crop / whether the recommendation worked).
    These rows are folded back into training data -> the adaptive/learning
    component for the ML side.
    """
    session = models.ForeignKey(CropRecommendationSession, on_delete=models.CASCADE, related_name="feedback")
    actual_best_crop = models.CharField(max_length=64)
    was_helpful = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)


class MLModelMeta(models.Model):
    """Bookkeeping row for whichever model version is currently active."""
    version = models.CharField(max_length=32)
    accuracy = models.FloatField()
    n_training_samples = models.PositiveIntegerField()
    trained_at = models.DateTimeField(auto_now_add=True)
    notes = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.version} acc={self.accuracy:.3f} n={self.n_training_samples}"

    class Meta:
        ordering = ["-trained_at"]
