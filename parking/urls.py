from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('park/', views.park_vehicle, name='park_vehicle'),
    path('exit/', views.exit_vehicle, name='exit_vehicle'),
    path('pay/<int:ticket_id>/', views.pay_fee, name='pay_fee'),
    path('monitor/', views.monitor, name='monitor'),
    path('config/', views.manage_config, name='manage_config'),
    path('history/', views.ticket_history, name='history'),
]
