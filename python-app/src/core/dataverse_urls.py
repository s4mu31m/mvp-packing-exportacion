"""
URLs para los endpoints de prueba de Dataverse
"""
from django.urls import path
from . import dataverse_views

urlpatterns = [
    path('ping/', dataverse_views.ping_dataverse, name='dataverse_ping'),
    path('check_tables/', dataverse_views.check_tables_available, name='dataverse_check_tables'),
    path('save_first_bin_code/', dataverse_views.save_first_bin_code, name='dataverse_save_first_bin_code'),
    path('get_first_bin_code/', dataverse_views.get_first_bin_code, name='dataverse_get_first_bin_code'),
]