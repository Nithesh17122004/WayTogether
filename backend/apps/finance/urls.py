from django.urls import path

from .razorpay_views import (
    RazorpayOrderCreateView,
    RazorpayPaymentFailureView,
    RazorpayPaymentVerifyView,
)
from .views import JourneyExpenseSettlementView, MyContributionListView

urlpatterns = [
    path("journeys/<int:journey_id>/settlement/", JourneyExpenseSettlementView.as_view(), name="journey-expense-settlement"),
    path("contributions/mine/", MyContributionListView.as_view(), name="my-contributions"),
    path("contributions/<int:contribution_id>/razorpay-order/", RazorpayOrderCreateView.as_view(), name="razorpay-order-create"),
    path("payments/<int:payment_id>/razorpay-verify/", RazorpayPaymentVerifyView.as_view(), name="razorpay-payment-verify"),
    path("payments/<int:payment_id>/razorpay-failed/", RazorpayPaymentFailureView.as_view(), name="razorpay-payment-failed"),
]
