from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.conf import settings
from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Sum
from django.core import signing
from django.core.management import CommandError, call_command
from django.db import transaction
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.models import Booking
from apps.drivers.models import DriverProfile, Vehicle, VerificationDocument
from apps.finance.models import ExpenseSettlement, PassengerContribution, RazorpayPayment, SandboxPayment
from apps.journeys.models import Journey
from apps.trust.models import SafetyReport

User = get_user_model()


def _status_totals(queryset):
    return {
        item["status"]: item["total"]
        for item in queryset.values("status").annotate(total=Count("id"))
    }


def _choice_counts(queryset, field):
    return {
        item[field]: item["total"]
        for item in queryset.values(field).annotate(total=Count("id"))
    }


class HealthCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok", "service": "waytogether-api", "version": "v1"})


class AdminOverviewView(APIView):
    """Aggregated, read-only operational metrics for staff administrators."""
    throttle_scope = "admin_read"
    permission_classes = [IsAdminUser]

    def get(self, request):
        now = timezone.now()
        trend_start = now - timedelta(days=180)
        monthly_journeys = (
            Journey.objects.filter(created_at__gte=trend_start)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(total=Count("id"))
            .order_by("month")
        )

        finalized_settlements = ExpenseSettlement.objects.filter(is_finalized=True)
        final_contributions = PassengerContribution.objects.filter(settlement__is_finalized=True)
        razorpay_statuses = _choice_counts(RazorpayPayment.objects.all(), "status")
        legacy_sandbox_statuses = _choice_counts(SandboxPayment.objects.all(), "status")
        return Response({
            "generated_at": now,
            "users": {
                "total": User.objects.count(),
                "active": User.objects.filter(is_active=True).count(),
                "inactive": User.objects.filter(is_active=False).count(),
                "by_role": _choice_counts(User.objects.all(), "role"),
                "email_verified": User.objects.filter(is_email_verified=True).count(),
                "phone_verified": User.objects.filter(is_phone_verified=True).count(),
            },
            "driver_verification": {
                "profiles_by_status": _choice_counts(DriverProfile.objects.all(), "verification_status"),
                "vehicles_by_status": _choice_counts(Vehicle.objects.all(), "verification_status"),
                "documents_pending": VerificationDocument.objects.filter(
                    review_status=VerificationDocument.ReviewStatus.PENDING,
                    is_current=True,
                ).count(),
            },
            "journeys": {
                "total": Journey.objects.count(),
                "by_status": _status_totals(Journey.objects.all()),
                "created_last_180_days": [
                    {"month": item["month"].date().isoformat(), "count": item["total"]}
                    for item in monthly_journeys
                ],
            },
            "bookings": {
                "total": Booking.objects.count(),
                "by_status": _status_totals(Booking.objects.all()),
                "confirmed_seats": Booking.objects.filter(
                    status=Booking.Status.CONFIRMED,
                ).aggregate(total=Sum("seats_requested"))["total"] or 0,
            },
            "safety": {
                "by_status": _status_totals(SafetyReport.objects.all()),
                "urgent_open": SafetyReport.objects.filter(
                    priority=SafetyReport.Priority.URGENT,
                    status__in=(SafetyReport.Status.OPEN, SafetyReport.Status.REVIEWING),
                ).count(),
            },
            "expense_sharing": {
                "finalized_settlements": finalized_settlements.count(),
                "eligible_expenses_total_inr": str(
                    finalized_settlements.aggregate(total=Sum("eligible_total"))["total"] or Decimal("0.00")
                ),
                "driver_own_shares_total_inr": str(
                    finalized_settlements.aggregate(total=Sum("driver_share"))["total"] or Decimal("0.00")
                ),
                "passenger_contributions_total_inr": str(
                    final_contributions.aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
                ),
                "passenger_contribution_records": final_contributions.count(),
                "sandbox_payment_attempts": sum(legacy_sandbox_statuses.values()),
                "sandbox_payments_by_status": legacy_sandbox_statuses,
                "razorpay_test_payment_attempts": sum(razorpay_statuses.values()),
                "razorpay_test_payments_by_status": razorpay_statuses,
                "notice": "Expense allocations are cost-sharing records. Razorpay transactions are in Test Mode only; no real money is collected or paid out to drivers.",
            },
        })


class AdminUserListView(APIView):
    throttle_scope = "admin_read"
    permission_classes = [IsAdminUser]

    def get(self, request):
        queryset = User.objects.all().order_by("-date_joined")
        search = request.query_params.get("q", "").strip()
        role = request.query_params.get("role", "").strip()
        active = request.query_params.get("active", "").strip().lower()

        if search:
            queryset = queryset.filter(
                Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )
        if role in {choice[0] for choice in User.Role.choices}:
            queryset = queryset.filter(role=role)
        if active in ("true", "false"):
            queryset = queryset.filter(is_active=(active == "true"))

        total_count = queryset.count()
        users = queryset[:100]
        return Response({
            "total_count": total_count,
            "results": [
                {
                    "id": user.pk,
                    "display_name": user.display_name,
                    "email": user.email,
                    "role": user.role,
                    "is_active": user.is_active,
                    "is_email_verified": user.is_email_verified,
                    "is_phone_verified": user.is_phone_verified,
                    "date_joined": user.date_joined,
                }
                for user in users
            ],
        })


