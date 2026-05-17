<div align="center">

# BillFlow

_Production-grade платформа для управления счетами, клиентами, платежами и финансовой отчётностью. Multi-tenant, multi-currency, готова к развёртыванию в Docker._

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-4.2-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.15-A30000?logo=django&logoColor=white)](https://www.django-rest-framework.org/)
[![Vue](https://img.shields.io/badge/Vue.js-3-4FC08D?logo=vuedotjs&logoColor=white)](https://vuejs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![Celery](https://img.shields.io/badge/Celery-5-37814A?logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

</div>

---

## Автор

- **Nodir Odilov**
- GitHub: [https://github.com/NodirOdilov](https://github.com/NodirOdilov)

---

## Содержание

- [1. О проекте](#1-о-проекте)
- [2. Ключевые возможности](#2-ключевые-возможности)
- [3. Технологический стек](#3-технологический-стек)
- [4. Структура репозитория](#4-структура-репозитория)
- [5. Архитектура и как это работает](#5-архитектура-и-как-это-работает)
- [6. Доменная модель (крупными блоками)](#6-доменная-модель-крупными-блоками)
- [7. Сервисы в Docker Compose](#7-сервисы-в-docker-compose)
- [8. Быстрый старт (локально, Docker)](#8-быстрый-старт-локально-docker)
- [9. Ручной запуск без Docker](#9-ручной-запуск-без-docker)
- [10. Конфигурация и переменные окружения](#10-конфигурация-и-переменные-окружения)
- [11. API, очереди и интеграции](#11-api-очереди-и-интеграции)
- [12. Фоновые задачи и расписание Celery](#12-фоновые-задачи-и-расписание-celery)
- [13. Мониторинг и эксплуатация](#13-мониторинг-и-эксплуатация)
- [14. Тестирование](#14-тестирование)
- [15. CI/CD](#15-cicd)
- [16. Роли компонентов в продакшене](#16-роли-компонентов-в-продакшене)
- [17. Лицензия](#17-лицензия)
- [18. Поддержка](#18-поддержка)

---

## 1. О проекте

**BillFlow** — это **продуктовая SaaS-платформа** для управления счетами и биллингом. Система покрывает полный цикл работы с клиентами: от создания клиентской базы и выставления счетов до приёма платежей, формирования финансовых отчётов и автоматических напоминаний. Решение рассчитано на малый и средний бизнес, фрилансеров и финансовых менеджеров — от локальной разработки до production.

### Что это за тип системы

По архитектуре BillFlow — **многосервисная распределённая платформа** (не монолит «в одном процессе»):

| Аспект              | Описание                                                                              |
|---------------------|---------------------------------------------------------------------------------------|
| Продукт             | B2B/SMB-сервис управления счетами с тарифами, лимитами и подписками                   |
| Архитектура         | REST API (Django + DRF) + SPA-фронтенд (Vue 3) + воркеры (Celery) + очередь (Redis)   |
| Состояние           | PostgreSQL (бизнес-данные), Redis (кеш, брокер, throttling), файловое хранилище (PDF) |
| Аутентификация      | JWT (access + refresh) с rotation и blacklist                                         |
| Доставка артефактов | Email с PDF-вложениями (через SMTP, выполняется в Celery-воркерах)                    |
| Развёртывание       | Docker Compose: единая команда поднимает API, БД, кеш, воркеры и reverse proxy        |

### Для кого

- **Фрилансеры и самозанятые** — быстрая выписка счетов, отслеживание оплат
- **Малый и средний бизнес** — клиентская база, регулярные счета (subscriptions), отчётность
- **Бухгалтеры и финансовые менеджеры** — мульти-валютность, налоговые отчёты, accounts receivable aging
- **Команды с разделёнными ролями** — RBAC на 4 уровня (Admin / Manager / Accountant / Viewer)

---

## 2. Ключевые возможности

### Управление счетами
- Создание, редактирование, дублирование и отправка счетов с настраиваемой нумерацией (`INV-00001`)
- Поддержка **частичных платежей**, **переплат** и **возвратов** с автоматическим пересчётом баланса
- Статусы: `Draft → Sent → Viewed → Partial → Paid` (+ `Overdue`, `Cancelled`)
- Автоматическая маркировка просроченных счетов (Celery Beat, ежедневно)

### Регулярные счета (subscriptions)
- 7 частот: daily, weekly, bi-weekly, monthly, quarterly, semi-annual, yearly
- Ограничение по дате окончания или количеству выпусков (`max_occurrences`)
- Опция auto-send: автоматическая отправка сгенерированного счёта клиенту

### Клиенты и контакты
- Полноценный CRM-блок: компании, контактные лица, заметки, история выставленных счетов
- CSV-импорт клиентов одним вызовом сервиса
- Вычисляемые свойства: `total_invoiced`, `total_paid`, `outstanding_balance`

### Платежи и возвраты
- 9 типов методов оплаты: bank transfer, card, PayPal, Stripe, wire, cash, check, …
- Возвраты с указанием причины (overpayment, cancellation, defective, duplicate, …)
- Защита от переплат через `PaymentExceedsBalance` exception

### Сметы (Estimates / Quotes)
- Жизненный цикл: `Draft → Sent → Viewed → Accepted → Converted` (+ `Declined`, `Expired`)
- One-click конвертация принятой сметы в полноценный счёт
- Срок действия с автоматической пометкой `is_expired`

### Налоги и валюты
- Multi-currency: ISO 4217 codes, валидация на уровне модели
- Налоги на уровне строки счёта: `exclusive` или `inclusive`
- Скидки: процентные и фиксированные (с защитой от отрицательных значений)

### PDF и Email
- Генерация PDF на ReportLab с брендингом (логотип, footer, terms)
- Отправка счетов и напоминаний через Celery (3 retry с экспоненциальной задержкой)
- Welcome email при регистрации, data export по запросу (GDPR-friendly)

### Безопасность и audit
- JWT с rotation + blacklist, RBAC на 4 роли
- Throttling: `100/hour` для анонимных, `1000/hour` для авторизованных
- **Audit middleware** — логирует все мутирующие запросы (POST/PUT/PATCH/DELETE) с IP и user
- **Rate limit middleware** — sliding window counter с cache backend
- **Request logging middleware** — каждый запрос с `X-Request-ID` для distributed tracing

### Финансовая аналитика
- Real-time dashboard: revenue, MRR, top clients, monthly trends
- Accounts Receivable Aging (0-30, 31-60, 61-90, 90+ дней)
- Tax summary по периодам

---

## 3. Технологический стек

| Слой              | Технология                                                                   |
|-------------------|------------------------------------------------------------------------------|
| **Backend**       | Python 3.11, Django 4.2.11, Django REST Framework 3.15.1                     |
| **Auth**          | `djangorestframework-simplejwt` 5.3.1 (rotation + blacklist)                 |
| **API docs**      | `drf-spectacular` 0.27.2 (OpenAPI 3, Swagger UI, ReDoc)                      |
| **Frontend**      | Vue.js 3 (Composition API), Vue Router, Vuex, Vite                           |
| **БД**            | PostgreSQL 15-alpine                                                         |
| **Cache/Broker**  | Redis 7-alpine                                                               |
| **Очередь задач** | Celery 5.4.0, `django-celery-beat` 2.6.0, `django-celery-results` 2.5.1      |
| **HTTP-сервер**   | Gunicorn 22.0.0 (4 workers, timeout 120s)                                    |
| **Reverse proxy** | Nginx 1.25-alpine                                                            |
| **Static files**  | WhiteNoise 6.6.0 (compressed manifest storage)                               |
| **PDF**           | ReportLab 4.2.0, Pillow 10.3.0                                               |
| **Конфигурация**  | `python-decouple` 3.8, `dj-database-url` 2.1.0                               |
| **Контейнеры**    | Docker, Docker Compose                                                       |

---

## 4. Структура репозитория

```text
BillFlow/
├── backend/
│   ├── apps/
│   │   ├── accounts/         # User, BusinessProfile, провижининг, data export
│   │   ├── clients/          # Client, ClientContact, ClientNote, CSV import
│   │   ├── invoices/         # Invoice, InvoiceLine, RecurringInvoice, InvoiceTemplate
│   │   │   └── tasks.py      # 5 Celery-тасков
│   │   ├── payments/         # Payment, PaymentMethod, Refund
│   │   ├── estimates/        # Estimate, EstimateLine + конвертация в счёт
│   │   └── reports/          # Revenue, dashboard, aging, tax summary
│   ├── config/
│   │   ├── settings/         # base.py / development.py / production.py
│   │   ├── celery.py         # Celery app + beat schedule + task routing
│   │   ├── urls.py           # Root URLConf + OpenAPI endpoints
│   │   └── wsgi.py
│   ├── middleware/
│   │   ├── audit.py          # AuditLogMiddleware
│   │   ├── rate_limit.py     # APIRateLimitMiddleware
│   │   └── request_logging.py
│   ├── utils/
│   │   ├── pdf_generator.py  # InvoicePDFGenerator (ReportLab)
│   │   ├── pagination.py     # StandardResultsSetPagination
│   │   ├── permissions.py    # IsAdminUser, IsManagerOrAbove, IsOwnerOrAdmin, …
│   │   ├── exceptions.py     # BillFlowException + 6 доменных исключений
│   │   └── validators.py     # phone, currency, tax_rate, line_item, …
│   ├── manage.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   └── src/
│       ├── api/              # Axios-обёртки над REST API
│       ├── components/       # auth, clients, dashboard, invoices, layout, payments
│       ├── views/            # Pages
│       ├── router/           # Vue Router
│       └── store/modules/    # Vuex modules
├── nginx/
│   └── nginx.conf            # Reverse proxy, gzip, кеш static/media
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## 5. Архитектура и как это работает

### Поток запроса (request lifecycle)

```text
   Browser / Mobile / Integrator
              │
              ▼
       Nginx (:80) ──── reverse proxy + gzip
              │
   ┌──────────┴──────────┐
   ▼                     ▼
 Vue SPA           Django + Gunicorn (:8000)
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
   PostgreSQL        Redis           Celery Worker
   (бизнес-         (cache,        (PDF, email,
    данные)          broker,         recurring,
                     throttle)       reminders)
                        │
                        ▼
                   Celery Beat
                   (расписание)
```

### Ключевые принципы

1. **Тонкие views, толстые сервисы.** Views только сериализуют и роутят; вся бизнес-логика — в `apps/<module>/services.py`.
2. **Денормализация для производительности.** Поля `subtotal`, `tax_amount`, `total`, `balance_due` хранятся на модели `Invoice` и пересчитываются в `calculate_totals()` при изменении line items.
3. **Целостность через доменные исключения.** Невалидные переходы (например, оплата уже оплаченного счёта) бросают `InvoiceAlreadyPaid`, `PaymentExceedsBalance` и автоматически конвертируются в `400 Bad Request` стандартизированным handler-ом.
4. **Async-first для дорогих операций.** Генерация PDF, отправка email, регулярные счета, напоминания, проверка просрочек — всё в Celery с retry-политикой.
5. **Multi-tenancy через `user` FK.** Каждая бизнес-сущность (Invoice, Client, Payment) привязана к пользователю; данные изолированы на уровне ORM-фильтров.

---

## 6. Доменная модель (крупными блоками)

### Accounts
- **`User`** — кастомная модель с email вместо username, UUID primary key, 4 роли (`Admin`, `Manager`, `Accountant`, `Viewer`).
- **`BusinessProfile`** — 1-к-1 к User: реквизиты компании, логотип, налоговый ID (EIN/VAT/GST/ABN), счётчики автонумерации (`next_invoice_number`, `next_estimate_number`), дефолтные `currency`, `payment_terms`, `tax_rate`.

### Clients
- **`Client`** — название, компания, контакты, адрес, валюта по умолчанию, payment terms, статус (`active`/`inactive`/`archived`).
- **`ClientContact`** — дополнительные контактные лица с пометкой `is_primary`.
- **`ClientNote`** — внутренние заметки от менеджера.
- **Computed properties**: `total_invoiced`, `total_paid`, `outstanding_balance` — агрегаты по связанным счетам и платежам.

### Invoices
- **`Invoice`** — ядро системы. UUID PK, FK на `User` и `Client`, статусы, валюта, денормализованные суммы, прикреплённый PDF, метки `sent_at` / `viewed_at` / `paid_at`.
- **`InvoiceLine`** — позиция счёта с поддержкой tax-exclusive / tax-inclusive расчётов.
- **`RecurringInvoice`** + **`RecurringInvoiceLine`** — шаблон для регулярной генерации с частотой, датой начала/окончания и max_occurrences.
- **`InvoiceTemplate`** — переиспользуемые шаблоны (line items в JSONField).

### Payments
- **`PaymentMethod`** — 9 типов: bank_transfer, credit_card, debit_card, check, cash, paypal, stripe, wire, other.
- **`Payment`** — сумма, валюта, дата, статус (`pending`/`completed`/`failed`/`refunded`/`partially_refunded`), reference number.
- **`Refund`** — частичный или полный возврат с причиной (overpayment, cancellation, defective, duplicate, customer_request, other).

### Estimates
- **`Estimate`** — смета/quote с lifecycle от `draft` до `converted`. Срок действия (`expiry_date`) с автоматическим `is_expired`.
- **`EstimateLine`** — позиции, аналогично `InvoiceLine`.
- **One-click convert**: принятая смета создаёт `Invoice` с FK `source_estimate`.

### Reports
- Без хранимых моделей — derived data из `Invoice`, `Payment`, `Client`.
- Сервисы: `RevenueReportService`, `DashboardStatsService` — агрегаты, MRR, top clients, AR aging, tax summary.

---

## 7. Сервисы в Docker Compose

| Сервис          | Образ / Build           | Порт      | Назначение                                                    |
|-----------------|-------------------------|-----------|---------------------------------------------------------------|
| `db`            | `postgres:15-alpine`    | 5432      | Основная база данных. Healthcheck через `pg_isready`.         |
| `redis`         | `redis:7-alpine`        | 6379      | Кеш, broker для Celery, sliding-window для rate limiting.     |
| `backend`       | `./backend/Dockerfile`  | 8000      | Django + Gunicorn (4 workers, timeout 120s). Авто-миграции.   |
| `celery_worker` | `./backend/Dockerfile`  | —         | Celery worker (`--concurrency=4`). Очереди: invoices, payments, notifications. |
| `celery_beat`   | `./backend/Dockerfile`  | —         | Celery Beat с `DatabaseScheduler` (расписание в БД).          |
| `frontend`      | `./frontend/Dockerfile` | 5173      | Vue 3 + Vite dev server (или production build).               |
| `nginx`         | `nginx:1.25-alpine`     | 80        | Reverse proxy, gzip, кеширование `/static/` и `/media/`.      |

**Healthcheck-зависимости:** `backend`, `celery_worker`, `celery_beat` ждут `service_healthy` для `db` и `redis`. `celery_*` дополнительно ждут запуска `backend`.

**Volumes:**
- `postgres_data` — данные PostgreSQL
- `redis_data` — AOF persistence Redis
- `static_volume` — collectstatic артефакты (читаются и backend, и nginx)
- `media_volume` — пользовательские загрузки (логотипы, PDF)

---

## 8. Быстрый старт (локально, Docker)

### Предусловия

- Docker 20.10+ и Docker Compose v2
- Git
- 4 GB свободной RAM, 2 GB на диске

### Шаги

1. **Клонировать репозиторий:**
   ```bash
   git clone https://github.com/NodirOdilov/billflow.git
   cd billflow
   ```

2. **Подготовить `.env`:**
   ```bash
   cp .env.example .env
   # Откройте .env и пропишите SECRET_KEY, SMTP-креды, COMPANY_NAME, …
   ```

3. **Поднять всё одной командой:**
   ```bash
   docker-compose up --build -d
   ```

4. **Применить миграции** (если auto-migrate не сработал):
   ```bash
   docker-compose exec backend python manage.py migrate
   ```

5. **Создать суперпользователя:**
   ```bash
   docker-compose exec backend python manage.py createsuperuser
   ```

6. **Открыть приложение:**
   - Frontend SPA: [http://localhost](http://localhost)
   - REST API: [http://localhost/api/](http://localhost/api/)
   - Swagger UI: [http://localhost/api/docs/](http://localhost/api/docs/)
   - ReDoc: [http://localhost/api/redoc/](http://localhost/api/redoc/)
   - Django Admin: [http://localhost/admin/](http://localhost/admin/)

### Полезные команды

```bash
# Логи всех сервисов
docker-compose logs -f

# Логи только worker-а
docker-compose logs -f celery_worker

# Открыть Django shell
docker-compose exec backend python manage.py shell

# Сбросить базу (осторожно!)
docker-compose down -v && docker-compose up --build -d
```

---

## 9. Ручной запуск без Docker

### Backend

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

pip install -r requirements.txt

export DJANGO_SETTINGS_MODULE=config.settings.development   # PowerShell: $env:DJANGO_SETTINGS_MODULE="..."
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

### Celery worker

```bash
cd backend
celery -A config worker -l info --concurrency=4
```

### Celery beat (планировщик)

```bash
cd backend
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Открыть http://localhost:5173
```

---

## 10. Конфигурация и переменные окружения

Все настройки читаются через `python-decouple` из `.env`. Полный список — в [.env.example](.env.example).

### Django

| Переменная                | По умолчанию                  | Описание                            |
|---------------------------|-------------------------------|-------------------------------------|
| `SECRET_KEY`              | *(обязательна в prod)*        | Django secret key                   |
| `DJANGO_SETTINGS_MODULE`  | `config.settings.development` | `development` или `production`      |
| `DEBUG`                   | `True`                        | Debug-режим                         |
| `ALLOWED_HOSTS`           | `localhost,127.0.0.1`         | CSV списка разрешённых хостов       |

### База и кеш

| Переменная       | Пример                                                       |
|------------------|--------------------------------------------------------------|
| `DATABASE_URL`   | `postgresql://billflow:billflow_secret@db:5432/billflow`     |
| `REDIS_URL`      | `redis://redis:6379/0`                                       |

### Celery

| Переменная              | По умолчанию                  |
|-------------------------|-------------------------------|
| `CELERY_BROKER_URL`     | `redis://redis:6379/0`        |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/1`        |

### Email (SMTP)

| Переменная            | Пример                                  |
|-----------------------|-----------------------------------------|
| `EMAIL_HOST`          | `smtp.gmail.com`                        |
| `EMAIL_PORT`          | `587`                                   |
| `EMAIL_USE_TLS`       | `True`                                  |
| `EMAIL_HOST_USER`     | `noreply@yourcompany.com`               |
| `EMAIL_HOST_PASSWORD` | `your-app-password`                     |
| `DEFAULT_FROM_EMAIL`  | `BillFlow <noreply@billflow.com>`       |

### Биллинг и бренд

| Переменная         | По умолчанию | Описание                                |
|--------------------|--------------|-----------------------------------------|
| `COMPANY_NAME`     | `BillFlow`   | Название компании в шапке PDF и email   |
| `DEFAULT_CURRENCY` | `USD`        | Валюта по умолчанию (ISO 4217)          |
| `INVOICE_PREFIX`   | `INV`        | Префикс автонумерации счетов            |
| `ESTIMATE_PREFIX`  | `EST`        | Префикс автонумерации смет              |

### JWT и CORS

| Переменная                          | По умолчанию                                         |
|-------------------------------------|------------------------------------------------------|
| `JWT_ACCESS_TOKEN_LIFETIME_MINUTES` | `60`                                                 |
| `JWT_REFRESH_TOKEN_LIFETIME_DAYS`   | `7`                                                  |
| `CORS_ALLOWED_ORIGINS`              | `http://localhost:5173,http://localhost`             |

---

## 11. API, очереди и интеграции

### REST API

OpenAPI 3 спецификация генерируется автоматически через `drf-spectacular`:

- **Swagger UI:** `/api/docs/`
- **ReDoc:** `/api/redoc/`
- **JSON-схема:** `/api/schema/`

### Основные эндпоинты

| Ресурс                 | URL                                | Методы                         |
|------------------------|------------------------------------|--------------------------------|
| **Auth**               | `/api/auth/login/`                 | `POST`                         |
| **Registration**       | `/api/auth/register/`              | `POST`                         |
| **Token refresh**      | `/api/auth/refresh/`               | `POST`                         |
| **Business Profile**   | `/api/accounts/profile/`           | `GET`, `PUT`, `PATCH`          |
| **Clients**            | `/api/clients/`                    | `GET`, `POST`, `PUT`, `DELETE` |
| **Invoices**           | `/api/invoices/`                   | `GET`, `POST`, `PUT`, `DELETE` |
| **Send invoice**       | `/api/invoices/{id}/send/`         | `POST`                         |
| **Download PDF**       | `/api/invoices/{id}/pdf/`          | `GET`                          |
| **Duplicate invoice**  | `/api/invoices/{id}/duplicate/`    | `POST`                         |
| **Recurring invoices** | `/api/invoices/recurring/`         | `GET`, `POST`, `PUT`, `DELETE` |
| **Payments**           | `/api/payments/`                   | `GET`, `POST`                  |
| **Refunds**            | `/api/payments/{id}/refund/`       | `POST`                         |
| **Estimates**          | `/api/estimates/`                  | `GET`, `POST`, `PUT`, `DELETE` |
| **Convert estimate**   | `/api/estimates/{id}/convert/`     | `POST`                         |
| **Revenue report**     | `/api/reports/revenue/`            | `GET`                          |
| **Dashboard stats**    | `/api/reports/dashboard/`          | `GET`                          |
| **AR aging**           | `/api/reports/aging/`              | `GET`                          |
| **Tax summary**        | `/api/reports/tax-summary/`        | `GET`                          |

### Формат ответа об ошибке

Все ошибки нормализуются `custom_exception_handler`:

```json
{
  "status_code": 400,
  "errors": [
    { "field": "amount", "message": "Payment amount exceeds the remaining invoice balance." }
  ]
}
```

### Очереди Celery

| Очередь         | Задачи                                                                |
|-----------------|-----------------------------------------------------------------------|
| `invoices`      | `generate_recurring_invoices`, `check_overdue_invoices`, `generate_invoice_pdf` |
| `notifications` | `send_payment_reminders`, `send_invoice_email`                        |
| `payments`      | (зарезервирована под `apps.payments.tasks.*`)                         |

---

## 12. Фоновые задачи и расписание Celery

Расписание описано в [backend/config/celery.py](backend/config/celery.py) и хранится в БД через `django_celery_beat.schedulers:DatabaseScheduler` (можно править из админки).

| Задача                          | Cron (UTC)        | Что делает                                                            |
|---------------------------------|-------------------|-----------------------------------------------------------------------|
| `generate_recurring_invoices`   | каждый день 01:00 | Создаёт счета из активных recurring schedules, у которых `next_date <= today` |
| `send_payment_reminders`        | каждый день 08:00 | Шлёт напоминания за 7, 3, 1 день до due, в день due, и через 1/7/14/30 дней после |
| `check_overdue_invoices`        | каждый день 00:30 | Помечает просроченные счета (`sent` / `viewed` / `partial` → `overdue`) |

Каждый таск настроен на `max_retries=3` с `default_retry_delay=300` (5 минут).

### On-demand задачи

- `generate_invoice_pdf(invoice_id)` — генерация PDF в фоне
- `send_invoice_email(invoice_id, recipient_email, message)` — отправка счёта по email с PDF-вложением

---

## 13. Мониторинг и эксплуатация

### Логирование

Три кастомных middleware обеспечивают наблюдаемость:

- **[`RequestLoggingMiddleware`](backend/middleware/request_logging.py)** — каждый запрос с timing, status, user, IP, request_id. Заголовок ответа `X-Request-ID` для distributed tracing.
- **[`AuditLogMiddleware`](backend/middleware/audit.py)** — write-операции (`POST`/`PUT`/`PATCH`/`DELETE`) на `/api/` с фиксацией user и status. Подходит для compliance-аудита.
- **[`APIRateLimitMiddleware`](backend/middleware/rate_limit.py)** — sliding window counter на cache. Возвращает `429` с `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`.

В production логи пишутся в файл `logs/billflow.log` (RotatingFileHandler: 10 MB × 5 файлов).

### Метрики и здоровье

| Что              | Где                                                 |
|------------------|-----------------------------------------------------|
| API статус       | `GET /api/schema/` (200 OK = живой)                 |
| Healthcheck БД   | `docker-compose ps` → service_healthy для `db`      |
| Очередь Celery   | `celery -A config inspect active` / `stats`         |
| Размер кеша      | `redis-cli INFO memory`                             |

### Безопасность в production

Production settings ([backend/config/settings/production.py](backend/config/settings/production.py)) включают:

- `SECURE_HSTS_SECONDS = 31536000` (1 год)
- `SECURE_SSL_REDIRECT = True`
- `SESSION_COOKIE_SECURE = True`, `CSRF_COOKIE_SECURE = True`
- `X_FRAME_OPTIONS = DENY`
- `SECURE_PROXY_SSL_HEADER` для работы за nginx

---

## 14. Тестирование

```bash
# Все тесты backend
docker-compose exec backend python manage.py test

# Один app
docker-compose exec backend python manage.py test apps.accounts

# С coverage
docker-compose exec backend coverage run --source='.' manage.py test
docker-compose exec backend coverage report
```

### Подход к тестам

- **Unit-тесты сервисов** — изолированно, без БД где возможно
- **Integration-тесты views** — через `APIClient` (DRF), с реальной БД (SQLite in-memory или PostgreSQL test DB)
- **Тесты Celery-тасков** — через `CELERY_TASK_ALWAYS_EAGER=True`

---

## 15. CI/CD

Рекомендуемый pipeline (GitHub Actions / GitLab CI):

1. **Lint & format** — `ruff check`, `black --check`, `isort --check`
2. **Type check** — `mypy` (опционально)
3. **Tests** — `python manage.py test` с PostgreSQL в сервисах CI
4. **Build** — `docker build` backend и frontend образов
5. **Push** — в registry (Docker Hub / GHCR / GitLab Registry)
6. **Deploy** — SSH + `docker-compose pull && docker-compose up -d` (или Helm/Kubernetes)

Шаблон workflow можно добавить в `.github/workflows/ci.yml`.

---

## 16. Роли компонентов в продакшене

| Компонент       | Роль                                                                                          |
|-----------------|-----------------------------------------------------------------------------------------------|
| **Nginx**       | TLS termination, gzip, отдача `/static/` и `/media/`, проксирование API и SPA                 |
| **Gunicorn**    | WSGI-сервер для Django (4 sync workers, timeout 120s)                                         |
| **Django + DRF**| HTTP API, бизнес-логика в сервисах, OpenAPI-схема                                             |
| **Celery worker** | Длительные операции: PDF, email, batch-обработка                                            |
| **Celery beat** | Cron-планировщик (расписание в БД, можно править из админки)                                  |
| **PostgreSQL**  | Транзакционное хранилище бизнес-данных                                                        |
| **Redis**       | Cache (sessions, throttle counters), broker для Celery, result backend                        |
| **WhiteNoise**  | Сжатый отдача collected static (если без CDN)                                                 |
| **Vue 3 SPA**   | UI: dashboard, CRUD клиентов и счетов, отчёты                                                 |

---

## 17. Лицензия

Проект распространяется под лицензией MIT. Полный текст — в файле [LICENSE](LICENSE).

---

## 18. Поддержка

- **Issues и баги:** [GitHub Issues](https://github.com/NodirOdilov/billflow/issues)
- **Email:** через профиль [Nodir Odilov](https://github.com/NodirOdilov)
- **Pull Requests:** приветствуются. Перед PR — прогоните тесты и линтеры.

---

<div align="center">

**BillFlow** — modern invoicing, made simple.

Made with care by [Nodir Odilov](https://github.com/NodirOdilov)

</div>
