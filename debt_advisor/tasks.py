from celery import shared_task
from django.contrib.auth.models import User
from .services.reminder_service import ReminderService
from .services.achievement_service import AchievementService

@shared_task
def process_daily_checks():
    users = User.objects.filter(is_active=True)
    for user in users:
        # Process reminders
        reminder_service = ReminderService(user)
        reminder_service.send_due_reminders()
        
        # Check achievements
        achievement_service = AchievementService(user)
        achievement_service.check_achievements() 