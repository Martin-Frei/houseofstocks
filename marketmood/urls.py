# marketmood/urls.py
from django.urls import path
from . import views

app_name = 'marketmood'

urlpatterns = [
    path('', views.dashboard, name='index'),
    path('zone/<str:zone_key>/', views.zone_detail, name='zone_detail'),
]