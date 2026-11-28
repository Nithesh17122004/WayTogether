import { useEffect, useState, type FormEvent } from "react";
import {
  CalendarDays, CarFront, FileCheck2,
  IndianRupee, RefreshCw, Search, ShieldAlert, ShieldCheck, Users, Wallet, Database, Trash2,
} from "lucide-react";
import {
  executeAdminDatabaseCleanup, getAdminBookings, getAdminDatabaseCleanupPreview,
  getAdminExpenseLedger, getAdminJourneys, getAdminOverview, getAdminUsers,
  type AdminBookingRecord, type AdminJourneyRecord, type AdminLedgerRecord, type AdminOverview,
  type AdminUserRecord, type AdminCleanupPreview,
} from "../services/admin";

function AdminNotice({ text, error = false }: { text: string; error?: boolean }) {
  return <p className={error ? "wt-auth-error" : "wt-inline-notice"} role={error ? "alert" : "status"}>{text}</p>;
}
function money(value: string | number) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(Number(value || 0));
}
function date(value: string | null) {
  return value ? new Date(value).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "—";
}
function when(value: string | null) {
  return value ? new Date(value).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : "—";
}
function statusText(value: string) { return value.replaceAll("_", " "); }
function AdminHeader({ eyebrow, title, description, refresh, refreshing = false }: {
  eyebrow: string; title: string; description: string; refresh?: () => void; refreshing?: boolean;
}) {
  return <div className="wt-dash-heading"><div><span className="wt-eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>{refresh && <button className="wt-btn wt-btn-outline" type="button" onClick={refresh} disabled={refreshing}><RefreshCw size={14}/> Refresh</button>}</div>;
}
function AdminMetric({ label, value, detail, icon: Icon }: {
  label: string; value: string | number; detail: string; icon: typeof Users;
}) {
  return <article className="wt-panel wt-admin-metric"><span><Icon size={18}/></span><small>{label}</small><b>{value}</b><em>{detail}</em></article>;
}
function Breakdown({ title, values }: { title: string; values: Record<string, number> }) {
  const items = Object.entries(values);
  return <section className="wt-panel wt-admin-breakdown"><h2>{title}</h2>{items.length ? items.map(([key, value]) => <div key={key}><span>{statusText(key)}</span><b>{value}</b></div>) : <p>No records yet.</p>}</section>;
}
function AdminTableEmpty({ loading, count }: { loading: boolean; count: number }) {
  return <div className="wt-admin-table-empty">{loading ? "Loading records…" : count === 0 ? "No matching records found." : "No records to display."}</div>;
}

export function AdminOverviewContent() {
  const [data, setData] = useState<AdminOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = () => {
    setLoading(true); setError("");
    getAdminOverview().then(setData).catch((err) => setError(err instanceof Error ? err.message : "Could not load admin analytics."))
      .finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, []);
  return <div className="wt-market-dashboard-page">
    <AdminHeader eyebrow="PLATFORM OPERATIONS" title="Admin overview." description="Live platform activity and operational health from the WayTogether database." refresh={load} refreshing={loading}/>
    {error && <AdminNotice text={error} error/>}
    {loading && !data ? <div className="wt-market-empty"><RefreshCw className="wt-spin"/>Loading platform analytics…</div> : data && <>
      <div className="wt-admin-metrics-grid">
        <AdminMetric label="Registered users" value={data.users.total.toLocaleString("en-IN")} detail={data.users.active+" active · "+data.users.inactive+" inactive"} icon={Users}/>
        <AdminMetric label="Journeys" value={data.journeys.total.toLocaleString("en-IN")} detail={(data.journeys.by_status.published ?? 0)+" published"} icon={CarFront}/>
        <AdminMetric label="Bookings" value={data.bookings.total.toLocaleString("en-IN")} detail={data.bookings.confirmed_seats+" confirmed seats"} icon={CalendarDays}/>
        <AdminMetric label="Pending documents" value={data.driver_verification.documents_pending} detail="Awaiting staff review" icon={FileCheck2}/>
        <AdminMetric label="Open urgent reports" value={data.safety.urgent_open} detail="Open or under review" icon={ShieldAlert}/>
        <AdminMetric label="Finalised expense records" value={data.expense_sharing.finalized_settlements} detail="Completed journey allocations" icon={Wallet}/>
      </div>
      <div className="wt-admin-overview-grid">
        <Breakdown title="Users by role" values={data.users.by_role}/>
        <Breakdown title="Journeys by status" values={data.journeys.by_status}/>
        <Breakdown title="Bookings by status" values={data.bookings.by_status}/>
        <Breakdown title="Safety reports by status" values={data.safety.by_status}/>
        <Breakdown title="Driver profile verification" values={data.driver_verification.profiles_by_status}/>
        <Breakdown title="Vehicle verification" values={data.driver_verification.vehicles_by_status}/>
      </div>
      <section className="wt-panel wt-admin-trend">
        <div className="wt-panel-heading"><div><h2>Journey activity</h2><p>Journeys created in the last 180 days, grouped by month.</p></div><span className="wt-admin-data-stamp">Updated {when(data.generated_at)}</span></div>
        {data.journeys.created_last_180_days.length ? <div className="wt-admin-trend-bars">{data.journeys.created_last_180_days.map(item => <div key={item.month}><b>{item.count}</b><span style={{height: Math.max(8, item.count / Math.max(...data.journeys.created_last_180_days.map(v => v.count), 1) * 104) + "px"}}/><small>{new Date(item.month).toLocaleDateString("en-IN",{month:"short",year:"2-digit"})}</small></div>)}</div> : <p className="wt-admin-muted">No journey activity in this period.</p>}
      </section>
      <section className="wt-panel wt-admin-ledger-summary">
        <div><span>Eligible expenses finalised</span><b>{money(data.expense_sharing.eligible_expenses_total_inr)}</b></div>
        <div><span>Passenger cost contributions recorded</span><b>{money(data.expense_sharing.passenger_contributions_total_inr)}</b></div>
        <div><span>Driver's own expense share</span><b>{money(data.expense_sharing.driver_own_shares_total_inr)}</b></div>
        <p><ShieldCheck size={15}/>{data.expense_sharing.notice}</p>
        <small>{data.expense_sharing.razorpay_test_payment_attempts} Razorpay Test Mode transactions recorded · no real funds moved</small>
      </section>
    </>}
  </div>;
}