class AdminJourneyListView(APIView):
    throttle_scope = "admin_read"
    permission_classes = [IsAdminUser]

    def get(self, request):
        queryset = (
            Journey.objects.select_related("driver")
            .annotate(
                booking_count=Count("bookings", distinct=True),
                confirmed_seats=Sum(
                    "bookings__seats_requested",
                    filter=Q(bookings__status=Booking.Status.CONFIRMED),
                ),
            )
            .order_by("-created_at")
        )
        search = request.query_params.get("q", "").strip()
        journey_status = request.query_params.get("status", "").strip()
        if search:
            queryset = queryset.filter(
                Q(origin_name__icontains=search)
                | Q(destination_name__icontains=search)
                | Q(driver__email__icontains=search)
                | Q(driver__first_name__icontains=search)
                | Q(driver__last_name__icontains=search)
            )
        if journey_status in {choice[0] for choice in Journey.Status.choices}:
            queryset = queryset.filter(status=journey_status)

        total_count = queryset.count()
        return Response({
            "total_count": total_count,
            "results": [
                {
                    "id": journey.pk,
                    "driver_name": journey.driver.display_name,
                    "origin_name": journey.origin_name,
                    "destination_name": journey.destination_name,
                    "travel_date": journey.travel_date,
                    "departure_time": journey.departure_time,
                    "status": journey.status,
                    "seats_offered": journey.seats_offered,
                    "confirmed_seats": journey.confirmed_seats or 0,
                    "booking_count": journey.booking_count,
                    "estimated_total_expenses_inr": str(journey.estimated_total_expenses),
                    "created_at": journey.created_at,
                }
                for journey in queryset[:100]
            ],
        })


class AdminBookingListView(APIView):
    throttle_scope = "admin_read"
    permission_classes = [IsAdminUser]

    def get(self, request):
        queryset = Booking.objects.select_related(
            "passenger", "journey", "journey__driver"
        ).order_by("-requested_at")
        search = request.query_params.get("q", "").strip()
        booking_status = request.query_params.get("status", "").strip()
        if search:
            queryset = queryset.filter(
                Q(journey__origin_name__icontains=search)
                | Q(journey__destination_name__icontains=search)
                | Q(passenger__email__icontains=search)
                | Q(passenger__first_name__icontains=search)
                | Q(passenger__last_name__icontains=search)
                | Q(journey__driver__email__icontains=search)
            )
        if booking_status in {choice[0] for choice in Booking.Status.choices}:
            queryset = queryset.filter(status=booking_status)

        total_count = queryset.count()
        return Response({
            "total_count": total_count,
            "results": [
                {
                    "id": booking.pk,
                    "journey_id": booking.journey_id,
                    "origin_name": booking.journey.origin_name,
                    "destination_name": booking.journey.destination_name,
                    "travel_date": booking.journey.travel_date,
                    "passenger_name": booking.passenger.display_name,
                    "driver_name": booking.journey.driver.display_name,
                    "status": booking.status,
                    "seats_requested": booking.seats_requested,
                    "estimated_contribution_per_passenger_inr": str(
                        booking.estimated_contribution_per_passenger
                    ),
                    "estimated_contribution_total_inr": str(
                        booking.estimated_contribution_total
                    ),
                    "requested_at": booking.requested_at,
                }
                for booking in queryset[:100]
            ],
        })


class AdminExpenseLedgerView(APIView):
    """Read-only view of completed expense allocations, never transaction processing."""
    throttle_scope = "admin_read"
    permission_classes = [IsAdminUser]

    def get(self, request):
        queryset = (
            ExpenseSettlement.objects.filter(is_finalized=True)
            .select_related("journey", "driver")
            .annotate(
                passenger_contribution_total=Sum("contributions__total_amount"),
                contribution_count=Count("contributions", distinct=True),
            )
            .order_by("-finalized_at")
        )
        return Response({
            "total_count": queryset.count(),
            "results": [
                {
                    "id": settlement.pk,
                    "journey_id": settlement.journey_id,
                    "origin_name": settlement.journey.origin_name,
                    "destination_name": settlement.journey.destination_name,
                    "travel_date": settlement.journey.travel_date,
                    "driver_name": settlement.driver.display_name,
                    "eligible_total_inr": str(settlement.eligible_total),
                    "driver_own_share_inr": str(settlement.driver_share),
                    "passenger_contribution_total_inr": str(
                        settlement.passenger_contribution_total or Decimal("0.00")
                    ),
                    "passenger_seat_count": settlement.passenger_seat_count,
                    "contribution_records": settlement.contribution_count,
                    "finalized_at": settlement.finalized_at,
                }
                for settlement in queryset[:100]
            ],
            "notice": "Read-only expense allocation records. This ledger does not indicate money collected, paid out or transferred.",
        })



