import "./phase2.css";
import { apiRequest, downloadPrivateFile, getCurrentUser, hasAuthSession, logoutCurrentSession, setAuthTokens } from "./services/api";
import { JourneyDetailContent, JourneyPublishContent, JourneySearchContent, MyJourneysContent } from "./pages/JourneyPages";
import { DriverBookingRequestsContent, PassengerBookingsContent } from "./pages/BookingPages";
import { getMyJourneys, getUpcomingJourneys, type JourneyRecord } from "./services/journeys";
import { DriverFinanceContent, PassengerFinanceContent } from "./pages/FinancePages";
import { AdminSafetyReportsContent, JourneyReviewsContent, MessagesContent, NotificationCenterContent, SafetyCenterContent } from "./pages/TrustPages";
import { AdminBookingsContent, AdminDatabaseCleanupContent, AdminExpenseLedgerContent, AdminJourneysContent, AdminOverviewContent, AdminUsersContent } from "./pages/AdminPages";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import {
  ArrowDownUp, ArrowRight, ArrowUpRight, BadgeCheck, Bell, CalendarDays,
  CarFront, Check, CircleHelp, Compass, FileCheck2,
  LayoutDashboard, LogOut, MapPin, Menu, MessageCircle, Plus, Search,
  Settings, ShieldCheck, Sparkles, Star, Users, Wallet, X,
} from "lucide-react";
import {
  BrowserRouter, Link, NavLink, Route, Routes, useNavigate,
} from "react-router-dom";

function Brand() {
  return <Link className="wt-brand" to="/" aria-label="WayTogether home"><img className="wt-brand-image" src="/waytogether-logo.svg" alt="" aria-hidden="true"/><span className="wt-brand-word">Way<span>Together</span></span></Link>;
}
function Eyebrow({ children }: { children: ReactNode }) { return <span className="wt-eyebrow">{children}</span>; }
function PreviewLabel() { return <span className="wt-preview-label">DOCUMENT WORKFLOW</span>; }

function PublicHeader() {
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);
  return <header className="wt-public-header"><div className="wt-container wt-nav">
    <Brand/>
    <nav className={open ? "wt-main-nav is-open" : "wt-main-nav"} aria-label="Main navigation">
      <a href="/#how-it-works" onClick={close}>How it works</a><Link to="/search" onClick={close}>Explore journeys</Link><a href="/#safety" onClick={close}>Safety</a><a href="/#about" onClick={close}>About</a>
      <div className="wt-mobile-nav-cta"><Link className="wt-btn wt-btn-ghost" to="/login" onClick={close}>Log in</Link><Link className="wt-btn wt-btn-primary" to="/publish" onClick={close}>Share a journey <ArrowUpRight size={16}/></Link></div>
    </nav>
    <div className="wt-nav-actions"><Link className="wt-login-link" to="/login">Log in</Link><Link className="wt-btn wt-btn-primary wt-nav-cta" to="/publish">Share a journey <ArrowUpRight size={16}/></Link></div>
    <button className="wt-menu-btn" onClick={()=>setOpen(!open)} aria-label={open?"Close menu":"Open menu"} aria-expanded={open}>{open?<X/>:<Menu/>}</button>
  </div></header>;
}
function PublicFooter() {
  return <footer className="wt-footer"><div className="wt-container wt-footer-top"><div><Brand/><p>Share the same route.<br/>Make the journey more connected.</p></div><div className="wt-footer-links">
    <div><b>Explore</b><Link to="/search">Find a journey</Link><Link to="/publish">Share a journey</Link><a href="/#how-it-works">How it works</a></div>
    <div><b>WayTogether</b><a href="/#about">About us</a><a href="/#safety">Safety</a><a href="/#routes">Popular routes</a></div>
    <div><b>Support</b><a href="mailto:hello@waytogether.in">Contact</a><a href="/#safety">Community guidelines</a><a href="/#safety">Help centre</a></div>
  </div></div><div className="wt-container wt-footer-bottom"><span>© {new Date().getFullYear()} WayTogether. All rights reserved.</span><span>Designed for journeys shared with care.</span></div></footer>;
}
function PublicLayout({ children }: { children: ReactNode }) { return <><PublicHeader/>{children}<PublicFooter/></>; }

function SearchForm({ compact = false }: { compact?: boolean }) {
  const navigate = useNavigate();
  const [from,setFrom] = useState(""); const [to,setTo] = useState(""); const [date,setDate] = useState(""); const [seats,setSeats] = useState("1"); const [notice,setNotice] = useState("");
  const submit = (event:FormEvent<HTMLFormElement>) => { event.preventDefault(); if(!from.trim()||!to.trim()){setNotice("Enter both your starting point and destination.");return;} navigate(`/search?from=${encodeURIComponent(from.trim())}&to=${encodeURIComponent(to.trim())}&date=${date}&seats=${seats}`); };
  return <div className={compact?"wt-search-panel compact":"wt-search-panel"}>
    {!compact&&<div className="wt-search-heading"><div><Eyebrow>YOUR NEXT JOURNEY</Eyebrow><h2>Where are you headed?</h2></div><span><ShieldCheck size={15}/> Thoughtful travel, together</span></div>}
    <form className="wt-search-form" onSubmit={submit}>
      <label className="wt-field"><span><MapPin size={14}/> From</span><input value={from} onChange={e=>setFrom(e.target.value)} placeholder="Leaving from" list="wt-cities" required/></label>
      <button type="button" className="wt-swap" aria-label="Swap locations" onClick={()=>{setFrom(to);setTo(from);}}><ArrowDownUp size={17}/></button>
      <label className="wt-field"><span><MapPin size={14}/> To</span><input value={to} onChange={e=>setTo(e.target.value)} placeholder="Going to" list="wt-cities" required/></label>
      <label className="wt-field"><span><CalendarDays size={14}/> Date</span><input type="date" value={date} onChange={e=>setDate(e.target.value)}/></label>
      <label className="wt-field wt-field-seats"><span><Users size={14}/> Seats</span><select value={seats} onChange={e=>setSeats(e.target.value)}><option value="1">1 seat</option><option value="2">2 seats</option><option value="3">3 seats</option><option value="4">4 seats</option></select></label>
      <datalist id="wt-cities">{["Chennai","Bengaluru","Coimbatore","Hyderabad","Mumbai","Pune","Kochi","Madurai","Delhi","Vijayawada","Mysuru","Salem"].map(c=><option key={c} value={c}/>)}</datalist>
      <button className="wt-btn wt-btn-primary wt-search-submit" type="submit"><Search size={16}/> Find journeys</button>
    </form>
    {notice&&<p className="wt-inline-notice" role="status">{notice}</p>}
    <p className="wt-search-disclaimer"><ShieldCheck size={14}/> Drivers share journeys they have already planned. Contributions are intended for eligible journey expenses.</p>
  </div>;
}

