# InvoiceForge - Invoice & Billing Management System

A production-grade invoice and billing management platform built with Django, Django REST Framework, Vue.js 3, PostgreSQL, Redis, and Celery. InvoiceForge provides comprehensive tools for creating invoices, managing clients, tracking payments, generating PDF documents, sending email notifications, and analyzing financial data.

---

## Features

- **Invoice Management**: Create, edit, duplicate, and send professional invoices with customizable templates and automatic numbering.
- **Recurring Invoices**: Configure automatic invoice generation on daily, weekly, monthly, quarterly, or yearly schedules.
- **Client Management**: Maintain a full client database with contacts, notes, billing history, and outstanding balance tracking.
- **Payment Tracking**: Record payments against invoices with support for partial payments, overpayments, and refunds.
- **Estimates / Quotes**: Create estimates and convert accepted estimates directly into invoices.
- **PDF Generation**: Produce polished PDF invoices and estimates using ReportLab with your business branding.
- **Email Delivery**: Send invoices and payment reminders via email with PDF attachments through Celery background tasks.
- **Multi-Currency**: Issue invoices in any currency with configurable exchange rates per client.
- **Tax Handling**: Define multiple tax rates per line item with compound and inclusive tax support.
- **Financial Dashboards**: Real-time revenue charts, accounts receivable aging, top clients, monthly trends, and tax summaries.
- **Authentication & Authorization**: JWT-based authentication with role-based access, user registration, and profile management.
- **Docker Ready**: Full Docker Compose setup for development and production with Nginx reverse proxy.

---

## Tech Stack

| Layer       | Technology                                    |
|-------------|-----------------------------------------------|
| Backend     | Python 3.11, Django 4.2, Django REST Framework |
| Frontend    | Vue.js 3 (Composition API), Vuex, Vue Router  |
| Database    | PostgreSQL 15                                 |
| Cache/Broker| Redis 7                                       |
| Task Queue  | Celery 5                                      |
| PDF Engine  | ReportLab                                     |
| HTTP Server | Gunicorn + Nginx                              |
| Containers  | Docker, Docker Compose                        |

---

## Project Structure

```
InvoiceForge/
├── backend/
│   ├── apps/
│   │   ├── accounts/       # User and business profile management
│   │   ├── clients/        # Client, contact, and notes
│   │   ├── invoices/       # Invoice, line items, recurring, templates
│   │   ├── payments/       # Payment recording, refunds
│   │   ├── estimates/      # Estimates and quote management
│   │   └── reports/        # Financial analytics and reporting
│   ├── config/
│   │   ├── settings/       # Split settings (base, dev, prod)
│   │   ├── celery.py       # Celery application
│   │   ├── urls.py         # Root URL configuration
│   │   └── wsgi.py         # WSGI entry point
│   ├── utils/              # Shared utilities (PDF, pagination, exceptions)
│   ├── manage.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/            # Axios API modules
│   │   ├── components/     # Reusable Vue components
│   │   ├── views/          # Page-level views
│   │   ├── router/         # Vue Router configuration
│   │   ├── store/          # Vuex store modules
│   │   ├── App.vue
│   │   └── main.js
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── nginx/
│   └── nginx.conf
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## Getting Started

### Prerequisites

- Docker and Docker Compose installed
- Git

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/invoiceforge.git
   cd invoiceforge
   ```

2. **Copy environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your own values (SECRET_KEY, database credentials, email settings)
   ```

3. **Build and start all services**
   ```bash
   docker-compose up --build -d
   ```

4. **Run database migrations**
   ```bash
   docker-compose exec backend python manage.py migrate
   ```

5. **Create a superuser**
   ```bash
   docker-compose exec backend python manage.py createsuperuser
   ```

6. **Access the application**
   - Frontend: [http://localhost](http://localhost)
   - Backend API: [http://localhost/api/](http://localhost/api/)
   - Django Admin: [http://localhost/admin/](http://localhost/admin/)

### Local Development (without Docker)

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
export DJANGO_SETTINGS_MODULE=config.settings.development
python manage.py migrate
python manage.py runserver
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Celery Worker:**
```bash
cd backend
celery -A config worker -l info
```

**Celery Beat (scheduler):**
```bash
cd backend
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

---

## API Documentation

Once the backend is running, interactive API documentation is available at:

- Swagger UI: `/api/docs/`
- ReDoc: `/api/redoc/`

### Key Endpoints

| Resource          | Endpoint                    | Methods                        |
|-------------------|-----------------------------|--------------------------------|
| Authentication    | `/api/auth/login/`          | POST                           |
| Registration      | `/api/auth/register/`       | POST                           |
| Business Profile  | `/api/accounts/profile/`    | GET, PUT, PATCH                |
| Clients           | `/api/clients/`             | GET, POST, PUT, PATCH, DELETE  |
| Invoices          | `/api/invoices/`            | GET, POST, PUT, PATCH, DELETE  |
| Send Invoice      | `/api/invoices/{id}/send/`  | POST                           |
| Record Payment    | `/api/payments/`            | GET, POST                      |
| Estimates         | `/api/estimates/`           | GET, POST, PUT, PATCH, DELETE  |
| Convert Estimate  | `/api/estimates/{id}/convert/` | POST                        |
| Revenue Report    | `/api/reports/revenue/`     | GET                            |
| Dashboard Stats   | `/api/reports/dashboard/`   | GET                            |

---

## Environment Variables

See `.env.example` for a full list. Key variables:

| Variable              | Description                              |
|-----------------------|------------------------------------------|
| `SECRET_KEY`          | Django secret key                        |
| `DATABASE_URL`        | PostgreSQL connection string             |
| `REDIS_URL`           | Redis connection string                  |
| `EMAIL_HOST`          | SMTP server hostname                     |
| `EMAIL_HOST_USER`     | SMTP username                            |
| `EMAIL_HOST_PASSWORD` | SMTP password                            |
| `DEFAULT_CURRENCY`    | Default invoice currency (e.g., USD)     |
| `COMPANY_NAME`        | Your business name for PDF headers       |

---

## Testing

```bash
# Backend tests
docker-compose exec backend python manage.py test

# Frontend tests
docker-compose exec frontend npm run test
```

---

## Deployment

For production deployment:

1. Set `DJANGO_SETTINGS_MODULE=config.settings.production` in `.env`.
2. Set `DEBUG=False` and configure `ALLOWED_HOSTS`.
3. Configure a proper `SECRET_KEY`.
4. Set up SSL certificates and update `nginx.conf` for HTTPS.
5. Configure a production-grade SMTP provider.
6. Run `docker-compose -f docker-compose.yml up --build -d`.

---

## License

This project is licensed under the MIT License. See the LICENSE file for details.
