from django.urls import path

from apps.messaging.views import (
    AdminManualReminderView,
    AdminSMSMessageListView,
    AdminSMSMessageRetryView,
    AdminSMSMessageSummaryView,
    AdminSMSSettingsView,
)

urlpatterns = [
    path("admin/sms-messages/", AdminSMSMessageListView.as_view(), name="admin-sms-message-list"),
    path(
        "admin/sms-messages/summary/",
        AdminSMSMessageSummaryView.as_view(),
        name="admin-sms-message-summary",
    ),
    path(
        "admin/sms-messages/<uuid:pk>/retry/",
        AdminSMSMessageRetryView.as_view(),
        name="admin-sms-message-retry",
    ),
    path(
        "admin/installments/<uuid:pk>/manual-reminder/",
        AdminManualReminderView.as_view(),
        name="admin-installment-manual-reminder",
    ),
    path("admin/sms-settings/", AdminSMSSettingsView.as_view(), name="admin-sms-settings"),
]
