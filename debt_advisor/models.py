from django.db import models
from django.contrib.auth.models import User
from debt_manager.models import DebtAccount

class ConversationSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    context = models.JSONField(default=dict)  # Stores session context
    
    def __str__(self):
        return f"Session with {self.user.username} at {self.start_time}"

class Message(models.Model):
    session = models.ForeignKey(ConversationSession, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    content = models.TextField()
    is_user = models.BooleanField(default=True)
    message_type = models.CharField(max_length=50, choices=[
        ('GENERAL', 'General Discussion'),
        ('ADVICE', 'Financial Advice'),
        ('REMINDER', 'Payment Reminder'),
        ('ENCOURAGEMENT', 'Encouragement'),
        ('ALERT', 'Alert'),
    ])
    
    def __str__(self):
        return f"{'User' if self.is_user else 'Bot'}: {self.content[:50]}"

class FinancialAdvice(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    category = models.CharField(max_length=50, choices=[
        ('DEBT_MANAGEMENT', 'Debt Management'),
        ('BUDGETING', 'Budgeting'),
        ('SAVING', 'Saving'),
        ('CREDIT_SCORE', 'Credit Score'),
        ('REFINANCING', 'Refinancing'),
    ])
    tags = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title

class UserProgress(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    last_interaction = models.DateTimeField(auto_now=True)
    mood_score = models.IntegerField(default=5)  # 1-10 scale
    engagement_level = models.CharField(max_length=20, choices=[
        ('HIGH', 'High'),
        ('MEDIUM', 'Medium'),
        ('LOW', 'Low'),
    ])
    achievements = models.JSONField(default=list)
    
    def __str__(self):
        return f"Progress for {self.user.username}" 

class Achievement(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=50)  # Font Awesome icon name
    points = models.IntegerField(default=10)
    category = models.CharField(max_length=50, choices=[
        ('DEBT_REDUCTION', 'Debt Reduction'),
        ('SAVING', 'Saving'),
        ('BUDGETING', 'Budgeting'),
        ('ENGAGEMENT', 'Engagement'),
        ('MILESTONE', 'Milestone'),
    ])
    
    def __str__(self):
        return self.name

class UserAchievement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'achievement']

class Reminder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    message = models.TextField()
    scheduled_time = models.DateTimeField()
    repeat_interval = models.CharField(max_length=50, choices=[
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('CUSTOM', 'Custom'),
    ])
    is_active = models.BooleanField(default=True)
    last_sent = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.title} for {self.user.username}" 

class Reward(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    points_required = models.IntegerField()
    reward_type = models.CharField(max_length=50, choices=[
        ('PREMIUM_FEATURE', 'Premium Feature Access'),
        ('FINANCIAL_TOOL', 'Financial Tool'),
        ('CONSULTATION', 'Expert Consultation'),
        ('BADGE', 'Special Badge'),
        ('DISCOUNT', 'Partner Discount'),
    ])
    is_active = models.BooleanField(default=True)
    duration_days = models.IntegerField(default=30)  # How long the reward lasts
    
    def __str__(self):
        return f"{self.name} ({self.points_required} points)"

class UserReward(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reward = models.ForeignKey(Reward, on_delete=models.CASCADE)
    redeemed_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user.username}'s {self.reward.name}"

class Level(models.Model):
    name = models.CharField(max_length=50)
    level_number = models.IntegerField(unique=True)
    points_required = models.IntegerField()
    icon = models.CharField(max_length=50)  # Font Awesome icon
    perks = models.JSONField(default=list)
    
    def __str__(self):
        return f"Level {self.level_number}: {self.name}"

class Challenge(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    points_reward = models.IntegerField()
    duration_days = models.IntegerField()
    challenge_type = models.CharField(max_length=50, choices=[
        ('SAVINGS', 'Save Amount'),
        ('DEBT_PAYMENT', 'Pay Extra Debt'),
        ('BUDGET', 'Stay Under Budget'),
        ('STREAK', 'Maintain Streak'),
        ('EDUCATION', 'Complete Education'),
    ])
    requirements = models.JSONField()  # Stores challenge-specific requirements
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.title

class UserChallenge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    progress = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=[
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ])
    
    def __str__(self):
        return f"{self.user.username}'s {self.challenge.title}"