function HomePage() {
  return <PublicLayout><main>
    <section className="wt-hero"><div className="wt-hero-grid wt-container"><div className="wt-hero-copy"><Eyebrow><i/> A BETTER WAY TO GET THERE</Eyebrow><h1>Same direction.<br/><em>Better together.</em></h1><p>Good journeys don't have to be solo. Find people heading your way and share the road, the experience and eligible travel expenses.</p><div className="wt-hero-actions"><Link to="/search" className="wt-btn wt-btn-primary wt-btn-large">Find your journey <ArrowRight size={18}/></Link><Link to="/publish" className="wt-btn wt-btn-outline wt-btn-large">Share your journey</Link></div><div className="wt-hero-note"><div className="wt-avatar-stack"><i>AK</i><i>MR</i><i>RS</i></div><span><b>One route can bring people together.</b><small>Designed around people, not just destinations.</small></span></div></div>
      <div className="wt-hero-art"><div className="wt-art-glow"/><div className="wt-art-grid"/><svg viewBox="0 0 600 420" aria-hidden="true"><path d="M75 330 C140 295 165 115 300 130 S430 300 525 78" fill="none" stroke="rgba(54,108,255,.23)" strokeWidth="17" strokeLinecap="round"/><path d="M75 330 C140 295 165 115 300 130 S430 300 525 78" fill="none" stroke="#347B75" strokeWidth="3.5" strokeDasharray="8 10" strokeLinecap="round"/><circle cx="75" cy="330" r="16" fill="#347B75" stroke="#ead5ff" strokeWidth="3"/><circle cx="525" cy="78" r="16" fill="#B8D9D3" stroke="#d5fbff" strokeWidth="3"/></svg><div className="wt-art-car"><CarFront size={48}/></div><div className="wt-art-pill wt-art-pill-top"><Users size={16}/><span><b>One shared route</b><small>More connected journeys</small></span></div><div className="wt-art-pill wt-art-pill-bottom"><ShieldCheck size={17}/><span><b>Thoughtful by design</b><small>Trust is part of the journey</small></span></div><span className="wt-art-coord">13.0827° N · 80.2707° E</span></div></div></section>
    <section className="wt-home-search wt-container"><SearchForm/></section>
    <section className="wt-trust-row"><div className="wt-container wt-trust-grid"><div><ShieldCheck/><span><b>Safety comes first</b><small>Verification-led community</small></span></div><div><Compass/><span><b>Journeys already planned</b><small>Share the route you're taking</small></span></div><div><Users/><span><b>People going your way</b><small>Connect along a common route</small></span></div><div><Sparkles/><span><b>Thoughtful by design</b><small>Clear, transparent experience</small></span></div></div></section>
    <section className="wt-section wt-section-light" id="how-it-works"><div className="wt-container"><div className="wt-section-head"><Eyebrow>HOW WAYTOGETHER WORKS</Eyebrow><h2>One route. A few simple steps.</h2><p>Whether you have a seat to share or need a way to get there, getting started is easy.</p></div><div className="wt-steps"><article><span>01</span><div><MapPin/></div><h3>Choose your route</h3><p>Enter where you're starting, where you're headed and when you plan to travel.</p></article><article><span>02</span><div><Users/></div><h3>Find your people</h3><p>Discover independently planned journeys and connect with people travelling the same way.</p></article><article><span>03</span><div><CarFront/></div><h3>Share the journey</h3><p>Confirm the details, meet fellow travellers and share eligible journey expenses.</p></article></div></div></section>
    <section className="wt-section wt-section-dark" id="routes"><div className="wt-container"><div className="wt-section-head wt-head-row"><div><Eyebrow>EXPLORE THE POSSIBILITIES</Eyebrow><h2>Routes worth sharing.</h2><p>Explore examples of the journeys our experience is designed to support.</p></div><Link className="wt-text-link" to="/search">Explore journeys <ArrowUpRight size={16}/></Link></div><div className="wt-route-list">{[["Chennai","Bengaluru","Approx. 350 km"],["Mumbai","Pune","Approx. 150 km"],["Coimbatore","Kochi","Approx. 190 km"],["Hyderabad","Vijayawada","Approx. 275 km"]].map(([a,b,c],i)=><Link to={`/search?from=${a}&to=${b}`} className="wt-route-tile" key={a}><span>0{i+1}</span><b>{a}</b><ArrowRight size={17}/><b>{b}</b><small>{c}</small><ArrowUpRight className="wt-route-open" size={17}/></Link>)}</div><p className="wt-muted-note">Route examples only. They do not indicate live journey availability.</p></div></section>
    <section className="wt-section wt-safety" id="safety"><div className="wt-container wt-safety-grid"><div className="wt-safety-visual"><div className="wt-safety-orbit"/><div className="wt-shield-graphic"><ShieldCheck size={70}/><small>TRAVEL<br/>THOUGHTFULLY</small></div><span className="wt-safety-chip chip-one"><BadgeCheck size={15}/> Verification workflow</span><span className="wt-safety-chip chip-two"><Check size={15}/> Clear trip information</span></div><div><Eyebrow>BUILT AROUND TRUST</Eyebrow><h2>Good journeys begin with feeling comfortable.</h2><p>Trust is part of the journey, not an afterthought. WayTogether is being designed with identity and vehicle checks, clear trip information and accessible support.</p><ul><li><Check/> Driver and vehicle verification workflow</li><li><Check/> Clear journey and expense information</li><li><Check/> Reporting and support pathways</li></ul><a href="#about" className="wt-text-link" id="about">Our approach to safer sharing <ArrowUpRight size={16}/></a></div></div></section>
    <section className="wt-cta"><div className="wt-container"><div><Eyebrow>THE ROAD IS BETTER SHARED</Eyebrow><h2>Wherever you're going,<br/><em>there may be someone going too.</em></h2></div><Link to="/search" className="wt-btn wt-btn-white wt-btn-large">Explore WayTogether <ArrowRight size={18}/></Link></div></section>
  </main></PublicLayout>;
}

function SearchPage() {
  return <PublicLayout><JourneySearchContent/></PublicLayout>;
}
function JourneyDetailPage() {
  return <PublicLayout><JourneyDetailContent/></PublicLayout>;
}
function PublishPage() {
  return <PublicLayout><JourneyPublishContent/></PublicLayout>;
}
type AuthMode = "login" | "register";
type AuthRole = "passenger" | "driver" | "admin";
type RegisterResult = {
  detail: string;
  access: string;
  refresh: string;
  user: { email: string; phone: string | null; role: AuthRole; is_email_verified: boolean };
  verification: { email: string };
  email_verification_required: boolean;
  delivery_notes?: Record<string,string>;
};
type LoginResult = {
  access: string;
  refresh: string;
  user: { email: string; role: AuthRole; display_name: string; is_email_verified: boolean };
};

function AuthPage({ mode }: { mode: AuthMode }) {
  const navigate = useNavigate();
  const isRegister = mode === "register";
  const [stage, setStage] = useState<"form" | "verify">("form");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"passenger" | "driver">("passenger");
  const [pendingRole, setPendingRole] = useState<AuthRole>("passenger");
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [emailCode, setEmailCode] = useState("");
  const [emailVerified, setEmailVerified] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const register = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true); setError(""); setNotice("");
    const normalizedPhone = phone.trim();
    if (!/^\+[1-9]\d{7,14}$/.test(normalizedPhone)) {
      setError("A mobile number is required. Use international format, for example +919876543210.");
      setBusy(false);
      return;
    }
    try {
      const result = await apiRequest<RegisterResult>("/auth/register/", {
        method: "POST",
        body: JSON.stringify({
          full_name: fullName.trim(),
          email: email.trim().toLowerCase(),
          phone: normalizedPhone,
          password,
          role,
          accepted_terms: acceptedTerms,
        }),
      });
      setAuthTokens({ access: result.access, refresh: result.refresh });
      setPendingRole(result.user.role);
      setStage("verify");
      setNotice(result.delivery_notes?.email
        ? result.detail + " " + result.delivery_notes.email
        : result.detail);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  const verifyEmail = async () => {
    if (!/^\d{6}$/.test(emailCode)) { setError("Enter the six-digit email code."); return; }
    setBusy(true); setError(""); setNotice("");
    try {
      const result = await apiRequest<{ detail: string; can_sign_in: boolean }>("/auth/verification/confirm/", {
        method: "POST",
        body: JSON.stringify({ email: email.trim().toLowerCase(), code: emailCode }),
      });
      setEmailVerified(true);
      setNotice(result.detail + " Opening your dashboard…");
      if (result.can_sign_in) {
        const destination = pendingRole === "admin"
          ? "/admin"
          : pendingRole === "driver"
            ? "/dashboard/driver"
            : "/dashboard/passenger";
        navigate(destination, { replace: true });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Email verification failed. Request a new code.");
    } finally {
      setBusy(false);
    }
  };

  const resendEmailCode = async () => {
    setBusy(true); setError(""); setNotice("");
    try {
      const result = await apiRequest<{ detail: string }>("/auth/verification/request/", {
        method: "POST",
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
      });
      setNotice(result.detail);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not request a new email code.");
    } finally {
      setBusy(false);
    }
  };

  const login = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true); setError(""); setNotice("");
    try {
      const result = await apiRequest<LoginResult>("/auth/login/", {
        method: "POST",
        body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
      });
      setAuthTokens({ access: result.access, refresh: result.refresh });
      setPendingRole(result.user.role);
      if (!result.user.is_email_verified) {
        setStage("verify");
        setEmail(result.user.email);
        setNotice("You are signed in. Verify your Gmail OTP to unlock bookings and ride publishing.");
        return;
      }
      const destination = result.user.role === "admin"
        ? "/admin"
        : result.user.role === "driver"
          ? "/dashboard/driver"
          : "/dashboard/passenger";
      navigate(destination, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed. Check your details and try again.");
    } finally {
      setBusy(false);
    }
  };

  return <PublicLayout><main className="wt-auth-page"><div className="wt-auth-shell">
    <div className="wt-auth-brand"><Brand/><Eyebrow>YOUR JOURNEY, CONNECTED</Eyebrow><h1>{isRegister ? "Start with a shared direction." : "Welcome back."}</h1><p>{isRegister ? "Create your WayTogether account and discover a more connected way to travel." : "Sign in to continue your WayTogether journey."}</p><div className="wt-auth-benefit"><ShieldCheck/><span><b>Thoughtful travel starts with trust.</b><small>Designed around independently planned journeys and transparent expense sharing.</small></span></div></div>
    {stage === "verify" ? <section className="wt-panel wt-auth-card">
      <Eyebrow>EMAIL VERIFICATION</Eyebrow><h2>{isRegister ? "Your account is ready." : "You are signed in."}</h2><p>Enter the six-digit Gmail OTP sent to {email}. Your session is active; email verification unlocks booking and ride-publishing actions.</p>
      <div className="wt-verify-row"><div><b>Email verification</b><small>{emailVerified ? "Your email address is verified." : "Check your inbox for the verification code."}</small></div>{emailVerified ? <span className="wt-verified-pill"><Check size={13}/> Verified</span> : <span className="wt-pending-pill">Pending</span>}</div>
      {!emailVerified && <><label className="wt-field"><span>Email code</span><input value={emailCode} onChange={e=>setEmailCode(e.target.value.replace(/\D/g,"").slice(0,6))} inputMode="numeric" autoComplete="one-time-code" placeholder="6-digit code"/></label><div className="wt-verify-actions"><button type="button" className="wt-btn wt-btn-primary" disabled={busy} onClick={()=>void verifyEmail()}>Verify email</button><button type="button" className="wt-link-button" disabled={busy} onClick={()=>void resendEmailCode()}>Resend code</button></div></>}
      {error && <p className="wt-auth-error" role="alert">{error}</p>}{notice && <p className="wt-inline-notice" role="status">{notice}</p>}
      {emailVerified ? <button className="wt-btn wt-btn-primary wt-full" type="button" onClick={()=>navigate(pendingRole==="admin"?"/admin":pendingRole==="driver"?"/dashboard/driver":"/dashboard/passenger",{replace:true})}>Continue to dashboard <ArrowRight size={16}/></button> : <p className="wt-legal-small">Email OTP is required to unlock protected actions. Phone OTP is not used.</p>}
    </section> : <form className="wt-panel wt-auth-card" onSubmit={isRegister ? register : login}>
      <Eyebrow>{isRegister ? "CREATE YOUR ACCOUNT" : "ACCOUNT ACCESS"}</Eyebrow><h2>{isRegister ? "Create your account" : "Sign in to WayTogether"}</h2><p>{isRegister ? "A few details to get started." : "Enter your details to access your account."}</p>
      {isRegister && <label className="wt-field"><span>Full name</span><input value={fullName} onChange={e=>setFullName(e.target.value)} placeholder="Your full name" autoComplete="name" required/></label>}
      <label className="wt-field"><span>Email address</span><input value={email} onChange={e=>setEmail(e.target.value)} type="email" placeholder="you@example.com" autoComplete="email" required/></label>
      {isRegister && <><label className="wt-field"><span>Mobile number <small>(required)</small></span><input value={phone} onChange={e=>setPhone(e.target.value.replace(/[^0-9+]/g,""))} type="tel" inputMode="tel" placeholder="+919876543210" autoComplete="tel" maxLength={16} required/><small className="wt-field-hint">Required for all passengers and drivers. This registered number is shared with the other booking participant only after a confirmed booking has a successful, verified payment. No mobile OTP is currently used.</small></label><label className="wt-field"><span>Account type</span><select value={role} onChange={e=>setRole(e.target.value as "passenger"|"driver")}><option value="passenger">Passenger</option><option value="driver">Driver</option></select></label></>}
      <label className="wt-field"><span>Password</span><input value={password} onChange={e=>setPassword(e.target.value)} type="password" minLength={8} placeholder="At least 8 characters" autoComplete={isRegister ? "new-password" : "current-password"} required/></label>
      {isRegister && <label className="wt-terms-check"><input type="checkbox" checked={acceptedTerms} onChange={e=>setAcceptedTerms(e.target.checked)} required/><span>I accept the WayTogether terms and privacy policy.</span></label>}
      {error && <p className="wt-auth-error" role="alert">{error}</p>}{notice && <p className="wt-inline-notice" role="status">{notice}</p>}
      <button className="wt-btn wt-btn-primary wt-full" type="submit" disabled={busy}>{busy ? "Please wait…" : isRegister ? "Create account" : "Sign in"} <ArrowRight size={16}/></button>
      <p className="wt-auth-switch">{isRegister ? "Already have an account?" : "New to WayTogether?"} <Link to={isRegister ? "/login" : "/register"}>{isRegister ? "Log in" : "Create an account"}</Link></p>
      <small className="wt-legal-small">{isRegister ? "You will be signed in immediately. Verify your Gmail OTP to unlock protected actions." : "You can sign in before email verification. Gmail OTP is still required before bookings and ride publishing."}</small>
    </form>}
  </div></main></PublicLayout>;
}