class AdminDatabaseCleanupView(APIView):
    """One-time, admin-only browser runner for the guarded database cleanup command."""

    permission_classes = [IsAdminUser]
    throttle_scope = "admin_read"

    CONFIRMATION_PHRASE = "DELETE NON-ADMIN AND NON-UPCOMING DATA"
    BACKUP_ACKNOWLEDGEMENT = "I UNDERSTAND THIS ACTION IS IRREVERSIBLE"
    TOKEN_SALT = "waytogether.admin-database-cleanup.preview.v1"
    COMPLETION_MARKER = "waytogether_database_cleanup_v1"

    def _ensure_enabled(self):
        if not getattr(settings, "ADMIN_DATABASE_CLEANUP_ENABLED", False):
            return Response({"detail": "Browser database cleanup is currently disabled."}, status=404)
        return None

    def _already_completed(self):
        return LogEntry.objects.filter(change_message=self.COMPLETION_MARKER).exists()

    def _run_command(self, *, execute=False):
        output = StringIO()
        args = ["--execute"] if execute else []
        call_command("cleanup_waytogether_data", *args, stdout=output)
        raw_output = output.getvalue()
        summary = []
        for line in raw_output.splitlines():
            if ": " not in line:
                continue
            label, _, value = line.rpartition(": ")
            try:
                count = int(value.strip())
            except ValueError:
                continue
            summary.append({"label": label.strip(), "count": count})
        return raw_output, summary

    def get(self, request):
        disabled = self._ensure_enabled()
        if disabled:
            return disabled
        if self._already_completed():
            return Response({
                "completed": True,
                "detail": "The one-time WayTogether database cleanup has already been completed.",
            })

        try:
            output, summary = self._run_command(execute=False)
        except (CommandError, LookupError) as exc:
            return Response({"detail": str(exc)}, status=503)

        token = signing.dumps({
            "admin_id": request.user.pk,
            "summary": summary,
        }, salt=self.TOKEN_SALT)
        return Response({
            "completed": False,
            "dry_run": True,
            "summary": summary,
            "preview_token": token,
            "token_expires_in_seconds": 900,
            "output": output,
            "confirmation_phrase": self.CONFIRMATION_PHRASE,
            "backup_acknowledgement": self.BACKUP_ACKNOWLEDGEMENT,
            "preserves": [
                "All admin, staff and superuser accounts",
                "Future published journeys that have not departed",
                "The driver accounts, profiles and vehicles required by those journeys",
                "Approved verification documents required by retained routes",
            ],
        })

    def post(self, request):
        disabled = self._ensure_enabled()
        if disabled:
            return disabled
        if self._already_completed():
            return Response({
                "detail": "The one-time cleanup has already been completed. Further executions are blocked.",
                "completed": True,
            }, status=409)
        if request.data.get("confirmation") != self.CONFIRMATION_PHRASE:
            return Response({"detail": "The confirmation phrase does not match."}, status=400)
        if request.data.get("backup_acknowledged") is not True:
            return Response({"detail": "Acknowledge that you have a backup or accept the irreversible risk before continuing."}, status=400)

        token = str(request.data.get("preview_token", ""))
        try:
            preview = signing.loads(token, salt=self.TOKEN_SALT, max_age=900)
        except signing.BadSignature:
            return Response({"detail": "The preview token is invalid or has expired. Refresh the dry-run preview."}, status=400)
        if preview.get("admin_id") != request.user.pk:
            return Response({"detail": "Only the administrator who generated this preview can execute it."}, status=403)

        try:
            _, current_summary = self._run_command(execute=False)
        except (CommandError, LookupError) as exc:
            return Response({"detail": str(exc)}, status=503)
        if preview.get("summary") != current_summary:
            return Response({
                "detail": "Database records changed since the preview. Refresh the preview and review the new counts.",
                "preview_required": True,
            }, status=409)

        try:
            with transaction.atomic():
                # Serialise executions by locking the initiating administrator row.
                User.objects.select_for_update().get(pk=request.user.pk)
                if self._already_completed():
                    return Response({
                        "detail": "The one-time cleanup has already been completed.",
                        "completed": True,
                    }, status=409)

                LogEntry.objects.create(
                    user=request.user,
                    content_type=None,
                    object_id="",
                    object_repr="WayTogether one-time database cleanup",
                    action_flag=CHANGE,
                    change_message=self.COMPLETION_MARKER,
                )
                output, summary = self._run_command(execute=True)
        except (CommandError, LookupError) as exc:
            return Response({"detail": str(exc)}, status=400)

        return Response({
            "completed": True,
            "detail": "WayTogether database cleanup completed. The administrator and upcoming published journeys were preserved.",
            "summary": summary,
            "output": output,
        })
