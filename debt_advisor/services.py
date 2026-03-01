import openai
from django.conf import settings
from datetime import datetime, timedelta
from .models import ConversationSession, Message, FinancialAdvice, UserProgress
from debt_manager.models import DebtAccount, DebtPaymentPlan
from budget_tracker.models import Expense
from debt_advisor.services.achievement_service import AchievementService
from debt_advisor.services.reminder_service import ReminderService


class DebtAdvisorService:
    def __init__(self, user):
        self.user = user
        self.session = self._get_or_create_session()
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

    def _get_or_create_session(self):
        active_session = ConversationSession.objects.filter(
            user=self.user,
            end_time__isnull=True
        ).first()

        if not active_session:
            active_session = ConversationSession.objects.create(
                user=self.user,
                context=self._get_initial_context()
            )

        return active_session

    def _get_initial_context(self):
        """Gather user's financial context"""
        debts = DebtAccount.objects.filter(user=self.user)
        total_debt = sum(debt.balance for debt in debts)
        recent_expenses = Expense.objects.filter(
            user=self.user,
            date__gte=datetime.now() - timedelta(days=30)
        )

        return {
            'total_debt': float(total_debt),
            'num_debts': debts.count(),
            'recent_spending': float(sum(exp.amount for exp in recent_expenses)),
            'last_interaction': datetime.now().isoformat(),
        }

    def get_response(self, user_message):
        """Generate response using OpenAI API"""
        # Store user message
        Message.objects.create(
            session=self.session,
            content=user_message,
            is_user=True,
            message_type='GENERAL'
        )

        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": user_message}
        ]

        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=150
        )

        return self._process_response(response.choices[0].message.content)

    def _get_system_prompt(self):
        """Create system prompt based on user's financial situation"""
        context = self.session.context
        return (
            f"You are a supportive and knowledgeable financial advisor. "
            f"The user has {context['num_debts']} debts totaling ${context['total_debt']}. "
            f"Be encouraging but realistic. Focus on practical advice and emotional support. "
            f"Avoid technical jargon unless specifically asked."
        )

    def _process_response(self, response_text):
        """Process and store the response"""
        message_type = self._classify_message(response_text)

        Message.objects.create(
            session=self.session,
            content=response_text,
            is_user=False,
            message_type=message_type
        )

        return response_text

    def _classify_message(self, text):
        """Classify message type for tracking purposes"""
        text_lower = text.lower()
        if "reminder" in text_lower:
            return "REMINDER"
        if "congratulations" in text_lower:
            return "ENCOURAGEMENT"
        if "suggest" in text_lower:
            return "ADVICE"
        return "GENERAL"

    def check_achievements(self):
        """Check and award achievements"""
        achievement_service = AchievementService(self.user)
        new_achievements = achievement_service.check_achievements()

        if new_achievements:
            achievement_messages = [
                f"Congratulations! You've earned the '{a.name}' achievement: {a.description}"
                for a in new_achievements
            ]
            return achievement_messages
        return []

    def schedule_check_ins(self):
        """Schedule regular check-ins"""
        reminder_service = ReminderService(self.user)
        reminder_service.create_check_in_reminder()
        reminder_service.create_payment_reminders()
