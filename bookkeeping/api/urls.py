from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'accounts', views.AccountViewSet, basename='account')
router.register(r'transactions', views.TransactionViewSet, basename='transaction')

urlpatterns = [
    path('', include(router.urls)),
    path('metrics/', views.MetricsAPIView.as_view(), name='metrics'),
    path('dashboard/', views.DashboardAPIView.as_view(), name='dashboard'),
    path('auth/', include('rest_framework.urls')),
] 