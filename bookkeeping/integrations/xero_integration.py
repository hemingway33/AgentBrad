from xero import Xero
from xero.auth import OAuth2Credentials
from .base import AccountingSoftwareIntegration
from ..models import Account, Transaction, TransactionLine

class XeroIntegration(AccountingSoftwareIntegration):
    def authenticate(self):
        self.credentials = OAuth2Credentials(
            client_id=self.credentials['client_id'],
            client_secret=self.credentials['client_secret'],
            callback_uri=self.credentials['callback_uri']
        )
        self.xero = Xero(self.credentials)
    
    def sync_accounts(self):
        accounts = self.xero.accounts.all()
        for account in accounts:
            Account.objects.update_or_create(
                user=self.user,
                external_id=account['AccountID'],
                defaults={
                    'name': account['Name'],
                    'account_type': self._map_account_type(account['Type']),
                    'account_number': account.get('Code', ''),
                    'description': account.get('Description', ''),
                }
            ) 