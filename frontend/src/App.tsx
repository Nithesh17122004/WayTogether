import { useState, type FormEvent } from "react";
import {
  ArrowDownUp,
  ArrowRight,
  ArrowUpRight,
  BadgeCheck,
  CalendarDays,
  CarFront,
  Check,
  ChevronRight,
  Clock3,
  Compass,
  Menu,
  MapPin,
  ShieldCheck,
  Sparkles,
  Users,
  X,
} from "lucide-react";

type SearchMode = "passenger" | "driver";

const sampleJourneys = [
  { from: "Chennai", to: "Bengaluru", date: "Sample date", time: "7:30 AM", seats: 2, contribution: "₹420", driver: "Arun", initials: "AK", rating: "4.9", vehicle: "Sedan" },
  { from: "Coimbatore", to: "Kochi", date: "Sample date", time: "9:00 AM", seats: 3, contribution: "₹280", driver: "Meera", initials: "MR", rating: "5.0", vehicle: "Hatchback" },
  { from: "Hyderabad", to: "Vijayawada", date: "Sample date", time: "6:45 AM", seats: 1, contribution: "₹350", driver: "Rahul", initials: "RS", rating: "4.8", vehicle: "SUV" },
];

function Brand() {
  return (
    <a className="brand" href="#home" aria-label="WayTogether home">
      <span className="brand-mark"><span>W</span></span>
      <span className="brand-word">Way<span>Together</span></span>
    </a>
  );
}

function Header() {
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);

  return (
    <header className="site-header">
      <div className="container nav-shell">
        <Brand />
        <nav className={open ? "main-nav is-open" : "main-nav"} aria-label="Main navigation">
          <a href="#how-it-works" onClick={close}>How it works</a>
          <a href="#routes" onClick={close}>Explore routes</a>
          <a href="#safety" onClick={close}>Safety</a>
          <a href="#about" onClick={close}>About</a>
          <div className="mobile-nav-actions">
            <a className="button button-quiet" href="#search" onClick={close}>Find a ride</a>
            <a className="button button-primary" href="#publish" onClick={close}>Offer a ride <ArrowUpRight size={16} /></a>
          </div>
        </nav>
        <div className="nav-actions">
          <a className="nav-login" href="#sign-in">Log in</a>
          <a className="button button-primary nav-cta" href="#publish">Offer a ride <ArrowUpRight size={16} /></a>
        </div>
        <button className="menu-toggle" aria-label={open ? "Close menu" : "Open menu"} aria-expanded={open} onClick={() => setOpen(!open)}>
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>
    </header>
  );
}

