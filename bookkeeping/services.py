from intuitlib.client import AuthClient
from intuitlib.enums import Scopes
from quickbooks import QuickBooks
from quickbooks.objects.account import Account as QBAccount
from quickbooks.objects.bill import Bill
from quickbooks.objects.invoice import Invoice
from .models import Account, Transaction, TransactionLine, QuickBooksIntegration

class QuickBooksService:
    def __init__(self, user):
        self.user = user
        self.integration = QuickBooksIntegration.objects.get(user=user)
        self.client = self._get_client()
    
    def _get_client(self):
        auth_client = AuthClient(
            client_id=settings.QUICKBOOKS_CLIENT_ID,
            client_secret=settings.QUICKBOOKS_CLIENT_SECRET,
            redirect_uri=settings.QUICKBOOKS_REDIRECT_URI,
            environment=settings.QUICKBOOKS_ENVIRONMENT,
        )
        auth_client.access_token = self.integration.access_token
        auth_client.refresh_token = self.integration.refresh_token
        
        return QuickBooks(
            auth_client=auth_client,
            refresh_token=self.integration.refresh_token,
            company_id=self.integration.realm_id
        )
    
    def sync_accounts(self):
        """Sync QuickBooks accounts with local accounts"""
        qb_accounts = QBAccount.all(qb=self.client)
        
        for qb_account in qb_accounts:
            Account.objects.update_or_create(
                user=self.user,
                account_number=qb_account.AcctNum,
                defaults={
                    'name': qb_account.Name,
                    'account_type': self._map_account_type(qb_account.AccountType),
                    'description': qb_account.Description or '',
                }
            )
    
    def sync_transactions(self, start_date=None):
        """Sync QuickBooks transactions with local transactions"""
        # Implement transaction sync logic here
        pass
    
    def _map_account_type(self, qb_account_type):
        """Map QuickBooks account types to local account types"""
        mapping = {
            'Asset': 'ASSET',
            'Liability': 'LIABILITY',
            'Equity': 'EQUITY',
            'Income': 'REVENUE',
            'Expense': 'EXPENSE',
        }
        return mapping.get(qb_account_type, 'ASSET') 