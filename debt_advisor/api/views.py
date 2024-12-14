from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ..services import DebtAdvisorService
from ..models import Message, UserProgress
from ..services.gamification_service import GamificationService

class ConversationViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def create(self, request):
        """Handle new message from user"""
        user_message = request.data.get('message')
        if not user_message:
            return Response(
                {'error': 'Message is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        advisor = DebtAdvisorService(request.user)
        response = advisor.get_response(user_message)
        
        return Response({
            'response': response,
            'achievements': self._check_achievements(request.user)
        })
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get conversation history"""
        messages = Message.objects.filter(
            session__user=request.user
        ).order_by('-timestamp')[:50]
        
        return Response({
            'messages': [
                {
                    'content': msg.content,
                    'is_user': msg.is_user,
                    'timestamp': msg.timestamp,
                    'type': msg.message_type
                }
                for msg in messages
            ]
        })
    
    def _check_achievements(self, user):
        progress = UserProgress.objects.get_or_create(user=user)[0]
        return progress.achievements 

class GamificationViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Get user's gamification status"""
        service = GamificationService(request.user)
        level = service.get_user_level()
        
        return Response({
            'level': {
                'name': level.name,
                'number': level.level_number,
                'icon': level.icon,
                'perks': level.perks
            },
            'points': service._calculate_total_points(),
            'available_rewards': self._format_rewards(service.get_available_rewards()),
            'active_challenges': self._format_challenges(service.get_active_challenges())
        })
    
    @action(detail=False, methods=['post'])
    def redeem_reward(self, request):
        """Redeem a reward"""
        reward_id = request.data.get('reward_id')
        if not reward_id:
            return Response(
                {'error': 'reward_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        service = GamificationService(request.user)
        success, message = service.redeem_reward(reward_id)
        
        return Response({
            'success': success,
            'message': message
        })
    
    @action(detail=False, methods=['post'])
    def join_challenge(self, request):
        """Join a new challenge"""
        challenge_id = request.data.get('challenge_id')
        if not challenge_id:
            return Response(
                {'error': 'challenge_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        service = GamificationService(request.user)
        service.join_challenge(challenge_id)
        
        return Response({'message': 'Successfully joined challenge'})
    
    @action(detail=True, methods=['post'])
    def update_progress(self, request, pk=None):
        """Update challenge progress"""
        progress_data = request.data.get('progress')
        if not progress_data:
            return Response(
                {'error': 'progress data is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        service = GamificationService(request.user)
        service.update_challenge_progress(pk, progress_data)
        
        return Response({'message': 'Progress updated successfully'})