import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight, CalendarDays, CheckCircle2, Clock3, FileCheck2,
  RefreshCw, ShieldCheck, Wallet,
} from "lucide-react";
import { getMyJourneys, type JourneyRecord } from "../services/journeys";
import {
  completeSandboxPayment, createSandboxPayment, finalizeJourneyExpenses,
  getDriverSettlement, getMyContributions,
  type ExpenseSettlementRecord, type PassengerContributionRecord, type SettlementInput,
} from "../services/finance";

const money=(value:string|number)=>new Intl.NumberFormat("en-IN",{
  style:"currency",currency:"INR",minimumFractionDigits:2,maximumFractionDigits:2,
}).format(Number(value||0));
const dateLabel=(value:string)=>new Date(value+"T00:00:00").toLocaleDateString(
  "en-IN",{weekday:"short",day:"numeric",month:"short",year:"numeric"},
);
function FinanceNotice({text,kind="success"}:{text:string;kind?:"success"|"error"|"info"}) {
  return <div className={"wt-market-notice "+kind} role={kind==="error"?"alert":"status"}>{text}</div>;
}
const emptyExpenses=():SettlementInput=>({
  actual_fuel_expense:"0.00",
  actual_toll_expense:"0.00",
  actual_parking_expense:"0.00",
  actual_other_expense:"0.00",
  actual_expense_note:"",
});

