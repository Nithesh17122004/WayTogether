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

export type SandboxPaymentRecord = {
  id: number;
  reference: string;
  contribution_id: number;
  provider: "sandbox";
  status: "created" | "succeeded" | "failed" | "refunded";
  amount: string;
  currency: "INR";
  failure_note: string;
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
  latest_payment: SandboxPaymentRecord | null;
};

export type SettlementInput = {
  actual_fuel_expense: string;
  actual_toll_expense: string;
  actual_parking_expense: string;
  actual_other_expense: string;
  actual_expense_note?: string;
};

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

export async function createSandboxPayment(contributionId:number) {
  return apiRequest<{detail:string;payment:SandboxPaymentRecord}>(
    "/finance/contributions/"+contributionId+"/sandbox-payment/",
    {method:"POST",body:JSON.stringify({})},
    true,
  );
}

export async function completeSandboxPayment(
  paymentId:number,
  outcome:"succeeded"|"failed",
  failureNote="",
) {
  return apiRequest<{detail:string;payment:SandboxPaymentRecord}>(
    "/finance/payments/"+paymentId+"/sandbox-result/",
    {method:"POST",body:JSON.stringify({outcome,failure_note:failureNote})},
    true,
  );
}
