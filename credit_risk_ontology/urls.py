from django.urls import path, include

urlpatterns = [
    path('api/v1/credit-risk/', include('credit_risk_ontology.api.urls')),
]
