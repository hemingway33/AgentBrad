from django.urls import path
from . import views

app_name = 'bookkeeping'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('transactions/', views.TransactionListView.as_view(), name='transaction-list'),
    path('transactions/create/', views.TransactionCreateView.as_view(), name='transaction-create'),
    path('reports/', views.FinancialReportView.as_view(), name='financial-reports'),
    path('metrics/', views.MetricsView.as_view(), name='metrics'),
    path('integrations/', views.IntegrationsView.as_view(), name='integrations'),
] 