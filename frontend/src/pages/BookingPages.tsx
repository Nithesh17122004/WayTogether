import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight, CalendarDays, CarFront, Check, Clock3, RefreshCw,
  ShieldCheck, Users, XCircle,
} from "lucide-react";
import {
  approveBooking, cancelBooking, declineBooking, getDriverBookingRequests,
  getMyBookings, type BookingRecord, type BookingStatus,
} from "../services/bookings";

const statusTitle:Record<BookingStatus,string> = {
  pending:"Awaiting driver response",
  confirmed:"Confirmed",
  declined:"Declined",
  cancelled:"Cancelled",
};
const money=(value:string|number)=>new Intl.NumberFormat("en-IN",{
  style:"currency",currency:"INR",maximumFractionDigits:0,
}).format(Number(value||0));
const dateLabel=(value:string)=>new Date(value+"T00:00:00").toLocaleDateString(
  "en-IN",{weekday:"short",day:"numeric",month:"short",year:"numeric"},
);
function BookingStatusPill({status}:{status:BookingStatus}) {
  return <span className={"wt-booking-status wt-booking-"+status}>{statusTitle[status]}</span>;
}
function BookingEmpty({driver}:{driver?:boolean}) {
  return <div className="wt-market-empty"><CalendarDays/><b>{driver?"No booking requests yet.":"You haven't requested a journey yet."}</b><p>{driver?"Passenger requests for your published journeys will appear here.":"Find a journey and request the seats you need. The driver must confirm before seats are reserved."}</p><Link to={driver?"/publish":"/search"} className="wt-btn wt-btn-primary">{driver?"Share a journey":"Find a journey"} <ArrowRight size={14}/></Link></div>;
}
function BookingNotice({text,kind="success"}:{text:string;kind?:"success"|"error"}) {
  return <div className={"wt-market-notice "+kind} role={kind==="error"?"alert":"status"}>{text}</div>;
}

export function PassengerBookingsContent() {
  const [bookings,setBookings]=useState<BookingRecord[]>([]);
  const [loading,setLoading]=useState(true);
  const [busyId,setBusyId]=useState<number|null>(null);
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");
  const load=()=>{
    setLoading(true);setError("");
    getMyBookings().then(setBookings)
      .catch(err=>setError(err instanceof Error?err.message:"Could not load your bookings."))
      .finally(()=>setLoading(false));
  };
  useEffect(()=>{load();},[]);
  const cancel=async(booking:BookingRecord)=>{
    setBusyId(booking.id);setError("");setNotice("");
    try{
      const result=await cancelBooking(booking.id);
      setNotice(result.detail);
      load();
    }catch(err){setError(err instanceof Error?err.message:"Booking could not be cancelled.");}
    finally{setBusyId(null);}
  };
  return <div className="wt-market-dashboard-page">
    <div className="wt-dash-heading"><div><span className="wt-eyebrow">PASSENGER WORKSPACE</span><h1>My bookings.</h1><p>Track requests, driver confirmations and your upcoming shared journeys.</p></div><Link to="/search" className="wt-btn wt-btn-primary">Find a journey <ArrowRight size={14}/></Link></div>
    <div className="wt-verification-intro"><ShieldCheck/><div><b>Booking confirmation</b><small>A request is not a reservation. Your seats become reserved only after the driver confirms your request.</small></div></div>
    {error&&<BookingNotice text={error} kind="error"/>}{notice&&<BookingNotice text={notice}/>}
    {loading?<div className="wt-market-empty"><RefreshCw className="wt-spin"/>Loading your bookings…</div>:bookings.length===0?<BookingEmpty/>:
      <div className="wt-booking-list">{bookings.map(booking=><article className="wt-panel wt-booking-card" key={booking.id}>
        <div className="wt-booking-card-head"><span>Booking #{booking.id}</span><BookingStatusPill status={booking.status}/></div>
        <h2>{booking.journey_origin} <ArrowRight size={15}/> {booking.journey_destination}</h2>
        <div className="wt-booking-meta"><span><CalendarDays size={13}/>{dateLabel(booking.travel_date)}</span><span><Clock3 size={13}/>{booking.departure_time.slice(0,5)}</span><span><Users size={13}/>{booking.seats_requested} seat(s)</span></div>
        <div className="wt-booking-details"><span>Driver <b>{booking.driver_name}</b></span><span>Vehicle <b>{booking.vehicle_name}</b></span></div>
        {booking.request_message&&<p className="wt-booking-message">Your note: {booking.request_message}</p>}
        {booking.driver_response&&<p className="wt-booking-message driver">Driver response: {booking.driver_response}</p>}
        {booking.status==="confirmed"&&<div className="wt-booking-contribution"><span>Current provisional expense share</span><b>{money(booking.estimated_contribution_total)}</b><small>{money(booking.estimated_contribution_per_passenger)} per passenger · may be recalculated as other seats are confirmed</small></div>}
        {booking.status==="pending"&&<p className="wt-booking-footnote">Waiting for the driver to approve or decline. These seats are not reserved yet.</p>}
        <div className="wt-booking-actions"><Link to={"/journeys/"+booking.journey_id} className="wt-text-link">View journey details</Link>{(booking.status==="pending"||booking.status==="confirmed")&&<button type="button" className="wt-btn wt-btn-outline" disabled={busyId===booking.id} onClick={()=>cancel(booking)}><XCircle size={14}/> Cancel request</button>}</div>
      </article>)}</div>}
    <p className="wt-market-footnote">Contribution values are estimates for eligible shared journey expenses only. No payment or refund is processed in this phase.</p>
  </div>;
}

