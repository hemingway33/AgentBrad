from datetime import datetime, timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from ..models import Reminder, DebtAccount

class ReminderService:
    def __init__(self, user):
        self.user = user

    def create_payment_reminders(self):
        """Create reminders for upcoming debt payments"""
        debts = DebtAccount.objects.filter(user=self.user)
        
        for debt in debts:
            # Create reminder 3 days before due date
            reminder_date = debt.due_date - timedelta(days=3)
            Reminder.objects.get_or_create(
                user=self.user,
                title=f"Payment Due: {debt.name}",
                message=f"Your payment of ${debt.minimum_payment} for {debt.name} is due in 3 days.",
                scheduled_time=reminder_date,
                repeat_interval='MONTHLY'
            )

    def create_check_in_reminder(self):
        """Create weekly check-in reminder"""
        next_check_in = timezone.now() + timedelta(days=7)
        Reminder.objects.get_or_create(
            user=self.user,
            title="Weekly Financial Check-in",
            message="Time for your weekly financial review! Let's check your progress.",
            scheduled_time=next_check_in,
            repeat_interval='WEEKLY'
        )

    def send_due_reminders(self):
        """Send all due reminders"""
        now = timezone.now()
        due_reminders = Reminder.objects.filter(
            user=self.user,
            scheduled_time__lte=now,
            is_active=True
        )
        
        for reminder in due_reminders:
            self._send_reminder(reminder)
            self._update_reminder_schedule(reminder)

    def _send_reminder(self, reminder):
        """Send reminder via email and in-app notification"""
        # Send email
        send_mail(
            subject=reminder.title,
            message=reminder.message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[self.user.email],
        )
        
        # Create in-app notification
        Message.objects.create(
            session=self._get_active_session(),
            content=reminder.message,
            is_user=False,
            message_type='REMINDER'
        )
        
        reminder.last_sent = timezone.now()
        reminder.save()

    def _update_reminder_schedule(self, reminder):
        """Update reminder schedule based on repeat interval"""
        if reminder.repeat_interval == 'DAILY':
            reminder.scheduled_time += timedelta(days=1)
        elif reminder.repeat_interval == 'WEEKLY':
            reminder.scheduled_time += timedelta(weeks=1)
        elif reminder.repeat_interval == 'MONTHLY':
            reminder.scheduled_time += timedelta(days=30)
        reminder.save() 