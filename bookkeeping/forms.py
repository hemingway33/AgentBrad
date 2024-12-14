from django import forms
from .models import Transaction, TransactionLine, Account

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['date', 'reference_number', 'description', 'status']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

class TransactionLineFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        total_debits = sum(form.cleaned_data.get('debit_amount', 0) 
                          for form in self.forms if form.cleaned_data)
        total_credits = sum(form.cleaned_data.get('credit_amount', 0) 
                          for form in self.forms if form.cleaned_data)
        
        if total_debits != total_credits:
            raise forms.ValidationError("Total debits must equal total credits")

TransactionLineInlineFormSet = forms.inlineformset_factory(
    Transaction,
    TransactionLine,
    formset=TransactionLineFormSet,
    fields=('account', 'description', 'debit_amount', 'credit_amount'),
    extra=2,
    can_delete=True
) 