function SearchPanel() {
  const [mode, setMode] = useState<SearchMode>("passenger");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [date, setDate] = useState("");
  const [seats, setSeats] = useState("1");
  const [notice, setNotice] = useState("");

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (mode === "driver") {
      setNotice("Journey publishing will open after driver profiles and verification are enabled. No journey has been published.");
      return;
    }
    if (!from.trim() || !to.trim()) {
      setNotice("Add both your starting point and destination to continue.");
      return;
    }
    setNotice(`Search preview: ${from.trim()} to ${to.trim()}. Live journey results will appear when the marketplace API is connected.`);
  };

  return (
    <div className="search-card" id="search">
      <div className="search-topline">
        <div>
          <span className="eyebrow">YOUR NEXT JOURNEY</span>
          <h2>Where are you headed?</h2>
        </div>
        <span className="secure-note"><ShieldCheck size={15} /> Thoughtful travel, together</span>
      </div>
      <div className="search-tabs" role="tablist" aria-label="Journey type">
        <button className={mode === "passenger" ? "search-tab active" : "search-tab"} onClick={() => { setMode("passenger"); setNotice(""); }} role="tab" aria-selected={mode === "passenger"}>
          <Users size={17} /> Find a seat
        </button>
        <button className={mode === "driver" ? "search-tab active" : "search-tab"} onClick={() => { setMode("driver"); setNotice(""); }} role="tab" aria-selected={mode === "driver"}>
          <CarFront size={17} /> Share your journey
        </button>
      </div>
      <form className="search-form" onSubmit={onSubmit}>
        <label className="field">
          <span><MapPin size={15} /> From</span>
          <input value={from} onChange={(event) => setFrom(event.target.value)} placeholder="Leaving from" list="indian-cities" required />
        </label>
        <button type="button" className="swap-button" aria-label="Swap starting point and destination" onClick={() => { setFrom(to); setTo(from); }}>
          <ArrowDownUp size={18} />
        </button>
        <label className="field">
          <span><MapPin size={15} /> To</span>
          <input value={to} onChange={(event) => setTo(event.target.value)} placeholder="Going to" list="indian-cities" required />
        </label>
        <label className="field field-date">
          <span><CalendarDays size={15} /> Date</span>
          <input type="date" value={date} onChange={(event) => setDate(event.target.value)} min={new Date().toISOString().slice(0, 10)} />
        </label>
        <label className="field field-seats">
          <span><Users size={15} /> Seats</span>
          <select value={seats} onChange={(event) => setSeats(event.target.value)} aria-label="Number of seats">
            <option value="1">1 seat</option>
            <option value="2">2 seats</option>
            <option value="3">3 seats</option>
            <option value="4">4 seats</option>
          </select>
        </label>
        <datalist id="indian-cities">
          {["Chennai", "Bengaluru", "Coimbatore", "Hyderabad", "Mumbai", "Pune", "Kochi", "Madurai", "Delhi", "Vijayawada"].map((city) => <option key={city} value={city} />)}
        </datalist>
        <button className="button button-primary search-submit" type="submit">{mode === "passenger" ? "Explore rides" : "Continue"} <ArrowRight size={17} /></button>
      </form>
      {notice && <div className="form-notice" role="status">{notice}</div>}
      <p className="search-footnote"><ShieldCheck size={14} /> Drivers share journeys they already planned. Passenger contributions are for eligible journey expenses.</p>
    </div>
  );
}

function RouteIllustration() {
  return (
    <div className="route-visual" aria-label="Illustration of a shared journey">
      <div className="visual-glow" />
      <div className="map-grid" />
      <svg className="route-svg" viewBox="0 0 600 420" role="img" aria-label="A curved route connecting two locations">
        <path className="route-shadow" d="M80 320 C150 280 160 110 305 125 S425 290 520 82" />
        <path className="route-dash" d="M80 320 C150 280 160 110 305 125 S425 290 520 82" />
        <circle cx="80" cy="320" r="17" className="route-pin-start" />
        <circle cx="520" cy="82" r="17" className="route-pin-end" />
        <circle cx="80" cy="320" r="5" fill="#fff" />
        <circle cx="520" cy="82" r="5" fill="#fff" />
      </svg>
      <div className="map-label label-start"><span className="map-label-dot" /> Your starting point</div>
      <div className="map-label label-end"><span className="map-label-dot cyan" /> Same destination</div>
      <div className="car-orbit"><div className="car-orbit-icon"><CarFront size={39} strokeWidth={1.5} /></div></div>
      <div className="floating-stat stat-top"><span className="stat-icon"><Users size={16} /></span><span><strong>One shared route</strong><small>More connected journeys</small></span></div>
      <div className="floating-stat stat-bottom"><span className="avatar-stack"><i>AK</i><i>MR</i><i>+</i></span><span><strong>Travel together</strong><small>Make room for the same way</small></span></div>
      <span className="visual-coordinate coord-one">13.0827° N</span>
      <span className="visual-coordinate coord-two">77.5946° E</span>
    </div>
  );
}

function JourneyCard({ journey }: { journey: typeof sampleJourneys[number] }) {
  return (
    <article className="journey-card">
      <div className="journey-date"><CalendarDays size={14} /> {journey.date}</div>
      <div className="journey-route">
        <div className="journey-times">
          <strong>{journey.time}</strong>
          <span>Flexible arrival</span>
        </div>
        <div className="journey-line"><i /><span /><i /></div>
        <div className="journey-cities"><strong>{journey.from}</strong><strong>{journey.to}</strong></div>
      </div>
      <div className="journey-bottom">
        <div className="driver-mini"><span className="driver-avatar">{journey.initials}</span><span><strong>{journey.driver}</strong><small><BadgeCheck size={12} /> Example profile · {journey.rating}</small></span></div>
        <div className="journey-price"><strong>{journey.contribution}</strong><small>Expense contribution</small></div>
      </div>
      <div className="journey-meta"><span><Users size={14} /> {journey.seats} seats</span><span><CarFront size={14} /> {journey.vehicle}</span><span><Clock3 size={14} /> {journey.time}</span></div>
    </article>
  );
}