const passengerMenu=[{label:"Overview",to:"/dashboard/passenger",icon:LayoutDashboard},{label:"Identity verification",to:"/dashboard/passenger/verification",icon:FileCheck2},{label:"My bookings",to:"/dashboard/passenger/bookings",icon:CalendarDays},{label:"Expense contributions",to:"/dashboard/passenger/finance",icon:Wallet},{label:"Messages",to:"/dashboard/passenger/messages",icon:MessageCircle},{label:"Notifications",to:"/dashboard/passenger/notifications",icon:Bell},{label:"Safety centre",to:"/dashboard/passenger/safety",icon:ShieldCheck},{label:"Reviews",to:"/dashboard/passenger/reviews",icon:Star},{label:"Saved journeys",to:"/dashboard/passenger",icon:Compass},{label:"Profile",to:"/dashboard/passenger",icon:Settings}];
function DashboardLayout({role,children}:{role:"Passenger"|"Driver"|"Admin";children:ReactNode}) {
  const [open,setOpen]=useState(false);
  const [authorised,setAuthorised]=useState(false);
  const navigate=useNavigate();
  useEffect(()=>{
    let active=true;
    const rolePaths={passenger:"/dashboard/passenger",driver:"/dashboard/driver",admin:"/admin"};
    const expectedRole=role==="Passenger"?"passenger":role==="Driver"?"driver":"admin";
    getCurrentUser().then(user=>{
      if(!active)return;
      if(user.role!==expectedRole){navigate(rolePaths[user.role],{replace:true});return;}
      setAuthorised(true);
    }).catch(()=>{if(active)navigate("/login",{replace:true});});
    return()=>{active=false;};
  },[role,navigate]);
  const signOut=async()=>{await logoutCurrentSession();navigate("/login",{replace:true});};
  const links=role==="Driver"?[{label:"Overview",to:"/dashboard/driver",icon:LayoutDashboard},{label:"My journeys",to:"/dashboard/driver/journeys",icon:CarFront},{label:"Booking requests",to:"/dashboard/driver/bookings",icon:Users},{label:"Expense records",to:"/dashboard/driver/finance",icon:Wallet},{label:"Messages",to:"/dashboard/driver/messages",icon:MessageCircle},{label:"Notifications",to:"/dashboard/driver/notifications",icon:Bell},{label:"Safety centre",to:"/dashboard/driver/safety",icon:ShieldCheck},{label:"Reviews",to:"/dashboard/driver/reviews",icon:Star},{label:"Vehicle & documents",to:"/driver/verification",icon:FileCheck2},{label:"Profile",to:"/dashboard/driver",icon:Settings}]:role==="Admin"?[{label:"Overview",to:"/admin",icon:LayoutDashboard},{label:"Users",to:"/admin/users",icon:Users},{label:"Driver documents",to:"/admin/verification",icon:FileCheck2},{label:"Passenger identity",to:"/admin/passenger-verification",icon:ShieldCheck},{label:"Journeys",to:"/admin/journeys",icon:CarFront},{label:"Bookings",to:"/admin/bookings",icon:CalendarDays},{label:"Expense ledger",to:"/admin/finance",icon:Wallet},{label:"Safety reports",to:"/admin/safety",icon:ShieldCheck},{label:"Database cleanup",to:"/admin/database-cleanup",icon:ShieldCheck}]:passengerMenu;
  if(!authorised)return <main className="wt-auth-wait" role="status">Checking your account access…</main>;
  return <div className="wt-dashboard"><aside className={open?"wt-sidebar is-open":"wt-sidebar"}><div className="wt-sidebar-brand"><Brand/><button onClick={()=>setOpen(false)} aria-label="Close menu"><X/></button></div><div className="wt-side-label">{role} workspace</div><nav>{links.map(item=>{const Icon=item.icon;return <NavLink key={item.label} to={item.to} end className={({isActive})=>isActive?"active":""} onClick={()=>setOpen(false)}><Icon size={17}/>{item.label}</NavLink>;})}</nav><div className="wt-sidebar-bottom"><Link to="/"><Compass size={16}/> View public website</Link><button type="button" onClick={()=>void signOut()}><LogOut size={16}/> Sign out</button></div></aside><div className="wt-dashboard-main"><header className="wt-dashboard-top"><button className="wt-dash-menu" onClick={()=>setOpen(true)} aria-label="Open dashboard menu"><Menu/></button><div className="wt-dash-top-title"><span>WayTogether / {role}</span><b>{role} dashboard</b></div><div className="wt-dash-top-actions"><button aria-label="Help"><CircleHelp/></button><Link to={role==="Driver"?"/dashboard/driver/notifications":role==="Passenger"?"/dashboard/passenger/notifications":"/admin"} aria-label="Notifications"><Bell/></Link><span className="wt-small-user">{role==="Driver"?"AK":role==="Admin"?"AD":"MR"}</span></div></header><main className="wt-dashboard-content">{children}</main></div></div>;
}

type DriverProfileRecord = {
  uploads_enabled: boolean;
  driver_photo_url: string | null;
  verification_status: string;
  verification_status_display: string;
  city: string;
  state: string;
  bio: string;
  contact_phone: string | null;
  submitted_at: string | null;
};
type VehicleRecord = {
  id: number; registration_number: string; make: string; model: string;
  manufacture_year: number; vehicle_type: string; passenger_seats: number;
  private_use_attested: boolean; verification_status: string; verification_status_display: string;
};
type DriverDocumentRecord = {
  id: number; document_type: string; vehicle: number | null; vehicle_registration: string | null;
  owner_name?: string; owner_email?: string;
  original_file_name: string; content_type: string; file_size: number; expiry_date: string | null;
  review_status: string; review_status_display: string; review_note: string;
  is_current: boolean; uploaded_at: string; download_url: string;
};
const documentLabels: Record<string,string> = {
  driver_license: "Driving licence",
  vehicle_registration: "Vehicle registration certificate",
  insurance: "Insurance certificate",
  pollution_certificate: "Pollution certificate",
  vehicle_photo: "Vehicle photograph",
  driver_photo: "Driver face photo",
};
function StatusPill({status}:{status:string}) {
  const tone = status === "approved" ? "approved" : status === "rejected" || status === "needs_resubmission" ? "rejected" : "pending";
  return <span className={"wt-review-pill " + tone}>{status.replaceAll("_"," ")}</span>;
}


