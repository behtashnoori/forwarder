# معماری سیستم Forwarder

## نمای کلی سیستم

این پروژه یک سیستم مدیریت حمل و نقل است که شامل دو بخش اصلی می‌باشد:

### 🎨 Frontend (React + Vite + TypeScript)
- **فریمورک**: React 18 با TypeScript
- **Build Tool**: Vite 5.4.19
- **UI Library**: Radix UI + Tailwind CSS
- **State Management**: React Query (TanStack Query)
- **Routing**: React Router DOM
- **Forms**: React Hook Form + Zod validation

### 🚀 Backend (Flask + SQLAlchemy)
- **فریمورک**: Flask 3.0+
- **Database ORM**: SQLAlchemy 2.0+
- **Database**: PostgreSQL (Production) / SQLite (Development)
- **Migration**: Alembic
- **CORS**: Flask-CORS
- **Security**: Flask-Security + JWT

## ساختار فایل‌ها

```
forwarder/
├── backend/                 # Backend Flask application
│   ├── routes/             # API endpoints
│   │   ├── health.py       # Health checks
│   │   ├── locations.py    # Provinces, counties, cities
│   │   ├── shipment_request.py  # Shipment management
│   │   ├── expert_console.py    # Expert panel
│   │   ├── crm.py          # Customer management
│   │   ├── monitoring.py   # System monitoring
│   │   └── admin_panel.py  # Admin functions
│   ├── models.py           # Database models
│   ├── models_expert_console.py  # Expert-specific models
│   ├── cors_config.py      # Dynamic CORS configuration
│   ├── security.py         # Security configuration
│   ├── app_logging.py      # Logging setup
│   └── extensions.py       # Flask extensions
├── src/                    # Frontend React application
│   ├── components/         # React components
│   │   ├── ui/            # Reusable UI components
│   │   ├── LocationForm.tsx
│   │   ├── ExpertLogin.tsx
│   │   └── ...
│   ├── pages/             # Page components
│   │   ├── Index.tsx
│   │   ├── ExpertConsole.tsx
│   │   ├── CRMDashboard.tsx
│   │   └── RequestDetail.tsx
│   ├── lib/               # Utilities and API
│   │   ├── api.ts         # API client
│   │   ├── env.ts         # Environment validation
│   │   └── utils.ts       # Helper functions
│   └── hooks/             # Custom React hooks
├── scripts/               # Development scripts
│   ├── setup-env.js       # Environment setup
│   └── test-api.js        # API testing
└── docs/                  # Documentation
```

## API Endpoints

### 🏥 Health & Monitoring
- `GET /api/health` - Health check
- `GET /api/monitoring/health` - System health
- `GET /api/monitoring/metrics` - System metrics

### 📍 Locations
- `GET /api/provinces` - List all provinces
- `GET /api/counties?province_id={id}` - Counties by province
- `GET /api/cities?county_id={id}` - Cities by county

### 📦 Shipment Management
- `POST /api/shipment-request` - Create shipment request
- `GET /api/shipment-request/ping` - Ping endpoint

### 👨‍💼 Expert Console
- `GET /api/expert/requests` - Get expert requests
- `GET /api/expert/requests/{id}` - Get request details
- `POST /api/expert/requests/{id}/assign` - Assign request
- `POST /api/expert/requests/{id}/status` - Update status
- `POST /api/expert/auth/login` - Expert login
- `GET /api/expert/dashboard/kpis` - Dashboard KPIs

### 🏢 CRM
- `GET /api/crm/customers` - List customers
- `POST /api/crm/customers` - Create customer
- `GET /api/crm/opportunities` - List opportunities
- `GET /api/crm/dashboard/kpis` - CRM KPIs

### 🔧 Admin Panel
- `GET /api/shipment-requests` - All shipment requests
- `GET /api/shipment-requests/{id}` - Request details

## Database Schema

