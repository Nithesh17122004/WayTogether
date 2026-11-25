import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight, Bell, Check, CheckCheck, Clock3, MessageCircle,
  RefreshCw, ShieldAlert, ShieldCheck, Star, Trash2, UserRound,
} from "lucide-react";
import { getMyBookings, getDriverBookingRequests, type BookingRecord } from "../services/bookings";
import {
  createEmergencyContact, createSafetyReport, deleteEmergencyContact,
  getBookingMessages, getEmergencyContacts, getMyJourneyReviews,
  getMySafetyReports, getNotifications, markAllNotificationsRead,
  markNotificationRead, sendBookingMessage, submitJourneyReview,
  type BookingMessageRecord, type EmergencyContactRecord,
  type JourneyReviewRecord, type NotificationRecord, type SafetyReportRecord,
} from "../services/trust";

type WorkspaceRole="Passenger"|"Driver";
const dateLabel=(value:string)=>new Date(value+"T00:00:00").toLocaleDateString(
  "en-IN",{weekday:"short",day:"numeric",month:"short",year:"numeric"},
);
function TrustNotice({text,kind="success"}:{text:string;kind?:"success"|"error"|"info"}) {
  return <div className={"wt-market-notice "+kind} role={kind==="error"?"alert":"status"}>{text}</div>;
}
function TrustEmpty({title,body,link}:{title:string;body:string;link?:string}) {
  return <div className="wt-market-empty"><ShieldCheck/><b>{title}</b><p>{body}</p>{link&&<Link to={link} className="wt-btn wt-btn-primary">Continue <ArrowRight size={14}/></Link>}</div>;
}

export function NotificationCenterContent() {
  const [items,setItems]=useState<NotificationRecord[]>([]);
  const [unread,setUnread]=useState(0);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");
  const [busyId,setBusyId]=useState<number|null>(null);
  const load=()=>{
    setLoading(true);setError("");
    getNotifications().then(data=>{setItems(data.results);setUnread(data.unread_count);})
      .catch(err=>setError(err instanceof Error?err.message:"Could not load notifications."))
      .finally(()=>setLoading(false));
  };
  useEffect(()=>{load();},[]);
  const markOne=async(id:number)=>{
    setBusyId(id);setError("");
    try{await markNotificationRead(id);setItems(current=>current.map(item=>item.id===id?{...item,read_at:new Date().toISOString()}:item));setUnread(value=>Math.max(0,value-1));}
    catch(err){setError(err instanceof Error?err.message:"Could not mark notification as read.");}
    finally{setBusyId(null);}
  };
  const markAll=async()=>{
    setBusyId(-1);setError("");setNotice("");
    try{const result=await markAllNotificationsRead();setItems(current=>current.map(item=>({...item,read_at:item.read_at??new Date().toISOString()})));setUnread(0);setNotice(result.detail);}
    catch(err){setError(err instanceof Error?err.message:"Could not mark notifications as read.");}
    finally{setBusyId(null);}
  };
  const destination=(item:NotificationRecord)=>{
    if(item.booking_id)return "/dashboard/messages?booking="+item.booking_id;
    if(item.journey_id)return "/journeys/"+item.journey_id;
    return "/dashboard/notifications";
  };
  return <div className="wt-market-dashboard-page">
    <div className="wt-dash-heading"><div><span className="wt-eyebrow">ACTIVITY CENTER</span><h1>Notifications.</h1><p>Stay informed about booking activity and shared journeys.</p></div><span className="wt-notification-count">{unread} unread</span></div>
    <div className="wt-trust-actions"><button className="wt-btn wt-btn-outline" type="button" onClick={load}><RefreshCw size={14}/> Refresh</button><button className="wt-btn wt-btn-primary" type="button" disabled={busyId!==null||unread===0} onClick={markAll}><CheckCheck size={14}/> Mark all as read</button></div>
    {error&&<TrustNotice text={error} kind="error"/>}{notice&&<TrustNotice text={notice}/>}
    {loading?<div className="wt-market-empty"><RefreshCw className="wt-spin"/>Loading notifications…</div>:items.length===0?<TrustEmpty title="You're all caught up." body="Booking requests, messages and journey updates will appear here."/>:
      <div className="wt-notification-list">{items.map(item=><article className={"wt-panel wt-notification-card "+(!item.read_at?"is-unread":"")} key={item.id}>
        <span className="wt-notification-icon"><Bell size={17}/></span>
        <div className="wt-notification-copy"><div className="wt-notification-top"><b>{item.title}</b>{!item.read_at&&<span className="wt-notification-dot"/>}</div><p>{item.body}</p><small>{new Date(item.created_at).toLocaleString("en-IN")}{item.actor_name?" · "+item.actor_name:""}</small><Link to={destination(item)} className="wt-text-link">Open related item <ArrowRight size={13}/></Link></div>
        {!item.read_at&&<button type="button" className="wt-link-button" disabled={busyId===item.id} onClick={()=>markOne(item.id)} aria-label="Mark as read"><Check size={16}/></button>}
      </article>)}</div>}
  </div>;
}

