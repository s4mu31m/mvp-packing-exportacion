from django.urls import path
from . import views

app_name = "operaciones"

urlpatterns = [
    path("",               views.DashboardView.as_view(),      name="dashboard"),
    path("recepcion/",     views.RecepcionView.as_view(),      name="recepcion"),
    path("pesaje/",        views.PesajeView.as_view(),         name="pesaje"),
    path("desverdizado/",  views.DesverdizadoView.as_view(),   name="desverdizado"),
    path("ingreso-packing/", views.IngresoPackingView.as_view(), name="ingreso_packing"),
    path("proceso/",       views.ProcesoView.as_view(),        name="proceso"),
    path("control/",       views.ControlView.as_view(),        name="control"),
    path("paletizado/",    views.PaletizadoView.as_view(),     name="paletizado"),
    path("camaras/",       views.CamarasView.as_view(),        name="camaras"),
    path("consulta/",          views.ConsultaJefaturaView.as_view(),     name="consulta"),
    path("consulta/exportar/", views.ExportarConsultaCSVView.as_view(), name="exportar_consulta"),
]
