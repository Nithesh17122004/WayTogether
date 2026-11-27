import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  ArrowRight, BadgeCheck, CalendarDays, CarFront, Check, Clock3,
  FileCheck2, MapPin, Plus, RefreshCw, Search, ShieldCheck, Users,
  XCircle,
} from "lucide-react";
import LocationPicker from "../components/LocationPicker";
import JourneyMap from "../components/JourneyMap";
import { createBooking } from "../services/bookings";
import {
  cancelJourney, createJourneyDraft, getJourney, getMyJourneys, getMyVehicles,
  previewRoute, publishJourney, searchJourneys,
  type JourneyDraftPayload, type JourneyRecord, type LocationChoice,
  type RoutePreview, type VehicleOption,
} from "../services/journeys";

const todayLocal = () => {
  const now = new Date();
  const offset = now.getTimezoneOffset();
  return new Date(now.getTime() - offset * 60000).toISOString().slice(0,10);
};
const money = (value: string | number) => new Intl.NumberFormat("en-IN", {
  style:"currency",currency:"INR",maximumFractionDigits:0,
}).format(Number(value || 0));
const readableDate = (value: string) => new Date(value + "T00:00:00").toLocaleDateString(
  "en-IN",{weekday:"short",day:"numeric",month:"short",year:"numeric"},
);
const displayDuration = (minutes: number | null) => {
  if (!minutes) return "Not calculated";
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return hours ? hours + " hr " + mins + " min" : mins + " min";
};

function PageNotice({children,kind="info"}:{children:ReactNode;kind?:"info"|"error"|"success"}) {
  return <div className={"wt-market-notice " + kind} role={kind==="error"?"alert":"status"}>{children}</div>;
}

function DriverAvatar({journey}:{journey:JourneyRecord}) {
  const initials = journey.driver_name.split(" ").map(n=>n[0]).slice(0,2).join("").toUpperCase();
  return <span className="wt-live-avatar">{journey.driver_photo_url
    ? <img src={journey.driver_photo_url} alt={journey.driver_name + " profile photo"}/>
    : initials}</span>;
}