export function DriverFinanceContent() {
  const [journeys,setJourneys]=useState<JourneyRecord[]>([]);
  const [settlements,setSettlements]=useState<Record<number,ExpenseSettlementRecord>>({});
  const [expenses,setExpenses]=useState<Record<number,SettlementInput>>({});
  const [loading,setLoading]=useState(true);
  const [busyId,setBusyId]=useState<number|null>(null);
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");

  const load=async()=>{
    setLoading(true);setError("");
    try{
      const records=await getMyJourneys();
      setJourneys(records);
      const completed=records.filter(item=>item.status==="completed");
      const loaded=await Promise.all(completed.map(async item=>{
        try{return [item.id,await getDriverSettlement(item.id)] as const;}
        catch{return null;}
      }));
      setSettlements(Object.fromEntries(loaded.filter((item):item is readonly [number,ExpenseSettlementRecord]=>item!==null)));
    }catch(err){setError(err instanceof Error?err.message:"Could not load financial records.");}
    finally{setLoading(false);}
  };
  useEffect(()=>{load();},[]);

  const changeExpense=(id:number,key:keyof SettlementInput,value:string)=>{
    setExpenses(current=>({...current,[id]:{...(current[id]??emptyExpenses()),[key]:value}}));
  };
  const submit=async(event:FormEvent<HTMLFormElement>,journey:JourneyRecord)=>{
    event.preventDefault();
    const value=expenses[journey.id]??emptyExpenses();
    const total=Number(value.actual_fuel_expense)+Number(value.actual_toll_expense)+Number(value.actual_parking_expense)+Number(value.actual_other_expense);
    if(!Number.isFinite(total)||total<=0){setError("Enter a positive total of actual eligible journey expenses.");return;}
    setBusyId(journey.id);setError("");setNotice("");
    try{
      const result=await finalizeJourneyExpenses(journey.id,value);
      setNotice(result.detail);
      await load();
    }catch(err){setError(err instanceof Error?err.message:"Expenses could not be finalized.");}
    finally{setBusyId(null);}
  };

  return <div className="wt-market-dashboard-page">
    <div className="wt-dash-heading"><div><span className="wt-eyebrow">DRIVER WORKSPACE</span><h1>Expense records.</h1><p>Submit actual eligible trip costs after the journey has departed and reconcile the shared expense record.</p></div><span className="wt-booking-status wt-booking-confirmed">Cost sharing only</span></div>
    <div className="wt-verification-intro"><Wallet/><div><b>How the final expense split works</b><small>The driver is one cost-sharing participant. Remaining eligible expenses are divided equally across the driver and confirmed passenger seats. Any paise rounding remainder is assigned to the driver's share. No driver earnings or payout is created.</small></div></div>
    {error&&<FinanceNotice text={error} kind="error"/>}{notice&&<FinanceNotice text={notice}/>}
    {loading?<div className="wt-market-empty"><RefreshCw className="wt-spin"/>Loading journey expenses…</div>:
      journeys.length===0?<div className="wt-market-empty"><FileCheck2/><b>No journey records yet.</b><p>Your published journeys and final expense records will appear here.</p><Link to="/dashboard/driver/journeys" className="wt-btn wt-btn-primary">My journeys <ArrowRight size={14}/></Link></div>:
      <div className="wt-finance-list">{journeys.map(journey=>{
        const value=expenses[journey.id]??emptyExpenses();
        const settlement=settlements[journey.id];
        return <article className="wt-panel wt-finance-card" key={journey.id}>
          <div className="wt-booking-card-head"><span>Journey #{journey.id}</span><span className={"wt-status wt-status-"+journey.status}>{journey.status}</span></div>
          <h2>{journey.origin_name} <ArrowRight size={14}/> {journey.destination_name}</h2>
          <div className="wt-booking-meta"><span><CalendarDays size={13}/>{dateLabel(journey.travel_date)}</span><span><Clock3 size={13}/>{journey.departure_time.slice(0,5)}</span><span>{journey.confirmed_seats} confirmed passenger seat(s)</span></div>
          {settlement?<div className="wt-final-settlement">
            <div className="wt-finance-total"><span>Final eligible expenses (driver submitted)</span><b>{money(settlement.eligible_total)}</b></div>
            <div className="wt-finance-grid"><span>Fuel <b>{money(settlement.actual_fuel_expense)}</b></span><span>Tolls <b>{money(settlement.actual_toll_expense)}</b></span><span>Parking <b>{money(settlement.actual_parking_expense)}</b></span><span>Other <b>{money(settlement.actual_other_expense)}</b></span></div>
            <div className="wt-finance-share"><span>Your equal cost share</span><b>{money(settlement.driver_share)}</b><small>Driver share · {settlement.passenger_seat_count} confirmed passenger seats · locked {settlement.finalized_at?new Date(settlement.finalized_at).toLocaleString("en-IN"):""}</small></div>
            {settlement.actual_expense_note&&<p className="wt-booking-message">{settlement.actual_expense_note}</p>}
            <FinanceNotice text="Final expenses are locked. Passenger contribution records have been created. No payments or payouts occur here." kind="info"/>
          </div>:journey.status==="published"?<form className="wt-expense-settlement-form" onSubmit={event=>submit(event,journey)}>
            <h3>Finalize actual eligible expenses</h3>
            <p>Available after the scheduled departure. Submit the amounts actually incurred for this journey. This action locks the contribution calculation and marks the journey completed.</p>
            <div className="wt-expense-input-grid">
              <label className="wt-field"><span>Fuel (₹)</span><input type="number" min="0" step="0.01" value={value.actual_fuel_expense} onChange={e=>changeExpense(journey.id,"actual_fuel_expense",e.target.value)}/></label>
              <label className="wt-field"><span>Tolls (₹)</span><input type="number" min="0" step="0.01" value={value.actual_toll_expense} onChange={e=>changeExpense(journey.id,"actual_toll_expense",e.target.value)}/></label>
              <label className="wt-field"><span>Parking (₹)</span><input type="number" min="0" step="0.01" value={value.actual_parking_expense} onChange={e=>changeExpense(journey.id,"actual_parking_expense",e.target.value)}/></label>
              <label className="wt-field"><span>Other eligible expenses (₹)</span><input type="number" min="0" step="0.01" value={value.actual_other_expense} onChange={e=>changeExpense(journey.id,"actual_other_expense",e.target.value)}/></label>
            </div>
            <label className="wt-field"><span>Expense note (optional)</span><textarea rows={2} maxLength={1000} value={value.actual_expense_note??""} onChange={e=>changeExpense(journey.id,"actual_expense_note",e.target.value)} placeholder="Brief explanation for the expense breakdown"/></label>
            <button className="wt-btn wt-btn-primary" type="submit" disabled={busyId===journey.id}>{busyId===journey.id?"Finalizing…":"Finalize actual expenses"} <CheckCircle2 size={14}/></button>
          </form>:<FinanceNotice text="No financial settlement is available for this journey." kind="info"/>}
        </article>;
      })}</div>}
    <p className="wt-market-footnote">Final expense records are declarations by the journey driver, not verified receipts or a legal determination of eligible expenses. The payment simulator below is not available to drivers.</p>
  </div>;
}

