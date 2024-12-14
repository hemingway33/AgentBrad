from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, F
from django.shortcuts import render
from django.urls import reverse_lazy
from .models import *
from .forms import TransactionForm, AccountForm
from .utils import generate_trial_balance
from .metrics import calculate_business_metrics

class DashboardView(LoginRequiredMixin, DetailView):
    template_name = 'bookkeeping/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get key financial metrics
        context['metrics'] = calculate_business_metrics(user)
        
        # Get recent transactions
        context['recent_transactions'] = Transaction.objects.filter(
            user=user
        ).order_by('-date')[:5]
        
        # Get account balances
        context['account_balances'] = Account.objects.filter(
            user=user,
            is_active=True
        ).annotate(
            balance=Sum(
                F('transactionline__debit_amount') - F('transactionline__credit_amount')
            )
        )
        
        return context

class TransactionListView(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = 'bookkeeping/transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 20
    
    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user).order_by('-date')

class TransactionCreateView(LoginRequiredMixin, CreateView):
    model = Transaction
    form_class = TransactionForm
    template_name = 'bookkeeping/transaction_form.html'
    success_url = reverse_lazy('transaction-list')
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class FinancialReportView(LoginRequiredMixin, DetailView):
    template_name = 'bookkeeping/financial_reports.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['trial_balance'] = generate_trial_balance(self.request.user)
        context['balance_sheet'] = self.generate_balance_sheet()
        context['income_statement'] = self.generate_income_statement()
        return context 