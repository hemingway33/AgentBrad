from django.contrib import admin
from django.urls import path, include
from bookkeeping.api.auth import CustomAuthToken, LogoutView

urlpatterns = [
    path('admin/', admin.site.urls),
    # Web UI
    path('', include('bookkeeping.urls')),
    # Bookkeeping API
    path('api/', include('bookkeeping.api.urls')),
    # Debt advisor API (conversation + gamification)
    path('', include('debt_advisor.urls')),
    # Auth API
    path('api/auth/login/', CustomAuthToken.as_view(), name='api_token_auth'),
    path('api/auth/logout/', LogoutView.as_view(), name='api_token_logout'),
]
