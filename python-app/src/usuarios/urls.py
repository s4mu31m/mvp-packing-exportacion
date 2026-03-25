from django.urls import path

from . import views

app_name = "usuarios"

urlpatterns = [

    path("login/",  views.CFNLoginView.as_view(),  name="login"),

    path("logout/", views.CFNLogoutView.as_view(),  name="logout"),

    path("portal/", views.PortalView.as_view(),     name="portal"),

]
