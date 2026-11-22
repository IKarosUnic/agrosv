import { Suspense, lazy, useCallback, useEffect, useState } from "react";
import { AppProvider } from "./stores/AppContext";
import { AppShell } from "./app/AppShell";
import { ROUTES, type RouteId } from "./app/routes";
import { HomeDashboard } from "./modules/home/HomeDashboard";
import { LoadingState } from "./components/data-status/DataStatus";

const MapPage = lazy(() => import("./modules/map/MapPage"));
const TerritoryPage = lazy(() => import("./modules/territory/TerritoryPage"));
const CropsPage = lazy(() => import("./modules/crops/CropsPage"));
const CalendarPage = lazy(() => import("./modules/calendar/CalendarPage"));
const MonitoringPage = lazy(() => import("./modules/monitoring/MonitoringPage"));
const RisksAlertsPage = lazy(() => import("./modules/risks/RisksAlertsPage"));
const ProductionCostsPage = lazy(() => import("./modules/economics/ProductionCostsPage"));
const MarketsPricesPage = lazy(() => import("./modules/economics/MarketsPricesPage"));
const ProfitabilityPage = lazy(() => import("./modules/economics/ProfitabilityPage"));
const ScenariosPage = lazy(() => import("./modules/economics/ScenariosPage"));
const ResearchDataPage = lazy(() => import("./modules/research/ResearchDataPage"));

function routeFromHash(): RouteId {
  const hash = window.location.hash.replace(/^#/, "") || "/";
  const match = ROUTES.find((r) => r.path === hash);
  return match ? match.id : "home";
}

export default function App() {
  const [route, setRoute] = useState<RouteId>(() => routeFromHash());

  useEffect(() => {
    const onHash = () => setRoute(routeFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const navigate = useCallback((id: RouteId) => {
    const target = ROUTES.find((r) => r.id === id);
    if (target) {
      window.location.hash = `#${target.path}`;
    }
    setRoute(id);
  }, []);

  return (
    <AppProvider>
      <AppShell activeRoute={route} onNavigate={navigate}>
        <Suspense fallback={<LoadingState message="Cargando módulo…" />}>
          {route === "home" && <HomeDashboard onNavigate={navigate} />}
          {route === "map" && <MapPage onNavigate={navigate} />}
          {route === "territory" && <TerritoryPage />}
          {route === "crops" && <CropsPage />}
          {route === "calendar" && <CalendarPage />}
          {route === "monitoring" && <MonitoringPage />}
          {route === "risks" && <RisksAlertsPage />}
          {route === "production" && <ProductionCostsPage />}
          {route === "markets" && <MarketsPricesPage />}
          {route === "profitability" && <ProfitabilityPage />}
          {route === "scenarios" && <ScenariosPage />}
          {route === "research" && <ResearchDataPage />}
        </Suspense>
      </AppShell>
    </AppProvider>
  );
}
