from django.urls import path

from . import views

app_name = "usuarios"

urlpatterns = [
    path("login/",   views.CaliProLoginView.as_view(),          name="login"),
    path("logout/",  views.CaliProLogoutView.as_view(),          name="logout"),
    path("portal/",  views.PortalView.as_view(),                 name="portal"),
    path("gestion/",                    views.GestionUsuariosView.as_view(),     name="gestion_usuarios"),
    path("gestion/nuevo/",             views.CrearUsuarioView.as_view(),        name="crear_usuario"),
    path("gestion/<int:pk>/toggle/",   views.ToggleUsuarioActivoView.as_view(), name="toggle_usuario"),
]
