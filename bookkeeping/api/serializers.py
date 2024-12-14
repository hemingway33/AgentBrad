from rest_framework import serializers
from ..models import Account, Transaction, TransactionLine, FinancialStatement
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']

class AccountSerializer(serializers.ModelSerializer):
    balance = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Account
        fields = ['id', 'name', 'account_type', 'account_number', 'description', 
                 'is_active', 'balance']
        read_only_fields = ['id']

class TransactionLineSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)
    
    class Meta:
        model = TransactionLine
        fields = ['id', 'account', 'account_name', 'description', 
                 'debit_amount', 'credit_amount']

class TransactionSerializer(serializers.ModelSerializer):
    lines = TransactionLineSerializer(many=True)
    
    class Meta:
        model = Transaction
        fields = ['id', 'date', 'reference_number', 'description', 
                 'status', 'source', 'lines']
        read_only_fields = ['id']
    
    def create(self, validated_data):
        lines_data = validated_data.pop('lines')
        transaction = Transaction.objects.create(**validated_data)
        
        for line_data in lines_data:
            TransactionLine.objects.create(transaction=transaction, **line_data)
        
        return transaction

class MetricsSerializer(serializers.Serializer):
    quick_ratio = serializers.FloatField()
    current_ratio = serializers.FloatField()
    operating_cash_flow_ratio = serializers.FloatField()
    gross_profit_margin = serializers.FloatField()
    debt_to_equity_ratio = serializers.FloatField()
    accounts_receivable_turnover = serializers.FloatField() 