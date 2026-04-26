from django.urls import path
from . import views

urlpatterns = [
    path("",        views.chat_view,    name="chat"),
    path("clear/",  views.clear_chat,   name="clear-chat"),
    path("api/",    views.chat_api,     name="chat-api"),
    path("stream/", views.chat_stream,  name="chat-stream"),
    path("weather/", views.weather_widget, name="weather-widget"),
    path("market/",  views.market_widget,  name="market-widget"),
]
