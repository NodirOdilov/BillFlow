"""
Celery configuration for InvoiceForge project.
"""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("invoiceforge")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

# Periodic tasks schedule
app.conf.beat_schedule = {
    "generate-recurring-invoices": {
        "task": "apps.invoices.tasks.generate_recurring_invoices",
        "schedule": crontab(hour=1, minute=0),  # Every day at 1:00 AM UTC
        "options": {"queue": "invoices"},
    },
    "send-payment-reminders": {
        "task": "apps.invoices.tasks.send_payment_reminders",
        "schedule": crontab(hour=8, minute=0),  # Every day at 8:00 AM UTC
        "options": {"queue": "notifications"},
    },
    "check-overdue-invoices": {
        "task": "apps.invoices.tasks.check_overdue_invoices",
        "schedule": crontab(hour=0, minute=30),  # Every day at 0:30 AM UTC
        "options": {"queue": "invoices"},
    },
}

app.conf.task_routes = {
    "apps.invoices.tasks.*": {"queue": "invoices"},
    "apps.payments.tasks.*": {"queue": "payments"},
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for verifying Celery is working."""
    print(f"Request: {self.request!r}")
