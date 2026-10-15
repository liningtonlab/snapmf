from django.urls import path
from . import views

app_name = "snapmf"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("submit", views.handle_snapms, name="handle_snapms"),
    path("output/<uuid:job_id>", views.job_output, name="job_output"),
    path(
        "output/<uuid:job_id>/<str:fmt>", views.download_output, name="download_output"
    ),
    path("docs", views.docs, name="docs"),
]
