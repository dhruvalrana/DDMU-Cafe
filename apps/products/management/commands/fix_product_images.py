"""
Management command to add/fix product images from online sources.
"""
import requests
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from apps.products.models import Product


class Command(BaseCommand):
    help = 'Add or fix product images from online sources'

    def handle(self, *args, **kwargs):
        # Products with specific image URLs
        image_mappings = {
            'Espresso': 'https://images.pexels.com/photos/312418/pexels-photo-312418.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Cappuccino': 'https://images.pexels.com/photos/312418/pexels-photo-312418.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Latte': 'https://images.pexels.com/photos/851555/pexels-photo-851555.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Americano': 'https://images.pexels.com/photos/302899/pexels-photo-302899.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Mocha': 'https://images.pexels.com/photos/982612/pexels-photo-982612.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Macchiato': 'https://images.pexels.com/photos/2834618/pexels-photo-2834618.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Cold Brew': 'https://images.pexels.com/photos/1251176/pexels-photo-1251176.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Iced Latte': 'https://images.pexels.com/photos/7194915/pexels-photo-7194915.jpeg?auto=compress&cs=tinysrgb&w=500',
            
            'Masala Chai': 'https://images.pexels.com/photos/1638280/pexels-photo-1638280.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Green Tea': 'https://images.pexels.com/photos/1638281/pexels-photo-1638281.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Black Tea': 'https://images.pexels.com/photos/230477/pexels-photo-230477.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Ginger Tea': 'https://images.pexels.com/photos/1417945/pexels-photo-1417945.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Lemon Tea': 'https://images.pexels.com/photos/1793036/pexels-photo-1793036.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Iced Tea': 'https://images.pexels.com/photos/96974/pexels-photo-96974.jpeg?auto=compress&cs=tinysrgb&w=500',
            
            'Idli Sambar': 'https://images.pexels.com/photos/5560763/pexels-photo-5560763.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Dosa': 'https://images.pexels.com/photos/5560763/pexels-photo-5560763.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Poha': 'https://images.pexels.com/photos/1640772/pexels-photo-1640772.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Upma': 'https://images.pexels.com/photos/1640772/pexels-photo-1640772.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Pancakes': 'https://images.pexels.com/photos/376464/pexels-photo-376464.jpeg?auto=compress&cs=tinysrgb&w=500',
            'French Toast': 'https://images.pexels.com/photos/704971/pexels-photo-704971.jpeg?auto=compress&cs=tinysrgb&w=500',
            
            'Samosa': 'https://images.pexels.com/photos/14477865/pexels-photo-14477865.jpeg?auto=compress&cs=tinysrgb&w=500',
            'French Fries': 'https://images.pexels.com/photos/115740/pexels-photo-115740.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Spring Rolls': 'https://images.pexels.com/photos/2544829/pexels-photo-2544829.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Pakoda': 'https://images.pexels.com/photos/6419720/pexels-photo-6419720.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Nachos': 'https://images.pexels.com/photos/2092507/pexels-photo-2092507.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Onion Rings': 'https://images.pexels.com/photos/209540/pexels-photo-209540.jpeg?auto=compress&cs=tinysrgb&w=500',
            
            'Veg Sandwich': 'https://images.pexels.com/photos/1639562/pexels-photo-1639562.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Grilled Sandwich': 'https://images.pexels.com/photos/1600711/pexels-photo-1600711.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Club Sandwich': 'https://images.pexels.com/photos/1600727/pexels-photo-1600727.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Paneer Sandwich': 'https://images.pexels.com/photos/1603901/pexels-photo-1603901.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Cheese Toast': 'https://images.pexels.com/photos/461431/pexels-photo-461431.jpeg?auto=compress&cs=tinysrgb&w=500',
            
            'Chocolate Cake': 'https://images.pexels.com/photos/291528/pexels-photo-291528.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Ice Cream': 'https://images.pexels.com/photos/1362534/pexels-photo-1362534.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Brownie': 'https://images.pexels.com/photos/1126359/pexels-photo-1126359.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Pastry': 'https://images.pexels.com/photos/140831/pexels-photo-140831.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Tiramisu': 'https://images.pexels.com/photos/6880219/pexels-photo-6880219.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Cheesecake': 'https://images.pexels.com/photos/3026804/pexels-photo-3026804.jpeg?auto=compress&cs=tinysrgb&w=500',
            
            'Croissant': 'https://images.pexels.com/photos/2135/food-france-morning-breakfast.jpg?auto=compress&cs=tinysrgb&w=500',
            'Muffin': 'https://images.pexels.com/photos/2067396/pexels-photo-2067396.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Donut': 'https://images.pexels.com/photos/205961/pexels-photo-205961.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Bagel': 'https://images.pexels.com/photos/1775043/pexels-photo-1775043.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Cookies': 'https://images.pexels.com/photos/230325/pexels-photo-230325.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Garlic Bread': 'https://images.pexels.com/photos/2544829/pexels-photo-2544829.jpeg?auto=compress&cs=tinysrgb&w=500',
            
            'Pizza Margherita': 'https://images.pexels.com/photos/2147491/pexels-photo-2147491.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Veg Burger': 'https://images.pexels.com/photos/1639557/pexels-photo-1639557.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Pasta Alfredo': 'https://images.pexels.com/photos/1279330/pexels-photo-1279330.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Biryani': 'https://images.pexels.com/photos/12737652/pexels-photo-12737652.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Fried Rice': 'https://images.pexels.com/photos/1624487/pexels-photo-1624487.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Noodles': 'https://images.pexels.com/photos/1907244/pexels-photo-1907244.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Dal Tadka': 'https://images.pexels.com/photos/5560763/pexels-photo-5560763.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Paneer Butter Masala': 'https://images.pexels.com/photos/2474661/pexels-photo-2474661.jpeg?auto=compress&cs=tinysrgb&w=500',
            
            'Orange Juice': 'https://images.pexels.com/photos/1446318/pexels-photo-1446318.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Apple Juice': 'https://images.pexels.com/photos/1842337/pexels-photo-1842337.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Mango Shake': 'https://images.pexels.com/photos/775032/pexels-photo-775032.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Watermelon Juice': 'https://images.pexels.com/photos/1337824/pexels-photo-1337824.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Smoothie Bowl': 'https://images.pexels.com/photos/1092730/pexels-photo-1092730.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Lassi': 'https://images.pexels.com/photos/1844487/pexels-photo-1844487.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Mojito': 'https://images.pexels.com/photos/1304540/pexels-photo-1304540.jpeg?auto=compress&cs=tinysrgb&w=500',
            'Hot Chocolate': 'https://images.pexels.com/photos/1549203/pexels-photo-1549203.jpeg?auto=compress&cs=tinysrgb&w=500',
        }
        
        updated_count = 0
        failed_count = 0
        
        for product_name, image_url in image_mappings.items():
            try:
                products = Product.objects.filter(name=product_name)
                
                if not products.exists():
                    continue
                
                product = products.first()
                
                # Skip if product already has an image
                if product.image:
                    self.stdout.write(f'  {product.name} already has an image, skipping...')
                    continue
                
                # Download and save image
                try:
                    response = requests.get(image_url, timeout=15)
                    if response.status_code == 200:
                        image_name = f"{product.id}_{product_name.replace(' ', '_')}.jpg"
                        product.image.save(image_name, ContentFile(response.content), save=True)
                        self.stdout.write(f'+ Updated {product.name} with image')
                        updated_count += 1
                    else:
                        self.stdout.write(f'- Failed to download image for {product.name} (HTTP {response.status_code})')
                        failed_count += 1
                except Exception as e:
                    self.stdout.write(f'- Error downloading image for {product.name}: {str(e)}')
                    failed_count += 1
                    
            except Exception as e:
                self.stdout.write(f'- Error processing {product_name}: {str(e)}')
                failed_count += 1
        
        self.stdout.write(f'\n[DONE] Updated {updated_count} products, {failed_count} failed')
