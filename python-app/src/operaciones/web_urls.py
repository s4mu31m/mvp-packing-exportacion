from django.urls import path
from . import views

app_name = "operaciones"

urlpatterns = [
    path("",               views.DashboardView.as_view(),      name="dashboard"),
    path("recepcion/",     views.RecepcionView.as_view(),      name="recepcion"),
    path("desverdizado/",  views.DesverdizadoView.as_view(),   name="desverdizado"),
    path("ingreso-packing/", views.IngresoPackingView.as_view(), name="ingreso_packing"),
    path("proceso/",       views.ProcesoView.as_view(),        name="proceso"),
    path("control/",             views.ControlCalidadIndexView.as_view(),        name="control"),
    path("control/desverdizado/", views.ControlCalidadDesverdizadoView.as_view(), name="control_desverdizado"),
    path("control/packing/",     views.ControlCalidadPackingView.as_view(),       name="control_packing"),
    path("control/camaras/",     views.ControlCalidadCamarasView.as_view(),       name="control_camaras"),
    path("control/proceso/",     views.ControlProcesoView.as_view(),              name="control_proceso"),
    path("paletizado/",    views.PaletizadoView.as_view(),     name="paletizado"),
    path("camaras/",       views.CamarasView.as_view(),        name="camaras"),
    path("consulta/",          views.ConsultaJefaturaView.as_view(),     name="consulta"),
    path("consulta/lotes/<str:lote_code>/", views.ConsultaLoteDetalleView.as_view(), name="consulta_lote_detalle"),
    path("consulta/pallets/<str:pallet_code>/", views.ConsultaPalletDetalleView.as_view(), name="consulta_pallet_detalle"),
    path("consulta/exportar/", views.ExportarConsultaCSVView.as_view(), name="exportar_consulta"),
    path("consulta/exportar/excel/", views.ExportarConsultaExcelView.as_view(), name="exportar_consulta_excel"),
]
