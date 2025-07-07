from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('upload/', views.upload_historical_data, name='upload'),
    path('upload/poll_state', views.poll_state, name='poll_state'),
    path('backtest_table/', views.backtest_table, name='backtest_table'),
    path('backtest_figure/', views.backtest_figure, name='backtest_figure'),

    # Export from database
    path('export/security', views.export_security, name='export_security'),

    # Research reports
    path('reports/', views.reports, name='reports'),
]
