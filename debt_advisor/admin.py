from django.contrib import admin
from .models import (
    ConversationSession, Message, FinancialAdvice, UserProgress,
    Achievement, UserAchievement, Reminder, Reward, UserReward,
    Level, Challenge, UserChallenge,
)


@admin.register(ConversationSession)
class ConversationSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'start_time', 'end_time')
    list_filter = ('start_time',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'is_user', 'message_type', 'timestamp')
    list_filter = ('message_type', 'is_user')


@admin.register(FinancialAdvice)
class FinancialAdviceAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'created_at')
    list_filter = ('category',)
    search_fields = ('title',)


@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'points', 'mood_score', 'engagement_level', 'last_interaction')


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'points')
    list_filter = ('category',)


@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ('user', 'achievement', 'earned_at')


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'scheduled_time', 'repeat_interval', 'is_active')
    list_filter = ('repeat_interval', 'is_active')


@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    list_display = ('name', 'reward_type', 'points_required', 'is_active')
    list_filter = ('reward_type', 'is_active')


@admin.register(UserReward)
class UserRewardAdmin(admin.ModelAdmin):
    list_display = ('user', 'reward', 'redeemed_at', 'expires_at', 'is_active')


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ('level_number', 'name', 'points_required')
    ordering = ('level_number',)


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ('title', 'challenge_type', 'points_reward', 'duration_days', 'is_active')
    list_filter = ('challenge_type', 'is_active')


@admin.register(UserChallenge)
class UserChallengeAdmin(admin.ModelAdmin):
    list_display = ('user', 'challenge', 'status', 'start_date', 'end_date')
    list_filter = ('status',)
