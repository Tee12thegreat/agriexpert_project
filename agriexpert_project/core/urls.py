from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("diagnose/", views.diagnose_view, name="diagnose"),
    path("diagnose/result/<int:session_id>/", views.diagnosis_result_view, name="diagnosis_result"),
    path("crop-advisor/", views.crop_advisor_view, name="crop_advisor"),
    path("crop-advisor/result/<int:session_id>/", views.crop_result_view, name="crop_result"),
    path("model-health/", views.model_health_view, name="model_health"),
    path("history/", views.history_view, name="history"),
]
