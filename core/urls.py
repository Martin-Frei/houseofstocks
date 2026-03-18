from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.index, name='index'),
    path('preise/', views.preise, name='preise'),
    path('waitlist/', views.waitlist, name='waitlist'),
]
