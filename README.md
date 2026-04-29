# Odoo Cafe POS - Restaurant Point of Sale System

A complete, production-ready Restaurant POS (Point of Sale) system built with Django and Django REST Framework. Features real-time kitchen display, customer-facing screens, self-ordering via QR codes, and comprehensive reporting.

## Features

### Core Features
- **Multi-terminal POS System** - Support for multiple terminals with session management
- **Order Management** - Full order lifecycle from draft to payment
- **Kitchen Display System (KDS)** - Real-time order tickets for kitchen staff
- **Customer Display** - Order information display for customers
- **Self-Ordering** - QR code based table ordering
- **Comprehensive Reporting** - Sales, products, staff performance reports

### Authentication & Security
- JWT-based authentication with refresh tokens
- PIN-based quick login for staff
- Role-based access control (Admin, Manager, Staff, Kitchen)
- Token blacklisting on logout

### Product Management
- Hierarchical categories
- Product variants with attributes
- Modifiers and combo products
- Inventory tracking with low-stock alerts
- Barcode support

### Payment Processing
- Multiple payment methods (Cash, Card, UPI, Wallet)
- Dynamic UPI QR code generation
- Split payments
- Refund management

### Floor & Table Management
- Visual floor plan with drag-and-drop
- Table reservation system
- Real-time table status updates

### Reporting & Analytics
- Dashboard with real-time metrics
- Daily/hourly sales reports
- Product & category performance
- Staff performance tracking
- Session cash summaries
- PDF & Excel export

## Tech Stack

- **Backend Framework**: Django 4.2+
- **API Framework**: Django REST Framework
- **WebSockets**: Django Channels 4.0+
- **Authentication**: djangorestframework-simplejwt
- **Database**: PostgreSQL (SQLite for development)
- **Channel Layer**: Redis (InMemoryChannelLayer for development)
- **Report Generation**: reportlab (PDF), openpyxl (Excel)
- **QR Codes**: qrcode, Pillow

## Project Structure

```
odoo_cafe_pos/
├── apps/
│   ├── core/                 # Base models, utilities, permissions
│   ├── authentication/       # User management, JWT auth
│   ├── products/            # Categories, products, variants
│   ├── payments/            # Payment methods, processing
│   ├── floors/              # Floor & table management
│   ├── terminals/           # POS terminals & sessions
│   ├── orders/              # Order management
│   ├── kitchen/             # Kitchen Display System
│   ├── customers/           # Customer display
│   ├── self_order/          # Self-ordering system
│   └── reports/             # Reporting & analytics
├── odoo_cafe_pos/
│   ├── settings/
│   │   ├── base.py          # Base settings
│   │   ├── local.py         # Development settings
│   │   └── production.py    # Production settings
│   ├── asgi.py              # ASGI configuration
│   ├── wsgi.py              # WSGI configuration
│   └── urls.py              # Main URL configuration
├── requirements.txt
└── manage.py
```

## Installation

### Prerequisites
- Python 3.10+
- PostgreSQL 13+ (optional for development)
- Redis (optional for development)

### Setup

1. **Clone the repository**
   ```bash
   cd "Odoo Cafe POS"
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   # Create .env file or set environment variables
   export DJANGO_SECRET_KEY='your-secret-key'
   export DJANGO_DEBUG=True
   export DJANGO_SETTINGS_MODULE=odoo_cafe_pos.settings.local
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Seed demo data**
   ```bash
   python manage.py seed_data
   ```

7. **Run the development server**
   ```bash
   python manage.py runserver
   ```

The API will be available at `http://localhost:8000/api/v1/`

## API Endpoints

### Authentication
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/signup/` | POST | Register new user |
| `/api/v1/auth/login/` | POST | Login with username/password |
| `/api/v1/auth/pin-login/` | POST | Quick login with PIN |
| `/api/v1/auth/logout/` | POST | Logout (blacklist token) |
| `/api/v1/auth/me/` | GET | Get current user |
| `/api/v1/auth/token/refresh/` | POST | Refresh access token |

### Products
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/products/categories/` | GET, POST | List/create categories |
| `/api/v1/products/` | GET, POST | List/create products |
| `/api/v1/products/pos/` | GET | Get optimized product list for POS |
| `/api/v1/products/by-barcode/<barcode>/` | GET | Find product by barcode |

### Payments
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/payments/methods/` | GET, POST | Payment methods |
| `/api/v1/payments/generate-upi-qr/` | POST | Generate UPI QR code |
| `/api/v1/payments/confirm-upi/` | POST | Confirm UPI payment |
| `/api/v1/payments/` | GET, POST | List/create payments |

### Floor & Tables
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/floors/` | GET, POST | List/create floors |
| `/api/v1/floors/<id>/status/` | GET | Get floor with table status |
| `/api/v1/floors/tables/` | GET, POST | List/create tables |
| `/api/v1/floors/tables/<id>/release/` | POST | Release table |
| `/api/v1/floors/reservations/` | GET, POST | Table reservations |

