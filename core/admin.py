from django.contrib import admin
from .models import (
    Rule, Symptom, DiagnosisSession, DiagnosisFeedback,
    CropRecommendationSession, CropFeedback, MLModelMeta,
)


@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = ("conclusion", "crop", "base_cf", "times_confirmed", "times_rejected", "updated_at")
    list_filter = ("crop",)


@admin.register(Symptom)
class SymptomAdmin(admin.ModelAdmin):
    list_display = ("label", "code", "crop")


admin.site.register(DiagnosisSession)
admin.site.register(DiagnosisFeedback)
admin.site.register(CropRecommendationSession)
admin.site.register(CropFeedback)
admin.site.register(MLModelMeta)