function JourneyResultCard({journey}:{journey:JourneyRecord}) {
  const matchedFrom = journey.matched_origin_name || journey.origin_name;
  const matchedTo = journey.matched_destination_name || journey.destination_name;
  const usesIntermediateSegment = matchedFrom !== journey.origin_name || matchedTo !== journey.destination_name;
  return <article className="wt-live-journey-card">
    <div className="wt-live-card-top"><span><CalendarDays size={13}/>{readableDate(journey.travel_date)}</span><span className="wt-live-chip"><BadgeCheck size={12}/> Driver verified</span></div>
    <div className="wt-live-route"><div><b>{journey.departure_time.slice(0,5)}</b><small>Departure</small></div><span className="wt-live-route-line"/><div><b>{displayDuration(journey.route_duration_minutes)}</b><small>Estimated journey</small></div></div>
    <div className="wt-live-cities"><b>{matchedFrom}</b><ArrowRight size={15}/><b>{matchedTo}</b></div>
    {usesIntermediateSegment&&<div className="wt-live-stops">Matches an intermediate segment of the driver's planned route</div>}
    {journey.stops.length>0&&<div className="wt-live-stops"><MapPin size={12}/> Via {journey.stops.map(stop=>stop.location_name).join(" · ")}</div>}
    <div className="wt-live-driver"><DriverAvatar journey={journey}/><span><b>{journey.driver_name}</b><small><ShieldCheck size={12}/> Approved driver · {journey.vehicle_details.vehicle_type} · {journey.vehicle_details.passenger_seats} seats</small></span><span className="wt-live-seats"><Users size={13}/>{journey.available_seats} seats available</span></div>
    <div className="wt-live-card-bottom"><span><small>Estimated expense share per passenger*</small><b>{money(journey.estimated_contribution_per_passenger)}</b></span><Link to={"/journeys/"+journey.id} className="wt-btn wt-btn-primary">View journey <ArrowRight size={15}/></Link></div>
  </article>;
}

export function JourneySearchContent() {
  const [searchParams] = useSearchParams();
  const [origin,setOrigin] = useState<LocationChoice|null>(null);
  const [destination,setDestination] = useState<LocationChoice|null>(null);
  const [date,setDate] = useState(searchParams.get("date") || todayLocal());
  const [seats,setSeats] = useState(searchParams.get("seats") || "1");
  const [radius,setRadius] = useState("25");
  const [results,setResults] = useState<JourneyRecord[]>([]);
  const [searched,setSearched] = useState(false);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState("");
  const [routePreview,setRoutePreview] = useState<RoutePreview|null>(null);
  const [routeBusy,setRouteBusy] = useState(false);
  const [routeError,setRouteError] = useState("");

  const buildSearchRoutePreview = async () => {
    if(!origin||!destination) {
      setRouteError("Select both locations before previewing the route.");
      return;
    }
    if(origin.latitude===destination.latitude&&origin.longitude===destination.longitude) {
      setRouteError("Choose two different locations to preview a route.");
      return;
    }
    setRouteBusy(true);
    setRouteError("");
    try {
      const preview = await previewRoute(origin,destination);
      setRoutePreview(preview);
    } catch(err) {
      setRoutePreview(null);
      setRouteError(err instanceof Error?err.message:"Road route preview is temporarily unavailable.");
    } finally {
      setRouteBusy(false);
    }
  };

  const submit = async (event:FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if(!origin||!destination) { setError("Search and select both your starting point and destination."); return; }
    if(origin.latitude===destination.latitude&&origin.longitude===destination.longitude) { setError("Choose two different locations."); return; }
    setBusy(true);setError("");setSearched(true);
    // The route preview is requested alongside the results so it appears
    // automatically after the user searches, without blocking journey matching.
    void buildSearchRoutePreview();
    try {
      const found = await searchJourneys({
        origin_lat:origin.latitude,origin_lon:origin.longitude,
        destination_lat:destination.latitude,destination_lon:destination.longitude,
        date,seats:Number(seats),radius_km:Number(radius),
      });
      setResults(found);
    } catch(err) {
      setResults([]);
      setError(err instanceof Error?err.message:"Journey search is temporarily unavailable.");
    } finally { setBusy(false); }
  };

  return <main className="wt-page"><div className="wt-container wt-market-page">
    <div className="wt-breadcrumb"><Link to="/">Home</Link><span>›</span> Find a journey</div>
    <div className="wt-page-heading"><div><span className="wt-eyebrow">LIVE JOURNEY SEARCH</span><h1>Find people going your way.</h1><p>Search independently planned journeys and share eligible travel expenses.</p></div><span className="wt-live-status"><i/> Live marketplace API</span></div>
    <form className="wt-panel wt-market-search-form" onSubmit={submit}>
      <div className="wt-market-fields">
        <LocationPicker label="Leaving from" placeholder="Search a city or landmark" value={origin} onChange={value=>{setOrigin(value);setRoutePreview(null);setRouteError("");}} initialQuery={searchParams.get("from") || ""}/>
        <LocationPicker label="Going to" placeholder="Search your destination" value={destination} onChange={value=>{setDestination(value);setRoutePreview(null);setRouteError("");}} initialQuery={searchParams.get("to") || ""}/>
        <label className="wt-field"><span><CalendarDays size={14}/> Travel date</span><input type="date" min={todayLocal()} value={date} onChange={e=>setDate(e.target.value)} required/></label>
        <label className="wt-field"><span><Users size={14}/> Passenger seats</span><select value={seats} onChange={e=>setSeats(e.target.value)}>{[1,2,3,4,5,6,7,8].map(n=><option key={n} value={n}>{n} {n===1?"seat":"seats"}</option>)}</select></label>
        <label className="wt-field"><span><MapPin size={14}/> Match radius</span><select value={radius} onChange={e=>setRadius(e.target.value)}><option value="10">Within 10 km</option><option value="25">Within 25 km</option><option value="50">Within 50 km</option><option value="100">Within 100 km</option></select></label>
      </div>
      <button className="wt-btn wt-btn-primary wt-market-submit" disabled={busy}>{busy?<RefreshCw size={16} className="wt-spin"/>:<Search size={16}/>} {busy?"Searching journeys":"Find journeys"}</button>
      <p className="wt-market-help"><ShieldCheck size={13}/> Search and select a result for both locations. You can preview the road route before checking journey availability.</p>
    </form>
    <div className="wt-route-preview-actions wt-search-route-preview-actions">
      <button type="button" className="wt-btn wt-btn-outline" onClick={()=>void buildSearchRoutePreview()} disabled={routeBusy||!origin||!destination}>
        {routeBusy?<RefreshCw size={16} className="wt-spin"/>:<MapPin size={16}/>} {routeBusy?"Building route preview":"Preview travel route"}
      </button>
      <span>Shows the estimated driving distance and time between your selected locations.</span>
    </div>
    {routeError&&<PageNotice kind="error">{routeError}</PageNotice>}
    {routePreview&&origin&&destination&&<section className="wt-search-route-card" aria-label="Travel route preview">
      <div className="wt-search-route-heading"><div><b>Travel preview</b><small>{origin.name} to {destination.name}</small></div><span className="wt-route-preview-badge"><Check size={13}/> Route ready</span></div>
      <JourneyMap
        origin={{latitude:origin.latitude,longitude:origin.longitude,label:origin.name}}
        destination={{latitude:destination.latitude,longitude:destination.longitude,label:destination.name}}
        geometry={routePreview.geometry}
        height={310}
      />
      <div className="wt-route-stats"><span><MapPin size={15}/>{routePreview.distance_km} km by road</span><span><Clock3 size={15}/>{displayDuration(routePreview.duration_minutes)} estimated driving time</span></div>
    </section>}
    {error&&<PageNotice kind="error">{error}</PageNotice>}
    {searched&&!busy&&<div className="wt-market-results-heading"><div><h2>{results.length?results.length+" matching journeys":"No matching journeys yet"}</h2><p>{origin?.name} to {destination?.name} · {readableDate(date)} · {seats} seat(s)</p></div><span>Sorted by route proximity</span></div>}
    {busy&&<div className="wt-market-empty"><RefreshCw className="wt-spin"/><b>Finding journeys near your route…</b></div>}
    {!busy&&searched&&results.length>0&&<div className="wt-live-results">{results.map(journey=><JourneyResultCard key={journey.id} journey={journey}/>)}</div>}
    {!busy&&searched&&results.length===0&&<div className="wt-market-empty"><Search/><b>No journeys found for this route and date.</b><p>Try another date, increase your match radius or check nearby cities. Only currently published, approved driver/vehicle journeys appear here.</p></div>}
    {!searched&&<div className="wt-market-empty wt-market-empty-start"><CompassIcon/><b>Your route search starts here.</b><p>Choose both locations, your travel date and the number of seats. We'll match journeys near both ends of your route.</p></div>}
    <p className="wt-market-footnote">*Illustrative expense contribution assumes all offered passenger seats are occupied and the driver shares the eligible estimated journey expenses. The final allocation is subject to the confirmed passenger count and the approved expense-sharing policy. WayTogether does not set a commercial fare here.</p>
  </div></main>;
}

function CompassIcon(){return <MapPin size={23}/>;}

export function JourneyPublishContent() {
  const navigate = useNavigate();
  const [vehicles,setVehicles] = useState<VehicleOption[]>([]);
  const [vehicleId,setVehicleId] = useState("");
  const [origin,setOrigin] = useState<LocationChoice|null>(null);
  const [destination,setDestination] = useState<LocationChoice|null>(null);
  const [stops,setStops] = useState<LocationChoice[]>([]);
  const [date,setDate] = useState(todayLocal());
  const [time,setTime] = useState("08:00");
  const [seats,setSeats] = useState("1");
  const [expenses,setExpenses] = useState({fuel:"",toll:"",parking:"",other:""});
  const [expenseNote,setExpenseNote] = useState("");
  const [description,setDescription] = useState("");
  const [attested,setAttested] = useState(false);
  const [route,setRoute] = useState<RoutePreview|null>(null);
  const [loadingVehicles,setLoadingVehicles] = useState(true);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState("");
  const [notice,setNotice] = useState("");
  const [draftId,setDraftId] = useState<number|null>(null);

  useEffect(()=>{
    getMyVehicles().then(items=>{
      setVehicles(items);
      if(items.length) setVehicleId(String(items[0].id));
    }).catch(err=>setError(err instanceof Error?err.message:"Sign in with a verified Driver account to publish a journey."))
      .finally(()=>setLoadingVehicles(false));
  },[]);

  const chosenVehicle = vehicles.find(vehicle=>String(vehicle.id)===vehicleId);
  const expenseTotal = useMemo(()=>Object.values(expenses).reduce((sum,value)=>sum+Number(value||0),0),[expenses]);
  const expenseShare = expenseTotal/(Number(seats)+1);
  const availableSeats = chosenVehicle?.passenger_seats ?? 0;

  const buildRoute = async () => {
    if(!origin||!destination){setError("Select your origin and destination before requesting a route preview.");return;}
    setBusy(true);setError("");setNotice("");
    try {
      const preview=await previewRoute(origin,destination);
      setRoute(preview);
      setNotice("Road route preview loaded.");
    } catch(err) {
      setRoute(null);
      setError(err instanceof Error?err.message:"A road routing provider is not configured. You can still save the journey without a route drawing.");
    } finally {setBusy(false);}
  };

  const addStop = () => {
    if(stops.length>=4){setError("You can add up to four intermediate stops in this version.");return;}
    setStops(items=>[...items,{name:"",display_name:"",latitude:0,longitude:0}]);
  };
  const updateStop = (index:number,location:LocationChoice|null) => {
    setStops(items=>items.map((item,i)=>i===index?(location??{name:"",display_name:"",latitude:0,longitude:0}):item));
  };

  const submit = async(event:FormEvent<HTMLFormElement>)=>{
    event.preventDefault();setError("");setNotice("");
    if(!origin||!destination){setError("Search and select both the origin and destination.");return;}
    if(!vehicleId||!chosenVehicle){setError("Register a vehicle before creating a journey.");return;}
    if(Number(seats)<1||Number(seats)>Math.min(8,availableSeats)){setError("Passenger seats cannot exceed the approved vehicle's registered capacity.");return;}
    if(!attested){setError("Confirm that you independently planned this journey and are sharing eligible expenses only.");return;}
    if(expenseTotal<=0){setError("Enter a reasonable estimate of eligible journey expenses.");return;}
    if(stops.some(stop=>!stop.display_name)){setError("Choose a location for each intermediate stop or remove the empty stop.");return;}

    setBusy(true);
    try {
      const payload:JourneyDraftPayload={
        vehicle:Number(vehicleId),
        origin_name:origin.display_name,origin_latitude:origin.latitude,origin_longitude:origin.longitude,
        destination_name:destination.display_name,destination_latitude:destination.latitude,destination_longitude:destination.longitude,
        travel_date:date,departure_time:time,seats_offered:Number(seats),
        fuel_expense:expenses.fuel||"0.00",toll_expense:expenses.toll||"0.00",
        parking_expense:expenses.parking||"0.00",other_expense:expenses.other||"0.00",
        expense_note:expenseNote,description,
        route_distance_km:route?.distance_km??null,
        route_duration_minutes:route?.duration_minutes??null,
        route_geometry:route?.geometry??[],
        stops:stops.filter(stop=>stop.display_name).map(stop=>({
          location_name:stop.display_name,latitude:stop.latitude,longitude:stop.longitude,
        })),
        independently_planned:true,expenses_only:true,
      };
      const draft=await createJourneyDraft(payload);
      setDraftId(draft.id);
      try {
        const published=await publishJourney(draft.id);
        setNotice(published.detail);
        navigate("/journeys/"+draft.id);
      } catch(publishError) {
        const detail=publishError instanceof Error?publishError.message:"Your draft was saved but could not be published.";
        setNotice("Journey draft #"+draft.id+" was saved. Publishing is not yet allowed: "+detail);
      }
    } catch(err) {
      setError(err instanceof Error?err.message:"The journey could not be saved.");
    } finally {setBusy(false);}
  };

  return <main className="wt-page"><div className="wt-container wt-market-page wt-publish-page">
    <div className="wt-breadcrumb"><Link to="/">Home</Link><span>›</span><Link to="/dashboard/driver">Driver workspace</Link><span>›</span> Share a journey</div>
    <div className="wt-page-heading"><div><span className="wt-eyebrow">FOR VERIFIED DRIVERS</span><h1>Share the journey you already planned.</h1><p>Offer available seats on a privately planned trip and share eligible journey expenses.</p></div><Link to="/driver/verification" className="wt-btn wt-btn-outline"><FileCheck2 size={15}/> Driver verification</Link></div>
    {error&&<PageNotice kind="error">{error}</PageNotice>}{notice&&<PageNotice kind="success">{notice}</PageNotice>}
    <form className="wt-publish-layout" onSubmit={submit}>
      <div className="wt-publish-main">
        <section className="wt-panel wt-publish-section">
          <div className="wt-publish-section-title"><span>01</span><div><h2>Journey route</h2><p>Choose the route you were already planning to travel.</p></div></div>
          <div className="wt-publish-locations">
            <LocationPicker label="Starting point" placeholder="Search city, town or landmark" value={origin} onChange={value=>{setOrigin(value);setRoute(null);}}/>
            <LocationPicker label="Destination" placeholder="Search where you're headed" value={destination} onChange={value=>{setDestination(value);setRoute(null);}}/>
          </div>
          <div className="wt-route-preview-actions"><button type="button" className="wt-btn wt-btn-outline" onClick={buildRoute} disabled={busy||!origin||!destination}><MapPin size={15}/> Preview road route</button><span>Road distance and duration depend on the configured routing provider.</span></div>
          {route&&origin&&destination&&<><JourneyMap origin={{latitude:origin.latitude,longitude:origin.longitude,label:origin.name}} destination={{latitude:destination.latitude,longitude:destination.longitude,label:destination.name}} geometry={route.geometry} height={250}/><div className="wt-route-stats"><span><MapPin size={14}/>{route.distance_km} km</span><span><Clock3 size={14}/>{displayDuration(route.duration_minutes)}</span></div></>}
          <div className="wt-intermediate-head"><b>Intermediate stops</b><button type="button" className="wt-link-button" onClick={addStop}><Plus size={13}/> Add stop</button></div>
          {stops.map((stop,index)=><div className="wt-stop-picker" key={index}><LocationPicker label={"Stop "+(index+1)} placeholder="Search a town or landmark" value={stop.display_name?stop:null} onChange={value=>updateStop(index,value)}/><button type="button" aria-label="Remove stop" className="wt-remove-stop" onClick={()=>setStops(items=>items.filter((_,i)=>i!==index))}><XCircle size={17}/></button></div>)}
        </section>

        <section className="wt-panel wt-publish-section">
          <div className="wt-publish-section-title"><span>02</span><div><h2>Travel schedule and vehicle</h2><p>Share accurate departure and seat information.</p></div></div>
          {loadingVehicles?<p className="wt-loading-inline">Loading your vehicles…</p>:vehicles.length===0?<PageNotice kind="error">No vehicles found. Complete driver verification and register a vehicle before publishing.</PageNotice>:<>
            <label className="wt-field"><span><CarFront size={14}/> Select an approved vehicle</span><select value={vehicleId} onChange={e=>setVehicleId(e.target.value)}>{vehicles.map(vehicle=><option key={vehicle.id} value={vehicle.id}>{vehicle.registration_number} · {vehicle.make} {vehicle.model} · {vehicle.verification_status_display}</option>)}</select></label>
            {chosenVehicle&&chosenVehicle.verification_status!=="approved"&&<PageNotice kind="info">This vehicle is {chosenVehicle.verification_status_display.toLowerCase()}. You can save a draft, but publishing requires administrator approval.</PageNotice>}
          </>}
          <div className="wt-publish-grid">
            <label className="wt-field"><span><CalendarDays size={14}/> Travel date</span><input type="date" min={todayLocal()} value={date} onChange={e=>setDate(e.target.value)} required/></label>
            <label className="wt-field"><span><Clock3 size={14}/> Departure time</span><input type="time" value={time} onChange={e=>setTime(e.target.value)} required/></label>
            <label className="wt-field"><span><Users size={14}/> Passenger seats offered</span><select value={seats} onChange={e=>setSeats(e.target.value)}>{Array.from({length:Math.max(1,Math.min(8,availableSeats))},(_,i)=>i+1).map(n=><option key={n} value={n}>{n} {n===1?"seat":"seats"}</option>)}</select></label>
          </div>
        </section>

        <section className="wt-panel wt-publish-section">
          <div className="wt-publish-section-title"><span>03</span><div><h2>Eligible journey expenses</h2><p>Enter estimated expenses for the whole journey, not a commercial fare.</p></div></div>
          <div className="wt-publish-grid wt-expense-grid">
            <label className="wt-field"><span>Fuel estimate (₹)</span><input type="number" min="0" step="0.01" value={expenses.fuel} onChange={e=>setExpenses(v=>({...v,fuel:e.target.value}))} placeholder="0.00"/></label>
            <label className="wt-field"><span>Tolls (₹)</span><input type="number" min="0" step="0.01" value={expenses.toll} onChange={e=>setExpenses(v=>({...v,toll:e.target.value}))} placeholder="0.00"/></label>
            <label className="wt-field"><span>Parking (₹)</span><input type="number" min="0" step="0.01" value={expenses.parking} onChange={e=>setExpenses(v=>({...v,parking:e.target.value}))} placeholder="0.00"/></label>
            <label className="wt-field"><span>Other eligible costs (₹)</span><input type="number" min="0" step="0.01" value={expenses.other} onChange={e=>setExpenses(v=>({...v,other:e.target.value}))} placeholder="0.00"/></label>
          </div>
          <label className="wt-field"><span>Expense notes (optional)</span><input value={expenseNote} onChange={e=>setExpenseNote(e.target.value)} maxLength={500} placeholder="For example: fuel estimate and tolls for the planned journey"/></label>
          <div className="wt-expense-estimate"><div><small>Total estimated expenses</small><b>{money(expenseTotal)}</b></div><div><small>Estimated share per passenger*</small><b>{money(expenseShare)}</b></div></div>
          <p className="wt-market-footnote">*Preview assumes every offered passenger seat is occupied and the driver shares the total eligible expenses equally. Final allocation will depend on actual confirmed passengers and the approved policy. No platform commission or driver profit is calculated here.</p>
        </section>

        <section className="wt-panel wt-publish-section">
          <div className="wt-publish-section-title"><span>04</span><div><h2>Journey details</h2><p>Help passengers understand your trip.</p></div></div>
          <label className="wt-field"><span>Additional information (optional)</span><textarea rows={3} maxLength={1000} value={description} onChange={e=>setDescription(e.target.value)} placeholder="Share useful details about your planned journey, meeting points or luggage space."/></label>
          <label className="wt-independent-attest"><input type="checkbox" checked={attested} onChange={e=>setAttested(e.target.checked)}/><span><b>I independently planned this journey and will make it even if no passengers join.</b><small>I confirm this is a private journey and passenger contributions are intended only to share eligible journey expenses. I am not creating this trip to earn income from passenger transport.</small></span></label>
        </section>
      </div>
      <aside className="wt-panel wt-publish-summary"><span className="wt-eyebrow">PUBLISH CHECKLIST</span><h3>Ready to share?</h3><ul>
        <li className={origin&&destination?"done":""}><Check size={14}/> Origin and destination selected</li>
        <li className={chosenVehicle?.verification_status==="approved"?"done":""}><Check size={14}/> Vehicle approved</li>
        <li className={expenseTotal>0?"done":""}><Check size={14}/> Expense estimate entered</li>
        <li className={attested?"done":""}><Check size={14}/> Independent journey confirmed</li>
      </ul>
      <div className="wt-publish-summary-note"><ShieldCheck size={17}/><span>Only approved drivers and approved vehicles can publish. A saved draft will remain private until it passes the verification checks.</span></div>
      <button className="wt-btn wt-btn-primary wt-full" disabled={busy||loadingVehicles||!vehicles.length}>{busy?"Saving journey…":"Save and publish journey"} <ArrowRight size={15}/></button>
      <Link to="/dashboard/driver/journeys" className="wt-text-link">View my journey drafts <ArrowRight size={14}/></Link>
      {draftId&&<p className="wt-market-footnote">Draft ID: {draftId}</p>}
    </aside>
    </form>
  </div></main>;
}

export function JourneyDetailContent() {
  const {id} = useParams();
  const [journey,setJourney]=useState<JourneyRecord|null>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  const [bookingError,setBookingError]=useState("");
  const [bookingNotice,setBookingNotice]=useState("");
  const [bookingBusy,setBookingBusy]=useState(false);
  const [seatsRequested,setSeatsRequested]=useState("1");
  const [requestMessage,setRequestMessage]=useState("");

  const loadJourney=()=>{
    if(!id||!/^\\d+$/.test(id)){setError("Journey not found.");setLoading(false);return;}
    setLoading(true);
    getJourney(Number(id)).then(data=>{
      setJourney(data);
      setSeatsRequested(current=>String(Math.max(1,Math.min(Number(current)||1,data.available_seats||1))));
    }).catch(err=>setError(err instanceof Error?err.message:"Journey could not be loaded."))
      .finally(()=>setLoading(false));
  };
  useEffect(()=>{loadJourney();},[id]);

  const submitBooking=async(event:FormEvent<HTMLFormElement>)=>{
    event.preventDefault();
    if(!journey)return;
    if(journey.available_seats<=0){setBookingError("This journey has no remaining seats.");return;}
    setBookingBusy(true);setBookingError("");setBookingNotice("");
    try{
      const result=await createBooking({
        journey:journey.id,
        seats_requested:Number(seatsRequested),
        request_message:requestMessage.trim(),
      });
      setBookingNotice(result.detail);
      setRequestMessage("");
      loadJourney();
    }catch(err){
      setBookingError(err instanceof Error?err.message:"Your booking request could not be sent.");
    }finally{setBookingBusy(false);}
  };

  if(loading) return <main className="wt-page"><div className="wt-container wt-market-empty"><RefreshCw className="wt-spin"/>Loading journey details…</div></main>;
  if(error||!journey) return <main className="wt-page"><div className="wt-container wt-market-page"><PageNotice kind="error">{error||"Journey not found."}</PageNotice><Link to="/search" className="wt-btn wt-btn-primary">Back to search</Link></div></main>;

  const origin={latitude:Number(journey.origin_latitude),longitude:Number(journey.origin_longitude),label:journey.origin_name};
  const destination={latitude:Number(journey.destination_latitude),longitude:Number(journey.destination_longitude),label:journey.destination_name};
  const stops=journey.stops.map(stop=>({latitude:Number(stop.latitude),longitude:Number(stop.longitude),label:stop.location_name}));
  return <main className="wt-page"><div className="wt-container wt-market-page">
    <div className="wt-breadcrumb"><Link to="/">Home</Link><span>›</span><Link to="/search">Find a journey</Link><span>›</span> Journey #{journey.id}</div>
    <div className="wt-page-heading"><div><span className="wt-eyebrow">PUBLISHED JOURNEY</span><h1>{journey.origin_name} <span className="wt-gradient-arrow">→</span> {journey.destination_name}</h1><p>Shared journey published by {journey.driver_name}.</p></div><span className="wt-live-status"><i/> {journey.status}</span></div>
    <div className="wt-live-detail-grid">
      <section className="wt-panel wt-live-detail-main">
        <div className="wt-detail-stats"><div><CalendarDays/><small>Travel date</small><b>{readableDate(journey.travel_date)}</b></div><div><Clock3/><small>Departure</small><b>{journey.departure_time.slice(0,5)}</b></div><div><Users/><small>Seats available</small><b>{journey.available_seats} / {journey.seats_offered}</b></div></div>
        <div className="wt-live-map-heading"><h2>Journey route</h2><span>{journey.route_distance_km?journey.route_distance_km+" km":"Distance unavailable"}</span></div>
        <JourneyMap origin={origin} destination={destination} geometry={journey.route_geometry} stops={stops} height={350}/>
        {stops.length>0&&<div className="wt-live-stop-list"><b>Intermediate stops</b>{stops.map((stop,index)=><span key={stop.label}><i>{index+1}</i>{stop.label}</span>)}</div>}
        <h2 className="wt-live-subheading">About this journey</h2>
        <p className="wt-live-description">{journey.description||"The driver has independently planned this journey and is sharing eligible journey expenses with fellow travellers."}</p>
        {journey.expense_note&&<div className="wt-expense-note"><b>Expense note</b><p>{journey.expense_note}</p></div>}
      </section>
      <aside className="wt-panel wt-live-booking-panel">
        <span className="wt-eyebrow">ESTIMATED EXPENSE SHARE</span>
        <strong>{money(journey.estimated_contribution_per_passenger)}</strong>
        <small>Estimated per passenger if all offered seats are occupied</small>
        <div className="wt-summary-line"><span>Total eligible expenses (estimate)</span><b>{money(journey.estimated_total_expenses)}</b></div>
        <div className="wt-summary-line"><span>Passenger seats confirmed</span><b>{journey.confirmed_seats}</b></div>
        <div className="wt-summary-line"><span>Passenger seats available</span><b>{journey.available_seats}</b></div>
        <div className="wt-summary-line"><span>Estimated distance</span><b>{journey.route_distance_km?journey.route_distance_km+" km":"Not available"}</b></div>
        <div className="wt-summary-line"><span>Estimated duration</span><b>{displayDuration(journey.route_duration_minutes)}</b></div>
        <div className="wt-live-driver-profile"><DriverAvatar journey={journey}/><span><b>{journey.driver_name}</b><small><BadgeCheck size={12}/> Verified driver · {journey.vehicle_details.vehicle_type} · {journey.vehicle_details.passenger_seats} seats</small></span></div>
        {bookingError&&<PageNotice kind="error">{bookingError}</PageNotice>}
        {bookingNotice&&<PageNotice kind="success">{bookingNotice}</PageNotice>}
        {journey.available_seats>0?<form className="wt-booking-request-form" onSubmit={submitBooking}>
          <h3>Request a seat</h3>
          <label className="wt-field"><span>Number of seats</span><select value={seatsRequested} onChange={e=>setSeatsRequested(e.target.value)}>{Array.from({length:journey.available_seats},(_,i)=>i+1).map(n=><option key={n} value={n}>{n} {n===1?"seat":"seats"}</option>)}</select></label>
          <label className="wt-field"><span>Message to driver (optional)</span><textarea rows={3} maxLength={500} value={requestMessage} onChange={e=>setRequestMessage(e.target.value)} placeholder="Add a brief pickup or travel note."/></label>
          <button className="wt-btn wt-btn-primary wt-full" type="submit" disabled={bookingBusy}>{bookingBusy?"Sending request…":"Request "+seatsRequested+" seat(s)"} <ArrowRight size={15}/></button>
          <p className="wt-booking-request-note">Your request is pending until the driver approves it. Seats are not reserved and no money is collected at this point.</p>
          <Link to="/dashboard/passenger/bookings" className="wt-text-link">View my bookings <ArrowRight size={13}/></Link>
        </form>:<div className="wt-market-notice info">All passenger seats are currently confirmed. Check again later for availability.</div>}
        <p className="wt-market-footnote">*The displayed full-occupancy estimate is provisional. Confirmed booking contributions are recalculated as seat occupancy changes. No payment is taken in Phase 6.</p>
      </aside>
    </div>
  </div></main>;
}

export function MyJourneysContent() {
  const [journeys,setJourneys]=useState<JourneyRecord[]>([]);
  const [loading,setLoading]=useState(true);
  const [busyId,setBusyId]=useState<number|null>(null);
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");
  const load=()=>{
    setLoading(true);setError("");
    getMyJourneys().then(setJourneys).catch(err=>setError(err instanceof Error?err.message:"Could not load your journeys."))
      .finally(()=>setLoading(false));
  };
  useEffect(()=>{load();},[]);
  const publish=async(id:number)=>{
    setBusyId(id);setError("");setNotice("");
    try{const result=await publishJourney(id);setNotice(result.detail);load();}
    catch(err){setError(err instanceof Error?err.message:"Journey could not be published.");}
    finally{setBusyId(null);}
  };
  const cancel=async(id:number)=>{
    setBusyId(id);setError("");setNotice("");
    try{const result=await cancelJourney(id);setNotice(result.detail);load();}
    catch(err){setError(err instanceof Error?err.message:"Journey could not be cancelled.");}
    finally{setBusyId(null);}
  };
  return <div className="wt-market-dashboard-page"><div className="wt-container wt-market-page">
    <div className="wt-breadcrumb"><Link to="/">Home</Link><span>›</span><Link to="/dashboard/driver">Driver workspace</Link><span>›</span> My journeys</div>
    <div className="wt-page-heading"><div><span className="wt-eyebrow">DRIVER WORKSPACE</span><h1>My journeys.</h1><p>Manage drafts and published journeys you've planned.</p></div><Link to="/publish" className="wt-btn wt-btn-primary"><Plus size={15}/> Create journey</Link></div>
    {error&&<PageNotice kind="error">{error}</PageNotice>}{notice&&<PageNotice kind="success">{notice}</PageNotice>}
    {loading?<div className="wt-market-empty"><RefreshCw className="wt-spin"/>Loading your journeys…</div>:journeys.length===0?<div className="wt-market-empty"><CarFront/><b>You haven't created a journey yet.</b><p>Publish a journey you were already planning to make.</p><Link to="/publish" className="wt-btn wt-btn-primary">Share a journey <ArrowRight size={14}/></Link></div>:
      <div className="wt-my-journeys">{journeys.map(journey=><article className="wt-panel wt-my-journey-card" key={journey.id}>
        <div className="wt-my-journey-top"><span>Journey #{journey.id}</span><span className={"wt-status wt-status-"+journey.status}>{journey.status}</span></div>
        <h2>{journey.origin_name} <ArrowRight size={15}/> {journey.destination_name}</h2>
        <p><CalendarDays size={13}/>{readableDate(journey.travel_date)} · {journey.departure_time.slice(0,5)} · {journey.seats_offered} seats</p>
        <div className="wt-my-journey-actions"><Link to={"/journeys/"+journey.id} className="wt-text-link">View details</Link>{journey.status==="draft"&&<button className="wt-btn wt-btn-primary" disabled={busyId===journey.id} onClick={()=>publish(journey.id)}>Publish <ArrowRight size={14}/></button>}{(journey.status==="draft"||journey.status==="published")&&<button className="wt-btn wt-btn-outline" disabled={busyId===journey.id} onClick={()=>cancel(journey.id)}><XCircle size={14}/> Cancel</button>}</div>
      </article>)}</div>}
  </div></div>;
}
