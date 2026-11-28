import { apiRequest } from "./api";

export type CountMap = Record<string, number>;

export type AdminOverview = {
  generated_at: string;
  users: {
    total: number; active: number; inactive: number;
    by_role: CountMap; email_verified: number; phone_verified: number;
  };
  driver_verification: {
    profiles_by_status: CountMap; vehicles_by_status: CountMap; documents_pending: number;
  };
  journeys: {
    total: number; by_status: CountMap; created_last_180_days: { month: string; count: number }[];
  };
  bookings: { total: number; by_status: CountMap; confirmed_seats: number };
  safety: { by_status: CountMap; urgent_open: number };
  expense_sharing: {
    finalized_settlements: number;
    eligible_expenses_total_inr: string;
    driver_own_shares_total_inr: string;
    passenger_contributions_total_inr: string;
    passenger_contribution_records: number;
    razorpay_test_payment_attempts: number;
    razorpay_test_payments_by_status: CountMap;
    notice: string;
  };
};

export type AdminUserRecord = {
  id: number; display_name: string; email: string; role: string; is_active: boolean;
  is_email_verified: boolean; is_phone_verified: boolean; date_joined: string;
};
export type AdminJourneyRecord = {
  id: number; driver_name: string; origin_name: string; destination_name: string;
  travel_date: string; departure_time: string; status: string; seats_offered: number;
  confirmed_seats: number; booking_count: number; estimated_total_expenses_inr: string;
  created_at: string;
};
export type AdminBookingRecord = {
  id: number; journey_id: number; origin_name: string; destination_name: string;
  travel_date: string; passenger_name: string; driver_name: string; status: string;
  seats_requested: number; estimated_contribution_per_passenger_inr: string;
  estimated_contribution_total_inr: string; requested_at: string;
};
export type AdminLedgerRecord = {
  id: number; journey_id: number; origin_name: string; destination_name: string;
  travel_date: string; driver_name: string; eligible_total_inr: string;
  driver_own_share_inr: string; passenger_contribution_total_inr: string;
  passenger_seat_count: number; contribution_records: number; finalized_at: string | null;
};

type ListResponse<T> = { total_count: number; results: T[] };
const query = (values: Record<string, string | undefined>) => {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => { if (value) params.set(key, value); });
  const suffix = params.toString();
  return suffix ? "?"+suffix : "";
};

export function getAdminOverview() {
  return apiRequest<AdminOverview>("/admin/overview/", {}, true);
}
export function getAdminUsers(filters: { q?: string; role?: string; active?: string } = {}) {
  return apiRequest<ListResponse<AdminUserRecord>>("/admin/users/"+query(filters), {}, true);
}
export function getAdminJourneys(filters: { q?: string; status?: string } = {}) {
  return apiRequest<ListResponse<AdminJourneyRecord>>("/admin/journeys/"+query(filters), {}, true);
}
export function getAdminBookings(filters: { q?: string; status?: string } = {}) {
  return apiRequest<ListResponse<AdminBookingRecord>>("/admin/bookings/"+query(filters), {}, true);
}
export function getAdminExpenseLedger() {
  return apiRequest<{ total_count: number; results: AdminLedgerRecord[]; notice: string }>(
    "/admin/expense-ledger/", {}, true,
  );
}


export type AdminCleanupItem = { label: string; count: number };
export type AdminCleanupPreview = {
  completed: boolean;
  dry_run?: boolean;
  summary?: AdminCleanupItem[];
  preview_token?: string;
  token_expires_in_seconds?: number;
  output?: string;
  confirmation_phrase?: string;
  backup_acknowledgement?: string;
  preserves?: string[];
  detail?: string;
};

export function getAdminDatabaseCleanupPreview() {
  return apiRequest<AdminCleanupPreview>("/admin/database-cleanup/", {}, true);
}

export function executeAdminDatabaseCleanup(payload: {
  confirmation: string;
  backup_acknowledged: boolean;
  preview_token: string;
}) {
  return apiRequest<AdminCleanupPreview>(
    "/admin/database-cleanup/",
    { method: "POST", body: JSON.stringify(payload) },
    true,
  );
}