type PassengerKycStatus = {
  status: string;
  uploads_enabled: boolean;
  review_note?: string;
  submitted_at?: string | null;
  reviewed_at?: string | null;
};

type AdminPassengerKycRecord = {
  id: number;
  owner_email: string;
  owner_name: string;
  masked_aadhaar_file_name: string;
  passenger_photo_file_name: string;
  consent_at: string;
  status: string;
  review_note: string;
  submitted_at: string;
};

function PassengerVerificationPage() {
  const navigate = useNavigate();
  const [verification,setVerification] = useState<PassengerKycStatus>({status:"not_submitted",uploads_enabled:false});
  const [aadhaarFile,setAadhaarFile] = useState<File|null>(null);
  const [photoFile,setPhotoFile] = useState<File|null>(null);
  const [consent,setConsent] = useState(false);
  const [phone,setPhone] = useState("");
  const [phoneSaved,setPhoneSaved] = useState(false);
  const [loading,setLoading] = useState(true);
  const [busy,setBusy] = useState(false);
  const [phoneBusy,setPhoneBusy] = useState(false);
  const [error,setError] = useState("");
  const [notice,setNotice] = useState("");

  const load = async () => {
    setLoading(true); setError("");
    if (!hasAuthSession()) {
      navigate("/login", { replace: true });
      setLoading(false);
      return;
    }
    try {
      const [statusData,userData] = await Promise.all([
        apiRequest<PassengerKycStatus>("/auth/passenger-verification/",{},true),
        apiRequest<{phone:string|null}>("/auth/me/",{},true),
      ]);
      setVerification(statusData);
      setPhone(userData.phone ?? "");
      setPhoneSaved(Boolean(userData.phone));
    } catch(err) {
      const message=err instanceof Error?err.message:"Could not load passenger identity status.";
      setError(message);
      if(message.toLowerCase().includes("session has expired")) navigate("/login",{replace:true});
    } finally { setLoading(false); }
  };
  useEffect(()=>{void load();},[]);

  const savePhone = async (event:FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalized=phone.trim();
    if(!/^\+[1-9]\d{7,14}$/.test(normalized)) {
      setError("Enter your mobile number in international format, such as +919876543210.");
      return;
    }
    setPhoneBusy(true); setError(""); setNotice("");
    try {
      const result=await apiRequest<{phone:string|null}>("/auth/me/",{
        method:"PATCH",body:JSON.stringify({phone:normalized}),
      },true);
      setPhone(result.phone ?? "");
      setPhoneSaved(Boolean(result.phone));
      setNotice("Registered mobile number saved.");
    } catch(err) { setError(err instanceof Error?err.message:"Could not save your mobile number."); }
    finally { setPhoneBusy(false); }
  };

  const submit = async (event:FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if(!hasAuthSession()) {
      navigate("/login",{replace:true});
      return;
    }
    if(!phoneSaved) {
      setError("Save your registered mobile number before submitting identity verification.");
      return;
    }
    if(!aadhaarFile||!photoFile||!consent) {
      setError("Choose both documents and accept the identity-verification consent.");
      return;
    }
    if(!verification.uploads_enabled) {
      setError("Private persistent document storage is not configured yet. Your documents have not been submitted.");
      return;
    }
    setBusy(true); setError(""); setNotice("");
    try {
      const body = new FormData();
      body.append("masked_aadhaar_document",aadhaarFile);
      body.append("passenger_photo",photoFile);
      body.append("consent","true");
      const result = await apiRequest<{detail:string;verification:PassengerKycStatus}>(
        "/auth/passenger-verification/",
        {method:"POST",body},
        true,
      );
      setVerification(result.verification);
      setNotice(result.detail);
      setAadhaarFile(null); setPhotoFile(null); setConsent(false);
      const a = document.getElementById("wt-passenger-aadhaar") as HTMLInputElement|null;
      const p = document.getElementById("wt-passenger-photo") as HTMLInputElement|null;
      if(a)a.value=""; if(p)p.value="";
    } catch(err) {
      const message=err instanceof Error?err.message:"Could not submit verification.";
      setError(message);
      if(message.toLowerCase().includes("session has expired")) navigate("/login",{replace:true});
    } finally { setBusy(false); }
  };

  return <DashboardLayout role="Passenger">
    <div className="wt-dash-heading"><div><Eyebrow>PASSENGER IDENTITY</Eyebrow><h1>Verify your passenger profile.</h1><p>Submit your identity proof and a clear profile photo for manual review.</p></div><StatusPill status={verification.status}/></div>
    <div className="wt-verification-intro"><ShieldCheck/><div><b>Private manual verification</b><small>Files are private and available only to you and authorised administrators. Do not upload a full unmasked Aadhaar number or biometric data.</small></div><StatusPill status={verification.status}/></div>
    {notice&&<p className="wt-inline-notice" role="status">{notice}</p>}
    <section className="wt-panel wt-verification-card">
      <div className="wt-panel-heading"><div><h2>Registered mobile number</h2><p>Required for all passenger accounts and shared only with the other participant after successful payment.</p></div>{phoneSaved?<StatusPill status="approved"/>:<StatusPill status="pending"/>}</div>
      <form className="wt-profile-fields" onSubmit={savePhone}>
        <label className="wt-field wt-span-2"><span>Mobile number</span><input value={phone} onChange={e=>{setPhone(e.target.value.replace(/[^0-9+]/g,""));setPhoneSaved(false);}} type="tel" inputMode="tel" maxLength={16} placeholder="+919876543210" required/><small>Use international format. No phone OTP is currently used.</small></label>
        <button className="wt-btn wt-btn-outline" type="submit" disabled={phoneBusy||!/^\+[1-9]\d{7,14}$/.test(phone.trim())}>{phoneBusy?"Saving…":phoneSaved?"Update mobile number":"Save mobile number"}</button>
      </form>
    </section>
    {!loading&&!verification.uploads_enabled&&<div className="wt-market-notice info" role="status"><b>Identity uploads are temporarily unavailable.</b> WayTogether must finish configuring private persistent document storage before accepting identity files. Your selected documents have not been submitted or saved. Please do not retry until this notice disappears.</div>}
    {loading?<div className="wt-panel wt-verification-loading">Loading your verification status…</div>:<>
      {verification.review_note&&<div className="wt-market-notice info">Administrator note: {verification.review_note}</div>}
      <section className="wt-panel wt-verification-card">
        <div className="wt-panel-heading"><div><h2>Identity documents</h2><p>Submit a masked Aadhaar copy and a recent face photo.</p></div><StatusPill status={verification.status}/></div>
        <form className="wt-document-form" onSubmit={submit}>
          <label className="wt-field wt-file-field"><span>Masked Aadhaar proof (PDF, JPG or PNG)</span><input id="wt-passenger-aadhaar" type="file" accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png" onChange={e=>setAadhaarFile(e.target.files?.[0]??null)} required/><small>{aadhaarFile?.name??"Upload a copy with the first eight Aadhaar digits hidden"}</small></label>
          <label className="wt-field wt-file-field"><span>Passenger photo (JPG or PNG)</span><input id="wt-passenger-photo" type="file" accept=".jpg,.jpeg,.png,image/jpeg,image/png" onChange={e=>setPhotoFile(e.target.files?.[0]??null)} required/><small>{photoFile?.name??"Upload a recent, clear face photo"}</small></label>
          <label className="wt-private-attest"><input type="checkbox" checked={consent} onChange={e=>setConsent(e.target.checked)}/><span>I consent to WayTogether using these documents for passenger identity verification, restricting access to authorised reviewers, and retaining them only as required for this verification purpose.</span></label>
          <button className="wt-btn wt-btn-primary" disabled={busy||!consent||!verification.uploads_enabled||!phoneSaved}>{busy?"Submitting…":"Submit for manual verification"} <ArrowRight size={15}/></button>
        </form>
        <p className="wt-legal-small">Only upload a masked Aadhaar document with the first eight digits redacted. Never enter a 12-digit Aadhaar number into the app. You can resubmit if a reviewer rejects the documents.</p>
      </section>
    </>}
  </DashboardLayout>;
}

