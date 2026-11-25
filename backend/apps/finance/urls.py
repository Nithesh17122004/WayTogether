from django.urls import path

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
    path("contributions/<int:contribution_id>/sandbox-payment/", SandboxPaymentCreateView.as_view(), name="sandbox-payment-create"),
    path("payments/<int:payment_id>/sandbox-result/", SandboxPaymentResultView.as_view(), name="sandbox-payment-result"),
    path("payments/<int:payment_id>/sandbox-refund/", SandboxRefundView.as_view(), name="sandbox-payment-refund"),
]
