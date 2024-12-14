from django.urls import path, include
from bookkeeping.api.auth import CustomAuthToken, LogoutView

urlpatterns = [
    # ... existing urls ...
    path('api/', include('bookkeeping.api.urls')),
    path('api/auth/login/', CustomAuthToken.as_view(), name='api_token_auth'),
    path('api/auth/logout/', LogoutView.as_view(), name='api_token_logout'),
] 