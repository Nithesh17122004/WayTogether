import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight, CalendarDays, CheckCircle2, Clock3, FileCheck2,
  RefreshCw, ShieldCheck, Wallet,
} from "lucide-react";
import { getMyJourneys, type JourneyRecord } from "../services/journeys";
import {
  createRazorpayOrder, finalizeJourneyExpenses, getDriverSettlement,
  getMyContributions, launchRazorpayCheckout, markRazorpayPaymentFailed,
  verifyRazorpayPayment, type ExpenseSettlementRecord,
  type PassengerContributionRecord, type SettlementInput,
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
    <div className="wt-verification-intro"><Wallet/><div><b>Published passenger pricing</b><small>Each passenger's amount is the fixed driver amount per seat plus the separately disclosed 30% platform fee. Actual journey expenses are collected here as a separate record and do not change the published passenger price. Driver payouts are not enabled.</small></div></div>
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
            <div className="wt-finance-share"><span>Actual eligible-expense allocation to driver</span><b>{money(settlement.driver_share)}</b><small>Cost record · {settlement.passenger_seat_count} confirmed passenger seats · locked {settlement.finalized_at?new Date(settlement.finalized_at).toLocaleString("en-IN"):""}</small></div>
            {settlement.actual_expense_note&&<p className="wt-booking-message">{settlement.actual_expense_note}</p>}
            <FinanceNotice text="Actual expenses are locked separately. Passenger payment records use the fixed amount published for each seat plus the 30% platform fee. No driver payout occurs here." kind="info"/>
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
    <p className="wt-market-footnote">Final expense records are declarations by the journey driver, not verified receipts or a legal determination of eligible expenses. Passenger checkout uses Razorpay Test Mode only. No real funds move, and driver payouts are not enabled.</p>
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
      const result=await createRazorpayOrder(contribution.id);
      setNotice(result.detail);
      await launchRazorpayCheckout({
        keyId:result.key_id,
        orderId:result.order.id,
        amount:result.order.amount,
        currency:result.order.currency,
        customerName:result.customer.name,
        customerEmail:result.customer.email,
        onSuccess:async response=>{
          try{
            const verified=await verifyRazorpayPayment(result.payment.id,response);
            setNotice(verified.detail);
            load();
          }catch(err){
            setError(err instanceof Error?err.message:"Razorpay payment verification failed. Check the payment status before retrying.");
            load();
          }finally{
            setBusyId(null);
          }
        },
        onFailure:async reason=>{
          try{
            const failed=await markRazorpayPaymentFailed(result.payment.id,reason);
            setError(failed.detail);
          }catch(err){
            setError(err instanceof Error?err.message:"The test payment failed; its final status could not be refreshed.");
          }finally{
            load();
            setBusyId(null);
          }
        },
        onDismiss:()=>{
          setBusyId(null);
          setNotice("Checkout closed. No payment was confirmed.");
        },
      });
    }catch(err){
      setError(err instanceof Error?err.message:"Razorpay Checkout could not be opened.");
      setBusyId(null);
    }
  };

  return <div className="wt-market-dashboard-page">
    <div className="wt-dash-heading"><div><span className="wt-eyebrow">PASSENGER WORKSPACE</span><h1>Passenger payments.</h1><p>Review your published per-seat amount and the separately disclosed 30% platform fee. Checkout is Razorpay Test Mode only.</p></div><span className="wt-booking-status wt-booking-confirmed">Razorpay Test Mode</span></div>
    <div className="wt-verification-intro"><ShieldCheck/><div><b>Test transactions only</b><small>Checkout uses Razorpay Test Mode credentials (rzp_test_). No real money is deducted. Live payment keys are rejected by the backend.</small></div></div>
    {error&&<FinanceNotice text={error} kind="error"/>}{notice&&<FinanceNotice text={notice} kind="info"/>}
    {loading?<div className="wt-market-empty"><RefreshCw className="wt-spin"/>Loading contribution records…</div>:
      contributions.length===0?<div className="wt-market-empty"><Wallet/><b>No finalized contribution records.</b><p>After the driver closes the journey's actual-expense record, the published passenger total will appear here. It includes the driver amount and the 30% platform fee.</p><Link to="/dashboard/passenger/bookings" className="wt-btn wt-btn-primary">My bookings <ArrowRight size={14}/></Link></div>:
      <div className="wt-finance-list">{contributions.map(item=>{
        const payment=item.latest_payment;
        const status=payment?.status;
        const isCaptured=status==="captured";
        const badgeClass=isCaptured?"wt-booking-confirmed":status==="failed"?"wt-booking-declined":"wt-booking-pending";
        const badgeLabel=isCaptured?"Paid · Test Mode":status==="failed"?"Payment failed":status==="created"?"Order ready · Test Mode":"Payment not started";
        return <article className="wt-panel wt-finance-card" key={item.id}>
          <div className="wt-booking-card-head"><span>Passenger payment #{item.id} · Booking #{item.booking_id}</span><span className={"wt-booking-status "+badgeClass}>{badgeLabel}</span></div>
          <h2>{item.origin_name} <ArrowRight size={14}/> {item.destination_name}</h2>
          <div className="wt-booking-meta"><span><CalendarDays size={13}/>{dateLabel(item.travel_date)}</span><span>{item.seat_count} seat(s)</span><span>Driver: {item.driver_name}</span></div>
          <div className="wt-finance-share"><span>Passenger total · {item.seat_count} seat(s)</span><b>{money(item.total_amount)}</b><small>Driver amount: {money(item.driver_amount_total)} · Platform fee (30%): {money(item.platform_fee_total)} · Per seat: {money(item.per_seat_amount)}</small></div>
          {payment&&<div className="wt-sandbox-payment-meta"><span>Razorpay order <b>{payment.order_id}</b></span>{payment.payment_id&&<span>Payment ID <b>{payment.payment_id}</b></span>}{payment.failure_reason&&<span>Payment status <b>{payment.failure_reason}</b></span>}</div>}
          <div className="wt-booking-actions">
            {!isCaptured&&<button className="wt-btn wt-btn-primary" type="button" disabled={busyId===item.id} onClick={()=>startPayment(item)}>{busyId===item.id?"Opening Razorpay…":status==="failed"?"Retry Test Mode payment":status==="created"?"Continue to payment":"Pay with Razorpay"} <ArrowRight size={14}/></button>}
            {isCaptured&&<><span className="wt-payment-confirmed"><CheckCircle2 size={15}/> Payment captured and verified</span><Link to="/dashboard/passenger/bookings" className="wt-text-link">View booking and released contact details <ArrowRight size={14}/></Link></>}
          </div>
        </article>;
      })}</div>}
    <p className="wt-market-footnote">This payment flow is restricted to Razorpay Test Mode. The backend creates the order, verifies Razorpay's signature, checks order amount and currency, and confirms capture before marking the contribution paid. The displayed 30% platform fee is included in the passenger total. Real-money collection and driver payouts remain disabled pending applicable legal, tax, insurance and payment-provider approvals.</p>
  </div>;
}
