from django.conf import settings
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PassengerContribution, RazorpayPayment
from .razorpay_gateway import (
    RazorpayGatewayError, RazorpayNotConfigured, create_order, verify_and_capture_payment,
)
from .serializers import RazorpayPaymentSerializer
from .permissions import IsVerifiedPassenger


class RazorpayOrderCreateView(APIView):
    permission_classes = [IsAuthenticated, IsVerifiedPassenger]
    throttle_scope = "finance_action"

    def post(self, request, contribution_id):
        contribution = get_object_or_404(
            PassengerContribution.objects.select_related("booking", "passenger"),
            pk=contribution_id, passenger=request.user,
        )
        if RazorpayPayment.objects.filter(
            contribution=contribution, status=RazorpayPayment.Status.CAPTURED
        ).exists():
            return Response({"detail": "This contribution has already been paid."}, status=409)
        try:
            with transaction.atomic():
                contribution = PassengerContribution.objects.select_for_update().select_related("booking").get(pk=contribution.pk)
                payment = RazorpayPayment.objects.filter(
                    contribution=contribution, status=RazorpayPayment.Status.CREATED
                ).first()
                if payment is None:
                    order = create_order(contribution=contribution)
                    payment = RazorpayPayment.objects.create(
                        contribution=contribution, order_id=order["id"],
                        status=RazorpayPayment.Status.CREATED,
                        amount=contribution.total_amount, currency=contribution.currency,
                        test_mode=True,
                    )
        except RazorpayNotConfigured as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except RazorpayGatewayError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        except IntegrityError:
            payment = RazorpayPayment.objects.filter(
                contribution=contribution, status=RazorpayPayment.Status.CREATED
            ).first()
            if payment is None:
                return Response({"detail": "Could not create a Razorpay order. Please retry."}, status=503)

        return Response({
            "detail": "Razorpay Test Mode order ready. No real money will be charged.",
            "key_id": settings.RAZORPAY_KEY_ID,
            "order": {
                "id": payment.order_id,
                "amount": int(payment.amount * 100),
                "currency": payment.currency,
            },
            "customer": {"name": request.user.display_name, "email": request.user.email},
            "payment": RazorpayPaymentSerializer(payment).data,
        }, status=status.HTTP_201_CREATED)


class RazorpayPaymentVerifyView(APIView):
    permission_classes = [IsAuthenticated, IsVerifiedPassenger]
    throttle_scope = "finance_action"

    def post(self, request, payment_id):
        payment = get_object_or_404(
            RazorpayPayment.objects.select_related("contribution", "contribution__passenger"),
            pk=payment_id, contribution__passenger=request.user,
        )
        gateway_payment_id = str(request.data.get("razorpay_payment_id", "")).strip()
        signature = str(request.data.get("razorpay_signature", "")).strip()
        returned_order_id = str(request.data.get("razorpay_order_id", "")).strip()
        if not gateway_payment_id or not signature or returned_order_id != payment.order_id:
            return Response({"detail": "Razorpay returned incomplete or mismatched payment details."}, status=400)
        try:
            payment = verify_and_capture_payment(
                local_payment=payment,
                gateway_payment_id=gateway_payment_id,
                signature=signature,
            )
        except RazorpayNotConfigured as exc:
            return Response({"detail": str(exc)}, status=503)
        except RazorpayGatewayError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response({
            "detail": "Razorpay Test Mode payment captured and verified.",
            "payment": RazorpayPaymentSerializer(payment).data,
        })


class RazorpayPaymentFailureView(APIView):
    permission_classes = [IsAuthenticated, IsVerifiedPassenger]
    throttle_scope = "finance_action"

    def post(self, request, payment_id):
        payment = get_object_or_404(
            RazorpayPayment.objects.select_related("contribution"),
            pk=payment_id, contribution__passenger=request.user,
        )
        if payment.status == RazorpayPayment.Status.CAPTURED:
            return Response({"detail": "A captured payment cannot be marked as failed."}, status=409)
        reason = str(request.data.get("failure_reason", "Payment was not completed."))[:500]
        payment.status = RazorpayPayment.Status.FAILED
        payment.failure_reason = reason
        payment.completed_at = None
        payment.save(update_fields=["status", "failure_reason", "completed_at", "updated_at"])
        return Response({
            "detail": "The failed Test Mode attempt was recorded. You can retry with a new order.",
            "payment": RazorpayPaymentSerializer(payment).data,
        })