export function MessagesContent({role}:{role:WorkspaceRole}) {
  const [bookings,setBookings]=useState<BookingRecord[]>([]);
  const [selectedId,setSelectedId]=useState<number|null>(null);
  const [messages,setMessages]=useState<BookingMessageRecord[]>([]);
  const [canSend,setCanSend]=useState(false);
  const [draft,setDraft]=useState("");
  const [loading,setLoading]=useState(true);
  const [threadLoading,setThreadLoading]=useState(false);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");
  const loadBookings=()=>{
    setLoading(true);setError("");
    const request=role==="Passenger"?getMyBookings():getDriverBookingRequests();
    request.then(records=>{
      setBookings(records);
      setSelectedId(current=>current&&records.some(item=>item.id===current)?current:(records[0]?.id??null));
    }).catch(err=>setError(err instanceof Error?err.message:"Could not load booking conversations."))
      .finally(()=>setLoading(false));
  };
  useEffect(()=>{loadBookings();},[role]);
  const selected=useMemo(()=>bookings.find(item=>item.id===selectedId)??null,[bookings,selectedId]);
  const loadThread=async(id:number)=>{
    setThreadLoading(true);setError("");
    try{const result=await getBookingMessages(id);setMessages(result.results);setCanSend(result.can_send);}
    catch(err){setMessages([]);setCanSend(false);setError(err instanceof Error?err.message:"Could not load this message thread.");}
    finally{setThreadLoading(false);}
  };
  useEffect(()=>{if(selectedId!==null)loadThread(selectedId);else{setMessages([]);setCanSend(false);}},[selectedId]);
  const send=async(event:FormEvent<HTMLFormElement>)=>{
    event.preventDefault();
    if(!selectedId||!draft.trim())return;
    setBusy(true);setError("");setNotice("");
    try{await sendBookingMessage(selectedId,draft.trim());setDraft("");await loadThread(selectedId);}
    catch(err){setError(err instanceof Error?err.message:"Message could not be sent.");}
    finally{setBusy(false);}
  };
  return <div className="wt-market-dashboard-page">
    <div className="wt-dash-heading"><div><span className="wt-eyebrow">BOOKING COMMUNICATION</span><h1>Messages.</h1><p>Use the booking thread to coordinate with the other journey participant.</p></div><span className="wt-booking-status wt-booking-confirmed">Private threads</span></div>
    <div className="wt-verification-intro"><MessageCircle/><div><b>Only booking participants can read these messages</b><small>WayTogether keeps messages within the booking thread. Avoid sharing passwords, OTPs, payment credentials or unnecessary personal information.</small></div></div>
    {error&&<TrustNotice text={error} kind="error"/>}{notice&&<TrustNotice text={notice}/>}
    <div className="wt-message-workspace">
      <aside className="wt-panel wt-message-bookings"><div className="wt-message-panel-head"><b>Your conversations</b><button className="wt-link-button" type="button" onClick={loadBookings}>Refresh</button></div>
        {loading?<p className="wt-message-empty">Loading conversations…</p>:bookings.length===0?<p className="wt-message-empty">No booking conversations yet. A thread becomes available after a booking request is created.</p>:
          bookings.map(item=><button type="button" key={item.id} className={"wt-message-booking "+(selectedId===item.id?"is-selected":"")} onClick={()=>setSelectedId(item.id)}>
            <span className="wt-message-avatar"><UserRound size={17}/></span><span className="wt-message-booking-copy"><b>{role==="Passenger"?item.driver_name:item.passenger_name}</b><small>{item.journey_origin} → {item.journey_destination}</small><em>{item.status.replaceAll("_"," ")} · #{item.id}</em></span><ArrowRight size={14}/>
          </button>)}
      </aside>
      <section className="wt-panel wt-message-thread">
        {selected?<><div className="wt-message-thread-head"><div><b>{role==="Passenger"?selected.driver_name:selected.passenger_name}</b><small>{selected.journey_origin} → {selected.journey_destination} · {dateLabel(selected.travel_date)}</small></div><Link className="wt-text-link" to={"/journeys/"+selected.journey_id}>Journey details</Link></div>
          <div className="wt-message-scroll">{threadLoading?<p className="wt-message-empty">Loading messages…</p>:messages.length===0?<p className="wt-message-empty">No messages yet. Send a short note to coordinate your booking.</p>:messages.map(message=><div className={"wt-message-bubble "+(message.is_mine?"mine":"theirs")} key={message.id}><span>{message.content}</span><small>{message.sender_name} · {new Date(message.created_at).toLocaleString("en-IN")}</small></div>)}</div>
          {canSend?<form className="wt-message-compose" onSubmit={send}><textarea rows={2} maxLength={1500} value={draft} onChange={e=>setDraft(e.target.value)} placeholder="Write a message about this booking…" required/><button className="wt-btn wt-btn-primary" type="submit" disabled={busy||!draft.trim()}>{busy?"Sending…":"Send"} <ArrowRight size={14}/></button></form>:<div className="wt-message-closed">This conversation is read-only because the booking or journey is no longer active.</div>}
        </>:<div className="wt-message-empty"><MessageCircle/><b>Select a booking conversation</b><small>Choose a booking on the left to see its messages.</small></div>}
      </section>
    </div>
  </div>;
}

