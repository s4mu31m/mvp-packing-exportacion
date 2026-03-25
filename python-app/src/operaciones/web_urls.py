from django.urls import path
from . import views

app_name = "operaciones"

urlpatterns = [
    path("",          views.DashboardView.as_view(),        name="dashboard"),
    path("recepcion/",views.RecepcionView.as_view(),        name="recepcion"),
    path("consulta/", views.ConsultaJefaturaView.as_view(), name="consulta"),
]