### Core Tables
- **Provinces**: استان‌ها
- **Counties**: شهرستان‌ها
- **Cities**: شهرها
- **Customers**: مشتریان
- **ShipmentRequests**: درخواست‌های حمل

### Expert Console Tables
- **ExpertUsers**: کاربران متخصص
- **ExpertRequests**: درخواست‌های متخصص
- **ExpertMessages**: پیام‌های متخصص

### CRM Tables
- **Opportunities**: فرصت‌های فروش
- **Activities**: فعالیت‌های CRM

## Security Architecture

### 🔐 Authentication & Authorization
- **Expert Users**: JWT-based authentication
- **API Security**: CORS + Security headers
- **Password Security**: bcrypt hashing

### 🛡️ Security Headers
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- X-XSS-Protection: 1; mode=block
- Content-Security-Policy: Comprehensive CSP

## Environment Configuration

### Frontend (.env)
```env
VITE_API_URL=http://127.0.0.1:5000
VITE_APP_NAME=Forwarder App
VITE_APP_VERSION=1.0.0
```

### Backend (.env)
```env
DATABASE_URL=postgresql+psycopg2://...
CORS_ORIGIN=http://localhost:8109,...
SLA_HOURS=2
SECRET_KEY=...
JWT_SECRET_KEY=...
FLASK_ENV=development
```

## CORS Configuration

### 🌐 Dynamic CORS Origins
سیستم CORS به صورت پویا تمام پورت‌های توسعه را پشتیبانی می‌کند:
- پورت‌های رایج: 3000, 5173, 8080
- محدوده Vite: 8080-8200
- localhost و 127.0.0.1
- پشتیبانی از origins سفارشی

### 🔧 CORS Headers
- Access-Control-Allow-Origin: Dynamic
- Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS, PATCH
- Access-Control-Allow-Headers: Content-Type, Authorization, etc.
- Access-Control-Allow-Credentials: true
- Access-Control-Max-Age: 3600

## Development Workflow

### 🚀 Quick Start
```bash
# 1. Setup environment
npm run setup:env

# 2. Start backend
$env:FLASK_APP = "backend.wsgi"
$env:FLASK_ENV = "development"
flask run

# 3. Start frontend
npm run dev

# 4. Test API
npm run test:api
```

### 🧪 Testing
- **API Tests**: `npm run test:api`
- **Environment Setup**: `npm run setup:env`
- **Linting**: `npm run lint`

## Performance Considerations

### 📊 Database
- Indexed queries for locations
- Relationship optimization
- Connection pooling

### 🚀 Frontend
- React Query for caching
- Code splitting
- Lazy loading components

### 🔧 Backend
- Flask debug mode for development
- Production WSGI server recommended
- Database connection optimization

## Deployment Architecture

### 🏗️ Production Setup
- **Frontend**: Static files (Nginx/Apache)
- **Backend**: Gunicorn/uWSGI
- **Database**: PostgreSQL
- **Reverse Proxy**: Nginx
- **SSL/TLS**: Let's Encrypt

### 📦 Container Deployment
- Docker containers for each service
- Docker Compose for orchestration
- Environment-specific configurations

## Monitoring & Logging

### 📝 Logging
- Application logs: `instance/logs/app.log`
- API logs: `instance/logs/api.log`
- Error logs: `instance/logs/error.log`
- Security logs: `instance/logs/security.log`

### 📊 Monitoring
- Health check endpoints
- System metrics
- Database monitoring
- Performance analytics

## Best Practices

### 🎯 Code Quality
- TypeScript for type safety
- ESLint for code quality
- Consistent naming conventions
- Comprehensive error handling

### 🔒 Security
- Input validation
- SQL injection prevention
- XSS protection
- CSRF protection

### 📈 Scalability
- Modular architecture
- Database optimization
- Caching strategies
- Load balancing ready

این معماری برای توسعه و نگهداری آسان طراحی شده و قابلیت گسترش دارد.
