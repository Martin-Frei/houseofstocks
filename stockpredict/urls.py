# stockpredict/urls.py
from django.urls import path
from . import views

app_name = 'stockpredict'

urlpatterns = [
    path('', views.dashboard, name='index'),
    path('api/sweet-spot/', views.get_sweet_spot, name='sweet_spot_api'),
]