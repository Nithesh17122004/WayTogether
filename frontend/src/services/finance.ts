import { apiRequest } from "./api";

export type ExpenseSettlementRecord = {
  id: number;
  journey_id: number;
  origin_name: string;
  destination_name: string;
  travel_date: string;
  driver_name: string;
  actual_fuel_expense: string;
  actual_toll_expense: string;
  actual_parking_expense: string;
  actual_other_expense: string;
  actual_expense_note: string;
  eligible_total: string;
  driver_share: string;
  passenger_seat_count: number;
  currency: "INR";
  is_finalized: boolean;
  submitted_at: string;
  finalized_at: string | null;
};

export type RazorpayPaymentRecord = {
  id: number;
  order_id: string;
  payment_id: string | null;
  status: "created" | "captured" | "failed";
  amount: string;
  currency: "INR";
  test_mode: boolean;
  failure_reason: string;
  created_at: string;
  completed_at: string | null;
};

export type PassengerContributionRecord = {
  id: number;
  booking_id: number;
  journey_id: number;
  origin_name: string;
  destination_name: string;
  travel_date: string;
  driver_name: string;
  seat_count: number;
  per_seat_amount: string;
  total_amount: string;
  currency: "INR";
  settlement_id: number;
  created_at: string;
  latest_payment: RazorpayPaymentRecord | null;
};

export type SettlementInput = {
  actual_fuel_expense: string;
  actual_toll_expense: string;
  actual_parking_expense: string;
  actual_other_expense: string;
  actual_expense_note?: string;
};

export type RazorpayCheckoutResponse = {
  razorpay_payment_id: string;
  razorpay_order_id: string;
  razorpay_signature: string;
};

type RazorpayFailureResponse = {
  error?: { description?: string; reason?: string; code?: string };
};

type RazorpayCheckoutOptions = {
  key: string;
  amount: number;
  currency: string;
  name: string;
  description: string;
  order_id: string;
  prefill: { name: string; email: string };
  theme: { color: string };
  handler: (response: RazorpayCheckoutResponse) => void | Promise<void>;
  modal: { ondismiss: () => void };
};

type RazorpayCheckoutInstance = {
  open: () => void;
  on: (event: "payment.failed", handler: (response: RazorpayFailureResponse) => void) => void;
};

declare global {
  interface Window {
    Razorpay?: new (options: RazorpayCheckoutOptions) => RazorpayCheckoutInstance;
  }
}

let razorpayScriptPromise: Promise<void> | null = null;

async function ensureRazorpayCheckout() {
  if (window.Razorpay) return;
  if (!razorpayScriptPromise) {
    razorpayScriptPromise = new Promise<void>((resolve, reject) => {
      const existing = document.querySelector<HTMLScriptElement>('script[data-waytogether-razorpay="true"]');
      if (existing) {
        existing.addEventListener("load", () => resolve(), { once: true });
        existing.addEventListener("error", () => reject(new Error("Razorpay Checkout could not be loaded.")), { once: true });
        return;
      }
      const script = document.createElement("script");
      script.src = "https://checkout.razorpay.com/v1/checkout.js";
      script.async = true;
      script.dataset.waytogetherRazorpay = "true";
      script.onload = () => resolve();
      script.onerror = () => reject(new Error("Razorpay Checkout could not be loaded. Check your connection and retry."));
      document.body.appendChild(script);
    }).catch(error => {
      razorpayScriptPromise = null;
      throw error;
    });
  }
  await razorpayScriptPromise;
  if (!window.Razorpay) throw new Error("Razorpay Checkout is unavailable in this browser.");
}

export async function launchRazorpayCheckout(args: {
  keyId: string;
  orderId: string;
  amount: number;
  currency: string;
  customerName: string;
  customerEmail: string;
  onSuccess: (response: RazorpayCheckoutResponse) => void | Promise<void>;
  onFailure: (reason: string) => void | Promise<void>;
  onDismiss: () => void;
}) {
  await ensureRazorpayCheckout();
  const RazorpayConstructor = window.Razorpay;
  if (!RazorpayConstructor) throw new Error("Razorpay Checkout is unavailable in this browser.");
  const checkout = new RazorpayConstructor({
    key: args.keyId,
    amount: args.amount,
    currency: args.currency,
    name: "WayTogether",
    description: "Shared journey expense contribution · Test Mode",
    order_id: args.orderId,
    prefill: { name: args.customerName, email: args.customerEmail },
    theme: { color: "#286fff" },
    handler: args.onSuccess,
    modal: { ondismiss: args.onDismiss },
  });
  checkout.on("payment.failed", response => {
    void args.onFailure(response.error?.description || "The Razorpay test payment failed.");
  });
  checkout.open();
}

export async function finalizeJourneyExpenses(journeyId:number,payload:SettlementInput) {
  return apiRequest<{detail:string;settlement:ExpenseSettlementRecord}>(
    "/finance/journeys/"+journeyId+"/settlement/",
    {method:"POST",body:JSON.stringify(payload)},
    true,
  );
}

export async function getDriverSettlement(journeyId:number) {
  return apiRequest<ExpenseSettlementRecord>(
    "/finance/journeys/"+journeyId+"/settlement/",
    {},
    true,
  );
}

export async function getMyContributions() {
  return apiRequest<PassengerContributionRecord[]>("/finance/contributions/mine/",{},true);
}

export async function createRazorpayOrder(contributionId:number) {
  return apiRequest<{
    detail:string;
    key_id:string;
    order:{id:string;amount:number;currency:"INR"};
    customer:{name:string;email:string};
    payment:RazorpayPaymentRecord;
  }>(
    "/finance/contributions/"+contributionId+"/razorpay-order/",
    {method:"POST",body:JSON.stringify({})},
    true,
  );
}

export async function verifyRazorpayPayment(paymentId:number,response:RazorpayCheckoutResponse) {
  return apiRequest<{detail:string;payment:RazorpayPaymentRecord}>(
    "/finance/payments/"+paymentId+"/razorpay-verify/",
    {method:"POST",body:JSON.stringify(response)},
    true,
  );
}

export async function markRazorpayPaymentFailed(paymentId:number,failureReason:string) {
  return apiRequest<{detail:string;payment:RazorpayPaymentRecord}>(
    "/finance/payments/"+paymentId+"/razorpay-failed/",
    {method:"POST",body:JSON.stringify({failure_reason:failureReason})},
    true,
  );
}
