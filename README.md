# Condomínios Manager

A comprehensive property management system for rental properties in Brazil, built with Django REST Framework and Next.js.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Django](https://img.shields.io/badge/Django-5.0-green.svg)
![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)
![TypeScript](https://img.shields.io/badge/TypeScript-5.0-blue.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-316192.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Tests](https://img.shields.io/badge/Tests-600+-brightgreen.svg)
![Coverage](https://img.shields.io/badge/Coverage-83.86%25-brightgreen.svg)

## Features

### Property Management
- **Buildings**: Manage multiple buildings with address, utilities, and common expenses
- **Apartments**: Track apartments with bedrooms, floor, position, and rental values
- **Furniture Inventory**: Track furniture condition and assignment to apartments/tenants

### Tenant Management
- **Tenant Registry**: Store tenant information with CPF/CNPJ validation
- **Dependents**: Track tenant dependents and family members
- **Multi-step Wizard**: 6-step form for complete tenant registration

### Lease Management
- **Lease Tracking**: Manage active, expired, and terminated leases
- **Multiple Tenants**: Support for multiple tenants per lease
- **Contract Generation**: Automatic PDF contract generation with customizable templates
- **Late Fee Calculator**: Calculate late payment fees
- **Due Date Changes**: Track and calculate fees for due date changes

### Dashboard & Analytics
- **Financial Summary**: Total revenue, average rent, collected fees
- **Late Payments**: Track overdue leases with amounts
- **Lease Metrics**: Expiring leases (30/60/90 days), occupancy rates
- **Tenant Statistics**: Demographics breakdown
- **Building Analytics**: Per-building revenue and occupancy

### Contract Template Editor
- **Monaco Editor**: HTML editing with syntax highlighting
- **Live Preview**: See changes with sample data
- **Auto-Backup**: Automatic backup on save
- **Version History**: Restore from previous backups

## Tech Stack

### Backend
- **Django 5.0.2** with Django REST Framework 3.14
- **PostgreSQL 15+** database
- **JWT Authentication** with SimpleJWT
- **Google OAuth2** integration
- **Pyppeteer** for PDF generation (Chrome headless)

### Frontend
- **Next.js 14** with App Router
- **React 18** with TypeScript
- **Ant Design 5** + Tailwind CSS
- **TanStack Query v5** for server state
- **Zustand** for client state
- **React Hook Form** + Zod validation
- **Monaco Editor** for template editing

### Testing
- **Backend**: pytest with pytest-django (523 tests, 83.86% coverage)
- **Frontend**: Vitest + React Testing Library + MSW (93 tests)

## Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **PostgreSQL 15+**
- **Google Chrome** (for PDF generation)
- **Redis** (optional, for caching)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/condominios_manager.git
cd condominios_manager
```

### 2. Backend Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development/testing

# Copy environment file
cp .env.example .env
# Edit .env with your settings

# Create database
createdb condominio  # Or use pgAdmin/psql

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy environment file
cp .env.example .env.local
# Edit .env.local with your settings

# Run development server
npm run dev
```

### 4. Access the Application

- **Frontend**: http://localhost:4000
- **Backend API**: http://localhost:8000/api/
- **Django Admin**: http://localhost:8000/admin/

## Environment Variables

### Backend (.env)

```env
# Required
SECRET_KEY=your-secret-key-here
DEBUG=True
DATABASE_URL=postgres://postgres:postgres@localhost:5432/condominio
ALLOWED_HOSTS=localhost,127.0.0.1

# Optional - Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Optional - Redis Cache
REDIS_URL=redis://localhost:6379/0
```

### Frontend (.env.local)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

## Database Management

### Creating a Backup

```bash
# Using the backup script
python scripts/backup_db.py

# Output: backups/backup_condominio_20250113_120000.backup
```

### Restoring from Backup

```bash
# Using the restore script
python scripts/restore_db.py backups/backup_condominio_20250113_120000.backup

# Or manually with pg_restore
pg_restore -d condominio -c backups/backup_condominio_20250113_120000.backup
```

### Manual PostgreSQL Commands

```bash
# Create backup
pg_dump -Fc condominio > backup.backup

# Restore backup
pg_restore -d condominio -c backup.backup

# Create database from scratch
createdb condominio
python manage.py migrate
```

## Docker Setup

### Development

```bash
# Start all services (PostgreSQL, Redis, Backend, Frontend)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production

```bash
# Start with production config
docker-compose -f docker-compose.prod.yml up -d
```

## Running Tests

### Backend Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=core --cov-report=html

# Run specific test categories
pytest tests/unit/                    # Unit tests
pytest tests/integration/             # Integration tests
pytest tests/e2e/                     # End-to-end tests

# Run specific test file
pytest tests/unit/test_models.py

# Run with verbose output
pytest -v --tb=short
```

### Frontend Tests

```bash
cd frontend

# Run all tests
npm run test

# Run in watch mode
npm run test:watch

# Run with coverage
npm run test:coverage
```

## Code Quality

### Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit
pre-commit install

# Run manually
pre-commit run --all-files
```

### Linting

```bash
# Backend
flake8 core/
black core/ --check
isort core/ --check

# Frontend
cd frontend
npm run lint
npm run type-check
```

## API Documentation

### Authentication

```bash
# Login (get tokens)
POST /api/token/
{
  "username": "admin",
  "password": "password"
}

# Response
{
  "access": "eyJ0eXAi...",
  "refresh": "eyJ0eXAi..."
}

# Refresh token
POST /api/token/refresh/
{
  "refresh": "eyJ0eXAi..."
}
```

### CRUD Endpoints

All resources support standard REST operations:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/{resource}/` | List all (paginated) |
| POST | `/api/{resource}/` | Create new |
| GET | `/api/{resource}/{id}/` | Get by ID |
| PUT | `/api/{resource}/{id}/` | Full update |
| PATCH | `/api/{resource}/{id}/` | Partial update |
| DELETE | `/api/{resource}/{id}/` | Delete |

**Available Resources**: `buildings`, `apartments`, `tenants`, `leases`, `furnitures`, `dependents`

### Special Endpoints

```bash
# Generate contract PDF
POST /api/leases/{id}/generate_contract/

# Calculate late fee
GET /api/leases/{id}/calculate_late_fee/

# Dashboard data
GET /api/dashboard/financial_summary/
GET /api/dashboard/late_payment_summary/
GET /api/dashboard/lease_metrics/
GET /api/dashboard/tenant_statistics/
GET /api/dashboard/building_statistics/

# Contract template
GET /api/templates/current/
POST /api/templates/save/
GET /api/templates/backups/
POST /api/templates/restore/
POST /api/templates/preview/

# Export data
GET /api/{resource}/export/excel/
GET /api/{resource}/export/csv/
```

## Project Structure

```
condominios_manager/
├── core/                       # Django app
│   ├── models.py              # Data models
│   ├── serializers.py         # DRF serializers
│   ├── views.py               # API viewsets
│   ├── viewsets/              # Specialized viewsets
│   ├── services/              # Business logic
│   ├── validators/            # CPF/CNPJ validation
│   ├── middleware/            # Request logging
│   └── templates/             # Contract templates
├── tests/                      # Backend tests
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   └── e2e/                   # End-to-end tests
├── frontend/                   # Next.js app
│   ├── app/                   # App Router pages
│   ├── components/            # React components
│   ├── lib/                   # Utilities & hooks
│   ├── store/                 # Zustand stores
│   └── tests/                 # Frontend tests
├── scripts/                    # Utility scripts
│   ├── backup_db.py           # Database backup
│   └── restore_db.py          # Database restore
├── backups/                    # Database backups
├── contracts/                  # Generated PDFs
├── docker-compose.yml          # Docker config
├── requirements.txt            # Python dependencies
└── CLAUDE.md                   # AI assistant instructions
```

## Brazilian-Specific Features

- **CPF/CNPJ Validation**: Full checksum validation for Brazilian tax IDs
- **Currency Formatting**: R$ 1.500,00 (Brazilian Real format)
- **Date Formatting**: DD/MM/YYYY
- **Marital Status**: Brazilian options (Solteiro(a), Casado(a), etc.)
- **Contract Language**: Portuguese contract templates
- **Currency in Words**: num2words integration for Portuguese

## Known Limitations

1. **PDF Generation**: Requires Chrome/Chromium installed
2. **Late Fee Calculation**: Assumes 30-day months
3. **Payment Tracking**: No partial payment support
4. **Multi-tenancy**: Single organization design
5. **Localization**: Brazilian Portuguese only

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 for Python code
- Use TypeScript strict mode for frontend
- Write tests for new features
- Update documentation as needed
- Run pre-commit hooks before committing

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Django REST Framework](https://www.django-rest-framework.org/)
- [Next.js](https://nextjs.org/)
- [Ant Design](https://ant.design/)
- [TanStack Query](https://tanstack.com/query)
- [Monaco Editor](https://microsoft.github.io/monaco-editor/)

---

For detailed technical documentation, see [CLAUDE.md](CLAUDE.md).
