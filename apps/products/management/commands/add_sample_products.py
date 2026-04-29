"""
Management command to add sample products with images from online sources.
"""
import os
import requests
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from apps.products.models import Category, Product


class Command(BaseCommand):
    help = 'Add 50+ sample products with images from online sources'

    def handle(self, *args, **kwargs):
        self.stdout.write('Creating categories...')
        categories = self.create_categories()
        
        self.stdout.write('Adding products...')
        products_data = self.get_products_data()
        
        created_count = 0
        for product_data in products_data:
            try:
                category = categories.get(product_data['category'])
                
                # Check if product already exists
                if Product.objects.filter(name=product_data['name']).exists():
                    self.stdout.write(f'Product {product_data["name"]} already exists, skipping...')
                    continue
                
                product = Product.objects.create(
                    name=product_data['name'],
                    category=category,
                    description=product_data['description'],
                    price=Decimal(str(product_data['price'])),
                    cost_price=Decimal(str(product_data['cost_price'])),
                    tax_rate=Decimal(str(product_data['tax_rate'])),
                    unit=product_data['unit'],
                    preparation_time=product_data['preparation_time'],
                    is_available_for_pos=True,
                    is_available_for_self_order=True,
                    is_active=True
                )
                
                # Download and save image
                if product_data['image_url']:
                    try:
                        response = requests.get(product_data['image_url'], timeout=10)
                        if response.status_code == 200:
                            image_name = f"{product.id}_{product_data['name'].replace(' ', '_')}.jpg"
                            product.image.save(image_name, ContentFile(response.content), save=True)
                            self.stdout.write(self.style.SUCCESS(f'✓ Created {product.name} with image'))
                        else:
                            self.stdout.write(self.style.WARNING(f'✓ Created {product.name} (image download failed)'))
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'✓ Created {product.name} (image error: {str(e)})'))
                else:
                    self.stdout.write(self.style.SUCCESS(f'✓ Created {product.name}'))
                
                created_count += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Failed to create {product_data["name"]}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n✓ Successfully created {created_count} products!'))

    def create_categories(self):
        """Create product categories"""
        categories_data = [
            {'name': 'Beverages', 'color': '#3B82F6', 'description': 'Hot and cold drinks'},
            {'name': 'Coffee', 'color': '#8B4513', 'description': 'Coffee varieties'},
            {'name': 'Tea', 'color': '#10B981', 'description': 'Tea varieties'},
            {'name': 'Breakfast', 'color': '#F59E0B', 'description': 'Breakfast items'},
            {'name': 'Snacks', 'color': '#EF4444', 'description': 'Quick bites and snacks'},
            {'name': 'Sandwiches', 'color': '#8B5CF6', 'description': 'Sandwiches and wraps'},
            {'name': 'Desserts', 'color': '#EC4899', 'description': 'Sweet treats'},
            {'name': 'Bakery', 'color': '#F97316', 'description': 'Fresh baked goods'},
            {'name': 'Main Course', 'color': '#DC2626', 'description': 'Main dishes'},
            {'name': 'Juices', 'color': '#06B6D4', 'description': 'Fresh juices'},
        ]
        
        categories = {}
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'description': cat_data['description'],
                    'color': cat_data['color'],
                    'is_active': True
                }
            )
            categories[cat_data['name']] = category
            if created:
                self.stdout.write(f'  Created category: {category.name}')
        
        return categories

    def get_products_data(self):
        """Return list of products with online image URLs"""
        return [
            # Coffee Items
            {'name': 'Espresso', 'category': 'Coffee', 'description': 'Strong black coffee', 'price': 80, 'cost_price': 30, 'tax_rate': 5, 'unit': 'cup', 'preparation_time': 3, 'image_url': 'https://images.unsplash.com/photo-1510591509098-f4fdc6d0ff04?w=500'},
            {'name': 'Cappuccino', 'category': 'Coffee', 'description': 'Espresso with steamed milk foam', 'price': 120, 'cost_price': 45, 'tax_rate': 5, 'unit': 'cup', 'preparation_time': 5, 'image_url': 'https://images.unsplash.com/photo-1572442388796-11668a67e53d?w=500'},
            {'name': 'Latte', 'category': 'Coffee', 'description': 'Smooth coffee with steamed milk', 'price': 130, 'cost_price': 50, 'tax_rate': 5, 'unit': 'cup', 'preparation_time': 5, 'image_url': 'https://images.unsplash.com/photo-1561882468-9110e03e0f78?w=500'},
            {'name': 'Americano', 'category': 'Coffee', 'description': 'Espresso with hot water', 'price': 90, 'cost_price': 35, 'tax_rate': 5, 'unit': 'cup', 'preparation_time': 3, 'image_url': 'https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=500'},
            {'name': 'Mocha', 'category': 'Coffee', 'description': 'Chocolate flavored coffee', 'price': 150, 'cost_price': 60, 'tax_rate': 5, 'unit': 'cup', 'preparation_time': 6, 'image_url': 'https://images.unsplash.com/photo-1607013251379-e6eecfffe234?w=500'},
            {'name': 'Macchiato', 'category': 'Coffee', 'description': 'Espresso with milk foam', 'price': 110, 'cost_price': 40, 'tax_rate': 5, 'unit': 'cup', 'preparation_time': 4, 'image_url': 'https://images.unsplash.com/photo-1557006021-b85faa2bc5e2?w=500'},
            {'name': 'Cold Brew', 'category': 'Coffee', 'description': 'Smooth cold coffee', 'price': 140, 'cost_price': 55, 'tax_rate': 5, 'unit': 'glass', 'preparation_time': 2, 'image_url': 'https://images.unsplash.com/photo-1517487881594-2787fef5ebf7?w=500'},
            {'name': 'Iced Latte', 'category': 'Coffee', 'description': 'Chilled latte with ice', 'price': 140, 'cost_price': 55, 'tax_rate': 5, 'unit': 'glass', 'preparation_time': 4, 'image_url': 'https://images.unsplash.com/photo-1578374173704-4474f2e04e2f?w=500'},
            
            # Tea Items
            {'name': 'Masala Chai', 'category': 'Tea', 'description': 'Indian spiced tea', 'price': 40, 'cost_price': 15, 'tax_rate': 5, 'unit': 'cup', 'preparation_time': 5, 'image_url': 'https://images.unsplash.com/photo-1597318130877-7f9a8986b2b6?w=500'},
            {'name': 'Green Tea', 'category': 'Tea', 'description': 'Healthy green tea', 'price': 50, 'cost_price': 20, 'tax_rate': 5, 'unit': 'cup', 'preparation_time': 3, 'image_url': 'https://images.unsplash.com/photo-1556679343-c7306c1976bc?w=500'},
            {'name': 'Black Tea', 'category': 'Tea', 'description': 'Classic black tea', 'price': 30, 'cost_price': 10, 'tax_rate': 5, 'unit': 'cup', 'preparation_time': 3, 'image_url': 'https://images.unsplash.com/photo-1594631661960-180f8bcb1043?w=500'},
            {'name': 'Ginger Tea', 'category': 'Tea', 'description': 'Tea with fresh ginger', 'price': 45, 'cost_price': 18, 'tax_rate': 5, 'unit': 'cup', 'preparation_time': 4, 'image_url': 'https://images.unsplash.com/photo-1571934811356-5cc061b6821f?w=500'},
            {'name': 'Lemon Tea', 'category': 'Tea', 'description': 'Refreshing lemon tea', 'price': 50, 'cost_price': 20, 'tax_rate': 5, 'unit': 'cup', 'preparation_time': 3, 'image_url': 'https://images.unsplash.com/photo-1563822249548-9a72b6163ad6?w=500'},
            {'name': 'Iced Tea', 'category': 'Tea', 'description': 'Cold refreshing tea', 'price': 60, 'cost_price': 25, 'tax_rate': 5, 'unit': 'glass', 'preparation_time': 2, 'image_url': 'https://images.unsplash.com/photo-1499638673689-79a0b5115d87?w=500'},
            
            # Breakfast Items
            {'name': 'Idli Sambar', 'category': 'Breakfast', 'description': 'Steamed rice cakes with sambar', 'price': 60, 'cost_price': 25, 'tax_rate': 5, 'unit': 'plate', 'preparation_time': 8, 'image_url': 'https://images.unsplash.com/photo-1630383249896-424e482df921?w=500'},
            {'name': 'Dosa', 'category': 'Breakfast', 'description': 'Crispy rice crepe', 'price': 70, 'cost_price': 30, 'tax_rate': 5, 'unit': 'plate', 'preparation_time': 10, 'image_url': 'https://images.unsplash.com/photo-1668236543090-82eba5ee5976?w=500'},
            {'name': 'Poha', 'category': 'Breakfast', 'description': 'Flattened rice breakfast', 'price': 50, 'cost_price': 20, 'tax_rate': 5, 'unit': 'plate', 'preparation_time': 7, 'image_url': 'https://images.unsplash.com/photo-1606491956689-2ea866880c84?w=500'},
            {'name': 'Upma', 'category': 'Breakfast', 'description': 'Savory semolina dish', 'price': 55, 'cost_price': 22, 'tax_rate': 5, 'unit': 'plate', 'preparation_time': 8, 'image_url': 'https://images.unsplash.com/photo-1601050690597-df0568f70950?w=500'},
            {'name': 'Pancakes', 'category': 'Breakfast', 'description': 'Fluffy pancakes with syrup', 'price': 120, 'cost_price': 50, 'tax_rate': 5, 'unit': 'plate', 'preparation_time': 10, 'image_url': 'https://images.unsplash.com/photo-1528207776546-365bb710ee93?w=500'},
            {'name': 'French Toast', 'category': 'Breakfast', 'description': 'Golden brown toast', 'price': 110, 'cost_price': 45, 'tax_rate': 5, 'unit': 'plate', 'preparation_time': 8, 'image_url': 'https://images.unsplash.com/photo-1484723091739-30a097e8f929?w=500'},
            
            # Snacks
            {'name': 'Samosa', 'category': 'Snacks', 'description': 'Crispy fried pastry', 'price': 30, 'cost_price': 12, 'tax_rate': 5, 'unit': 'unit', 'preparation_time': 5, 'image_url': 'https://images.unsplash.com/photo-1601050690532-da0c37f79330?w=500'},
            {'name': 'French Fries', 'category': 'Snacks', 'description': 'Crispy golden fries', 'price': 80, 'cost_price': 30, 'tax_rate': 5, 'unit': 'portion', 'preparation_time': 8, 'image_url': 'https://images.unsplash.com/photo-1573080496219-bb080dd4f877?w=500'},
            {'name': 'Spring Rolls', 'category': 'Snacks', 'description': 'Crispy vegetable rolls', 'price': 90, 'cost_price': 35, 'tax_rate': 5, 'unit': 'portion', 'preparation_time': 10, 'image_url': 'https://images.unsplash.com/photo-1625220194771-7ebdea0b70b9?w=500'},
            {'name': 'Pakoda', 'category': 'Snacks', 'description': 'Fried fritters', 'price': 60, 'cost_price': 25, 'tax_rate': 5, 'unit': 'portion', 'preparation_time': 8, 'image_url': 'https://images.unsplash.com/photo-1606491048993-a816a8be2dc4?w=500'},
            {'name': 'Nachos', 'category': 'Snacks', 'description': 'Chips with cheese and salsa', 'price': 120, 'cost_price': 50, 'tax_rate': 5, 'unit': 'portion', 'preparation_time': 6, 'image_url': 'https://images.unsplash.com/photo-1513456852971-30c0b8199d4d?w=500'},
            {'name': 'Onion Rings', 'category': 'Snacks', 'description': 'Crispy fried onion rings', 'price': 90, 'cost_price': 35, 'tax_rate': 5, 'unit': 'portion', 'preparation_time': 8, 'image_url': 'https://images.unsplash.com/photo-1639024471283-03518883512d?w=500'},
            
            # Sandwiches
            {'name': 'Veg Sandwich', 'category': 'Sandwiches', 'description': 'Fresh vegetable sandwich', 'price': 80, 'cost_price': 35, 'tax_rate': 5, 'unit': 'unit', 'preparation_time': 7, 'image_url': 'https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=500'},
            {'name': 'Grilled Sandwich', 'category': 'Sandwiches', 'description': 'Toasted grilled sandwich', 'price': 100, 'cost_price': 40, 'tax_rate': 5, 'unit': 'unit', 'preparation_time': 10, 'image_url': 'https://images.unsplash.com/photo-1621852004158-f3bc188ace2d?w=500'},
            {'name': 'Club Sandwich', 'category': 'Sandwiches', 'description': 'Triple decker sandwich', 'price': 150, 'cost_price': 60, 'tax_rate': 5, 'unit': 'unit', 'preparation_time': 12, 'image_url': 'https://images.unsplash.com/photo-1567234669003-dce7a7a88821?w=500'},
            {'name': 'Paneer Sandwich', 'category': 'Sandwiches', 'description': 'Cottage cheese sandwich', 'price': 120, 'cost_price': 50, 'tax_rate': 5, 'unit': 'unit', 'preparation_time': 10, 'image_url': 'https://images.unsplash.com/photo-1619740455993-5c994d3aea4e?w=500'},
            {'name': 'Cheese Toast', 'category': 'Sandwiches', 'description': 'Cheesy toasted bread', 'price': 70, 'cost_price': 30, 'tax_rate': 5, 'unit': 'unit', 'preparation_time': 5, 'image_url': 'https://images.unsplash.com/photo-1612392166886-ee8475b8fe39?w=500'},
            
            # Desserts
            {'name': 'Chocolate Cake', 'category': 'Desserts', 'description': 'Rich chocolate cake slice', 'price': 120, 'cost_price': 50, 'tax_rate': 5, 'unit': 'unit', 'preparation_time': 2, 'image_url': 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=500'},
            {'name': 'Ice Cream', 'category': 'Desserts', 'description': 'Creamy ice cream scoop', 'price': 80, 'cost_price': 30, 'tax_rate': 5, 'unit': 'unit', 'preparation_time': 2, 'image_url': 'https://images.unsplash.com/photo-1563805042-7684c019e1cb?w=500'},
            {'name': 'Brownie', 'category': 'Desserts', 'description': 'Fudgy chocolate brownie', 'price': 90, 'cost_price': 35, 'tax_rate': 5, 'unit': 'unit', 'preparation_time': 2, 'image_url': 'https://images.unsplash.com/photo-1606313564200-e75d5e30476c?w=500'},
            {'name': 'Pastry', 'category': 'Desserts', 'description': 'Assorted pastries', 'price': 100, 'cost_price': 40, 'tax_rate': 5, 'unit': 'unit', 'preparation_time': 2, 'image_url': 'https://images.unsplash.com/photo-1488477181946-6428a0291777?w=500'},
            {'name': 'Tiramisu', 'category': 'Desserts', 'description': 'Italian coffee dessert', 'price': 150, 'cost_price': 65, 'tax_rate': 5, 'unit': 'unit', 'preparation_time': 2, 'image_url': 'https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?w=500'},
            {'name': 'Cheesecake', 'category': 'Desserts', 'description': 'Creamy cheesecake slice', 'price': 140, 'cost_price': 60, 'tax_rate': 5, 'unit': 'unit', 'preparation_time': 2, 'image_url': 'https://images.unsplash.com/photo-1524351199678-941a58a3df50?w=500'},
            
            # Bakery
            {'name': 'Croissant', 'category': 'Bakery', 'description': 'Buttery flaky pastry', 'price': 60, 'cost_price': 25, 'tax_rate': 5, 'unit': 'unit', 'preparation_time': 2, 'image_url': 'https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=500'},
            {'name': 'Muffin', 'category': 'Bakery', 'description': 'Soft fluffy muffin', 'price': 50, 'cost_price': 20, 'tax_rate': 5, 'unit': 'unit', 'preparation_time': 2, 'image_url': 'https://images.unsplash.com/photo-1607920591413-4ec007e70023?w=500'},
            {'name': 'Donut', 'category': 'Bakery', 'description': 'Sweet glazed donut', 'price': 40, 'cost_price': 15, 'tax_rate': 5, 'unit': 'unit', 'preparation_time': 2, 'image_url': 'https://images.unsplash.com/photo-1551024601-bec78aea704b?w=500'},
            {'name': 'Bagel', 'category': 'Bakery', 'description': 'Chewy round bread', 'price': 70, 'cost_price': 30, 'tax_rate': 5, 'unit': 'unit', 'preparation_time': 3, 'image_url': 'https://images.unsplash.com/photo-1509440159596-0249088772ff?w=500'},
            {'name': 'Cookies', 'category': 'Bakery', 'description': 'Freshly baked cookies', 'price': 60, 'cost_price': 25, 'tax_rate': 5, 'unit': 'portion', 'preparation_time': 2, 'image_url': 'https://images.unsplash.com/photo-1499636136210-6f4ee915583e?w=500'},
            {'name': 'Garlic Bread', 'category': 'Bakery', 'description': 'Toasted bread with garlic', 'price': 80, 'cost_price': 30, 'tax_rate': 5, 'unit': 'portion', 'preparation_time': 5, 'image_url': 'https://images.unsplash.com/photo-1573140401552-388e6f4f0e2d?w=500'},
            
            # Main Course
            {'name': 'Pizza Margherita', 'category': 'Main Course', 'description': 'Classic tomato and cheese pizza', 'price': 250, 'cost_price': 100, 'tax_rate': 5, 'unit': 'unit', 'preparation_time': 20, 'image_url': 'https://images.unsplash.com/photo-1574071318508-1cdbab80d002?w=500'},
            {'name': 'Veg Burger', 'category': 'Main Course', 'description': 'Delicious veggie burger', 'price': 120, 'cost_price': 50, 'tax_rate': 5, 'unit': 'unit', 'preparation_time': 12, 'image_url': 'https://images.unsplash.com/photo-1520072959219-c595dc870360?w=500'},
            {'name': 'Pasta Alfredo', 'category': 'Main Course', 'description': 'Creamy pasta with white sauce', 'price': 180, 'cost_price': 70, 'tax_rate': 5, 'unit': 'plate', 'preparation_time': 15, 'image_url': 'https://images.unsplash.com/photo-1621996346565-e3dbc646d9a9?w=500'},
            {'name': 'Biryani', 'category': 'Main Course', 'description': 'Aromatic rice dish', 'price': 200, 'cost_price': 80, 'tax_rate': 5, 'unit': 'plate', 'preparation_time': 25, 'image_url': 'https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=500'},
            {'name': 'Fried Rice', 'category': 'Main Course', 'description': 'Stir fried rice with vegetables', 'price': 150, 'cost_price': 60, 'tax_rate': 5, 'unit': 'plate', 'preparation_time': 12, 'image_url': 'https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=500'},
            {'name': 'Noodles', 'category': 'Main Course', 'description': 'Stir fried noodles', 'price': 140, 'cost_price': 55, 'tax_rate': 5, 'unit': 'plate', 'preparation_time': 10, 'image_url': 'https://images.unsplash.com/photo-1612929633738-8fe44f7ec841?w=500'},
            {'name': 'Dal Tadka', 'category': 'Main Course', 'description': 'Tempered lentil curry', 'price': 100, 'cost_price': 40, 'tax_rate': 5, 'unit': 'plate', 'preparation_time': 15, 'image_url': 'https://images.unsplash.com/photo-1546833998-877b37c2e5c6?w=500'},
            {'name': 'Paneer Butter Masala', 'category': 'Main Course', 'description': 'Cottage cheese in rich gravy', 'price': 180, 'cost_price': 70, 'tax_rate': 5, 'unit': 'plate', 'preparation_time': 18, 'image_url': 'https://images.unsplash.com/photo-1631452180519-c014fe946bc7?w=500'},
            
            # Juices & Beverages
            {'name': 'Orange Juice', 'category': 'Juices', 'description': 'Fresh squeezed orange juice', 'price': 80, 'cost_price': 30, 'tax_rate': 5, 'unit': 'glass', 'preparation_time': 5, 'image_url': 'https://images.unsplash.com/photo-1600271886742-f049cd451bba?w=500'},
            {'name': 'Apple Juice', 'category': 'Juices', 'description': 'Fresh apple juice', 'price': 90, 'cost_price': 35, 'tax_rate': 5, 'unit': 'glass', 'preparation_time': 5, 'image_url': 'https://images.unsplash.com/photo-1600271886742-f049cd451bba?w=500'},
            {'name': 'Mango Shake', 'category': 'Juices', 'description': 'Creamy mango milkshake', 'price': 100, 'cost_price': 40, 'tax_rate': 5, 'unit': 'glass', 'preparation_time': 5, 'image_url': 'https://images.unsplash.com/photo-1622484211881-f38b1ba1c69f?w=500'},
            {'name': 'Watermelon Juice', 'category': 'Juices', 'description': 'Refreshing watermelon juice', 'price': 70, 'cost_price': 28, 'tax_rate': 5, 'unit': 'glass', 'preparation_time': 4, 'image_url': 'https://images.unsplash.com/photo-1546547850-a3ee36fe86f4?w=500'},
            {'name': 'Smoothie Bowl', 'category': 'Juices', 'description': 'Healthy fruit smoothie bowl', 'price': 150, 'cost_price': 60, 'tax_rate': 5, 'unit': 'bowl', 'preparation_time': 8, 'image_url': 'https://images.unsplash.com/photo-1590301157890-4810ed352733?w=500'},
            {'name': 'Lassi', 'category': 'Juices', 'description': 'Traditional yogurt drink', 'price': 60, 'cost_price': 25, 'tax_rate': 5, 'unit': 'glass', 'preparation_time': 4, 'image_url': 'https://images.unsplash.com/photo-1623412341830-e5cce89e3384?w=500'},
            {'name': 'Mojito', 'category': 'Beverages', 'description': 'Refreshing mint drink', 'price': 90, 'cost_price': 35, 'tax_rate': 5, 'unit': 'glass', 'preparation_time': 5, 'image_url': 'https://images.unsplash.com/photo-1551538827-9c037cb4f32a?w=500'},
            {'name': 'Hot Chocolate', 'category': 'Beverages', 'description': 'Rich hot chocolate drink', 'price': 110, 'cost_price': 45, 'tax_rate': 5, 'unit': 'cup', 'preparation_time': 5, 'image_url': 'https://images.unsplash.com/photo-1517487881594-2787fef5ebf7?w=500'},
        ]
