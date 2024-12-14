from abc import ABC, abstractmethod

class AccountingSoftwareIntegration(ABC):
    def __init__(self, user, credentials):
        self.user = user
        self.credentials = credentials

    @abstractmethod
    def authenticate(self):
        pass

    @abstractmethod
    def sync_accounts(self):
        pass

    @abstractmethod
    def sync_transactions(self):
        pass

    @abstractmethod
    def sync_contacts(self):
        pass 