### Terminals & Sessions
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/terminals/` | GET, POST | List/create terminals |
| `/api/v1/terminals/sessions/` | GET | List sessions |
| `/api/v1/terminals/sessions/open/` | POST | Open new session |
| `/api/v1/terminals/sessions/<id>/close/` | POST | Close session |
| `/api/v1/terminals/sessions/<id>/summary/` | GET | Get session summary |
| `/api/v1/terminals/sessions/<id>/cash-movement/` | POST | Record cash movement |

### Orders
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/orders/` | GET, POST | List/create orders |
| `/api/v1/orders/<id>/send-to-kitchen/` | POST | Send order to kitchen |
| `/api/v1/orders/<id>/mark-ready/` | POST | Mark order as ready |
| `/api/v1/orders/<id>/mark-served/` | POST | Mark order as served |
| `/api/v1/orders/<id>/cancel/` | POST | Cancel order |
| `/api/v1/orders/<id>/add-line/` | POST | Add item to order |
| `/api/v1/orders/<id>/apply-discount/` | POST | Apply discount |

### Kitchen Display
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/kitchen/orders/` | GET | List kitchen orders |
| `/api/v1/kitchen/orders/<id>/bump/` | POST | Bump order to next status |
| `/api/v1/kitchen/orders/<id>/start/` | POST | Start preparing |
| `/api/v1/kitchen/orders/<id>/complete/` | POST | Mark completed |
| `/api/v1/kitchen/orders/stats/` | GET | Kitchen statistics |

### Self-Ordering
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/self-order/initiate/` | POST | Start self-order session |
| `/api/v1/self-order/menu/` | GET | Get menu for ordering |
| `/api/v1/self-order/cart/` | GET, POST | View/add to cart |
| `/api/v1/self-order/cart/item/<id>/` | PUT, DELETE | Update/remove cart item |
| `/api/v1/self-order/submit/` | POST | Submit order |
| `/api/v1/self-order/status/<order_id>/` | GET | Check order status |

### Reports
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/reports/dashboard/` | GET | Dashboard summary |
| `/api/v1/reports/daily-sales/` | GET | Daily sales report |
| `/api/v1/reports/hourly-sales/` | GET | Hourly breakdown |
| `/api/v1/reports/product-sales/` | GET | Product performance |
| `/api/v1/reports/category-sales/` | GET | Category performance |
| `/api/v1/reports/payment-methods/` | GET | Payment breakdown |
| `/api/v1/reports/staff-performance/` | GET | Staff performance |
| `/api/v1/reports/sessions/` | GET | Session summaries |
| `/api/v1/reports/export/` | POST | Export report (PDF/Excel) |

## WebSocket Endpoints

| Endpoint | Description |
|----------|-------------|
| `ws://host/ws/kitchen/<terminal_id>/` | Kitchen display updates |
| `ws://host/ws/customer/<terminal_id>/` | Customer display updates |
| `ws://host/ws/orders/<session_id>/` | POS order updates |

## Default Credentials

After running `python manage.py seed_data`:

| Role | Username | Password | PIN |
|------|----------|----------|-----|
| Admin | admin | admin123 | - |
| Manager | manager1 | password123 | 1234 |
| Staff | cashier1 | password123 | 1234 |
| Kitchen | kitchen1 | password123 | 1234 |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DJANGO_SECRET_KEY` | Django secret key | Required in production |
| `DJANGO_DEBUG` | Debug mode | True |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts | localhost,127.0.0.1 |
| `DB_NAME` | Database name | odoo_cafe_pos |
| `DB_USER` | Database user | postgres |
| `DB_PASSWORD` | Database password | postgres |
| `DB_HOST` | Database host | localhost |
| `DB_PORT` | Database port | 5432 |
| `REDIS_URL` | Redis URL for channels | redis://localhost:6379/0 |

## Development

### Running Tests
```bash
python manage.py test
```

### Code Style
```bash
# Install dev dependencies
pip install flake8 black isort

# Format code
black .
isort .

# Check code
flake8
```

### Creating Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

## Production Deployment

1. Set proper environment variables
2. Use PostgreSQL database
3. Use Redis for channel layer
4. Run with Daphne/Uvicorn for WebSocket support
5. Use Nginx as reverse proxy
6. Enable HTTPS

```bash
# Example production run
daphne -b 0.0.0.0 -p 8000 odoo_cafe_pos.asgi:application
```

## License

This project is licensed under the MIT License.

## Support

For issues and feature requests, please create an issue in the repository.