export function AdminUsersContent() {
  const [records, setRecords] = useState<AdminUserRecord[]>([]);
  const [q, setQ] = useState("");
  const [role, setRole] = useState("");
  const [active, setActive] = useState("");
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [submittedQ, setSubmittedQ] = useState("");
  const load = () => {
    setLoading(true); setError("");
    getAdminUsers({ q: submittedQ, role, active }).then((result) => { setRecords(result.results); setCount(result.total_count); })
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load users."))
      .finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, [submittedQ, role, active]);
  const search = (event: FormEvent) => { event.preventDefault(); setSubmittedQ(q.trim()); };
  return <div className="wt-market-dashboard-page">
    <AdminHeader eyebrow="ADMINISTRATOR · COMMUNITY" title="User directory." description="Search registered accounts and review account verification state." refresh={load} refreshing={loading}/>
    {error && <AdminNotice text={error} error/>}
    <form className="wt-admin-filters" onSubmit={search}>
      <label><span>Search name or email</span><div><Search size={15}/><input value={q} onChange={e=>setQ(e.target.value)} placeholder="Search users…"/></div></label>
      <label><span>Role</span><select value={role} onChange={e=>setRole(e.target.value)}><option value="">All roles</option><option value="passenger">Passenger</option><option value="driver">Driver</option><option value="admin">Administrator</option></select></label>
      <label><span>Account</span><select value={active} onChange={e=>setActive(e.target.value)}><option value="">All accounts</option><option value="true">Active</option><option value="false">Inactive</option></select></label>
      <button className="wt-btn wt-btn-primary" type="submit"><Search size={14}/> Search</button>
    </form>
    <section className="wt-panel wt-admin-table-panel">
      <div className="wt-panel-heading"><div><h2>Registered accounts</h2><p>{count} matching accounts · showing up to 100 newest records</p></div></div>
      {loading ? <AdminTableEmpty loading count={count}/> : records.length === 0 ? <AdminTableEmpty loading={false} count={count}/> :
        <div className="wt-table-wrap"><table><thead><tr><th>User</th><th>Role</th><th>Account</th><th>Verification</th><th>Joined</th></tr></thead><tbody>{records.map(user=><tr key={user.id}>
          <td><b>{user.display_name}</b><small>{user.email}</small></td>
          <td><span className="wt-admin-tag">{user.role}</span></td>
          <td><span className={"wt-admin-state "+(user.is_active?"is-good":"is-muted")}>{user.is_active?"Active":"Inactive"}</span></td>
          <td><span className={"wt-admin-state "+(user.is_email_verified?"is-good":"is-warn")}>Email {user.is_email_verified?"verified":"pending"}</span><span className={"wt-admin-state "+(user.is_phone_verified?"is-good":"is-warn")}>Phone {user.is_phone_verified?"verified":"pending"}</span></td>
          <td>{date(user.date_joined)}</td>
        </tr>)}</tbody></table></div>}
    </section>
    <p className="wt-admin-muted">This directory is read-only in this phase. Contact and emergency-contact numbers, identity documents and private report notes are not exposed here.</p>
  </div>;
}

