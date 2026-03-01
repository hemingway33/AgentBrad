from django.views.generic import ListView, CreateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, F
from django.urls import reverse_lazy
from .models import Account, Transaction, TransactionLine, FinancialStatement
from .forms import TransactionForm, TransactionLineInlineFormSet
from .utils import generate_trial_balance
from .metrics import BusinessMetrics


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'bookkeeping/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        metrics = BusinessMetrics(user)
        context['metrics'] = metrics.get_all_metrics()

        context['recent_transactions'] = Transaction.objects.filter(
            user=user
        ).order_by('-date')[:5]

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
    success_url = reverse_lazy('bookkeeping:transaction-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['lines_formset'] = TransactionLineInlineFormSet(self.request.POST)
        else:
            context['lines_formset'] = TransactionLineInlineFormSet()
        return context

    def form_valid(self, form):
        form.instance.user = self.request.user
        context = self.get_context_data()
        lines_formset = context['lines_formset']
        if lines_formset.is_valid():
            self.object = form.save()
            lines_formset.instance = self.object
            lines_formset.save()
            return super().form_valid(form)
        return self.form_invalid(form)


class FinancialReportView(LoginRequiredMixin, TemplateView):
    template_name = 'bookkeeping/financial_reports.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['trial_balance'] = generate_trial_balance(user)

        accounts = Account.objects.filter(user=user, is_active=True).annotate(
            balance=Sum(
                F('transactionline__debit_amount') - F('transactionline__credit_amount')
            )
        )
        context['assets'] = accounts.filter(account_type='ASSET')
        context['liabilities'] = accounts.filter(account_type='LIABILITY')
        context['equity'] = accounts.filter(account_type='EQUITY')
        context['revenue'] = accounts.filter(account_type='REVENUE')
        context['expenses'] = accounts.filter(account_type='EXPENSE')

        return context


class MetricsView(LoginRequiredMixin, TemplateView):
    template_name = 'bookkeeping/metrics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        metrics = BusinessMetrics(self.request.user)
        context['metrics'] = metrics.get_all_metrics()
        return context


class IntegrationsView(LoginRequiredMixin, TemplateView):
    template_name = 'bookkeeping/integrations.html'