export function DriverBookingRequestsContent() {
  const [bookings,setBookings]=useState<BookingRecord[]>([]);
  const [filter,setFilter]=useState("pending");
  const [responses,setResponses]=useState<Record<number,string>>({});
  const [loading,setLoading]=useState(true);
  const [busyId,setBusyId]=useState<number|null>(null);
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");
  const load=()=>{
    setLoading(true);setError("");
    getDriverBookingRequests(filter).then(setBookings)
      .catch(err=>setError(err instanceof Error?err.message:"Could not load booking requests."))
      .finally(()=>setLoading(false));
  };
  useEffect(()=>{load();},[filter]);
  const decide=async(booking:BookingRecord,decision:"approve"|"decline")=>{
    setBusyId(booking.id);setError("");setNotice("");
    try{
      const response=responses[booking.id]??"";
      const result=decision==="approve"
        ?await approveBooking(booking.id,response)
        :await declineBooking(booking.id,response);
      setNotice(result.detail);
      load();
    }catch(err){setError(err instanceof Error?err.message:"Booking decision failed.");}
    finally{setBusyId(null);}
  };
  return <div className="wt-market-dashboard-page">
    <div className="wt-dash-heading"><div><span className="wt-eyebrow">DRIVER WORKSPACE</span><h1>Booking requests.</h1><p>Review passenger requests and approve only the seats you can offer.</p></div><Link to="/dashboard/driver/journeys" className="wt-btn wt-btn-outline"><CarFront size={14}/> My journeys</Link></div>
    <div className="wt-verification-intro"><ShieldCheck/><div><b>Seat availability is protected</b><small>Approving a request reserves its seats in a database transaction. Pending requests do not hold seats, and the system will prevent approvals that exceed capacity.</small></div></div>
    {error&&<BookingNotice text={error} kind="error"/>}{notice&&<BookingNotice text={notice}/>}
    <div className="wt-booking-filter-row">
      <label><span>Filter requests</span><select value={filter} onChange={e=>setFilter(e.target.value)}><option value="pending">Pending</option><option value="confirmed">Confirmed</option><option value="declined">Declined</option><option value="cancelled">Cancelled</option></select></label>
      <button type="button" className="wt-btn wt-btn-outline" onClick={load}><RefreshCw size={14}/> Refresh</button>
    </div>
    {loading?<div className="wt-market-empty"><RefreshCw className="wt-spin"/>Loading booking requests…</div>:bookings.length===0?<BookingEmpty driver/>:
      <div className="wt-booking-list">{bookings.map(booking=><article className="wt-panel wt-booking-card" key={booking.id}>
        <div className="wt-booking-card-head"><span>Booking #{booking.id}</span><BookingStatusPill status={booking.status}/></div>
        <h2>{booking.journey_origin} <ArrowRight size={15}/> {booking.journey_destination}</h2>
        <div className="wt-booking-meta"><span><CalendarDays size={13}/>{dateLabel(booking.travel_date)}</span><span><Clock3 size={13}/>{booking.departure_time.slice(0,5)}</span><span><Users size={13}/>{booking.seats_requested} seat(s) requested</span></div>
        <div className="wt-booking-details"><span>Passenger <b>{booking.passenger_name}</b></span><span>Vehicle <b>{booking.vehicle_name}</b></span></div>
        {booking.request_message&&<p className="wt-booking-message">Passenger note: {booking.request_message}</p>}
        {booking.status==="confirmed"&&<div className="wt-booking-contribution"><span>Current provisional expense share</span><b>{money(booking.estimated_contribution_total)}</b><small>{money(booking.estimated_contribution_per_passenger)} per passenger · recalculated when confirmed occupancy changes</small></div>}
        {booking.status==="pending"&&<>
          <label className="wt-field wt-booking-response"><span>Optional response to passenger</span><input value={responses[booking.id]??""} onChange={e=>setResponses(v=>({...v,[booking.id]:e.target.value}))} maxLength={500} placeholder="Add a pickup instruction or response"/></label>
          <div className="wt-booking-actions"><button type="button" className="wt-btn wt-btn-outline" disabled={busyId===booking.id} onClick={()=>decide(booking,"decline")}>Decline</button><button type="button" className="wt-btn wt-btn-primary" disabled={busyId===booking.id} onClick={()=>decide(booking,"approve")}><Check size={14}/> Approve and reserve seats</button></div>
        </>}
        {booking.status!=="pending"&&booking.driver_response&&<p className="wt-booking-message driver">Your response: {booking.driver_response}</p>}
        <div className="wt-booking-bottom-link"><Link to={"/journeys/"+booking.journey_id} className="wt-text-link">View journey</Link></div>
      </article>)}</div>}
    <p className="wt-market-footnote">Confirmations reserve seats but do not collect money. Contribution amounts remain provisional until the final booking/payment policy is implemented.</p>
  </div>;
}
