import { apiRequest } from "./api";

export type LocationChoice = {
  name: string;
  display_name: string;
  latitude: number;
  longitude: number;
  state?: string;
  postcode?: string;
};

export type JourneyStop = {
  id?: number;
  sequence?: number;
  location_name: string;
  latitude: string | number;
  longitude: string | number;
};

export type JourneyVehicle = {
  registration_number: string;
  make: string;
  model: string;
  vehicle_type: string;
  passenger_seats: number;
};

export type JourneyRecord = {
  id: number;
  driver_name: string;
  driver_verification_status: string;
  vehicle_details: JourneyVehicle;
  origin_name: string;
  origin_latitude: string;
  origin_longitude: string;
  destination_name: string;
  destination_latitude: string;
  destination_longitude: string;
  travel_date: string;
  departure_time: string;
  seats_offered: number;
  fuel_expense: string;
  toll_expense: string;
  parking_expense: string;
  other_expense: string;
  estimated_total_expenses: string;
  estimated_contribution_per_passenger: string;
  expense_note: string;
  description: string;
  route_distance_km: string | null;
  route_duration_minutes: number | null;
  route_geometry: [number, number][];
  stops: JourneyStop[];
  independently_planned: boolean;
  expenses_only: boolean;
  status: "draft" | "published" | "cancelled" | "completed";
  published_at: string | null;
  created_at: string;
  updated_at: string;
  origin_match_distance_km?: number | null;
  destination_match_distance_km?: number | null;
  matched_origin_name?: string | null;
  matched_destination_name?: string | null;
};

export type JourneySearchParams = {
  origin_lat: number;
  origin_lon: number;
  destination_lat: number;
  destination_lon: number;
  date: string;
  seats: number;
  radius_km?: number;
};

export type JourneyDraftPayload = {
  vehicle: number;
  origin_name: string;
  origin_latitude: number;
  origin_longitude: number;
  destination_name: string;
  destination_latitude: number;
  destination_longitude: number;
  travel_date: string;
  departure_time: string;
  seats_offered: number;
  fuel_expense: string;
  toll_expense: string;
  parking_expense: string;
  other_expense: string;
  expense_note: string;
  description: string;
  route_distance_km?: number | null;
  route_duration_minutes?: number | null;
  route_geometry?: [number, number][];
  stops: Omit<JourneyStop, "id" | "sequence">[];
  independently_planned: true;
  expenses_only: true;
};

export type RoutePreview = {
  distance_km: number;
  duration_minutes: number;
  geometry: [number, number][];
};

export type VehicleOption = {
  id: number;
  registration_number: string;
  make: string;
  model: string;
  passenger_seats: number;
  verification_status: string;
  verification_status_display: string;
};

export async function searchLocations(query: string) {
  const result = await apiRequest<{ results: LocationChoice[] }>(
    "/journeys/locations/search/?q=" + encodeURIComponent(query),
  );
  return result.results;
}

export async function previewRoute(
  origin: LocationChoice,
  destination: LocationChoice,
) {
  return apiRequest<RoutePreview>(
    "/journeys/route-preview/?" + new URLSearchParams({
      origin_lat: String(origin.latitude),
      origin_lon: String(origin.longitude),
      destination_lat: String(destination.latitude),
      destination_lon: String(destination.longitude),
    }),
    {},
    true,
  );
}

export async function searchJourneys(params: JourneySearchParams) {
  const query = new URLSearchParams({
    origin_lat: String(params.origin_lat),
    origin_lon: String(params.origin_lon),
    destination_lat: String(params.destination_lat),
    destination_lon: String(params.destination_lon),
    date: params.date,
    seats: String(params.seats),
    radius_km: String(params.radius_km ?? 25),
  });
  return apiRequest<JourneyRecord[]>("/journeys/?" + query.toString());
}

export async function getJourney(id: number) {
  return apiRequest<JourneyRecord>("/journeys/" + id + "/");
}

export async function getMyJourneys() {
  return apiRequest<JourneyRecord[]>("/journeys/mine/", {}, true);
}

export async function getMyVehicles() {
  return apiRequest<VehicleOption[]>("/drivers/vehicles/", {}, true);
}

export async function createJourneyDraft(payload: JourneyDraftPayload) {
  return apiRequest<JourneyRecord>("/journeys/", {
    method: "POST",
    body: JSON.stringify(payload),
  }, true);
}

export async function publishJourney(id: number) {
  return apiRequest<{ detail: string; journey: JourneyRecord }>(
    "/journeys/" + id + "/publish/",
    { method: "POST", body: JSON.stringify({}) },
    true,
  );
}

export async function cancelJourney(id: number) {
  return apiRequest<{ detail: string; status: string }>(
    "/journeys/" + id + "/cancel/",
    { method: "POST", body: JSON.stringify({}) },
    true,
  );
}
