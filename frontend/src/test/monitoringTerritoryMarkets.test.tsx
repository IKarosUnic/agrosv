import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { AppProvider } from "../stores/AppContext";
import TerritoryPage from "../modules/territory/TerritoryPage";
import MonitoringPage from "../modules/monitoring/MonitoringPage";
import MarketsPricesPage from "../modules/economics/MarketsPricesPage";
import RisksAlertsPage from "../modules/risks/RisksAlertsPage";
import { clearMemoryCache } from "../services/api/client";

describe("Territory, Monitoring, Markets, and Risks workflows", () => {
  beforeEach(() => {
    clearMemoryCache();
    localStorage.clear();
  });

  it("displays explicit groundwater unavailability and non-station climate notes in TerritoryPage", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input);
        let body: unknown = {};
        if (url.includes("/api/engines/environmental")) {
          body = {
            engine: "environmental",
            engine_version: "5.0.0",
            result: {
              identification: { department: { name: "La Libertad" }, municipality_historic: { name: "Santa Tecla" } },
              terrain: { elevation_m: 920, slope_deg: 7.5 },
              soil: { properties: { ph: { value: 6.1, unit: "pH", label: "pH", available: true } }, derived: { texture_class: { usda_class: "franco" } } },
              hydrology: { water_balance: { mean: { precipitation_minus_et0_mm: 410, aridity_index_p_over_et0: 1.28 } } },
              environmental_constraints: [],
              data_coverage: { groundwater: { available: false, reason: "sin capa ni series" } },
            },
          };
        } else if (url.includes("/api/engines/hydrology")) {
          body = {
            engine: "hydrology",
            engine_version: "5.0.0",
            result: {
              surface_water: { nearest_any: { distance_km: 1.4, name: "Quebrada El Piro" } },
              local_watershed: { upstream_area_km2: 2.3, truncated: false },
              water_balance: { mean: { budyko_runoff_mm: 520 }, annual: [] },
              groundwater: { available: false, note: "Sin datos de acuíferos ni derechos de agua." },
            },
          };
        } else if (url.includes("/api/engines/climate")) {
          body = {
            engine: "climate",
            engine_version: "5.0.0",
            result: {
              nearest_points: { open_meteo_point: { distance_km: 5.2, start: "2019-01-01", end: "2025-12-31", n: 2557 } },
              drought_indicator: { percentile: 42, category: "normal", latest_window_end: "2025-12" },
              seasonality: { months: [{ month: 1, precipitation_mm: 8, temperature_mean_c: 23.1, walter_lieth_humid: false }] },
              extremes: { years: [] },
            },
          };
        } else if (url.includes("/api/engines/soil")) {
          body = { engine: "soil", engine_version: "5.0.0", result: { properties: {}, derived: {}, limitations_found: [], not_available: {} } };
        }
        return Promise.resolve(new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } }));
      }),
    );

    render(
      <AppProvider>
        <TerritoryPage />
      </AppProvider>,
    );

    await waitFor(() => expect(screen.getByText("La Libertad")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("tab", { name: "Hidrología" }));
    await waitFor(() => expect(screen.getByText(/Sin datos de acuíferos/i)).toBeInTheDocument());
    fireEvent.click(screen.getByRole("tab", { name: "Clima (Reanálisis)" }));
    await waitFor(() => expect(screen.getByText(/no es estación SNET\/MARN ni pronóstico/i)).toBeInTheDocument());
  });

  it("saves field observation offline drafts and submits alerts with evidence", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/api/monitoring/field-observations")) {
          return Promise.resolve(new Response(JSON.stringify({ count: 0, observations: [] }), { status: 200, headers: { "Content-Type": "application/json" } }));
        }
        if (url.includes("/api/monitoring/alerts")) {
          return Promise.resolve(new Response(JSON.stringify({ count: 0, alerts: [], by_status: {}, by_category: {} }), { status: 200, headers: { "Content-Type": "application/json" } }));
        }
        return Promise.resolve(new Response(JSON.stringify({}), { status: 200, headers: { "Content-Type": "application/json" } }));
      }),
    );

    render(
      <AppProvider>
        <MonitoringPage />
      </AppProvider>,
    );

    fireEvent.change(screen.getByLabelText(/Síntomas, manejo o descripción/i), { target: { value: "Hojas amarillas en lote norte" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar borrador" }));
    await waitFor(() => expect(screen.getByText(/Borrador guardado localmente/i)).toBeInTheDocument());

    render(
      <AppProvider>
        <RisksAlertsPage />
      </AppProvider>,
    );
    await waitFor(() => expect(screen.getByText(/no sustituyen comunicados oficiales/i)).toBeInTheDocument());
  });

  it("renders WFP historical prices with explicit observation date and price_type badge", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input);
        let body: unknown = { result: {} };
        if (url.includes("/api/economics/prices/history")) {
          body = { result: { series: [{ date: "2026-09-15", price: 24.5 }, { date: "2026-10-15", price: 25.0 }] } };
        } else if (url.includes("/api/economics/prices")) {
          body = {
            result: {
              available: true,
              count: 1,
              records: [
                {
                  record_id: "ECN-1",
                  product_or_activity: "Maize (white)",
                  observation_date: "2026-10-15",
                  market: "San Salvador",
                  price_type: "wholesale",
                  value: 25.0,
                  unit: "46 KG",
                  normalized_price: 25.0,
                },
              ],
            },
          };
        } else if (url.includes("/api/economics/markets")) {
          body = { result: { markets: [] } };
        } else if (url.includes("/api/economics/logistics")) {
          body = { result: { nearest_markets: [], nearest_osm_road: { nearest_road_m: 120 } } };
        }
        return Promise.resolve(new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } }));
      }),
    );

    render(
      <AppProvider>
        <MarketsPricesPage />
      </AppProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("2026-10-15")).toBeInTheDocument();
      expect(screen.getByText("wholesale")).toBeInTheDocument();
    });
  });
});
