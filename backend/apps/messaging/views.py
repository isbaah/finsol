from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

import apps.messaging.services as messaging_services
from apps.audit.services import record_event
from apps.loans.models import RepaymentInstallment
from apps.messaging.filters import SMSMessageFilter
from apps.messaging.models import SMSMessage, SMSSettings
from apps.messaging.serializers import (
    ManualReminderSerializer,
    SMSMessageSerializer,
    SMSSettingsSerializer,
)
from common.permissions import (
    FINANCE_OFFICER,
    LOAN_OFFICER,
    STAFF_ROLES,
    SUPER_ADMIN,
    has_any_role,
)

_REMINDER_ROLES = (LOAN_OFFICER, FINANCE_OFFICER, SUPER_ADMIN)


class AdminSMSMessageListView(generics.ListAPIView):
    """GET /api/v1/admin/sms-messages/ — Stage 11: "Build SMS history and
    summary UI." Read access for every staff role."""

    serializer_class = SMSMessageSerializer
    permission_classes = [permissions.IsAuthenticated, has_any_role(*STAFF_ROLES)]
    filterset_class = SMSMessageFilter
    queryset = SMSMessage.objects.select_related("customer", "loan")


class AdminSMSMessageSummaryView(APIView):
    """GET /api/v1/admin/sms-messages/summary/ — the counts the admin
    dashboard shows (Section 21: "sent, delivered, failed, and pending
    counts")."""

    permission_classes = [permissions.IsAuthenticated, has_any_role(*STAFF_ROLES)]

    def get(self, request):
        counts = {
            status_value: SMSMessage.objects.filter(status=status_value).count()
            for status_value, _ in SMSMessage.Status.choices
        }
        return Response(counts)


class AdminSMSMessageRetryView(APIView):
    """POST /api/v1/admin/sms-messages/{id}/retry/ — manual resend for a
    FAILED message, bypassing the normal attempt-limit/backoff window
    (Stage 11 test list: "Manual resend audit")."""

    permission_classes = [permissions.IsAuthenticated, has_any_role(LOAN_OFFICER, SUPER_ADMIN)]

    def post(self, request, pk):
        message = get_object_or_404(SMSMessage, pk=pk)
        before_status = message.status
        message.status = SMSMessage.Status.PENDING
        message.save(update_fields=["status", "updated_at"])
        messaging_services.dispatch_sms(message.pk)
        message.refresh_from_db()
        record_event(
            actor=request.user,
            action="sms_message.manual_retry",
            entity=message,
            before={"status": before_status},
            after={"status": message.status},
        )
        return Response(SMSMessageSerializer(message).data)


class AdminManualReminderView(APIView):
    """POST /api/v1/admin/installments/{id}/manual-reminder/ — Section 16's
    upcoming-repayments-table "Send SMS now" action / Section 17's
    MANUAL_REMINDER type. Exempt from the scheduled-reminder uniqueness
    constraint, so it may be sent more than once, but always records the
    admin actor and reason (audited)."""

    permission_classes = [permissions.IsAuthenticated, has_any_role(*_REMINDER_ROLES)]

    def post(self, request, pk):
        installment = get_object_or_404(
            RepaymentInstallment.objects.select_related("loan", "loan__customer"), pk=pk
        )
        serializer = ManualReminderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data["reason"]

        message = messaging_services.record_manual_reminder_sms(
            installment=installment, actor=request.user, reason=reason
        )
        # dispatch_after_commit() may have already sent it synchronously
        # (autocommit mode fires on_commit callbacks immediately) — refetch
        # so the response reflects the real post-send status, not the
        # stale in-memory PENDING captured at creation.
        message.refresh_from_db()
        record_event(
            actor=request.user,
            action="sms_message.manual_reminder",
            entity=message,
            after={"installment_id": str(installment.pk)},
            reason=reason,
        )
        return Response(SMSMessageSerializer(message).data, status=201)


class AdminSMSSettingsView(APIView):
    """GET/PUT /api/v1/admin/sms-settings/ — the settings form behind
    /admin/settings: pause/resume Hubtel sending and edit the daily
    reminder times. Any staff role may read; only the SUPER_ADMIN may
    change it (same access pattern as AdminRepaymentAccountView), and every
    change is audited since it controls whether real, paid SMS goes out."""

    def get_permissions(self):
        if self.request.method == "PUT":
            return [permissions.IsAuthenticated(), has_any_role(SUPER_ADMIN)()]
        return [permissions.IsAuthenticated(), has_any_role(*STAFF_ROLES)()]

    def get(self, request):
        return Response(SMSSettingsSerializer(SMSSettings.get_solo()).data)

    def put(self, request):
        sms_settings = SMSSettings.get_solo()
        before = {
            "hubtel_enabled": sms_settings.hubtel_enabled,
            "morning_reminder_time": str(sms_settings.morning_reminder_time),
            "afternoon_reminder_time": str(sms_settings.afternoon_reminder_time),
        }
        serializer = SMSSettingsSerializer(instance=sms_settings, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        record_event(
            actor=request.user,
            action="sms_settings.update",
            entity=sms_settings,
            before=before,
            after={
                "hubtel_enabled": sms_settings.hubtel_enabled,
                "morning_reminder_time": str(sms_settings.morning_reminder_time),
                "afternoon_reminder_time": str(sms_settings.afternoon_reminder_time),
            },
        )
        return Response(serializer.data)
