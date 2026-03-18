"""
URLs para los endpoints de prueba de Dataverse
"""
from django.urls import path
from . import dataverse_views

urlpatterns = [
    path('ping/', dataverse_views.ping_dataverse, name='dataverse_ping'),
    path('accounts/', dataverse_views.test_accounts, name='dataverse_accounts'),
    path('entities/', dataverse_views.test_entities, name='dataverse_entities'),
]