from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api import views

router = DefaultRouter()
router.register(r'conversation', views.ConversationViewSet, basename='conversation')
router.register(r'gamification', views.GamificationViewSet, basename='gamification')

urlpatterns = [
    path('api/', include(router.urls)),
] 