export function AdminJourneysContent() {
  const [records,setRecords]=useState<AdminJourneyRecord[]>([]);
  const [q,setQ]=useState("");
  const [filter,setFilter]=useState("");
  const [count,setCount]=useState(0);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  const [submittedQ,setSubmittedQ]=useState("");
  const load=()=>{
    setLoading(true);setError("");
    getAdminJourneys({q:submittedQ,status:filter}).then(result=>{setRecords(result.results);setCount(result.total_count);})
      .catch(err=>setError(err instanceof Error?err.message:"Could not load journeys.")).finally(()=>setLoading(false));
  };
  useEffect(()=>{load();},[submittedQ,filter]);
  const search=(event:FormEvent)=>{event.preventDefault();setSubmittedQ(q.trim());};
  return <div className="wt-market-dashboard-page">
    <AdminHeader eyebrow="ADMINISTRATOR · MARKETPLACE" title="Journey monitoring." description="Monitor journey publication, route, date and confirmed seat usage." refresh={load} refreshing={loading}/>
    {error&&<AdminNotice text={error} error/>}
    <form className="wt-admin-filters" onSubmit={search}>
      <label><span>Search route or driver</span><div><Search size={15}/><input value={q} onChange={e=>setQ(e.target.value)} placeholder="City or driver email…"/></div></label>
      <label><span>Journey status</span><select value={filter} onChange={e=>setFilter(e.target.value)}><option value="">All statuses</option><option value="draft">Draft</option><option value="published">Published</option><option value="cancelled">Cancelled</option><option value="completed">Completed</option></select></label>
      <button className="wt-btn wt-btn-primary" type="submit"><Search size={14}/> Search</button>
    </form>
    <section className="wt-panel wt-admin-table-panel"><div className="wt-panel-heading"><div><h2>Journey records</h2><p>{count} matching journeys · showing up to 100 newest records</p></div></div>
      {loading?<AdminTableEmpty loading count={count}/>:records.length===0?<AdminTableEmpty loading={false} count={count}/>:<div className="wt-table-wrap"><table><thead><tr><th>Route</th><th>Driver</th><th>Departure</th><th>Seats</th><th>Bookings</th><th>Expense estimate</th><th>Status</th></tr></thead><tbody>{records.map(item=><tr key={item.id}><td><b>{item.origin_name} → {item.destination_name}</b><small>Journey #{item.id}</small></td><td>{item.driver_name}</td><td>{date(item.travel_date)}<small>{item.departure_time}</small></td><td>{item.confirmed_seats}/{item.seats_offered}</td><td>{item.booking_count}</td><td>{money(item.estimated_total_expenses_inr)}</td><td><span className="wt-admin-tag">{statusText(item.status)}</span></td></tr>)}</tbody></table></div>}
    </section>
  </div>;
}

export function AdminBookingsContent() {
  const [records,setRecords]=useState<AdminBookingRecord[]>([]);
  const [q,setQ]=useState("");
  const [filter,setFilter]=useState("");
  const [count,setCount]=useState(0);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  const [submittedQ,setSubmittedQ]=useState("");
  const load=()=>{
    setLoading(true);setError("");
    getAdminBookings({q:submittedQ,status:filter}).then(result=>{setRecords(result.results);setCount(result.total_count);})
      .catch(err=>setError(err instanceof Error?err.message:"Could not load bookings.")).finally(()=>setLoading(false));
  };
  useEffect(()=>{load();},[submittedQ,filter]);
  const search=(event:FormEvent)=>{event.preventDefault();setSubmittedQ(q.trim());};
  return <div className="wt-market-dashboard-page">
    <AdminHeader eyebrow="ADMINISTRATOR · BOOKINGS" title="Booking oversight." description="Review booking requests and confirmation activity across journeys." refresh={load} refreshing={loading}/>
    {error&&<AdminNotice text={error} error/>}
    <form className="wt-admin-filters" onSubmit={search}>
      <label><span>Search route or participant</span><div><Search size={15}/><input value={q} onChange={e=>setQ(e.target.value)} placeholder="City or account email…"/></div></label>
      <label><span>Booking status</span><select value={filter} onChange={e=>setFilter(e.target.value)}><option value="">All statuses</option><option value="pending">Pending</option><option value="confirmed">Confirmed</option><option value="declined">Declined</option><option value="cancelled">Cancelled</option></select></label>
      <button className="wt-btn wt-btn-primary" type="submit"><Search size={14}/> Search</button>
    </form>
    <section className="wt-panel wt-admin-table-panel"><div className="wt-panel-heading"><div><h2>Booking records</h2><p>{count} matching bookings · showing up to 100 newest records</p></div></div>
      {loading?<AdminTableEmpty loading count={count}/>:records.length===0?<AdminTableEmpty loading={false} count={count}/>:<div className="wt-table-wrap"><table><thead><tr><th>Booking</th><th>Passenger</th><th>Driver</th><th>Seats</th><th>Contribution estimate</th><th>Requested</th><th>Status</th></tr></thead><tbody>{records.map(item=><tr key={item.id}><td><b>#{item.id}</b><small>{item.origin_name} → {item.destination_name}</small></td><td>{item.passenger_name}</td><td>{item.driver_name}</td><td>{item.seats_requested}</td><td>{money(item.estimated_contribution_total_inr)}<small>{money(item.estimated_contribution_per_passenger_inr)} per seat</small></td><td>{when(item.requested_at)}</td><td><span className="wt-admin-tag">{statusText(item.status)}</span></td></tr>)}</tbody></table></div>}
    </section>
  </div>;
}

export function AdminExpenseLedgerContent() {
  const [records,setRecords]=useState<AdminLedgerRecord[]>([]);
  const [count,setCount]=useState(0);
  const [notice,setNotice]=useState("");
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  const load=()=>{
    setLoading(true);setError("");
    getAdminExpenseLedger().then(result=>{setRecords(result.results);setCount(result.total_count);setNotice(result.notice);})
      .catch(err=>setError(err instanceof Error?err.message:"Could not load the expense ledger.")).finally(()=>setLoading(false));
  };
  useEffect(()=>{load();},[]);
  return <div className="wt-market-dashboard-page">
    <AdminHeader eyebrow="ADMINISTRATOR · FINANCE OVERSIGHT" title="Expense allocation ledger." description="Read-only visibility into finalised eligible journey expense shares." refresh={load} refreshing={loading}/>
    {error&&<AdminNotice text={error} error/>}
    <div className="wt-safety-emergency-note"><Wallet/><div><b>Expense allocation only — not payment processing</b><p>{notice||"These records do not indicate that money was collected, transferred or paid out. Sandbox transaction attempts are simulated separately."}</p></div></div>
    <section className="wt-panel wt-admin-table-panel"><div className="wt-panel-heading"><div><h2>Finalised expense settlements</h2><p>{count} completed allocations · showing up to 100 latest records</p></div></div>
      {loading?<AdminTableEmpty loading count={count}/>:records.length===0?<AdminTableEmpty loading={false} count={count}/>:<div className="wt-table-wrap"><table><thead><tr><th>Journey</th><th>Driver</th><th>Eligible total</th><th>Driver's own share</th><th>Passenger contributions</th><th>Seats</th><th>Finalised</th></tr></thead><tbody>{records.map(item=><tr key={item.id}><td><b>{item.origin_name} → {item.destination_name}</b><small>Journey #{item.journey_id}</small></td><td>{item.driver_name}</td><td>{money(item.eligible_total_inr)}</td><td>{money(item.driver_own_share_inr)}</td><td>{money(item.passenger_contribution_total_inr)}<small>{item.contribution_records} records</small></td><td>{item.passenger_seat_count}</td><td>{when(item.finalized_at)}</td></tr>)}</tbody></table></div>}
    </section>
    <p className="wt-admin-muted"><IndianRupee size={14}/> Displayed values are final cost-sharing allocations from database records. No payout, refund or live payment action is available in this workspace.</p>
  </div>;
}


export function AdminDatabaseCleanupContent() {
  const [preview,setPreview]=useState<AdminCleanupPreview|null>(null);
  const [loading,setLoading]=useState(true);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");
  const [confirmation,setConfirmation]=useState("");
  const [backupAcknowledged,setBackupAcknowledged]=useState(false);
  const [completed,setCompleted]=useState(false);

  const load=async()=>{
    setLoading(true);setError("");setNotice("");setConfirmation("");setBackupAcknowledged(false);
    try{
      const result=await getAdminDatabaseCleanupPreview();
      setPreview(result);
      setCompleted(Boolean(result.completed));
      if(result.completed)setNotice(result.detail||"The one-time cleanup has already been completed.");
    }catch(err){
      setError(err instanceof Error?err.message:"Could not load the database cleanup preview.");
    }finally{setLoading(false);}
  };
  useEffect(()=>{void load();},[]);

  const execute=async()=>{
    if(!preview?.preview_token)return;
    setBusy(true);setError("");setNotice("");
    try{
      const result=await executeAdminDatabaseCleanup({
        confirmation,
        backup_acknowledged:backupAcknowledged,
        preview_token:preview.preview_token,
      });
      setPreview(result);
      setCompleted(Boolean(result.completed));
      setNotice(result.detail||"Database cleanup finished.");
      setConfirmation("");
      setBackupAcknowledged(false);
    }catch(err){
      const message=err instanceof Error?err.message:"Database cleanup could not be completed.";
      setError(message);
      if(message.toLowerCase().includes("preview")||message.toLowerCase().includes("changed"))void load();
    }finally{setBusy(false);}
  };

  return <div className="wt-market-dashboard-page">
    <AdminHeader
      eyebrow="ADMINISTRATOR · DATABASE MAINTENANCE"
      title="Database cleanup."
      description="Remove demonstration and old application data while preserving administrator access and genuine upcoming journeys."
      refresh={()=>void load()}
      refreshing={loading||busy}
    />
    <div className="wt-admin-cleanup-warning">
      <ShieldAlert size={21}/>
      <div>
        <b>Destructive action — review before executing</b>
        <p>This permanently deletes selected application records. Take a database backup first. This tool is one-time only and cannot be run again from the browser after completion.</p>
      </div>
    </div>

    {error&&<AdminNotice text={error} error/>}
    {notice&&<AdminNotice text={notice}/>}

    {loading?<div className="wt-market-empty"><RefreshCw className="wt-spin"/>Preparing a live database dry run…</div>:
      completed?<section className="wt-panel wt-admin-cleanup-complete">
        <ShieldCheck size={28}/>
        <div><h2>Cleanup completed</h2><p>The one-time database cleanup is recorded. Re-running it from this browser is blocked.</p></div>
      </section>:
      preview?.dry_run?<>
        <section className="wt-panel wt-admin-cleanup-panel">
          <div className="wt-panel-heading">
            <div><h2><Database size={18}/> Live dry-run summary</h2><p>Counts are read directly from your current PostgreSQL database. No records have been deleted.</p></div>
            <span className="wt-booking-status wt-booking-confirmed">Dry run · no changes</span>
          </div>
          <div className="wt-admin-cleanup-counts">
            {(preview.summary||[]).map(item=><div key={item.label}><span>{item.label}</span><b>{item.count.toLocaleString("en-IN")}</b></div>)}
          </div>
          <div className="wt-admin-cleanup-preserve">
            <h3>Records that will be preserved</h3>
            {(preview.preserves||[]).map(item=><p key={item}><ShieldCheck size={15}/>{item}</p>)}
          </div>
        </section>

        <section className="wt-panel wt-admin-cleanup-confirm">
          <h2>Confirm permanent cleanup</h2>
          <p>Before proceeding, export or otherwise secure a backup of the database. The operation removes the counts shown above and cannot be undone from this dashboard.</p>
          <label className="wt-admin-cleanup-checkbox">
            <input type="checkbox" checked={backupAcknowledged} onChange={e=>setBackupAcknowledged(e.target.checked)}/>
            <span>I have taken a database backup, or I understand and accept that this cleanup is irreversible.</span>
          </label>
          <label className="wt-field">
            <span>Type this exact phrase to confirm</span>
            <code className="wt-admin-cleanup-phrase">{preview.confirmation_phrase}</code>
            <input value={confirmation} onChange={e=>setConfirmation(e.target.value)} autoComplete="off" placeholder="Enter the confirmation phrase"/>
          </label>
          <button
            className="wt-btn wt-admin-cleanup-danger"
            type="button"
            disabled={busy||!backupAcknowledged||confirmation!==preview.confirmation_phrase||!preview.preview_token}
            onClick={()=>void execute()}
          >
            {busy?<><RefreshCw className="wt-spin" size={15}/> Cleaning database…</>:<><Trash2 size={15}/> Permanently clean database</>}
          </button>
          <small>The preview token expires after 15 minutes. If the database changes, you must refresh and review a new preview.</small>
        </section>
      </>:<section className="wt-panel wt-admin-cleanup-panel"><p>The cleanup preview is unavailable. Refresh to try again.</p></section>
    }
  </div>;
}
