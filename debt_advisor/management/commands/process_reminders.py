from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from debt_advisor.services.reminder_service import ReminderService

class Command(BaseCommand):
    help = 'Process and send due reminders'

    def handle(self, *args, **options):
        users = User.objects.filter(is_active=True)
        for user in users:
            reminder_service = ReminderService(user)
            reminder_service.send_due_reminders()
        
        self.stdout.write(self.style.SUCCESS('Successfully processed reminders')) 