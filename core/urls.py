from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from chat import views as chat_views

urlpatterns = [
    path("",         include("home.urls")),
    path("chat/",    include("chat.urls")),
    path("pest/",    include("pest.urls")),
    path("farmer/",  include("farmers.urls")),
    path("weather/", chat_views.weather_widget, name="weather-api"),
    path("market/",  chat_views.market_widget,  name="market-api"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
