INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'debt_manager',
    'budget_tracker',
    'goals',
    'crispy_forms',
    'crispy_bootstrap5',
    'bookkeeping',
    'rest_framework',
    'rest_framework.authtoken',
    'debt_advisor',
]

# Add Crispy Forms settings
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Add QuickBooks OAuth settings
QUICKBOOKS_CLIENT_ID = 'your_client_id'
QUICKBOOKS_CLIENT_SECRET = 'your_client_secret'
QUICKBOOKS_REDIRECT_URI = 'your_redirect_uri'
QUICKBOOKS_ENVIRONMENT = 'sandbox'  # or 'production'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20
}

# OpenAI API settings
OPENAI_API_KEY = 'your_openai_api_key'