export function SafetyCenterContent({role}:{role:WorkspaceRole}) {
  const [contacts,setContacts]=useState<EmergencyContactRecord[]>([]);
  const [reports,setReports]=useState<SafetyReportRecord[]>([]);
  const [bookings,setBookings]=useState<BookingRecord[]>([]);
  const [contactForm,setContactForm]=useState({contact_name:"",phone:"+91",relationship:"",is_primary:false});
  const [reportForm,setReportForm]=useState({booking_id:"",category:"other",priority:"normal",description:""});
  const [loading,setLoading]=useState(true);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");
  const load=async()=>{
    setLoading(true);setError("");
    try{
      const [contactData,reportData,bookingData]=await Promise.all([
        getEmergencyContacts(),getMySafetyReports(),
        role==="Passenger"?getMyBookings():getDriverBookingRequests(),
      ]);
      setContacts(contactData);setReports(reportData);setBookings(bookingData);
      if(!reportForm.booking_id&&bookingData.length)setReportForm(current=>({...current,booking_id:String(bookingData[0].id)}));
    }catch(err){setError(err instanceof Error?err.message:"Could not load safety centre data.");}
    finally{setLoading(false);}
  };
  useEffect(()=>{load();},[role]);
  const addContact=async(event:FormEvent<HTMLFormElement>)=>{
    event.preventDefault();setBusy(true);setError("");setNotice("");
    try{
      const result=await createEmergencyContact(contactForm);
      setNotice("Emergency contact saved privately to your account.");
      setContactForm({contact_name:"",phone:"+91",relationship:"",is_primary:false});
      await load();
    }catch(err){setError(err instanceof Error?err.message:"Emergency contact could not be saved.");}
    finally{setBusy(false);}
  };
  const removeContact=async(id:number)=>{
    setBusy(true);setError("");setNotice("");
    try{await deleteEmergencyContact(id);setNotice("Emergency contact removed.");await load();}
    catch(err){setError(err instanceof Error?err.message:"Contact could not be removed.");}
    finally{setBusy(false);}
  };
  const report=async(event:FormEvent<HTMLFormElement>)=>{
    event.preventDefault();
    if(!reportForm.booking_id){setError("Select a booking to link your report to.");return;}
    setBusy(true);setError("");setNotice("");
    try{
      const result=await createSafetyReport({...reportForm,booking_id:Number(reportForm.booking_id)});
      setNotice(result.detail);
      setReportForm(current=>({...current,description:""}));
      await load();
    }catch(err){setError(err instanceof Error?err.message:"Safety report could not be submitted.");}
    finally{setBusy(false);}
  };
  return <div className="wt-market-dashboard-page">
    <div className="wt-dash-heading"><div><span className="wt-eyebrow">SAFETY & TRUST</span><h1>Safety centre.</h1><p>Manage your private emergency contacts and report a concern about a booking.</p></div><span className="wt-booking-status wt-booking-confirmed">Private account data</span></div>
    <div className="wt-safety-emergency-note"><ShieldAlert/><div><b>Immediate danger or medical emergency?</b><p>Contact local emergency services directly. A WayTogether report is for platform review; it does not dispatch emergency help or contact your saved contacts.</p></div></div>
    {error&&<TrustNotice text={error} kind="error"/>}{notice&&<TrustNotice text={notice}/>}
    {loading?<div className="wt-market-empty"><RefreshCw className="wt-spin"/>Loading safety centre…</div>:<>
      <section className="wt-panel wt-safety-card"><div className="wt-panel-heading"><div><h2>Emergency contacts</h2><p>Save up to three trusted contacts in your account. Their details are visible only to you.</p></div><span className="wt-notification-count">{contacts.length}/3 saved</span></div>
        {contacts.length>0?<div className="wt-contact-list">{contacts.map(contact=><article className="wt-contact-row" key={contact.id}><span className="wt-message-avatar"><UserRound size={16}/></span><div><b>{contact.contact_name} {contact.is_primary&&<em>Primary</em>}</b><small>{contact.phone} {contact.relationship?"· "+contact.relationship:""}</small></div><button className="wt-link-button danger" type="button" disabled={busy} onClick={()=>removeContact(contact.id)} aria-label={"Remove "+contact.contact_name}><Trash2 size={15}/></button></article>)}</div>:<p className="wt-message-empty">No emergency contacts saved yet.</p>}
        {contacts.length<3&&<form className="wt-contact-form" onSubmit={addContact}>
          <label className="wt-field"><span>Contact name</span><input value={contactForm.contact_name} maxLength={120} onChange={e=>setContactForm(v=>({...v,contact_name:e.target.value}))} placeholder="Trusted contact name" required/></label>
          <label className="wt-field"><span>Phone (international format)</span><input value={contactForm.phone} maxLength={16} onChange={e=>setContactForm(v=>({...v,phone:e.target.value}))} placeholder="+919876543210" required/></label>
          <label className="wt-field"><span>Relationship</span><input value={contactForm.relationship} maxLength={80} onChange={e=>setContactForm(v=>({...v,relationship:e.target.value}))} placeholder="Family, friend…"/></label>
          <label className="wt-primary-contact"><input type="checkbox" checked={contactForm.is_primary} onChange={e=>setContactForm(v=>({...v,is_primary:e.target.checked}))}/> Set as primary contact</label>
          <button className="wt-btn wt-btn-primary" disabled={busy}>Save contact <Check size={14}/></button>
        </form>}
      </section>
      <section className="wt-panel wt-safety-card"><div className="wt-panel-heading"><div><h2>Report a safety concern</h2><p>Only participants in the selected booking can submit a report. Reports are private to you and authorised administrators.</p></div></div>
        {bookings.length===0?<TrustEmpty title="No booking to report." body="A report can be linked to a booking you participated in." link="/search"/>:
          <form className="wt-safety-report-form" onSubmit={report}>
            <label className="wt-field"><span>Booking / journey</span><select value={reportForm.booking_id} onChange={e=>setReportForm(v=>({...v,booking_id:e.target.value}))}>{bookings.map(item=><option key={item.id} value={item.id}>#{item.id} · {item.journey_origin} → {item.journey_destination} · {item.status}</option>)}</select></label>
            <div className="wt-expense-input-grid">
              <label className="wt-field"><span>Concern type</span><select value={reportForm.category} onChange={e=>setReportForm(v=>({...v,category:e.target.value}))}><option value="unsafe_driving">Unsafe driving</option><option value="harassment">Harassment / inappropriate behaviour</option><option value="misrepresentation">Profile or journey misrepresentation</option><option value="payment_dispute">Expense contribution dispute</option><option value="accident">Accident or injury</option><option value="other">Other safety concern</option></select></label>
              <label className="wt-field"><span>Priority</span><select value={reportForm.priority} onChange={e=>setReportForm(v=>({...v,priority:e.target.value}))}><option value="normal">Normal</option><option value="high">High</option><option value="urgent">Urgent</option></select></label>
            </div>
            <label className="wt-field"><span>What happened?</span><textarea rows={4} maxLength={5000} value={reportForm.description} onChange={e=>setReportForm(v=>({...v,description:e.target.value}))} placeholder="Describe the concern factually. Include relevant details and timing." required/></label>
            <button className="wt-btn wt-btn-primary" disabled={busy||!reportForm.description.trim()}>Submit private report <ShieldAlert size={14}/></button>
          </form>}
      </section>
      <section className="wt-panel wt-safety-card"><div className="wt-panel-heading"><div><h2>Your reports</h2><p>Track reports submitted from this account.</p></div></div>
        {reports.length===0?<p className="wt-message-empty">No safety reports submitted.</p>:<div className="wt-report-list">{reports.map(item=><article key={item.id} className="wt-report-row"><div><b>Report #{item.id} · {item.category_display}</b><small>{new Date(item.created_at).toLocaleString("en-IN")} · {item.description}</small></div><span className={"wt-booking-status wt-booking-"+(item.status==="resolved"||item.status==="closed"?"confirmed":"pending")}>{item.status}</span></article>)}</div>}
      </section>
    </>}
  </div>;
}

export function JourneyReviewsContent({role}:{role:WorkspaceRole}) {
  const [bookings,setBookings]=useState<BookingRecord[]>([]);
  const [written,setWritten]=useState<JourneyReviewRecord[]>([]);
  const [received,setReceived]=useState<JourneyReviewRecord[]>([]);
  const [ratings,setRatings]=useState<Record<number,number>>({});
  const [comments,setComments]=useState<Record<number,string>>({});
  const [loading,setLoading]=useState(true);
  const [busyId,setBusyId]=useState<number|null>(null);
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");
  const load=async()=>{
    setLoading(true);setError("");
    try{
      const [bookingData,writtenData,receivedData]=await Promise.all([
        role==="Passenger"?getMyBookings():getDriverBookingRequests(),
        getMyJourneyReviews("written"),getMyJourneyReviews("received"),
      ]);
      setBookings(bookingData);setWritten(writtenData);setReceived(receivedData);
    }catch(err){setError(err instanceof Error?err.message:"Could not load journey reviews.");}
    finally{setLoading(false);}
  };
  useEffect(()=>{load();},[role]);
  const submit=async(event:FormEvent<HTMLFormElement>,booking:BookingRecord)=>{
    event.preventDefault();
    setBusyId(booking.id);setError("");setNotice("");
    try{
      const result=await submitJourneyReview(booking.id,{
        rating:ratings[booking.id]??5,
        comment:comments[booking.id]??"",
      });
      setNotice(result.detail);await load();
    }catch(err){setError(err instanceof Error?err.message:"Review could not be submitted.");}
    finally{setBusyId(null);}
  };
  const reviewable=bookings.filter(item=>item.journey_status==="completed"&&item.status==="confirmed"&&!written.some(review=>review.booking_id===item.id));
  return <div className="wt-market-dashboard-page">
    <div className="wt-dash-heading"><div><span className="wt-eyebrow">COMMUNITY TRUST</span><h1>Journey reviews.</h1><p>Share respectful feedback after a completed shared journey.</p></div><span className="wt-booking-status wt-booking-confirmed">Verified bookings only</span></div>
    {error&&<TrustNotice text={error} kind="error"/>}{notice&&<TrustNotice text={notice}/>}
    {loading?<div className="wt-market-empty"><RefreshCw className="wt-spin"/>Loading reviews…</div>:<>
      <section className="wt-panel wt-safety-card"><div className="wt-panel-heading"><div><h2>Ready to review</h2><p>One review per participant per completed booking. Your feedback is linked to the booking.</p></div></div>
        {reviewable.length===0?<p className="wt-message-empty">No completed bookings are waiting for your review.</p>:<div className="wt-review-list">{reviewable.map(booking=><article className="wt-review-form-card" key={booking.id}>
          <div><b>{booking.journey_origin} → {booking.journey_destination}</b><small>{dateLabel(booking.travel_date)} · Review {role==="Passenger"?booking.driver_name:booking.passenger_name}</small></div>
          <form onSubmit={event=>submit(event,booking)}>
            <label className="wt-field"><span>Rating</span><select value={ratings[booking.id]??5} onChange={e=>setRatings(v=>({...v,[booking.id]:Number(e.target.value)}))}>{[5,4,3,2,1].map(n=><option key={n} value={n}>{n} / 5</option>)}</select></label>
            <label className="wt-field"><span>Comment (optional)</span><textarea rows={2} maxLength={1000} value={comments[booking.id]??""} onChange={e=>setComments(v=>({...v,[booking.id]:e.target.value}))} placeholder="Share respectful feedback about this journey."/></label>
            <button className="wt-btn wt-btn-primary" type="submit" disabled={busyId===booking.id}>Submit review <Star size={14}/></button>
          </form>
        </article>)}</div>}
      </section>
      <div className="wt-reviews-columns">
        <section className="wt-panel wt-safety-card"><h2>Reviews received</h2>{received.length===0?<p className="wt-message-empty">No reviews received yet.</p>:received.map(review=><article className="wt-review-row" key={review.id}><b>{review.reviewer_name} <span>{review.rating}/5 ★</span></b><small>Booking #{review.booking_id} · {new Date(review.created_at).toLocaleDateString("en-IN")}</small>{review.comment&&<p>{review.comment}</p>}</article>)}</section>
        <section className="wt-panel wt-safety-card"><h2>Reviews written</h2>{written.length===0?<p className="wt-message-empty">You haven't written any reviews yet.</p>:written.map(review=><article className="wt-review-row" key={review.id}><b>For {review.reviewee_name} <span>{review.rating}/5 ★</span></b><small>Booking #{review.booking_id} · {new Date(review.created_at).toLocaleDateString("en-IN")}</small>{review.comment&&<p>{review.comment}</p>}</article>)}</section>
      </div>
    </>}
  </div>;
}
