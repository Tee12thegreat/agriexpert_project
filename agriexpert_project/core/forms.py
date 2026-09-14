from django import forms
from .models import Rule, Symptom


class DiagnosisForm(forms.Form):
    crop = forms.ChoiceField(choices=Rule.CROP_CHOICES,
                              widget=forms.Select(attrs={"class": "form-select"}))
    symptoms = forms.MultipleChoiceField(
        choices=[], widget=forms.CheckboxSelectMultiple, required=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate symptom choices from DB (general + all crop-specific ones);
        # the view narrows this per selected crop via JS-free full listing.
        all_symptoms = Symptom.objects.all().order_by("crop", "label")
        self.fields["symptoms"].choices = [(s.code, f"{s.label} ({s.crop})") for s in all_symptoms]


class CropInputForm(forms.Form):
    n = forms.FloatField(label="Nitrogen (N, kg/ha)", min_value=0,
                          widget=forms.NumberInput(attrs={"class": "form-control"}))
    p = forms.FloatField(label="Phosphorus (P, kg/ha)", min_value=0,
                          widget=forms.NumberInput(attrs={"class": "form-control"}))
    k = forms.FloatField(label="Potassium (K, kg/ha)", min_value=0,
                          widget=forms.NumberInput(attrs={"class": "form-control"}))
    temperature = forms.FloatField(label="Avg. temperature (°C)",
                                    widget=forms.NumberInput(attrs={"class": "form-control"}))
    humidity = forms.FloatField(label="Relative humidity (%)", min_value=0, max_value=100,
                                 widget=forms.NumberInput(attrs={"class": "form-control"}))
    ph = forms.FloatField(label="Soil pH", min_value=3.0, max_value=9.5,
                           widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.1"}))
    rainfall = forms.FloatField(label="Rainfall (mm)", min_value=0,
                                 widget=forms.NumberInput(attrs={"class": "form-control"}))


class DiagnosisFeedbackForm(forms.Form):
    rule_id = forms.IntegerField(widget=forms.HiddenInput)
    is_correct = forms.ChoiceField(
        choices=[("yes", "Yes, that's right"), ("no", "No, that's wrong")],
        widget=forms.RadioSelect,
    )


class CropFeedbackForm(forms.Form):
    session_id = forms.IntegerField(widget=forms.HiddenInput)
    was_helpful = forms.ChoiceField(
        choices=[("yes", "Yes"), ("no", "No")], widget=forms.RadioSelect
    )
    actual_best_crop = forms.CharField(
        max_length=64,
        help_text="What crop did you actually plant / would you recommend for this plot?",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
