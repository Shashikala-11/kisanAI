from django.urls import path
from . import views

urlpatterns = [
    path("", views.chat_view, name="chat"),
    path("clear/", views.clear_chat, name="clear-chat"),
]
