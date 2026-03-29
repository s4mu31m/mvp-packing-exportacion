from django.urls import path

from . import views

app_name = "usuarios"

urlpatterns = [

    path("login/",  views.CaliProLoginView.as_view(),  name="login"),

    path("logout/", views.CaliProLogoutView.as_view(),  name="logout"),

    path("portal/", views.PortalView.as_view(),     name="portal"),

]
