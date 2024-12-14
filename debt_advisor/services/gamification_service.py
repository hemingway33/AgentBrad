from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Sum
from ..models import (
    UserProgress, Level, Challenge, UserChallenge,
    Reward, UserReward, Achievement, UserAchievement
)

class GamificationService:
    def __init__(self, user):
        self.user = user
        self.progress = UserProgress.objects.get_or_create(user=user)[0]

    def get_user_level(self):
        """Get user's current level based on total points"""
        total_points = self._calculate_total_points()
        return Level.objects.filter(
            points_required__lte=total_points
        ).order_by('-points_required').first()

    def get_available_rewards(self):
        """Get rewards that user can redeem"""
        total_points = self._calculate_total_points()
        return Reward.objects.filter(
            points_required__lte=total_points,
            is_active=True
        ).exclude(
            userreward__user=self.user,
            userreward__is_active=True
        )

    def redeem_reward(self, reward_id):
        """Redeem a reward if user has enough points"""
        reward = Reward.objects.get(id=reward_id)
        total_points = self._calculate_total_points()
        
        if total_points >= reward.points_required:
            expires_at = timezone.now() + timedelta(days=reward.duration_days)
            UserReward.objects.create(
                user=self.user,
                reward=reward,
                expires_at=expires_at
            )
            return True, "Reward redeemed successfully!"
        return False, "Not enough points to redeem this reward."

    def get_active_challenges(self):
        """Get user's active challenges"""
        return UserChallenge.objects.filter(
            user=self.user,
            status='ACTIVE'
        )

    def join_challenge(self, challenge_id):
        """Join a new challenge"""
        challenge = Challenge.objects.get(id=challenge_id)
        end_date = timezone.now() + timedelta(days=challenge.duration_days)
        
        UserChallenge.objects.create(
            user=self.user,
            challenge=challenge,
            end_date=end_date,
            status='ACTIVE'
        )

    def update_challenge_progress(self, user_challenge_id, progress_data):
        """Update progress for a challenge"""
        user_challenge = UserChallenge.objects.get(
            id=user_challenge_id,
            user=self.user
        )
        
        user_challenge.progress.update(progress_data)
        user_challenge.save()
        
        if self._check_challenge_completion(user_challenge):
            self._complete_challenge(user_challenge)

    def _calculate_total_points(self):
        """Calculate total points from achievements and challenges"""
        achievement_points = UserAchievement.objects.filter(
            user=self.user
        ).aggregate(
            total=Sum('achievement__points')
        )['total'] or 0
        
        challenge_points = UserChallenge.objects.filter(
            user=self.user,
            status='COMPLETED'
        ).aggregate(
            total=Sum('challenge__points_reward')
        )['total'] or 0
        
        return achievement_points + challenge_points

    def _check_challenge_completion(self, user_challenge):
        """Check if challenge requirements are met"""
        requirements = user_challenge.challenge.requirements
        progress = user_challenge.progress
        
        if user_challenge.challenge.challenge_type == 'SAVINGS':
            return progress.get('saved_amount', 0) >= requirements.get('target_amount', 0)
        elif user_challenge.challenge.challenge_type == 'DEBT_PAYMENT':
            return progress.get('extra_payment', 0) >= requirements.get('target_amount', 0)
        # Add other challenge type checks
        return False

    def _complete_challenge(self, user_challenge):
        """Mark challenge as completed and award points"""
        user_challenge.status = 'COMPLETED'
        user_challenge.save()
        
        # Update user progress
        self.progress.points += user_challenge.challenge.points_reward
        self.progress.save() 