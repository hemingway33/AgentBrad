from sage_one import SageOne
from .base import AccountingSoftwareIntegration

class SageIntegration(AccountingSoftwareIntegration):
    def authenticate(self):
        self.client = SageOne(
            client_id=self.credentials['client_id'],
            client_secret=self.credentials['client_secret'],
            access_token=self.credentials['access_token']
        )
    
    def sync_accounts(self):
        accounts = self.client.accounts.all()
        # Implementation similar to other integrations 