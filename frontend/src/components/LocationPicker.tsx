import { useState } from "react";
import { LoaderCircle, MapPin, Search } from "lucide-react";
import { searchLocations, type LocationChoice } from "../services/journeys";

type Props = {
  label: string;
  placeholder: string;
  value: LocationChoice | null;
  onChange: (value: LocationChoice | null) => void;
};

export default function LocationPicker({ label, placeholder, value, onChange }: Props) {
  const [query, setQuery] = useState(value?.display_name ?? "");
  const [results, setResults] = useState<LocationChoice[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const findLocation = async () => {
    const text = query.trim();
    if (text.length < 3) {
      setError("Enter at least three characters to search.");
      return;
    }
    setBusy(true);
    setError("");
    setResults([]);
    try {
      const found = await searchLocations(text);
      setResults(found);
      if (!found.length) setError("No matching Indian locations were found. Try a city or landmark.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Location search failed.");
    } finally {
      setBusy(false);
    }
  };

  const choose = (location: LocationChoice) => {
    onChange(location);
    setQuery(location.display_name);
    setResults([]);
    setError("");
  };

  return <div className="wt-location-picker">
    <label className="wt-field">
      <span><MapPin size={14}/> {label}</span>
      <div className="wt-location-input-row">
        <input
          value={query}
          onChange={event => {
            setQuery(event.target.value);
            if (value) onChange(null);
          }}
          placeholder={placeholder}
          aria-label={label}
          onKeyDown={event => {
            if (event.key === "Enter") {
              event.preventDefault();
              void findLocation();
            }
          }}
        />
        <button type="button" className="wt-location-search-button" onClick={() => void findLocation()} disabled={busy}>
          {busy ? <LoaderCircle size={15} className="wt-spin"/> : <Search size={15}/>}
          <span>{busy ? "Searching" : "Find"}</span>
        </button>
      </div>
    </label>
    {value && <p className="wt-location-selected"><MapPin size={12}/> Selected: {value.name}, {value.state || value.display_name}</p>}
    {error && <p className="wt-location-error" role="status">{error}</p>}
    {results.length > 0 && <div className="wt-location-results" role="listbox" aria-label={label + " search results"}>
      {results.map((result,index)=><button type="button" key={result.display_name + index} onClick={()=>choose(result)}>
        <MapPin size={14}/><span><b>{result.name}</b><small>{result.display_name}</small></span>
      </button>)}
    </div>}
  </div>;
}