function App() {
  return (
    <>
      <Header />
      <main id="home">
        <section className="hero-section">
          <div className="hero-noise" />
          <div className="container hero-grid">
            <div className="hero-copy">
              <div className="hero-kicker"><span className="kicker-pulse" /> A better way to get there <span className="kicker-line" /></div>
              <h1>Same direction.<br /><span>Better together.</span></h1>
              <p className="hero-description">Good journeys don't have to be solo. Find people heading your way and share the road, the experience and eligible travel expenses.</p>
              <div className="hero-actions">
                <a className="button button-primary button-large" href="#search">Find your ride <ArrowRight size={18} /></a>
                <a className="button button-outline button-large" href="#how-it-works">Discover how it works</a>
              </div>
              <div className="hero-proof">
                <div className="proof-avatars"><i>AK</i><i>MR</i><i>RS</i><i>+</i></div>
                <div><strong>Every journey starts with a shared direction.</strong><span>Designed around people, not just destinations.</span></div>
              </div>
            </div>
            <RouteIllustration />
          </div>
          <div className="hero-bottom-fade" />
        </section>

        <section className="search-section">
          <div className="container"><SearchPanel /></div>
        </section>

        <section className="section journey-preview">
          <div className="container">
            <div className="section-heading section-heading-row">
              <div><span className="eyebrow">A GLIMPSE OF THE EXPERIENCE</span><h2>Journeys, made more connected.</h2><p>These sample cards show how a shared journey could appear in the marketplace.</p></div>
              <span className="preview-label">DESIGN PREVIEW · NOT LIVE LISTINGS</span>
            </div>
            <div className="journeys-grid">{sampleJourneys.map((journey) => <JourneyCard key={journey.from + journey.to} journey={journey} />)}</div>
            <p className="journey-preview-note">Illustrative content only. Live journey discovery and availability will be connected in the marketplace phase.</p>
          </div>
        </section>

        <section className="trust-strip" id="safety">
          <div className="container trust-grid">
            <div className="trust-item"><ShieldCheck size={21} /><span><strong>Safety comes first</strong><small>Verification-led community</small></span></div>
            <div className="trust-item"><Compass size={21} /><span><strong>Journeys already planned</strong><small>Share the route you're taking</small></span></div>
            <div className="trust-item"><Users size={21} /><span><strong>People going your way</strong><small>Connect along a common route</small></span></div>
            <div className="trust-item"><Sparkles size={21} /><span><strong>Thoughtful by design</strong><small>Clear, transparent experience</small></span></div>
          </div>
        </section>

        <section className="section section-light" id="how-it-works">
          <div className="container">
            <div className="section-heading">
              <span className="eyebrow eyebrow-light">A SIMPLE WAY TO SHARE THE ROAD</span>
              <h2>One route. A few simple steps.</h2>
              <p>Whether you have a seat to share or need a way to get there, getting started is easy.</p>
            </div>
            <div className="steps-grid">
              <article className="step-card"><span className="step-number">01</span><div className="step-icon"><MapPin size={23} /></div><h3>Choose your route</h3><p>Enter where you're starting, where you're headed and when you plan to travel.</p><span className="step-link">Start with a direction <ChevronRight size={15} /></span></article>
              <article className="step-card"><span className="step-number">02</span><div className="step-icon"><Users size={23} /></div><h3>Find your people</h3><p>Discover independently planned journeys and connect with people travelling the same way.</p><span className="step-link">Meet along the way <ChevronRight size={15} /></span></article>
              <article className="step-card"><span className="step-number">03</span><div className="step-icon"><CarFront size={23} /></div><h3>Share the journey</h3><p>Confirm the details, meet your fellow travellers and share eligible journey expenses.</p><span className="step-link">Make the trip together <ChevronRight size={15} /></span></article>
            </div>
          </div>
        </section>

        <section className="section section-dark" id="routes">
          <div className="container">
            <div className="section-heading section-heading-row">
              <div><span className="eyebrow">A LITTLE CLOSER TO YOUR NEXT TRIP</span><h2>Routes worth sharing.</h2><p>Explore a few of the journeys our experience is designed to support.</p></div>
              <a className="text-link" href="#search">Search a route <ArrowUpRight size={16} /></a>
            </div>
            <div className="routes-grid">
              {[
                { from: "Chennai", to: "Bengaluru", distance: "Approx. 350 km", code: "01" },
                { from: "Mumbai", to: "Pune", distance: "Approx. 150 km", code: "02" },
                { from: "Coimbatore", to: "Kochi", distance: "Approx. 190 km", code: "03" },
                { from: "Hyderabad", to: "Vijayawada", distance: "Approx. 275 km", code: "04" },
              ].map((route) => <a className="route-card" href="#search" key={route.code}><span className="route-card-number">{route.code}</span><span className="route-card-path"><strong>{route.from}</strong><ArrowRight size={17} /><strong>{route.to}</strong></span><span className="route-card-distance">{route.distance}</span><ArrowUpRight className="route-card-arrow" size={18} /></a>)}
            </div>
            <p className="route-disclaimer">Illustrative route examples only. Live journey availability is not yet connected.</p>
          </div>
        </section>

        <section className="section safety-section" id="about">
          <div className="container safety-grid">
            <div className="safety-art">
              <div className="safety-orbit orbit-a" /><div className="safety-orbit orbit-b" />
              <div className="safety-shield"><ShieldCheck size={76} strokeWidth={1.15} /><span>TRAVEL<br />THOUGHTFULLY</span></div>
              <div className="safety-chip chip-a"><BadgeCheck size={15} /> Verified journey partners</div>
              <div className="safety-chip chip-b"><Check size={15} /> Clear journey details</div>
            </div>
            <div className="safety-copy">
              <span className="eyebrow">BUILT AROUND TRUST</span>
              <h2>Good journeys begin with feeling comfortable.</h2>
              <p>Trust is part of the journey, not an afterthought. WayTogether is being designed with identity and vehicle checks, clear trip information and accessible support.</p>
              <ul><li><Check size={16} /> Driver and vehicle verification workflow</li><li><Check size={16} /> Clear journey and expense information</li><li><Check size={16} /> Reporting and support pathways</li></ul>
              <a className="text-link" href="#how-it-works">Our approach to safer sharing <ArrowUpRight size={16} /></a>
            </div>
          </div>
        </section>

        <section className="cta-section" id="publish">
          <div className="container cta-inner"><div><span className="eyebrow">THE ROAD IS BETTER SHARED</span><h2>Wherever you're going,<br /><span>there may be someone going too.</span></h2></div><a className="button button-white button-large" href="#search">Explore WayTogether <ArrowRight size={18} /></a></div>
        </section>
      </main>
      <footer className="site-footer">
        <div className="container footer-top">
          <div className="footer-brand"><Brand /><p>Share the same route.<br />Make the journey more connected.</p></div>
          <div className="footer-links"><div><strong>Explore</strong><a href="#search">Find a ride</a><a href="#publish">Share a journey</a><a href="#routes">Popular routes</a></div><div><strong>WayTogether</strong><a href="#about">About us</a><a href="#how-it-works">How it works</a><a href="#safety">Safety</a></div><div><strong>Support</strong><a href="mailto:hello@waytogether.in">Contact</a><a href="#safety">Help centre</a><a href="#safety">Community guidelines</a></div></div>
        </div>
        <div className="container footer-bottom"><span>© {new Date().getFullYear()} WayTogether. All rights reserved.</span><span>Designed for journeys shared with care.</span></div>
      </footer>
    </>
  );
}

export default App;