function AdminPassengerVerificationPage() {
  const [queue,setQueue] = useState<AdminPassengerKycRecord[]>([]);
  const [loading,setLoading] = useState(true);
  const [busyId,setBusyId] = useState<number|null>(null);
  const [notes,setNotes] = useState<Record<number,string>>({});
  const [error,setError] = useState("");
  const [notice,setNotice] = useState("");

  const load = async () => {
    setLoading(true); setError("");
    try {
      setQueue(await apiRequest<AdminPassengerKycRecord[]>("/auth/admin/passenger-verification/queue/",{},true));
    } catch(err) { setError(err instanceof Error?err.message:"Administrator access is required."); }
    finally { setLoading(false); }
  };
  useEffect(()=>{void load();},[]);

  const review = async (item:AdminPassengerKycRecord,decision:"approved"|"rejected") => {
    const reviewNote=notes[item.id]??"";
    if(decision==="rejected"&&!reviewNote.trim()){setError("Add a rejection reason before rejecting a passenger.");return;}
    setBusyId(item.id);setError("");setNotice("");
    try {
      const result=await apiRequest<{detail:string}>("/auth/admin/passenger-verification/"+item.id+"/review/",{
        method:"POST",body:JSON.stringify({decision,review_note:reviewNote}),
      },true);
      setNotice(result.detail);await load();
    } catch(err) {setError(err instanceof Error?err.message:"Could not review this passenger.");}
    finally {setBusyId(null);}
  };

  return <DashboardLayout role="Admin">
    <div className="wt-dash-heading"><div><Eyebrow>ADMINISTRATOR · PASSENGER IDENTITY</Eyebrow><h1>Passenger verification queue.</h1><p>Review masked Aadhaar proof and profile photos before allowing seat bookings.</p></div><span className="wt-staff-label">STAFF ONLY · PRIVATE KYC</span></div>
    {error&&<p className="wt-auth-error" role="alert">{error}</p>}{notice&&<p className="wt-inline-notice" role="status">{notice}</p>}
    <div className="wt-verification-intro"><ShieldCheck/><div><b>Restricted personal data</b><small>Open these files only for the review. Do not copy or share Aadhaar data outside the verification purpose.</small></div><span className="wt-queue-count">{queue.length} pending</span></div>
    <section className="wt-panel wt-admin-queue">
      <div className="wt-panel-heading"><div><h2>Pending passengers</h2><p>Approve only after checking the masked document and matching photo.</p></div><button className="wt-btn wt-btn-outline" type="button" onClick={load}>Refresh</button></div>
      {loading?<p className="wt-queue-empty">Loading passenger queue…</p>:queue.length===0?<div className="wt-queue-empty"><Check/><b>No pending passengers</b><small>New submissions will appear here.</small></div>:queue.map(item=><article className="wt-admin-document" key={item.id}>
        <div className="wt-admin-document-head"><span className="wt-doc-icon"><FileCheck2/></span><div><b>{item.owner_name}</b><small>{item.owner_email}</small></div><StatusPill status={item.status}/></div>
        <div className="wt-admin-document-meta"><span>Aadhaar file: <b>{item.masked_aadhaar_file_name}</b></span><span>Photo: <b>{item.passenger_photo_file_name}</b></span><span>Consent: <b>{new Date(item.consent_at).toLocaleString("en-IN")}</b></span></div>
        <div className="wt-admin-review-actions">
          <button className="wt-link-button" type="button" onClick={async()=>{try{await downloadPrivateFile("/auth/passenger-verification/"+item.id+"/download/aadhaar/",item.masked_aadhaar_file_name);}catch(err){setError(err instanceof Error?err.message:"Private download failed.");}}}>Download masked Aadhaar</button>
          <button className="wt-link-button" type="button" onClick={async()=>{try{await downloadPrivateFile("/auth/passenger-verification/"+item.id+"/download/photo/",item.passenger_photo_file_name);}catch(err){setError(err instanceof Error?err.message:"Private download failed.");}}}>Download photo</button>
          <input value={notes[item.id]??""} onChange={e=>setNotes(n=>({...n,[item.id]:e.target.value}))} placeholder="Rejection reason (required to reject)"/>
          <button className="wt-btn wt-btn-outline" disabled={busyId===item.id} onClick={()=>review(item,"rejected")}>Reject</button>
          <button className="wt-btn wt-btn-primary" disabled={busyId===item.id} onClick={()=>review(item,"approved")}>Approve <Check size={14}/></button>
        </div>
      </article>)}
    </section>
  </DashboardLayout>;
}

