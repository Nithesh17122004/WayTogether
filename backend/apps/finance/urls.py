from django.urls import path

from .razorpay_views import (
    RazorpayOrderCreateView,
    RazorpayPaymentFailureView,
    RazorpayPaymentVerifyView,
)
from .views import (
    JourneyExpenseSettlementView,
    MyContributionListView,
    SandboxPaymentCreateView,
    SandboxPaymentResultView,
    SandboxRefundView,
)

urlpatterns = [
    path("journeys/<int:journey_id>/settlement/", JourneyExpenseSettlementView.as_view(), name="journey-expense-settlement"),
    path("contributions/mine/", MyContributionListView.as_view(), name="my-contributions"),
    # Legacy sandbox routes remain available only when FINANCE_SANDBOX_ENABLED is explicitly enabled.
    # Production keeps this feature flag false; the customer UI uses Razorpay Test Mode.
    path("contributions/<int:contribution_id>/sandbox-payment/", SandboxPaymentCreateView.as_view(), name="sandbox-payment-create"),
    path("payments/<int:payment_id>/sandbox-result/", SandboxPaymentResultView.as_view(), name="sandbox-payment-result"),
    path("payments/<int:payment_id>/sandbox-refund/", SandboxRefundView.as_view(), name="sandbox-payment-refund"),
    path("contributions/<int:contribution_id>/razorpay-order/", RazorpayOrderCreateView.as_view(), name="razorpay-order-create"),
    path("payments/<int:payment_id>/razorpay-verify/", RazorpayPaymentVerifyView.as_view(), name="razorpay-payment-verify"),
    path("payments/<int:payment_id>/razorpay-failed/", RazorpayPaymentFailureView.as_view(), name="razorpay-payment-failed"),
]