export function PassengerFinanceContent() {
  const [contributions,setContributions]=useState<PassengerContributionRecord[]>([]);
  const [loading,setLoading]=useState(true);
  const [busyId,setBusyId]=useState<number|null>(null);
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");

  const load=()=>{
    setLoading(true);setError("");
    getMyContributions().then(setContributions)
      .catch(err=>setError(err instanceof Error?err.message:"Could not load contribution records."))
      .finally(()=>setLoading(false));
  };
  useEffect(()=>{load();},[]);

  const startPayment=async(contribution:PassengerContributionRecord)=>{
    setBusyId(contribution.id);setError("");setNotice("");
    try{
      const result=await createSandboxPayment(contribution.id);
      setNotice(result.detail);load();
    }catch(err){setError(err instanceof Error?err.message:"Sandbox payment could not be started.");}
    finally{setBusyId(null);}
  };
  const simulate=async(contribution:PassengerContributionRecord,outcome:"succeeded"|"failed")=>{
    const payment=contribution.latest_payment;
    if(!payment)return;
    setBusyId(contribution.id);setError("");setNotice("");
    try{
      const result=await completeSandboxPayment(
        payment.id,outcome,outcome==="failed"?"Simulated test decline":""
      );
      setNotice(result.detail);load();
    }catch(err){setError(err instanceof Error?err.message:"Sandbox result could not be recorded.");}
    finally{setBusyId(null);}
  };

  return <div className="wt-market-dashboard-page">
    <div className="wt-dash-heading"><div><span className="wt-eyebrow">PASSENGER WORKSPACE</span><h1>Expense contributions.</h1><p>Review your final eligible-expense share and explore the test payment workflow.</p></div><span className="wt-booking-status wt-booking-confirmed">Sandbox only</span></div>
    <div className="wt-verification-intro"><ShieldCheck/><div><b>Nothing here moves real money</b><small>Payments on this page are simulated records for testing. No bank, UPI, card, payment gateway or driver account is contacted. Do not enter payment credentials.</small></div></div>
    {error&&<FinanceNotice text={error} kind="error"/>}{notice&&<FinanceNotice text={notice}/>}
    {loading?<div className="wt-market-empty"><RefreshCw className="wt-spin"/>Loading contribution records…</div>:
      contributions.length===0?<div className="wt-market-empty"><Wallet/><b>No finalized contribution records.</b><p>After a driver submits the actual eligible expenses for a completed journey, your individual contribution will appear here.</p><Link to="/dashboard/passenger/bookings" className="wt-btn wt-btn-primary">My bookings <ArrowRight size={14}/></Link></div>:
      <div className="wt-finance-list">{contributions.map(item=>{
        const payment=item.latest_payment;
        const status=payment?.status;
        return <article className="wt-panel wt-finance-card" key={item.id}>
          <div className="wt-booking-card-head"><span>Contribution #{item.id} · Booking #{item.booking_id}</span>
            <span className={"wt-booking-status "+(status==="succeeded"?"wt-booking-confirmed":status==="refunded"?"wt-booking-cancelled":status==="failed"?"wt-booking-declined":"wt-booking-pending")}>{status?status==="created"?"Sandbox initiated":status==="succeeded"?"Sandbox successful":status==="failed"?"Sandbox failed":"Sandbox refunded":"Final expense recorded"}</span>
          </div>
          <h2>{item.origin_name} <ArrowRight size={14}/> {item.destination_name}</h2>
          <div className="wt-booking-meta"><span><CalendarDays size={13}/>{dateLabel(item.travel_date)}</span><span>{item.seat_count} seat(s)</span><span>Driver: {item.driver_name}</span></div>
          <div className="wt-finance-share"><span>Final eligible expense contribution</span><b>{money(item.total_amount)}</b><small>{money(item.per_seat_amount)} per seat · calculated from actual expenses</small></div>
          {payment&&<div className="wt-sandbox-payment-meta"><span>Sandbox reference <b>{payment.reference.slice(0,13)}…</b></span><span>Simulated transaction <b>{payment.status}</b></span>{payment.failure_note&&<span>Test result <b>{payment.failure_note}</b></span>}</div>}
          <div className="wt-booking-actions">
            {!payment||status==="failed"||status==="refunded"?<button className="wt-btn wt-btn-primary" type="button" disabled={busyId===item.id} onClick={()=>startPayment(item)}>{busyId===item.id?"Starting…":status==="failed"?"Retry sandbox test":"Start sandbox payment"} <ArrowRight size={14}/></button>:null}
            {status==="created"&&<>
              <button className="wt-btn wt-btn-outline" type="button" disabled={busyId===item.id} onClick={()=>simulate(item,"failed")}>Simulate failure</button>
              <button className="wt-btn wt-btn-primary" type="button" disabled={busyId===item.id} onClick={()=>simulate(item,"succeeded")}><CheckCircle2 size={14}/> Simulate success</button>
            </>}
          </div>
        </article>;
      })}</div>}
    <p className="wt-market-footnote">The current test interface never collects card or UPI information. A sandbox success is only a database status change. No receipt, real payment confirmation or transfer to the driver is produced.</p>
  </div>;
}
