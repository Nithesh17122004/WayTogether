import { useMemo } from "react";
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
  useMemo(() => {
    if (points.length) map.fitBounds(points, { padding: [28, 28], maxZoom: 10 });
    return undefined;
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

  return <div className="wt-journey-map" style={{height}} aria-label="Journey map">
    <MapContainer center={center} zoom={6} scrollWheelZoom={false} style={{height:"100%",width:"100%"}}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
        url={import.meta.env.VITE_OSM_TILE_URL || "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"}
      />
      <FitJourney points={positions.length ? positions : points}/>
      {positions.length > 1 && <Polyline positions={positions} pathOptions={{color:"#826bff",weight:5,opacity:.9}}/>}
      <CircleMarker center={points[0]} radius={8} pathOptions={{color:"#ffffff",weight:2,fillColor:"#a43dff",fillOpacity:1}}>
        <></>
      </CircleMarker>
      {stops.map((stop,index)=><CircleMarker key={stop.label+index} center={[stop.latitude,stop.longitude]} radius={6} pathOptions={{color:"#fff",weight:2,fillColor:"#687dff",fillOpacity:1}}/>)}
      <CircleMarker center={points[points.length-1]} radius={8} pathOptions={{color:"#ffffff",weight:2,fillColor:"#18b9d9",fillOpacity:1}}/>
    </MapContainer>
  </div>;
}
