import type { RouteId } from "../../app/routes";
import { AgriculturalMapExperience } from "../../components/maps/AgriculturalMapExperience";

export default function MapPage({ onNavigate }: { onNavigate: (id: RouteId) => void }) {
  return <AgriculturalMapExperience onNavigate={onNavigate} />;
}
