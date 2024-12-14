from decimal import Decimal
from .models import Account, Transaction, TransactionLine

def calculate_account_balance(account, as_of_date=None):
    """Calculate the balance of an account as of a specific date"""
    query = TransactionLine.objects.filter(account=account)
    if as_of_date:
        query = query.filter(transaction__date__lte=as_of_date)
    
    debits = query.aggregate(total=models.Sum('debit_amount'))['total'] or Decimal('0')
    credits = query.aggregate(total=models.Sum('credit_amount'))['total'] or Decimal('0')
    
    if account.account_type in ['ASSET', 'EXPENSE']:
        return debits - credits
    return credits - debits

def generate_trial_balance(user, as_of_date=None):
    """Generate a trial balance report"""
    accounts = Account.objects.filter(user=user, is_active=True)
    trial_balance = []
    
    for account in accounts:
        balance = calculate_account_balance(account, as_of_date)
        if balance != 0:
            trial_balance.append({
                'account': account,
                'debit': balance if balance > 0 else Decimal('0'),
                'credit': abs(balance) if balance < 0 else Decimal('0'),
            })
    
    return trial_balance 