import { apiRequest } from "./api";

export type BookingStatus = "pending" | "confirmed" | "declined" | "cancelled";

export type BookingRecord = {
  id: number;
  journey_id: number;
  journey_origin: string;
  journey_destination: string;
  travel_date: string;
  departure_time: string;
  journey_status: "draft"|"published"|"cancelled"|"completed";
  driver_name: string;
  passenger_name: string;
  vehicle_name: string;
  seats_requested: number;
  request_message: string;
  driver_response: string;
  status: BookingStatus;
  estimated_contribution_per_passenger: string;
  estimated_contribution_total: string;
  requested_at: string;
  updated_at: string;
  responded_at: string | null;
  cancelled_at: string | null;
};

export async function createBooking(payload: {
  journey: number;
  seats_requested: number;
  request_message?: string;
}) {
  return apiRequest<{detail:string;booking:BookingRecord}>(
    "/bookings/",
    {method:"POST",body:JSON.stringify(payload)},
    true,
  );
}

export async function getMyBookings() {
  return apiRequest<BookingRecord[]>("/bookings/mine/",{},true);
}

export async function getDriverBookingRequests(statusFilter?: string) {
  const query = statusFilter ? "?status=" + encodeURIComponent(statusFilter) : "";
  return apiRequest<BookingRecord[]>("/bookings/driver/requests/" + query,{},true);
}

export async function approveBooking(id:number, driverResponse="") {
  return apiRequest<{detail:string;booking:BookingRecord}>(
    "/bookings/"+id+"/approve/",
    {method:"POST",body:JSON.stringify({driver_response:driverResponse})},
    true,
  );
}

export async function declineBooking(id:number, driverResponse="") {
  return apiRequest<{detail:string;booking:BookingRecord}>(
    "/bookings/"+id+"/decline/",
    {method:"POST",body:JSON.stringify({driver_response:driverResponse})},
    true,
  );
}

export async function cancelBooking(id:number) {
  return apiRequest<{detail:string;booking:BookingRecord}>(
    "/bookings/"+id+"/cancel/",
    {method:"POST",body:JSON.stringify({})},
    true,
  );
}
