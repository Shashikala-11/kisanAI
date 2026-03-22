from django.urls import path
from . import views

urlpatterns = [
    path("", views.pest_view, name="pest"),
]