function DriverVerificationPage() {
  const navigate = useNavigate();
  const [profile,setProfile] = useState<DriverProfileRecord | null>(null);
  const [vehicles,setVehicles] = useState<VehicleRecord[]>([]);
  const [documents,setDocuments] = useState<DriverDocumentRecord[]>([]);
  const [loading,setLoading] = useState(true);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState("");
  const [notice,setNotice] = useState("");
  const [selectedVehicle,setSelectedVehicle] = useState("");
  const [documentType,setDocumentType] = useState("driver_license");
  const [file,setFile] = useState<File | null>(null);
  const [expiryDate,setExpiryDate] = useState("");
  const [vehicleForm,setVehicleForm] = useState({
    registration_number:"",make:"",model:"",manufacture_year:String(new Date().getFullYear()-2),
    colour:"",vehicle_type:"sedan",passenger_seats:"3",private_use_attested:false,
  });

  const load = async () => {
    setLoading(true); setError("");
    if (!hasAuthSession()) {
      navigate("/login", { replace: true });
      setLoading(false);
      return;
    }
    try {
      const [profileData,vehicleData,documentData] = await Promise.all([
        apiRequest<DriverProfileRecord>("/drivers/profile/",{},true),
        apiRequest<VehicleRecord[]>("/drivers/vehicles/",{},true),
        apiRequest<DriverDocumentRecord[]>("/drivers/documents/",{},true),
      ]);
      setProfile(profileData); setVehicles(vehicleData); setDocuments(documentData);
      if (!selectedVehicle && vehicleData.length) setSelectedVehicle(String(vehicleData[0].id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in with a verified driver account to manage verification.");
    } finally { setLoading(false); }
  };
  useEffect(()=>{ void load(); },[]);

  const createVehicle = async (event:FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setBusy(true); setError(""); setNotice("");
    try {
      const result = await apiRequest<VehicleRecord>("/drivers/vehicles/",{
        method:"POST",
        body:JSON.stringify({
          ...vehicleForm,
          manufacture_year:Number(vehicleForm.manufacture_year),
          passenger_seats:Number(vehicleForm.passenger_seats),
        }),
      },true);
      setNotice("Vehicle " + result.registration_number + " added. Upload its documents to continue.");
      setVehicleForm({registration_number:"",make:"",model:"",manufacture_year:String(new Date().getFullYear()-2),colour:"",vehicle_type:"sedan",passenger_seats:"3",private_use_attested:false});
      setSelectedVehicle(String(result.id));
      await load();
    } catch(err) { setError(err instanceof Error ? err.message : "Vehicle could not be saved."); }
    finally { setBusy(false); }
  };

  const uploadDocument = async (event:FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!profile?.uploads_enabled) { setError("Private persistent file storage is not configured. Driver documents have not been uploaded."); return; }
    if (!file) { setError("Choose a PDF, JPG or PNG document."); return; }
    const needsVehicle = !["driver_license","driver_photo"].includes(documentType);
    if (needsVehicle && !selectedVehicle) { setError("Add and select a vehicle first."); return; }
    setBusy(true); setError(""); setNotice("");
    try {
      const body = new FormData();
      body.append("document_type",documentType);
      body.append("file",file);
      if (needsVehicle) body.append("vehicle",selectedVehicle);
      if (expiryDate) body.append("expiry_date",expiryDate);
      const result = await apiRequest<DriverDocumentRecord>("/drivers/documents/",{method:"POST",body},true);
      setNotice((documentLabels[result.document_type] ?? "Document") + " uploaded. Its review status is pending.");
      setFile(null); setExpiryDate("");
      const input = document.getElementById("wt-driver-document-file") as HTMLInputElement | null;
      if (input) input.value = "";
      await load();
    } catch(err) { setError(err instanceof Error ? err.message : "Document upload failed."); }
    finally { setBusy(false); }
  };

  const submitVehicle = async (vehicleId:number) => {
    setBusy(true); setError(""); setNotice("");
    try {
      const result = await apiRequest<{detail:string;driver_status:string;vehicle_status:string;missing_documents?:string[]}>(
        "/drivers/verification/submit/",
        {method:"POST",body:JSON.stringify({vehicle_id:vehicleId})},
        true,
      );
      setNotice(result.detail);
      await load();
    } catch(err) { setError(err instanceof Error ? err.message : "Could not submit for review."); await load(); }
    finally { setBusy(false); }
  };

  const currentDocs = documents.filter(doc=>doc.is_current);
  const licenseUploaded = currentDocs.some(doc=>doc.document_type==="driver_license");
  const driverPhotoUploaded = currentDocs.some(doc=>doc.document_type==="driver_photo");
  return <DashboardLayout role="Driver"><div className="wt-dash-heading"><div><Eyebrow>DRIVER VERIFICATION</Eyebrow><h1>Verify your driver profile.</h1><p>Add your vehicle and submit the required documents for administrator review.</p></div><PreviewLabel/></div>
    <div className="wt-verification-intro"><ShieldCheck/><div><b>Private document handling</b><small>Your uploaded documents are stored privately. Only your account and authorised platform administrators can access them through the protected document endpoint.</small></div><StatusPill status={profile?.verification_status ?? "draft"}/></div>
    {error&&<p className="wt-auth-error" role="alert">{error}</p>}{notice&&<p className="wt-inline-notice" role="status">{notice}</p>}
    {!loading&&!profile?.uploads_enabled&&<div className="wt-market-notice info" role="status"><b>Driver document uploads are temporarily unavailable.</b> Private persistent file storage must be configured before WayTogether can accept your driving licence, driver photo, RC or vehicle documents. Nothing has been submitted yet.</div>}
    {loading ? <div className="wt-panel wt-verification-loading">Loading your verification details…</div> : <>
      <section className="wt-panel wt-verification-card">
        <div className="wt-panel-heading"><div><h2>Driver profile</h2><p>Basic information used for driver verification.</p></div><StatusPill status={profile?.verification_status ?? "draft"}/></div>
        <form className="wt-profile-fields" onSubmit={async e=>{e.preventDefault();setBusy(true);setError("");try{const fd=new FormData(e.currentTarget);const body=new FormData();body.append("city",String(fd.get("city")??""));body.append("state",String(fd.get("state")??""));body.append("bio",String(fd.get("bio")??""));body.append("contact_phone",String(fd.get("contact_phone")??""));const photo=fd.get("profile_photo");if(photo instanceof File&&photo.size>0)body.append("profile_photo",photo);const data=await apiRequest<DriverProfileRecord>("/drivers/profile/",{method:"PATCH",body},true);setProfile(data);setNotice("Driver profile saved.");const input=document.getElementById("wt-driver-profile-photo") as HTMLInputElement|null;if(input)input.value="";}catch(err){setError(err instanceof Error?err.message:"Could not save profile.");}finally{setBusy(false);}}}>
          <label className="wt-field"><span>City</span><input name="city" defaultValue={profile?.city ?? ""} placeholder="Your city"/></label>
          <label className="wt-field"><span>State</span><input name="state" defaultValue={profile?.state ?? ""} placeholder="Your state"/></label>
          <label className="wt-field wt-span-2"><span>Contact phone number</span><input name="contact_phone" type="tel" inputMode="tel" defaultValue={profile?.contact_phone ?? ""} placeholder="+919876543210" required/><small>Shown to a passenger only after a confirmed booking and successful payment. No OTP or phone verification is used.</small></label>
          <label className="wt-field wt-span-2"><span>Short driver introduction</span><input name="bio" defaultValue={profile?.bio ?? ""} maxLength={500} placeholder="A brief introduction for fellow travellers"/></label>
          <div className="wt-field wt-span-2"><span>Driver profile photo</span>{profile?.driver_photo_url?<img className="wt-driver-photo-preview" src={profile.driver_photo_url} alt="Your administrator-approved driver photo"/>:<small>Upload a driver face photo in the verification documents section. It will appear on published rides only after administrator approval.</small>}</div>
          <button className="wt-btn wt-btn-outline" disabled={busy}>Save profile</button>
        </form>
      </section>

      <section className="wt-panel wt-verification-card">
        <div className="wt-panel-heading"><div><h2>Your vehicles</h2><p>Register a privately used vehicle. It must not be offered as a commercial taxi through this platform.</p></div></div>
        {vehicles.length>0&&<div className="wt-vehicle-list">{vehicles.map(vehicle=><article className="wt-vehicle-row" key={vehicle.id}><span className="wt-vehicle-icon"><CarFront/></span><div><b>{vehicle.registration_number} · {vehicle.make} {vehicle.model}</b><small>{vehicle.manufacture_year} · {vehicle.vehicle_type.toUpperCase()} · {vehicle.passenger_seats} passenger seats</small></div><StatusPill status={vehicle.verification_status}/><button className="wt-link-button" type="button" onClick={()=>setSelectedVehicle(String(vehicle.id))}>Select</button></article>)}</div>}
        <form className="wt-form-grid wt-vehicle-form" onSubmit={createVehicle}>
          <label className="wt-field"><span>Registration number</span><input value={vehicleForm.registration_number} onChange={e=>setVehicleForm(v=>({...v,registration_number:e.target.value}))} placeholder="TN01AB1234" required/></label>
          <label className="wt-field"><span>Make</span><input value={vehicleForm.make} onChange={e=>setVehicleForm(v=>({...v,make:e.target.value}))} placeholder="Honda" required/></label>
          <label className="wt-field"><span>Model</span><input value={vehicleForm.model} onChange={e=>setVehicleForm(v=>({...v,model:e.target.value}))} placeholder="City" required/></label>
          <label className="wt-field"><span>Manufacture year</span><input type="number" min="1980" max="2100" value={vehicleForm.manufacture_year} onChange={e=>setVehicleForm(v=>({...v,manufacture_year:e.target.value}))} required/></label>
          <label className="wt-field"><span>Vehicle type</span><select value={vehicleForm.vehicle_type} onChange={e=>setVehicleForm(v=>({...v,vehicle_type:e.target.value}))}><option value="hatchback">Hatchback</option><option value="sedan">Sedan</option><option value="suv">SUV</option><option value="muv">MUV</option><option value="other">Other</option></select></label>
          <label className="wt-field"><span>Passenger seats available</span><select value={vehicleForm.passenger_seats} onChange={e=>setVehicleForm(v=>({...v,passenger_seats:e.target.value}))}>{[1,2,3,4,5,6,7,8].map(n=><option key={n} value={n}>{n}</option>)}</select></label>
          <label className="wt-field"><span>Colour (optional)</span><input value={vehicleForm.colour} onChange={e=>setVehicleForm(v=>({...v,colour:e.target.value}))} placeholder="Blue"/></label>
          <label className="wt-private-attest"><input type="checkbox" checked={vehicleForm.private_use_attested} onChange={e=>setVehicleForm(v=>({...v,private_use_attested:e.target.checked}))}/><span>I confirm this is a privately used vehicle and I am not registering it as a commercial taxi.</span></label>
          <button className="wt-btn wt-btn-primary" disabled={busy}>Add vehicle <Plus size={15}/></button>
        </form>
      </section>

      <section className="wt-panel wt-verification-card">
        <div className="wt-panel-heading"><div><h2>Upload verification documents</h2><p>Accepted file formats: PDF, JPG or PNG. Maximum file size: 8 MB per document.</p></div></div>
        <form className="wt-document-form" onSubmit={uploadDocument}>
          <label className="wt-field"><span>Document type</span><select value={documentType} onChange={e=>setDocumentType(e.target.value)}>{Object.entries(documentLabels).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label>
          {!["driver_license","driver_photo"].includes(documentType)&&<label className="wt-field"><span>Vehicle</span><select value={selectedVehicle} onChange={e=>setSelectedVehicle(e.target.value)} required><option value="">Select a vehicle</option>{vehicles.map(v=><option key={v.id} value={v.id}>{v.registration_number} · {v.make} {v.model}</option>)}</select></label>}
          <label className="wt-field"><span>Expiry date (where applicable)</span><input type="date" min={new Date().toISOString().slice(0,10)} value={expiryDate} onChange={e=>setExpiryDate(e.target.value)}/></label>
          <label className="wt-field wt-file-field"><span>Select document file</span><input id="wt-driver-document-file" type="file" accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png" onChange={e=>setFile(e.target.files?.[0]??null)} required/><small>{file ? file.name : "Choose a file from your device"}</small></label>
          <button className="wt-btn wt-btn-primary" disabled={busy||!profile?.uploads_enabled||(!vehicles.length&&!["driver_license","driver_photo"].includes(documentType))}>Upload document <ArrowUpRight size={15}/></button>
        </form>
        <div className="wt-required-docs"><b>Required before submitting a vehicle</b><div className="wt-required-grid">
          {[["Driving licence",licenseUploaded],["Driver face photo",driverPhotoUploaded],["Vehicle registration",currentDocs.some(d=>d.document_type==="vehicle_registration"&&String(d.vehicle)===selectedVehicle)],["Insurance certificate",currentDocs.some(d=>d.document_type==="insurance"&&String(d.vehicle)===selectedVehicle)],["Vehicle photograph",currentDocs.some(d=>d.document_type==="vehicle_photo"&&String(d.vehicle)===selectedVehicle)]].map(([label,done])=><span key={String(label)} className={done?"is-uploaded":""}>{done?<Check size={13}/>:<FileCheck2 size={13}/>} {label}</span>)}
        </div><small>Pollution certificate can also be uploaded where applicable. Document completeness is checked before submission; approval requires administrator review.</small></div>
        {currentDocs.length>0&&<div className="wt-document-list"><b>Uploaded documents</b>{currentDocs.map(doc=><div className="wt-document-row" key={doc.id}><FileCheck2 size={17}/><span><b>{documentLabels[doc.document_type]??doc.document_type}</b><small>{doc.original_file_name} · {doc.vehicle_registration??"Driver document"}{doc.review_note ? " · " + doc.review_note : ""}</small></span><StatusPill status={doc.review_status}/><button className="wt-link-button" type="button" onClick={async()=>{try{await downloadPrivateFile("/drivers/documents/"+doc.id+"/download/",doc.original_file_name);}catch(err){setError(err instanceof Error?err.message:"Download failed.");}}}>Download</button></div>)}</div>}
      </section>

      <section className="wt-panel wt-submit-verification">
        <div><h3>Submit a vehicle for verification</h3><p>Upload your driving licence and face photo, then submit each vehicle with its RC, insurance and vehicle photo.</p></div>
        {vehicles.length===0?<span className="wt-muted">Add a vehicle first.</span>:vehicles.map(vehicle=><div className="wt-submit-row" key={vehicle.id}><span><b>{vehicle.registration_number}</b><small>{vehicle.make} {vehicle.model}</small></span><StatusPill status={vehicle.verification_status}/><button className="wt-btn wt-btn-primary" type="button" disabled={busy||!profile?.uploads_enabled||vehicle.verification_status==="approved"} onClick={()=>submitVehicle(vehicle.id)}>Submit for review <ArrowRight size={15}/></button></div>)}
      </section>
    </>}
  </DashboardLayout>;
}

function AdminVerificationPage() {
  const [queue,setQueue] = useState<DriverDocumentRecord[]>([]);
  const [loading,setLoading] = useState(true);
  const [busyId,setBusyId] = useState<number|null>(null);
  const [notes,setNotes] = useState<Record<number,string>>({});
  const [error,setError] = useState("");
  const [notice,setNotice] = useState("");
  const load = async () => {
    setLoading(true); setError("");
    try { setQueue(await apiRequest<DriverDocumentRecord[]>("/drivers/admin/verification/queue/",{},true)); }
    catch(err) { setError(err instanceof Error?err.message:"Administrator access is required to view this queue."); }
    finally { setLoading(false); }
  };
  useEffect(()=>{void load();},[]);
  const review = async (doc:DriverDocumentRecord,decision:"approved"|"rejected") => {
    const reviewNote = notes[doc.id]??"";
    if(decision==="rejected"&&!reviewNote.trim()){setError("Add a rejection reason before rejecting a document.");return;}
    setBusyId(doc.id);setError("");setNotice("");
    try {
      const result = await apiRequest<{detail:string}>("/drivers/admin/verification/documents/"+doc.id+"/review/",{
        method:"POST",body:JSON.stringify({decision,review_note:reviewNote}),
      },true);
      setNotice(result.detail);await load();
    } catch(err) { setError(err instanceof Error?err.message:"Could not review this document."); }
    finally { setBusyId(null); }
  };
  return <DashboardLayout role="Admin"><div className="wt-dash-heading"><div><Eyebrow>ADMINISTRATOR · VERIFICATION</Eyebrow><h1>Driver document review.</h1><p>Review private driver and vehicle documents submitted by the community.</p></div><span className="wt-staff-label">STAFF ONLY · PRIVATE DOCUMENT REVIEW</span></div>
    {error&&<p className="wt-auth-error" role="alert">{error}</p>}{notice&&<p className="wt-inline-notice" role="status">{notice}</p>}
    <div className="wt-verification-intro"><ShieldCheck/><div><b>Restricted document access</b><small>Only staff accounts can view the review queue and download submitted files. Each review decision is recorded with the reviewer and timestamp.</small></div><span className="wt-queue-count">{queue.length} pending</span></div>
    <section className="wt-panel wt-admin-queue"><div className="wt-panel-heading"><div><h2>Pending documents</h2><p>Approve only after checking the document and its validity.</p></div><button className="wt-btn wt-btn-outline" type="button" onClick={load}>Refresh</button></div>
      {loading?<p className="wt-queue-empty">Loading verification queue…</p>:queue.length===0?<div className="wt-queue-empty"><Check/><b>No pending documents</b><small>New driver submissions will appear here.</small></div>:queue.map(doc=><article className="wt-admin-document" key={doc.id}><div className="wt-admin-document-head"><span className="wt-doc-icon"><FileCheck2/></span><div><b>{documentLabels[doc.document_type]??doc.document_type}</b><small>{doc.owner_name} · {doc.owner_email}</small></div><StatusPill status={doc.review_status}/></div><div className="wt-admin-document-meta"><span>Vehicle: <b>{doc.vehicle_registration??"Driver licence"}</b></span><span>File: <b>{doc.original_file_name}</b></span><span>Uploaded: <b>{new Date(doc.uploaded_at).toLocaleDateString("en-IN")}</b></span><span>Expiry: <b>{doc.expiry_date??"Not supplied"}</b></span></div><div className="wt-admin-review-actions"><button className="wt-link-button" type="button" onClick={async()=>{try{await downloadPrivateFile("/drivers/documents/"+doc.id+"/download/",doc.original_file_name);}catch(err){setError(err instanceof Error?err.message:"Download failed.");}}}>Download private file</button><input value={notes[doc.id]??""} onChange={e=>setNotes(n=>({...n,[doc.id]:e.target.value}))} placeholder="Rejection reason (required to reject)"/><button className="wt-btn wt-btn-outline" disabled={busyId===doc.id} onClick={()=>review(doc,"rejected")}>Reject</button><button className="wt-btn wt-btn-primary" disabled={busyId===doc.id} onClick={()=>review(doc,"approved")}>Approve <Check size={14}/></button></div></article>)}
    </section>
  </DashboardLayout>;
}

function Metric({label,value,detail,icon:Icon}:{label:string;value:string;detail:string;icon:typeof Users}) {
  return <div className="wt-metric"><span><Icon size={18}/></span><small>{label}</small><b>{value}</b><em>{detail}</em></div>;
}
function PassengerDashboard() {
  const [journeys, setJourneys] = useState<JourneyRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getUpcomingJourneys()
      .then(records => { if (active) setJourneys(records); })
      .catch(err => { if (active) setError(err instanceof Error ? err.message : "Could not load upcoming journeys."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const money = (value: string | number) => new Intl.NumberFormat("en-IN", {
    style: "currency", currency: "INR", maximumFractionDigits: 0,
  }).format(Number(value || 0));
  const dateLabel = (value: string) => new Date(value + "T00:00:00").toLocaleDateString(
    "en-IN", { weekday: "short", day: "numeric", month: "short" },
  );
  const availableSeats = journeys.reduce((total, journey) => total + journey.available_seats, 0);
  const averageShare = journeys.length
    ? journeys.reduce((total, journey) => total + Number(journey.estimated_contribution_per_passenger || 0), 0) / journeys.length
    : 0;
  const nextJourney = journeys[0];

  return <DashboardLayout role="Passenger">
    <div className="wt-dash-heading">
      <div><Eyebrow>PASSENGER WORKSPACE</Eyebrow><h1>Your shared journeys.</h1><p>Explore genuine upcoming routes published by verified drivers.</p></div>
      <Link to="/search" className="wt-btn wt-btn-primary">Find a journey <ArrowRight size={15}/></Link>
    </div>
    <div className="wt-dash-metrics">
      <Metric label="Upcoming routes" value={loading ? "…" : String(journeys.length)} detail="Live published journeys" icon={CalendarDays}/>
      <Metric label="Seats available" value={loading ? "…" : String(availableSeats)} detail="Across upcoming routes" icon={Users}/>
      <Metric label="Average estimated share" value={loading ? "…" : money(averageShare)} detail="Per passenger · indicative" icon={Wallet}/>
      <Metric label="Next departure" value={loading ? "…" : nextJourney ? dateLabel(nextJourney.travel_date) : "—"} detail={nextJourney ? nextJourney.departure_time.slice(0,5) : "No upcoming route"} icon={CarFront}/>
    </div>
    <section className="wt-panel wt-dash-section">
      <div className="wt-panel-heading">
        <div><h2>Upcoming journeys</h2><p>Real routes from the WayTogether marketplace.</p></div>
        <Link to="/search" className="wt-text-link">Find a journey <ArrowRight size={15}/></Link>
      </div>
      {error ? <div className="wt-dash-error" role="alert">{error}</div> : loading ? (
        <div className="wt-market-empty"><span className="wt-spin"/>Loading upcoming journeys…</div>
      ) : journeys.length === 0 ? (
        <div className="wt-empty-dashboard">
          <Compass/>
          <div><b>No upcoming journeys are published yet.</b><p>New verified routes will appear here when drivers publish them.</p></div>
          <Link className="wt-btn wt-btn-primary" to="/search">Explore journeys <ArrowRight size={15}/></Link>
        </div>
      ) : (
        <div className="wt-table-wrap">
          <table><thead><tr><th>Journey</th><th>Date &amp; time</th><th>Estimated share</th><th>Seats</th></tr></thead>
            <tbody>{journeys.map(journey => <tr key={journey.id}>
              <td><Link className="wt-dashboard-journey-link" to={"/journeys/" + journey.id}><b>{journey.origin_name} → {journey.destination_name}</b><small>Verified driver · {journey.driver_name}</small></Link></td>
              <td>{dateLabel(journey.travel_date)} · {journey.departure_time.slice(0,5)}</td>
              <td>{money(journey.estimated_contribution_per_passenger)}<small>Per passenger · indicative</small></td>
              <td><span className={"wt-status " + (journey.available_seats > 0 ? "status-open" : "status-full")}>{journey.available_seats > 0 ? journey.available_seats + " available" : "Full"}</span></td>
            </tr>)}</tbody>
          </table>
        </div>
      )}
    </section>
    <div className="wt-panel wt-empty-dashboard">
      <Compass/><div><b>Find people travelling your way.</b><p>Search the live marketplace for a route that fits your plans.</p></div>
      <Link className="wt-btn wt-btn-primary" to="/search">Explore journeys <ArrowRight size={15}/></Link>
    </div>
  </DashboardLayout>;
}
function DriverDashboard() {
  const [journeys, setJourneys] = useState<JourneyRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getMyJourneys()
      .then(records => { if (active) setJourneys(records); })
      .catch(err => { if (active) setError(err instanceof Error ? err.message : "Could not load your journeys."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const upcomingJourneys = journeys
    .filter(journey => {
      if (journey.status !== "published") return false;
      const departure = new Date(journey.travel_date + "T" + journey.departure_time);
      return departure.getTime() >= Date.now();
    })
    .sort((a, b) => {
      const aDate = new Date(a.travel_date + "T" + a.departure_time).getTime();
      const bDate = new Date(b.travel_date + "T" + b.departure_time).getTime();
      return aDate - bDate;
    });
  const availableSeats = upcomingJourneys.reduce((total, journey) => total + journey.available_seats, 0);
  const nextJourney = upcomingJourneys[0];
  const money = (value: string | number) => new Intl.NumberFormat("en-IN", {
    style: "currency", currency: "INR", maximumFractionDigits: 0,
  }).format(Number(value || 0));
  const dateLabel = (value: string) => new Date(value + "T00:00:00").toLocaleDateString(
    "en-IN", { weekday: "short", day: "numeric", month: "short" },
  );

  return <DashboardLayout role="Driver">
    <div className="wt-dash-heading">
      <div><Eyebrow>DRIVER WORKSPACE</Eyebrow><h1>Your journeys, in one place.</h1><p>Manage upcoming journeys you have independently planned and published.</p></div>
      <Link to="/publish" className="wt-btn wt-btn-primary">Share a journey <Plus size={15}/></Link>
    </div>
    <div className="wt-dash-banner">
      <div><span><ShieldCheck size={18}/> DRIVER PRINCIPLE</span><b>Share the journey you already planned.</b><p>WayTogether is designed for eligible expense sharing, not profit-seeking passenger transport.</p></div>
      <Link to="/dashboard/driver/bookings" className="wt-btn wt-btn-primary">Booking requests <Users size={15}/></Link>
    </div>
    <div className="wt-dash-metrics">
      <Metric label="Upcoming journeys" value={loading ? "…" : String(upcomingJourneys.length)} detail="Your live published routes" icon={CarFront}/>
      <Metric label="Seats available" value={loading ? "…" : String(availableSeats)} detail="Across upcoming journeys" icon={Users}/>
      <Metric label="Next departure" value={loading ? "…" : nextJourney ? dateLabel(nextJourney.travel_date) : "—"} detail={nextJourney ? nextJourney.departure_time.slice(0,5) : "No upcoming journey"} icon={CalendarDays}/>
      <Metric label="Next estimated share" value={loading ? "…" : nextJourney ? money(nextJourney.estimated_contribution_per_passenger) : "—"} detail="Per passenger · indicative" icon={Wallet}/>
    </div>
    <section className="wt-panel wt-dash-section">
      <div className="wt-panel-heading"><div><h2>Your upcoming journeys</h2><p>Live published routes from your account.</p></div><Link to="/dashboard/driver/journeys" className="wt-text-link">Manage journeys <ArrowRight size={15}/></Link></div>
      {error ? <div className="wt-dash-error" role="alert">{error}</div> : loading ? (
        <div className="wt-market-empty"><span className="wt-spin"/>Loading your journeys…</div>
      ) : upcomingJourneys.length === 0 ? (
        <div className="wt-empty-dashboard">
          <Compass/><div><b>You have no upcoming published journeys.</b><p>Publish a journey you have already planned and it will appear here.</p></div>
          <Link className="wt-btn wt-btn-primary" to="/publish">Share a journey <Plus size={15}/></Link>
        </div>
      ) : (
        <div className="wt-table-wrap">
          <table><thead><tr><th>Route</th><th>Departure</th><th>Estimated share</th><th>Seats</th><th>Manage</th></tr></thead>
            <tbody>{upcomingJourneys.slice(0,5).map(journey=><tr key={journey.id}>
              <td><Link className="wt-dashboard-journey-link" to={"/journeys/"+journey.id}><b>{journey.origin_name} → {journey.destination_name}</b><small>Journey #{journey.id}</small></Link></td>
              <td>{dateLabel(journey.travel_date)} · {journey.departure_time.slice(0,5)}</td>
              <td>{money(journey.estimated_contribution_per_passenger)}<small>Per passenger · indicative</small></td>
              <td><span className={"wt-status "+(journey.available_seats>0?"status-open":"status-full")}>{journey.available_seats>0?journey.available_seats+" available":"Full"}</span></td>
              <td><Link className="wt-text-link" to="/dashboard/driver/journeys">View</Link></td>
            </tr>)}</tbody>
          </table>
        </div>
      )}
    </section>
  </DashboardLayout>;
}

function AdminDashboard() {
  return <DashboardLayout role="Admin"><AdminOverviewContent/></DashboardLayout>;
}
function NotFound() {
  return <PublicLayout><main className="wt-page"><div className="wt-container wt-not-found"><Eyebrow>404 · ROUTE NOT FOUND</Eyebrow><h1>This route hasn't been mapped yet.</h1><p>Let's get you back on the right way.</p><Link to="/" className="wt-btn wt-btn-primary">Back to homepage <ArrowRight size={16}/></Link></div></main></PublicLayout>;
}

export default function Phase2App() {
  return <BrowserRouter><Routes>
    <Route path="/" element={<HomePage/>}/><Route path="/search" element={<SearchPage/>}/><Route path="/journeys/:id" element={<JourneyDetailPage/>}/><Route path="/publish" element={<PublishPage/>}/>
    <Route path="/login" element={<AuthPage mode="login"/>}/><Route path="/register" element={<AuthPage mode="register"/>}/>
    <Route path="/dashboard/passenger" element={<PassengerDashboard/>}/><Route path="/dashboard/passenger/verification" element={<PassengerVerificationPage/>}/><Route path="/dashboard/passenger/bookings" element={<DashboardLayout role="Passenger"><PassengerBookingsContent/></DashboardLayout>}/><Route path="/dashboard/passenger/finance" element={<DashboardLayout role="Passenger"><PassengerFinanceContent/></DashboardLayout>}/><Route path="/dashboard/passenger/messages" element={<DashboardLayout role="Passenger"><MessagesContent role="Passenger"/></DashboardLayout>}/><Route path="/dashboard/passenger/notifications" element={<DashboardLayout role="Passenger"><NotificationCenterContent role="Passenger"/></DashboardLayout>}/><Route path="/dashboard/passenger/safety" element={<DashboardLayout role="Passenger"><SafetyCenterContent role="Passenger"/></DashboardLayout>}/><Route path="/dashboard/passenger/reviews" element={<DashboardLayout role="Passenger"><JourneyReviewsContent role="Passenger"/></DashboardLayout>}/><Route path="/dashboard/driver" element={<DriverDashboard/>}/><Route path="/dashboard/driver/bookings" element={<DashboardLayout role="Driver"><DriverBookingRequestsContent/></DashboardLayout>}/><Route path="/dashboard/driver/finance" element={<DashboardLayout role="Driver"><DriverFinanceContent/></DashboardLayout>}/><Route path="/dashboard/driver/messages" element={<DashboardLayout role="Driver"><MessagesContent role="Driver"/></DashboardLayout>}/><Route path="/dashboard/driver/notifications" element={<DashboardLayout role="Driver"><NotificationCenterContent role="Driver"/></DashboardLayout>}/><Route path="/dashboard/driver/safety" element={<DashboardLayout role="Driver"><SafetyCenterContent role="Driver"/></DashboardLayout>}/><Route path="/dashboard/driver/reviews" element={<DashboardLayout role="Driver"><JourneyReviewsContent role="Driver"/></DashboardLayout>}/><Route path="/dashboard/driver/journeys" element={<DashboardLayout role="Driver"><MyJourneysContent/></DashboardLayout>}/><Route path="/driver/verification" element={<DriverVerificationPage/>}/><Route path="/admin" element={<AdminDashboard/>}/><Route path="/admin/users" element={<DashboardLayout role="Admin"><AdminUsersContent/></DashboardLayout>}/><Route path="/admin/verification" element={<AdminVerificationPage/>}/><Route path="/admin/passenger-verification" element={<AdminPassengerVerificationPage/>}/><Route path="/admin/journeys" element={<DashboardLayout role="Admin"><AdminJourneysContent/></DashboardLayout>}/><Route path="/admin/bookings" element={<DashboardLayout role="Admin"><AdminBookingsContent/></DashboardLayout>}/><Route path="/admin/finance" element={<DashboardLayout role="Admin"><AdminExpenseLedgerContent/></DashboardLayout>}/><Route path="/admin/database-cleanup" element={<DashboardLayout role="Admin"><AdminDatabaseCleanupContent/></DashboardLayout>}/><Route path="/admin/safety" element={<DashboardLayout role="Admin"><AdminSafetyReportsContent/></DashboardLayout>}/>
    <Route path="*" element={<NotFound/>}/>
  </Routes></BrowserRouter>;
}
