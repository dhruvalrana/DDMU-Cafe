"""
API Views for the POS Virtual Assistant chatbot.
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from decimal import Decimal

from .models import ChatSession, ChatMessage, RecommendationLog
from .serializers import (
    ChatInputSerializer,
    ChatResponseSerializer,
    ChatSessionSerializer,
    QuickActionSerializer,
)
from .services import recommendation_engine
from apps.products.models import Category


class ChatbotView(APIView):
    """
    Main chatbot API endpoint.
    Handles user messages and returns AI-powered recommendations.
    """
    permission_classes = [AllowAny]  # Allow both authenticated and anonymous users
    
    def post(self, request):
        """
        Process a chat message and return recommendations.
        """
        serializer = ChatInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        message = data['message']
        session_id = data.get('session_id')
        group_size = data.get('group_size')
        dietary_preferences = data.get('dietary_preferences', [])
        category_id = data.get('category_id')
        budget = data.get('budget')
        
        # Get or create chat session
        session = None
        if session_id:
            try:
                session = ChatSession.objects.get(id=session_id, is_active=True)
                # Update session with new preferences if provided
                if group_size:
                    session.group_size = group_size
                if dietary_preferences:
                    session.dietary_preferences = dietary_preferences
                session.save()
            except ChatSession.DoesNotExist:
                session = None
        
        if not session:
            session = ChatSession.objects.create(
                user=request.user if request.user.is_authenticated else None,
                session_key=request.session.session_key or '',
                group_size=group_size,
                dietary_preferences=dietary_preferences
            )
        
        # Use session values if not provided in request
        if not group_size and session.group_size:
            group_size = session.group_size
        if not dietary_preferences and session.dietary_preferences:
            dietary_preferences = session.dietary_preferences
        
        # Save user message
        ChatMessage.objects.create(
            session=session,
            message_type='user',
            content=message
        )
        
        # Generate recommendation using AI engine
        recommendation = recommendation_engine.generate_recommendation(
            query=message,
            group_size=group_size,
            dietary_preferences=dietary_preferences,
            category_id=str(category_id) if category_id else None,
            budget=budget
        )
        
        # Log recommendations
        for rec in recommendation.get('recommendations', []):
            if 'product_id' in rec:
                try:
                    RecommendationLog.objects.create(
                        session=session,
                        product_id=rec['product_id'],
                        reason=rec.get('reason', '')
                    )
                except Exception:
                    pass  # Don't fail if logging fails
        
        # Save assistant message
        ChatMessage.objects.create(
            session=session,
            message_type='assistant',
            content=recommendation['message'],
            recommended_products=[
                {'id': r.get('product_id'), 'name': r.get('name')}
                for r in recommendation.get('recommendations', [])
            ]
        )
        
        # Prepare response
        response_data = {
            'session_id': str(session.id),
            'message': recommendation['message'],
            'recommendations': recommendation.get('recommendations', []),
            'follow_up_questions': recommendation.get('follow_up_questions', []),
            'total_estimated_price': float(recommendation.get('total_estimated_price', 0)),
        }
        
        return Response(response_data)
    
    def get(self, request):
        """
        Get initial chatbot greeting and quick actions.
        """
        categories = Category.objects.filter(
            is_active=True,
            is_deleted=False
        ).order_by('display_order')[:6]
        
        category_list = [
            {'id': str(c.id), 'name': c.name, 'color': c.color}
            for c in categories
        ]
        
        return Response({
            'greeting': "👋 Welcome to DDMU Cafe! I'm your virtual assistant. How can I help you today?",
            'quick_actions': [
                {'action': 'group_order', 'label': '👥 Order for Team', 'icon': 'users'},
                {'action': 'combos', 'label': '🎁 Combo Deals', 'icon': 'gift'},
                {'action': 'popular', 'label': '⭐ Popular Items', 'icon': 'star'},
                {'action': 'menu', 'label': '📋 Full Menu', 'icon': 'menu'},
            ],
            'categories': category_list,
            'suggestions': [
                "What's best for a team of 5?",
                "Show me today's specials",
                "Vegetarian options please",
                "I need combo deals"
            ]
        })


class QuickActionView(APIView):
    """
    Handle quick action button clicks.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Process a quick action and return recommendations.
        """
        serializer = QuickActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        action = data['action']
        group_size = data.get('group_size')
        session_id = data.get('session_id')
        
        # Map action to query
        action_queries = {
            'group_order': f"Order for a team of {group_size or 4} people",
            'combos': "Show me combo deals and meal packages",
            'popular': "What are your most popular items?",
            'menu': "Show me the full menu",
            'vegetarian': "Show me vegetarian options",
            'drinks': "What drinks do you have?",
            'desserts': "Show me desserts",
        }
        
        query = action_queries.get(action, "Show me the menu")
        
        # Get or create session
        session = None
        if session_id:
            try:
                session = ChatSession.objects.get(id=session_id, is_active=True)
            except ChatSession.DoesNotExist:
                pass
        
        if not session:
            session = ChatSession.objects.create(
                user=request.user if request.user.is_authenticated else None,
                session_key=request.session.session_key or '',
                group_size=group_size
            )
        
        # Handle vegetarian as dietary preference
        dietary_preferences = []
        if action == 'vegetarian':
            dietary_preferences = ['vegetarian']
        
        # Generate recommendation
        recommendation = recommendation_engine.generate_recommendation(
            query=query,
            group_size=group_size,
            dietary_preferences=dietary_preferences
        )
        
        return Response({
            'session_id': str(session.id),
            'message': recommendation['message'],
            'recommendations': recommendation.get('recommendations', []),
            'follow_up_questions': recommendation.get('follow_up_questions', []),
            'total_estimated_price': float(recommendation.get('total_estimated_price', 0)),
        })


class ChatHistoryView(APIView):
    """
    Retrieve chat history for a session.
    """
    permission_classes = [AllowAny]
    
    def get(self, request, session_id):
        """
        Get chat history for a specific session.
        """
        try:
            session = ChatSession.objects.get(id=session_id)
            serializer = ChatSessionSerializer(session)
            return Response(serializer.data)
        except ChatSession.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class CategoryMenuView(APIView):
    """
    Get menu items by category for the chatbot.
    """
    permission_classes = [AllowAny]
    
    def get(self, request, category_id=None):
        """
        Get products for a specific category.
        """
        products = recommendation_engine.get_active_products(
            category_id=str(category_id) if category_id else None
        )
        
        product_list = [
            {
                'id': str(p.id),
                'name': p.name,
                'description': p.description,
                'price': float(p.price),
                'image': p.image.url if p.image else None,
                'category': p.category.name if p.category else None,
                'is_combo': p.is_combo,
                'has_variants': p.has_variants,
                'in_stock': recommendation_engine.check_stock_availability(p),
            }
            for p in products
        ]
        
        return Response({
            'products': product_list,
            'count': len(product_list)
        })
