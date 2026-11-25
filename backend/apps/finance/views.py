from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.models import Booking
from apps.journeys.models import Journey

from .models import ExpenseSettlement, PassengerContribution, SandboxPayment
from .permissions import IsVerifiedDriver, IsVerifiedPassenger
from .serializers import (
    ExpenseSettlementInputSerializer,
    ExpenseSettlementSerializer,
    PassengerContributionSerializer,
    SandboxPaymentSerializer,
    SandboxRefundSerializer,
)
from .services import (
    complete_sandbox_payment,
    create_sandbox_payment,
    finalize_expense_settlement,
    refund_sandbox_payment,
)


class JourneyExpenseSettlementView(APIView):
    permission_classes = [IsAuthenticated, IsVerifiedDriver]
    throttle_scope = "finance_action"

    def get(self, request, journey_id):
        journey = get_object_or_404(
            Journey.objects.select_related("driver").filter(
                pk=journey_id,
            )
        )
        if journey.driver_id != request.user.id:
            return Response({"detail": "Settlement not found."}, status=404)
        settlement = get_object_or_404(
            ExpenseSettlement.objects.select_related("journey", "driver"),
            journey=journey,
        )
        return Response(ExpenseSettlementSerializer(settlement).data)

    def post(self, request, journey_id):
        serializer = ExpenseSettlementInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            settlement = finalize_expense_settlement(
                journey_id=journey_id,
                driver=request.user,
                data=serializer.validated_data,
            )
        except Journey.DoesNotExist:
            return Response({"detail": "Journey not found."}, status=404)
        return Response({
            "detail": "Actual eligible expenses finalized. Passenger contribution records have been frozen.",
            "settlement": ExpenseSettlementSerializer(settlement).data,
        }, status=status.HTTP_201_CREATED)


class MyContributionListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsVerifiedPassenger]
    serializer_class = PassengerContributionSerializer

    def get_queryset(self):
        return (
            PassengerContribution.objects.filter(passenger=self.request.user)
            .select_related(
                "booking", "booking__journey", "booking__journey__driver", "settlement",
            )
            .prefetch_related("sandbox_payments")
            .order_by("-created_at")
        )


class SandboxPaymentCreateView(APIView):
    permission_classes = [IsAuthenticated, IsVerifiedPassenger]
    throttle_scope = "finance_action"

    def post(self, request, contribution_id):
        contribution = get_object_or_404(
            PassengerContribution.objects.select_related("passenger"),
            pk=contribution_id,
        )
        try:
            payment = create_sandbox_payment(contribution=contribution, passenger=request.user)
        except PassengerContribution.DoesNotExist:
            return Response({"detail": "Contribution not found."}, status=404)
        return Response({
            "detail": "Sandbox payment started. This is a simulated transaction and no money is moved.",
            "payment": SandboxPaymentSerializer(payment).data,
        }, status=status.HTTP_201_CREATED)


class SandboxPaymentResultView(APIView):
    permission_classes = [IsAuthenticated, IsVerifiedPassenger]
    throttle_scope = "finance_action"

    def post(self, request, payment_id):
        outcome = str(request.data.get("outcome", "")).lower()
        failure_note = str(request.data.get("failure_note", "")).strip()
        try:
            payment = complete_sandbox_payment(
                payment_id=payment_id,
                passenger=request.user,
                outcome=outcome,
                failure_note=failure_note,
            )
        except SandboxPayment.DoesNotExist:
            return Response({"detail": "Payment not found."}, status=404)
        return Response({
            "detail": "Sandbox outcome recorded. No real payment was processed.",
            "payment": SandboxPaymentSerializer(payment).data,
        })


class SandboxRefundView(APIView):
    permission_classes = [IsAdminUser]
    throttle_scope = "finance_action"

    def post(self, request, payment_id):
        reason = str(request.data.get("reason", "")).strip()
        if not reason:
            return Response({"detail": "A refund reason is required."}, status=400)
        try:
            from .services import refund_sandbox_payment
            refund = refund_sandbox_payment(
                payment_id=payment_id,
                admin_user=request.user,
                reason=reason,
            )
        except SandboxPayment.DoesNotExist:
            return Response({"detail": "Payment not found."}, status=404)
        return Response({
            "detail": "Sandbox refund recorded. No money was returned because no real payment occurred.",
            "refund": SandboxRefundSerializer(refund).data,
        })
