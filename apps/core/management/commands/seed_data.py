"""
Management command to seed initial demo data for the POS system.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from decimal import Decimal


class Command(BaseCommand):
    help = 'Seed initial demo data for the POS system'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )
    
    def handle(self, *args, **options):
        self.stdout.write('Seeding demo data...\n')
        
        User = get_user_model()
        
        # Create admin user
        admin_user, created = User.objects.get_or_create(
            email='admin@odoo-cafe.com',
            defaults={
                'first_name': 'Admin',
                'last_name': 'User',
                'role': 'admin',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('Created admin user'))
        
        # Create staff users
        staff_users = [
            {'email': 'cashier1@odoo-cafe.com', 'first_name': 'John', 'last_name': 'Doe', 'role': 'staff'},
            {'email': 'cashier2@odoo-cafe.com', 'first_name': 'Jane', 'last_name': 'Smith', 'role': 'staff'},
            {'email': 'manager1@odoo-cafe.com', 'first_name': 'Mike', 'last_name': 'Johnson', 'role': 'manager'},
            {'email': 'kitchen1@odoo-cafe.com', 'first_name': 'Chef', 'last_name': 'Gordon', 'role': 'kitchen'},
        ]
        
        for user_data in staff_users:
            email = user_data['email']
            user, created = User.objects.get_or_create(
                email=email,
                defaults=user_data
            )
            if created:
                user.set_password('password123')
                user.pin_code = '1234'
                user.save()
                self.stdout.write(f"Created user: {user.email}")
        
        # Create categories
        from apps.products.models import Category, Product, ProductModifier
        
        categories_data = [
            {'name': 'Hot Beverages', 'color': '#EF4444', 'display_order': 1},
            {'name': 'Cold Beverages', 'color': '#3B82F6', 'display_order': 2},
            {'name': 'Breakfast', 'color': '#F59E0B', 'display_order': 3},
            {'name': 'Main Course', 'color': '#10B981', 'display_order': 4},
            {'name': 'Snacks', 'color': '#8B5CF6', 'display_order': 5},
            {'name': 'Desserts', 'color': '#EC4899', 'display_order': 6},
        ]
        
        categories = {}
        for cat_data in categories_data:
            cat, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults=cat_data
            )
            categories[cat.name] = cat
            if created:
                self.stdout.write(f"Created category: {cat.name}")
        
        # Create products
        products_data = [
            # Hot Beverages
            {'name': 'Espresso', 'category': 'Hot Beverages', 'price': 80, 'preparation_time': 3},
            {'name': 'Cappuccino', 'category': 'Hot Beverages', 'price': 120, 'preparation_time': 5},
            {'name': 'Latte', 'category': 'Hot Beverages', 'price': 130, 'preparation_time': 5},
            {'name': 'Hot Chocolate', 'category': 'Hot Beverages', 'price': 110, 'preparation_time': 4},
            {'name': 'Green Tea', 'category': 'Hot Beverages', 'price': 70, 'preparation_time': 3},
            
            # Cold Beverages
            {'name': 'Iced Coffee', 'category': 'Cold Beverages', 'price': 140, 'preparation_time': 4},
            {'name': 'Cold Brew', 'category': 'Cold Beverages', 'price': 160, 'preparation_time': 2},
            {'name': 'Fruit Smoothie', 'category': 'Cold Beverages', 'price': 150, 'preparation_time': 5},
            {'name': 'Fresh Orange Juice', 'category': 'Cold Beverages', 'price': 100, 'preparation_time': 3},
            {'name': 'Milkshake', 'category': 'Cold Beverages', 'price': 130, 'preparation_time': 4},
            
            # Breakfast
            {'name': 'Classic Eggs Benedict', 'category': 'Breakfast', 'price': 280, 'preparation_time': 15},
            {'name': 'Pancake Stack', 'category': 'Breakfast', 'price': 220, 'preparation_time': 12},
            {'name': 'Avocado Toast', 'category': 'Breakfast', 'price': 200, 'preparation_time': 8},
            {'name': 'Full English Breakfast', 'category': 'Breakfast', 'price': 350, 'preparation_time': 20},
            {'name': 'French Toast', 'category': 'Breakfast', 'price': 180, 'preparation_time': 10},
            
            # Main Course
            {'name': 'Grilled Chicken Sandwich', 'category': 'Main Course', 'price': 280, 'preparation_time': 15},
            {'name': 'Margherita Pizza', 'category': 'Main Course', 'price': 350, 'preparation_time': 20},
            {'name': 'Caesar Salad', 'category': 'Main Course', 'price': 220, 'preparation_time': 10},
            {'name': 'Pasta Carbonara', 'category': 'Main Course', 'price': 300, 'preparation_time': 18},
            {'name': 'Fish and Chips', 'category': 'Main Course', 'price': 380, 'preparation_time': 20},
            
            # Snacks
            {'name': 'French Fries', 'category': 'Snacks', 'price': 120, 'preparation_time': 8},
            {'name': 'Onion Rings', 'category': 'Snacks', 'price': 130, 'preparation_time': 8},
            {'name': 'Garlic Bread', 'category': 'Snacks', 'price': 100, 'preparation_time': 6},
            {'name': 'Chicken Wings', 'category': 'Snacks', 'price': 200, 'preparation_time': 15},
            {'name': 'Nachos', 'category': 'Snacks', 'price': 180, 'preparation_time': 10},
            
            # Desserts
            {'name': 'Chocolate Brownie', 'category': 'Desserts', 'price': 150, 'preparation_time': 5},
            {'name': 'Cheesecake', 'category': 'Desserts', 'price': 180, 'preparation_time': 3},
            {'name': 'Ice Cream Sundae', 'category': 'Desserts', 'price': 160, 'preparation_time': 5},
            {'name': 'Tiramisu', 'category': 'Desserts', 'price': 200, 'preparation_time': 3},
            {'name': 'Apple Pie', 'category': 'Desserts', 'price': 170, 'preparation_time': 5},
        ]
        
        for prod_data in products_data:
            category = categories.get(prod_data.pop('category'))
            prod, created = Product.objects.get_or_create(
                name=prod_data['name'],
                defaults={
                    'category': category,
                    'price': Decimal(str(prod_data['price'])),
                    'preparation_time': prod_data['preparation_time'],
                    'tax_rate': Decimal('5.00'),
                }
            )
            if created:
                self.stdout.write(f"Created product: {prod.name}")
        
        # Create modifiers
        modifiers_data = [
            {'name': 'Extra Shot', 'price': 30},
            {'name': 'Oat Milk', 'price': 40},
            {'name': 'Almond Milk', 'price': 40},
            {'name': 'Whipped Cream', 'price': 25},
            {'name': 'Extra Cheese', 'price': 50},
            {'name': 'Bacon', 'price': 60},
            {'name': 'Avocado', 'price': 70},
        ]
        
        for mod_data in modifiers_data:
            mod, created = ProductModifier.objects.get_or_create(
                name=mod_data['name'],
                defaults={'price': Decimal(str(mod_data['price']))}
            )
            if created:
                self.stdout.write(f"Created modifier: {mod.name}")
        
        # Create floors and tables
        from apps.floors.models import Floor, Table
        
        floors_data = [
            {'name': 'Ground Floor', 'tables': [
                {'table_number': 'T1', 'name': 'Table 1', 'seats': 2, 'position_x': 50, 'position_y': 50},
                {'table_number': 'T2', 'name': 'Table 2', 'seats': 2, 'position_x': 150, 'position_y': 50},
                {'table_number': 'T3', 'name': 'Table 3', 'seats': 4, 'position_x': 250, 'position_y': 50},
                {'table_number': 'T4', 'name': 'Table 4', 'seats': 4, 'position_x': 50, 'position_y': 150},
                {'table_number': 'T5', 'name': 'Table 5', 'seats': 4, 'position_x': 150, 'position_y': 150},
                {'table_number': 'T6', 'name': 'Table 6', 'seats': 6, 'position_x': 250, 'position_y': 150, 'shape': 'rectangle'},
            ]},
            {'name': 'First Floor', 'tables': [
                {'table_number': 'F1', 'name': 'VIP 1', 'seats': 4, 'position_x': 50, 'position_y': 50},
                {'table_number': 'F2', 'name': 'VIP 2', 'seats': 4, 'position_x': 150, 'position_y': 50},
                {'table_number': 'F3', 'name': 'VIP 3', 'seats': 6, 'position_x': 250, 'position_y': 50, 'shape': 'rectangle'},
                {'table_number': 'F4', 'name': 'VIP 4', 'seats': 8, 'position_x': 100, 'position_y': 150, 'shape': 'rectangle'},
            ]},
            {'name': 'Terrace', 'tables': [
                {'table_number': 'TR1', 'name': 'Terrace 1', 'seats': 2, 'position_x': 50, 'position_y': 50},
                {'table_number': 'TR2', 'name': 'Terrace 2', 'seats': 2, 'position_x': 150, 'position_y': 50},
                {'table_number': 'TR3', 'name': 'Terrace 3', 'seats': 4, 'position_x': 250, 'position_y': 50},
            ]},
        ]
        
        for floor_data in floors_data:
            tables = floor_data.pop('tables')
            floor, created = Floor.objects.get_or_create(
                name=floor_data['name'],
                defaults=floor_data
            )
            if created:
                self.stdout.write(f"Created floor: {floor.name}")
            
            for table_data in tables:
                table_number = table_data['table_number']
                table, created = Table.objects.get_or_create(
                    table_number=table_number,
                    floor=floor,
                    defaults=table_data
                )
                if created:
                    self.stdout.write(f"  Created table: {table.display_name}")
        
        # Create payment methods
        from apps.payments.models import PaymentMethod, UPIConfiguration
        
        payment_methods = [
            {'name': 'Cash', 'method_type': 'cash', 'is_default': True},
            {'name': 'Credit/Debit Card', 'method_type': 'card'},
            {'name': 'UPI', 'method_type': 'upi'},
        ]
        
        for pm_data in payment_methods:
            pm, created = PaymentMethod.objects.get_or_create(
                method_type=pm_data['method_type'],
                defaults=pm_data
            )
            if created:
                self.stdout.write(f"Created payment method: {pm.name}")
        
        # Create UPI configuration
        upi_config, created = UPIConfiguration.objects.get_or_create(
            payment_method=PaymentMethod.objects.get(method_type='upi'),
            defaults={
                'upi_id': 'cafe@paytm',
                'merchant_name': 'Odoo Cafe',
                'merchant_code': 'CAFE001',
            }
        )
        if created:
            self.stdout.write('Created UPI configuration')
        
        # Create POS terminal
        from apps.terminals.models import POSTerminal
        
        terminal, created = POSTerminal.objects.get_or_create(
            name='Main Counter',
            defaults={
                'code': 'POS-001',
                'description': 'Main counter terminal',
            }
        )
        if created:
            self.stdout.write('Created POS terminal')
        
        self.stdout.write(self.style.SUCCESS('\nDemo data seeded successfully!'))
        self.stdout.write('\nDefault Credentials (email / password):')
        self.stdout.write('  Admin: admin@odoo-cafe.com / admin123')
        self.stdout.write('  Staff: cashier1@odoo-cafe.com / password123 (PIN: 1234)')
        self.stdout.write('  Manager: manager1@odoo-cafe.com / password123 (PIN: 1234)')
        self.stdout.write('  Kitchen: kitchen1@odoo-cafe.com / password123 (PIN: 1234)')
