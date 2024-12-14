from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Sum, F
from ..models import Account, Transaction, TransactionLine
from ..metrics import BusinessMetrics
from .serializers import (
    AccountSerializer, TransactionSerializer, 
    MetricsSerializer, UserSerializer
)

class AccountViewSet(viewsets.ModelViewSet):
    serializer_class = AccountSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Account.objects.filter(user=self.request.user).annotate(
            balance=Sum(
                F('transactionline__debit_amount') - F('transactionline__credit_amount')
            )
        )
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        recent_transactions = self.get_queryset().order_by('-date')[:5]
        serializer = self.get_serializer(recent_transactions, many=True)
        return Response(serializer.data)

class MetricsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        metrics = BusinessMetrics(request.user)
        serializer = MetricsSerializer(metrics.get_all_metrics())
        return Response(serializer.data)

class DashboardAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        # Get account balances
        accounts = Account.objects.filter(user=request.user).annotate(
            balance=Sum(
                F('transactionline__debit_amount') - F('transactionline__credit_amount')
            )
        )
        
        # Get recent transactions
        recent_transactions = Transaction.objects.filter(
            user=request.user
        ).order_by('-date')[:5]
        
        # Get metrics
        metrics = BusinessMetrics(request.user)
        
        return Response({
            'accounts': AccountSerializer(accounts, many=True).data,
            'recent_transactions': TransactionSerializer(recent_transactions, many=True).data,
            'metrics': MetricsSerializer(metrics.get_all_metrics()).data
        }) 