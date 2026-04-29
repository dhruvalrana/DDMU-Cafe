# DDMU Cafe POS Virtual Assistant

The Virtual Assistant is an AI-powered chatbot that helps customers and staff make informed ordering decisions, especially for group orders.

## Features

### 🎯 Core Capabilities

1. **Group Order Recommendations**
   - Suggests appropriate quantities based on group size
   - Recommends balanced meals with starters, mains, drinks, and desserts
   - Calculates estimated totals

2. **Combo & Deal Suggestions**
   - Prioritizes combo products for better value
   - Shows what's included in each combo
   - Highlights savings

3. **Dietary Preference Filtering**
   - Supports: Vegetarian, Vegan, Gluten-free, Halal, Spicy/Mild
   - Filters recommendations based on preferences

4. **Inventory Awareness**
   - Excludes low-stock items from recommendations
   - Checks real-time availability

5. **Modifier Upselling**
   - Suggests add-ons and customizations
   - Shows modifier prices

## API Endpoints

### Main Chat Endpoint
```
POST /api/v1/chatbot/
```

**Request Body:**
```json
{
    "message": "What's best for a team of 5?",
    "session_id": "uuid (optional)",
    "group_size": 5,
    "dietary_preferences": ["vegetarian"],
    "category_id": "uuid (optional)",
    "budget": 2000.00
}
```

**Response:**
```json
{
    "session_id": "uuid",
    "message": "🎉 Great choice! Here's my recommendation...",
    "recommendations": [
        {
            "product_id": "uuid",
            "name": "Party Starter Platter",
            "description": "Perfect for sharing",
            "price": 450.00,
            "quantity": 2,
            "category": "Appetizers",
            "reason": "Perfect for sharing among 5 people",
            "is_combo": true,
            "modifiers": [
                {"id": "uuid", "name": "Extra Dip", "price": 30.00}
            ]
        }
    ],
    "follow_up_questions": [
        "Show me vegetarian options",
        "Any dessert recommendations?"
    ],
    "total_estimated_price": 2250.00
}
```

### Quick Actions
```
POST /api/v1/chatbot/quick-action/
```

**Request Body:**
```json
{
    "action": "group_order",
    "group_size": 5,
    "session_id": "uuid (optional)"
}
```

Available actions:
- `group_order` - Order for a team/group
- `combos` - View combo deals
- `popular` - See popular items
- `vegetarian` - Vegetarian options
- `drinks` - Drinks menu
- `desserts` - Desserts menu

### Get Initial Greeting
```
GET /api/v1/chatbot/
```

Returns greeting message, quick action buttons, and available categories.

### Chat History
```
GET /api/v1/chatbot/history/<session_id>/
```

### Menu by Category
```
GET /api/v1/chatbot/menu/
GET /api/v1/chatbot/menu/<category_id>/
```

## Frontend Integration

### Widget Integration

Include the chatbot widget in any template:

```django
{% include 'chatbot/widget.html' %}
```

This adds a floating chat button in the bottom-right corner.

### POS Integration

The chatbot is integrated into the POS terminal. When a user selects a product from the chatbot recommendations, it dispatches a custom event:

```javascript
window.addEventListener('chatbotAddProduct', function(e) {
    const { productId, productName, price } = e.detail;
    // Add to cart logic
});
```

### Fullscreen Assistant

Access the fullscreen chatbot at:
```
/app/assistant/
```

This is ideal for self-service kiosks or customer-facing tablets.

## Database Models

### ChatSession
- Stores user sessions with group size and dietary preferences
- Links to authenticated users (optional)
- Tracks session activity

### ChatMessage
- Individual messages (user, assistant, system)
- Stores recommended products for each response

### RecommendationLog
- Analytics for recommendation performance
- Tracks which recommendations were actually ordered

## Example Interactions

### Team Order
```
User: "What should our team of 5 order?"