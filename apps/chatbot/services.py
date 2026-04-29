"""
AI-powered recommendation engine for the POS Virtual Assistant.
Analyzes menu data and provides intelligent recommendations.
"""

import re
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from django.db.models import Count, Avg, Sum, Q
from apps.products.models import (
    Category,
    Product,
    ProductVariant,
    ComboProduct,
    ProductModifier,
)
from apps.orders.models import Order, OrderLine


class MenuRecommendationEngine:
    """
    AI-powered engine for menu recommendations.
    Provides intelligent suggestions based on group size, preferences, and menu data.
    """
    
    # Dietary preference keywords mapping
    DIETARY_KEYWORDS = {
        'vegetarian': ['veg', 'vegetarian', 'veggie', 'plant-based'],
        'vegan': ['vegan', 'plant-based', 'dairy-free'],
        'gluten-free': ['gluten-free', 'gluten free', 'celiac'],
        'halal': ['halal'],
        'spicy': ['spicy', 'hot', 'chili'],
        'mild': ['mild', 'not spicy', 'no spice'],
        'healthy': ['healthy', 'light', 'low-calorie', 'diet'],
        'kids': ['kids', 'children', 'child-friendly'],
    }
    
    # Category type suggestions for balanced meals
    MEAL_STRUCTURE = {
        'starter': ['appetizers', 'starters', 'snacks', 'soups', 'salads', 'sandwich', 'sandwiches'],
        'main': ['main course', 'entrees', 'mains', 'burgers', 'pizza', 'pasta', 'rice', 'breakfast'],
        'side': ['sides', 'accompaniments', 'extras', 'bakery'],
        'drink': ['drinks', 'beverages', 'coffee', 'tea', 'juice', 'juices', 'sodas', 'hot beverages', 'cold beverages'],
        'dessert': ['desserts', 'dessert', 'desert', 'sweets', 'ice cream', 'cakes'],
    }
    
    def __init__(self):
        self.products_cache = None
        self.categories_cache = None
    
    def get_active_products(self, category_id: Optional[str] = None) -> List[Product]:
        """Get all active products available for POS."""
        queryset = Product.objects.filter(
            is_active=True,
            is_deleted=False,
            is_available_for_pos=True
        ).select_related('category').prefetch_related(
            'variants', 'modifiers', 'combo_items'
        )
        
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        return list(queryset)
    
    def get_active_categories(self) -> List[Category]:
        """Get all active categories."""
        return list(Category.objects.filter(
            is_active=True,
            is_deleted=False
        ).order_by('display_order'))
    
    def check_stock_availability(self, product: Product) -> bool:
        """Check if a product has sufficient stock."""
        if not product.track_inventory:
            return True
        return product.stock_quantity > product.low_stock_threshold
    
    def get_combo_products(self) -> List[Product]:
        """Get all combo/meal deal products."""
        return list(Product.objects.filter(
            is_active=True,
            is_deleted=False,
            is_available_for_pos=True,
            is_combo=True
        ).prefetch_related('combo_items__product'))
    
    def get_products_with_variants(self) -> List[Product]:
        """Get products with variants for variety."""
        return list(Product.objects.filter(
            is_active=True,
            is_deleted=False,
            is_available_for_pos=True,
            has_variants=True
        ).prefetch_related('variants'))
    
    def get_popular_products(self, limit: int = 10) -> List[Dict]:
        """Get most ordered products based on order history."""
        popular = OrderLine.objects.filter(
            order__status__in=['served', 'paid']
        ).values('product_id', 'product_name').annotate(
            order_count=Count('id'),
            total_quantity=Sum('quantity')
        ).order_by('-order_count')[:limit]
        
        product_ids = [p['product_id'] for p in popular]
        products = Product.objects.filter(
            id__in=product_ids,
            is_active=True,
            is_available_for_pos=True
        )
        
        return list(products)
    
    def categorize_products_by_meal_type(self, products: List[Product]) -> Dict[str, List[Product]]:
        """Categorize products by meal structure (starter, main, etc.)."""
        categorized = {key: [] for key in self.MEAL_STRUCTURE.keys()}
        
        for product in products:
            if not product.category:
                continue
            
            category_name = product.category.name.lower()
            
            for meal_type, keywords in self.MEAL_STRUCTURE.items():
                if any(keyword in category_name for keyword in keywords):
                    categorized[meal_type].append(product)
                    break
        
        return categorized
    
    def filter_by_dietary_preferences(
        self,
        products: List[Product],
        preferences: List[str]
    ) -> List[Product]:
        """Filter products based on dietary preferences."""
        if not preferences:
            return products
        
        filtered = []
        for product in products:
            product_text = f"{product.name} {product.description}".lower()
            
            # Check if product matches preferences
            matches_all = True
            for pref in preferences:
                pref_keywords = self.DIETARY_KEYWORDS.get(pref.lower(), [pref.lower()])
                if not any(keyword in product_text for keyword in pref_keywords):
                    matches_all = False
                    break
            
            if matches_all:
                filtered.append(product)
        
        return filtered if filtered else products
    
    def calculate_group_quantities(
        self,
        group_size: int,
        products: List[Product]
    ) -> List[Dict]:
        """Calculate recommended quantities for group orders."""
        recommendations = []
        
        # Categorize products
        categorized = self.categorize_products_by_meal_type(products)
        
        # Appetizers/Starters: 1-2 items per 2-3 people
        starters = categorized.get('starter', [])
        if starters:
            starter_qty = max(1, (group_size + 1) // 2)
            for i, starter in enumerate(starters[:2]):
                recommendations.append({
                    'product': starter,
                    'quantity': 1 if i > 0 else starter_qty,
                    'reason': f"Perfect for sharing among {group_size} people"
                })
        
        # Main courses: 1 per person
        mains = categorized.get('main', [])
        if mains:
            recommendations.append({
                'product': mains[0],
                'quantity': group_size,
                'reason': "One main course per person"
            })
        
        # Drinks: 1 per person
        drinks = categorized.get('drink', [])
        if drinks:
            recommendations.append({
                'product': drinks[0],
                'quantity': group_size,
                'reason': "One drink per person"
            })
        
        # Desserts: 1 per 2 people (for sharing)
        desserts = categorized.get('dessert', [])
        if desserts:
            dessert_qty = max(1, (group_size + 1) // 2)
            recommendations.append({
                'product': desserts[0],
                'quantity': dessert_qty,
                'reason': "Perfect for sharing after the meal"
            })
        
        return recommendations
    
    def get_modifiers_suggestions(self, product: Product) -> List[ProductModifier]:
        """Get suggested modifiers for a product."""
        return list(product.modifiers.filter(is_active=True))
    
    def calculate_total_price(self, recommendations: List[Dict]) -> Decimal:
        """Calculate total estimated price for recommendations."""
        total = Decimal('0.00')
        for rec in recommendations:
            product = rec['product']
            quantity = rec['quantity']
            total += product.price * quantity
        return total
    
    def format_price(self, price: Decimal) -> str:
        """Format price for display."""
        return f"₹{price:,.2f}"
    
    def generate_recommendation(
        self,
        query: str,
        group_size: Optional[int] = None,
        dietary_preferences: Optional[List[str]] = None,
        category_id: Optional[str] = None,
        budget: Optional[Decimal] = None
    ) -> Dict:
        """
        Generate intelligent recommendations based on user query and context.
        
        Returns a structured response with recommendations.
        """
        response = {
            'message': '',
            'recommendations': [],
            'follow_up_questions': [],
            'total_estimated_price': Decimal('0.00'),
        }
        
        # Get available products
        products = self.get_active_products(category_id)
        
        # Filter out low stock items
        products = [p for p in products if self.check_stock_availability(p)]
        
        if not products:
            response['message'] = "I'm sorry, but there are no items available at the moment. Please check back later!"
            return response
        
        # Apply dietary filters
        if dietary_preferences:
            products = self.filter_by_dietary_preferences(products, dietary_preferences)
        
        # Analyze query intent
        query_lower = query.lower()
        
        # Check for group/team order
        if group_size or any(word in query_lower for word in ['team', 'group', 'party', 'people', 'friends']):
            if not group_size:
                # Try to extract group size from query
                numbers = re.findall(r'\d+', query)
                if numbers:
                    group_size = int(numbers[0])
                else:
                    response['message'] = "I'd love to help you order for your group! How many people will be dining?"
                    response['follow_up_questions'] = [
                        "2-3 people",
                        "4-6 people",
                        "7-10 people",
                        "More than 10"
                    ]
                    return response
            
            return self._generate_group_recommendation(products, group_size, budget)
        
        # Check for combo/deal requests
        if any(word in query_lower for word in ['combo', 'deal', 'meal', 'package', 'bundle']):
            return self._generate_combo_recommendation(budget)
        
        # Check for category-specific requests
        for meal_type, keywords in self.MEAL_STRUCTURE.items():
            if any(keyword in query_lower for keyword in keywords):
                return self._generate_category_recommendation(products, meal_type, group_size or 1)
        
        # Check for popular/best items
        if any(word in query_lower for word in ['popular', 'best', 'recommend', 'top', 'famous']):
            return self._generate_popular_recommendation(group_size or 1)
        
        # Default recommendation
        return self._generate_balanced_recommendation(products, group_size or 1, budget)
    
    def _generate_group_recommendation(
        self,
        products: List[Product],
        group_size: int,
        budget: Optional[Decimal] = None
    ) -> Dict:
        """Generate recommendations for a group order."""
        response = {
            'message': '',
            'recommendations': [],
            'follow_up_questions': [],
            'total_estimated_price': Decimal('0.00'),
        }
        
        # First, check for combo products
        combos = self.get_combo_products()
        
        if combos and group_size >= 2:
            # Recommend combos for groups
            best_combo = combos[0]
            combo_qty = max(1, group_size // 2)
            
            response['message'] = f"""🎉 Great choice ordering for {group_size} people! Here's what I recommend:

**For the best value and variety, I suggest:**"""
            
            response['recommendations'].append({
                'product_id': str(best_combo.id),
                'name': best_combo.name,
                'description': best_combo.description,
                'price': float(best_combo.price),
                'quantity': combo_qty,
                'category': best_combo.category.name if best_combo.category else 'Combos',
                'reason': f"Perfect combo meal for sharing - order {combo_qty} for your group",
                'is_combo': True,
                'modifiers': [
                    {'id': str(m.id), 'name': m.name, 'price': float(m.price)}
                    for m in best_combo.modifiers.filter(is_active=True)[:3]
                ]
            })
        
        # Add balanced meal recommendations
        categorized = self.categorize_products_by_meal_type(products)
        
        # Starters
        for starter in categorized.get('starter', [])[:2]:
            qty = max(1, (group_size + 2) // 3)
            response['recommendations'].append({
                'product_id': str(starter.id),
                'name': starter.name,
                'description': starter.description,
                'price': float(starter.price),
                'quantity': qty,
                'category': starter.category.name if starter.category else 'Appetizers',
                'reason': f"Shareable starter - {qty} servings for the table",
                'is_combo': False,
                'modifiers': [
                    {'id': str(m.id), 'name': m.name, 'price': float(m.price)}
                    for m in starter.modifiers.filter(is_active=True)[:3]
                ]
            })
        
        # Mains
        for main in categorized.get('main', [])[:3]:
            response['recommendations'].append({
                'product_id': str(main.id),
                'name': main.name,
                'description': main.description,
                'price': float(main.price),
                'quantity': max(1, group_size // 2),
                'category': main.category.name if main.category else 'Main Course',
                'reason': "Popular main course option",
                'is_combo': False,
                'has_variants': main.has_variants,
                'modifiers': [
                    {'id': str(m.id), 'name': m.name, 'price': float(m.price)}
                    for m in main.modifiers.filter(is_active=True)[:3]
                ]
            })
        
        # Drinks
        drinks = categorized.get('drink', [])
        if drinks:
            drink = drinks[0]
            response['recommendations'].append({
                'product_id': str(drink.id),
                'name': drink.name,
                'description': drink.description,
                'price': float(drink.price),
                'quantity': group_size,
                'category': drink.category.name if drink.category else 'Beverages',
                'reason': f"One refreshing drink per person ({group_size} total)",
                'is_combo': False,
                'modifiers': []
            })
        
        # Calculate total
        for rec in response['recommendations']:
            response['total_estimated_price'] += Decimal(str(rec['price'])) * rec['quantity']
        
        response['message'] = response.get('message', '') or f"""🎉 Perfect! Here's my recommendation for your team of {group_size}:"""
        
        response['message'] += f"""

**Estimated Total: {self.format_price(response['total_estimated_price'])}**

💡 **Pro tip:** Add some modifiers to customize your order!"""
        
        response['follow_up_questions'] = [
            "Show me vegetarian options",
            "Any dessert recommendations?",
            "What's popular today?",
            "Add extra toppings"
        ]
        
        return response
    
    def _generate_combo_recommendation(self, budget: Optional[Decimal] = None) -> Dict:
        """Generate combo/deal recommendations."""
        response = {
            'message': '',
            'recommendations': [],
            'follow_up_questions': [],
            'total_estimated_price': Decimal('0.00'),
        }
        
        combos = self.get_combo_products()
        
        if not combos:
            response['message'] = "We don't have specific combo meals right now, but I can help you build a great meal! What are you in the mood for?"
            response['follow_up_questions'] = [
                "Show me appetizers",
                "Best main courses",
                "Something light",
                "Full meal for 2"
            ]
            return response
        
        response['message'] = """🎁 **Here are our best combo deals:**

Get more value with our specially curated meal packages!"""
        
        for combo in combos[:5]:
            # Get combo items
            combo_items = combo.combo_items.all()
            items_list = ", ".join([f"{ci.quantity}x {ci.product.name}" for ci in combo_items[:3]])
            
            response['recommendations'].append({
                'product_id': str(combo.id),
                'name': combo.name,
                'description': combo.description or items_list,
                'price': float(combo.price),
                'quantity': 1,
                'category': 'Combo Meals',
                'reason': f"Includes: {items_list}" if items_list else "Great value combo",
                'is_combo': True,
                'combo_items': [
                    {'name': ci.product.name, 'quantity': ci.quantity}
                    for ci in combo_items
                ],
                'modifiers': [
                    {'id': str(m.id), 'name': m.name, 'price': float(m.price)}
                    for m in combo.modifiers.filter(is_active=True)[:3]
                ]
            })
            response['total_estimated_price'] += combo.price
        
        response['follow_up_questions'] = [
            "Order for a group",
            "Show individual items",
            "What's in each combo?",
            "Customize a combo"
        ]
        
        return response
    
    def _generate_category_recommendation(
        self,
        products: List[Product],
        meal_type: str,
        quantity: int = 1
    ) -> Dict:
        """Generate category-specific recommendations."""
        response = {
            'message': '',
            'recommendations': [],
            'follow_up_questions': [],
            'total_estimated_price': Decimal('0.00'),
        }
        
        categorized = self.categorize_products_by_meal_type(products)
        category_products = categorized.get(meal_type, [])
        
        if not category_products:
            response['message'] = f"I couldn't find any {meal_type} items at the moment. Would you like to see other categories?"
            response['follow_up_questions'] = [
                "Show all menu",
                "Popular items",
                "Combo deals"
            ]
            return response
        
        emoji_map = {
            'starter': '🥗',
            'main': '🍽️',
            'side': '🍟',
            'drink': '🍹',
            'dessert': '🍰'
        }
        
        response['message'] = f"""{emoji_map.get(meal_type, '✨')} **Here are our {meal_type.title()} options:**"""
        
        for product in category_products[:5]:
            response['recommendations'].append({
                'product_id': str(product.id),
                'name': product.name,
                'description': product.description,
                'price': float(product.price),
                'quantity': quantity,
                'category': product.category.name if product.category else meal_type.title(),
                'reason': "Staff favorite!" if product.display_order < 3 else "",
                'is_combo': product.is_combo,
                'has_variants': product.has_variants,
                'modifiers': [
                    {'id': str(m.id), 'name': m.name, 'price': float(m.price)}
                    for m in product.modifiers.filter(is_active=True)[:3]
                ]
            })
            response['total_estimated_price'] += product.price * quantity
        
        other_categories = [k for k in self.MEAL_STRUCTURE.keys() if k != meal_type]
        response['follow_up_questions'] = [
            f"Show me {other_categories[0]}s" if other_categories else "Show combos",
            "Order for group",
            "Popular items"
        ]
        
        return response
    
    def _generate_popular_recommendation(self, quantity: int = 1) -> Dict:
        """Generate recommendations based on popular items."""
        response = {
            'message': '',
            'recommendations': [],
            'follow_up_questions': [],
            'total_estimated_price': Decimal('0.00'),
        }
        
        popular_products = self.get_popular_products(limit=5)
        
        if not popular_products:
            # Fall back to featured products
            popular_products = Product.objects.filter(
                is_active=True,
                is_available_for_pos=True,
                is_deleted=False
            ).order_by('display_order')[:5]
        
        response['message'] = """⭐ **Our Most Popular Items:**

These are the dishes our customers love the most!"""
        
        for product in popular_products:
            response['recommendations'].append({
                'product_id': str(product.id),
                'name': product.name,
                'description': product.description,
                'price': float(product.price),
                'quantity': quantity,
                'category': product.category.name if product.category else 'Popular',
                'reason': "Customer favorite!",
                'is_combo': product.is_combo,
                'has_variants': product.has_variants,
                'modifiers': [
                    {'id': str(m.id), 'name': m.name, 'price': float(m.price)}
                    for m in product.modifiers.filter(is_active=True)[:3]
                ]
            })
            response['total_estimated_price'] += product.price * quantity
        
        response['follow_up_questions'] = [
            "Order for a group",
            "Show me combos",
            "Vegetarian options",
            "Something new"
        ]
        
        return response
    
    def _generate_balanced_recommendation(
        self,
        products: List[Product],
        group_size: int = 1,
        budget: Optional[Decimal] = None
    ) -> Dict:
        """Generate a balanced meal recommendation."""
        response = {
            'message': '',
            'recommendations': [],
            'follow_up_questions': [],
            'total_estimated_price': Decimal('0.00'),
        }
        
        response['message'] = """👋 **Welcome to DDMU Cafe!**

I'm your virtual assistant. Here's what I can help you with:"""
        
        # Show category overview
        categories = self.get_active_categories()
        
        if categories:
            response['message'] += "\n\n**Our Menu Categories:**\n"
            for cat in categories[:6]:
                product_count = cat.product_count
                response['message'] += f"• {cat.name} ({product_count} items)\n"
        
        response['message'] += "\n💡 **How can I help you today?**"
        
        response['follow_up_questions'] = [
            "Order for my team",
            "Show combo deals",
            "What's popular?",
            "Browse full menu"
        ]
        
        return response


# Singleton instance
recommendation_engine = MenuRecommendationEngine()
