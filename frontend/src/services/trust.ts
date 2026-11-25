import { apiRequest } from "./api";

export type NotificationRecord = {
  id:number;
  event_type:string;
  title:string;
  body:string;
  actor_name:string|null;
  booking_id:number|null;
  journey_id:number|null;
  read_at:string|null;
  created_at:string;
};
export type BookingMessageRecord = {
  id:number;
  booking_id:number;
  sender_name:string;
  is_mine:boolean;
  content:string;
  created_at:string;
};
export type EmergencyContactRecord = {
  id:number;
  contact_name:string;
  phone:string;
  relationship:string;
  is_primary:boolean;
  created_at:string;
  updated_at:string;
};
export type SafetyReportRecord = {
  id:number;
  booking_id:number|null;
  journey_id:number|null;
  category:string;
  category_display:string;
  priority:string;
  description:string;
  status:string;
  created_at:string;
  updated_at:string;
  resolved_at:string|null;
};
export type JourneyReviewRecord = {
  id:number;
  booking_id:number;
  reviewer_name:string;
  reviewee_name:string;
  rating:number;
  comment:string;
  created_at:string;
};

export async function getNotifications(){
  return apiRequest<{unread_count:number;results:NotificationRecord[]}>("/trust/notifications/",{},true);
}
export async function markNotificationRead(id:number){
  return apiRequest<{detail:string}>("/trust/notifications/"+id+"/read/",{method:"POST",body:JSON.stringify({})},true);
}
export async function markAllNotificationsRead(){
  return apiRequest<{detail:string;updated_count:number}>("/trust/notifications/read-all/",{method:"POST",body:JSON.stringify({})},true);
}
export async function getBookingMessages(bookingId:number){
  return apiRequest<{booking_id:number;can_send:boolean;results:BookingMessageRecord[]}>(
    "/trust/bookings/"+bookingId+"/messages/",{},true,
  );
}
export async function sendBookingMessage(bookingId:number,content:string){
  return apiRequest<{detail:string;message:BookingMessageRecord}>(
    "/trust/bookings/"+bookingId+"/messages/",
    {method:"POST",body:JSON.stringify({content})},
    true,
  );
}
export async function getEmergencyContacts(){
  return apiRequest<EmergencyContactRecord[]>("/trust/safety/contacts/",{},true);
}
export async function createEmergencyContact(payload:Pick<EmergencyContactRecord,"contact_name"|"phone"|"relationship"|"is_primary">){
  return apiRequest<EmergencyContactRecord>(
    "/trust/safety/contacts/",{method:"POST",body:JSON.stringify(payload)},true,
  );
}
export async function updateEmergencyContact(
  id:number,payload:Partial<Pick<EmergencyContactRecord,"contact_name"|"phone"|"relationship"|"is_primary">>,
){
  return apiRequest<EmergencyContactRecord>(
    "/trust/safety/contacts/"+id+"/",{method:"PATCH",body:JSON.stringify(payload)},true,
  );
}
export async function deleteEmergencyContact(id:number){
  return apiRequest<void>("/trust/safety/contacts/"+id+"/",{method:"DELETE"},true);
}
export async function createSafetyReport(payload:{
  booking_id:number;
  category:string;
  priority:string;
  description:string;
}){
  return apiRequest<{detail:string;report:SafetyReportRecord}>(
    "/trust/safety/reports/",{method:"POST",body:JSON.stringify(payload)},true,
  );
}
export async function getMySafetyReports(){
  return apiRequest<SafetyReportRecord[]>("/trust/safety/reports/mine/",{},true);
}
export async function submitJourneyReview(bookingId:number,payload:{rating:number;comment:string}){
  return apiRequest<{detail:string;review:JourneyReviewRecord}>(
    "/trust/reviews/"+bookingId+"/",{method:"POST",body:JSON.stringify(payload)},true,
  );
}
export async function getMyJourneyReviews(type:"written"|"received"="written"){
  return apiRequest<JourneyReviewRecord[]>("/trust/reviews/mine/?type="+type,{},true);
}
