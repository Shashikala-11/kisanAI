from django.urls import path
from . import views

urlpatterns = [
    path("register/",           views.register,      name="farmer-register"),
    path("login/",              views.farmer_login,  name="farmer-login"),
    path("dashboard/",          views.dashboard,     name="farmer-dashboard"),
    path("report/",             views.report,        name="farmer-report"),
    path("logout/",             views.farmer_logout, name="farmer-logout"),
    path("loss/report/",        views.report_loss,   name="report-loss"),
    path("loss/<int:pk>/",      views.loss_detail,   name="loss-detail"),
]
