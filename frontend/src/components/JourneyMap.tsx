import { useEffect, useMemo } from "react";
import { CircleMarker, MapContainer, Polyline, TileLayer, useMap } from "react-leaflet";
import type { LatLngTuple } from "leaflet";
import "leaflet/dist/leaflet.css";

type Point = { latitude: number; longitude: number; label: string };
type Props = {
  origin: Point;
  destination: Point;
  geometry?: [number, number][] | null;
  stops?: Point[];
  height?: number;
};

function FitJourney({ points }: { points: LatLngTuple[] }) {
  const map = useMap();
  useEffect(() => {
    if (points.length) map.fitBounds(points, { padding: [28, 28], maxZoom: 10 });
  }, [map, points]);
  return null;
}

export default function JourneyMap({
  origin, destination, geometry = [], stops = [], height = 280,
}: Props) {
  const positions = useMemo<LatLngTuple[]>(
    () => (geometry ?? []).map(([longitude,latitude])=>[latitude,longitude] as LatLngTuple),
    [geometry],
  );
  const points = useMemo<LatLngTuple[]>(
    () => [
      [origin.latitude,origin.longitude],
      ...stops.map(stop=>[stop.latitude,stop.longitude] as LatLngTuple),
      [destination.latitude,destination.longitude],
    ],
    [origin.latitude,origin.longitude,destination.latitude,destination.longitude,stops],
  );
  const center: LatLngTuple = [
    (origin.latitude + destination.latitude) / 2,
    (origin.longitude + destination.longitude) / 2,
  ];
  // Use OSM tiles by default in production too; keep the provider configurable
  // so a dedicated tile service can replace it as traffic grows.
  const tileUrl = import.meta.env.VITE_OSM_TILE_URL || "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
  const tileAttribution = import.meta.env.VITE_OSM_TILE_ATTRIBUTION || '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

  return <div className="wt-journey-map" style={{height}} aria-label="Journey map">
    <MapContainer center={center} zoom={6} maxZoom={19} scrollWheelZoom={false} style={{height:"100%",width:"100%"}}>
      {tileUrl && <TileLayer attribution={tileAttribution} url={tileUrl}/>}

      <FitJourney points={positions.length ? positions : points}/>
      {positions.length > 1 && <Polyline positions={positions} pathOptions={{color:"#826bff",weight:5,opacity:.9}}/>}
      <CircleMarker center={points[0]} radius={8} pathOptions={{color:"#ffffff",weight:2,fillColor:"#a43dff",fillOpacity:1}}/>
      {stops.map((stop,index)=><CircleMarker key={stop.label+index} center={[stop.latitude,stop.longitude]} radius={6} pathOptions={{color:"#fff",weight:2,fillColor:"#687dff",fillOpacity:1}}/>)}
      <CircleMarker center={points[points.length-1]} radius={8} pathOptions={{color:"#ffffff",weight:2,fillColor:"#18b9d9",fillOpacity:1}}/>
    </MapContainer>
    {!tileUrl && <div className="wt-map-missing-tiles">Configure a permitted map tile provider for this deployment.</div>}
  </div>;
}
