import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { AppProvider } from "../stores/AppContext";
import { HomeDashboard } from "../modules/home/HomeDashboard";
import CropsPage from "../modules/crops/CropsPage";
import ProfitabilityPage from "../modules/economics/ProfitabilityPage";
import ScenariosPage from "../modules/economics/ScenariosPage";
import { clearMemoryCache } from "../services/api/client";

function mockApiRouter(url: string) {
  if (url.includes("/api/health")) {
    return { status: "ok", missing: [], version: "1.0.0" };
  }
  if (url.includes("/api/territory/departments")) {
    return {
      type: "FeatureCollection",
      features: [{ type: "Feature", properties: { adm1_code: "SLV-SS", name: "San Salvador", area_km2: 886.2 }, geometry: null }],
    };
  }
  if (url.includes("/api/engines/environmental")) {
    return {
      engine: "environmental",
      engine_version: "5.0.0",
      result: {
        identification: { department: { name: "San Salvador" }, municipality_historic: { name: "San Salvador" } },
        terrain: { elevation_m: 658, slope_deg: 4.2 },
        soil: { properties: { ph: { value: 6.2 }, clay: { value: 28 }, soil_organic_carbon: { value: 18 } } },
        hydrology: { water_balance: { mean: { precipitation_mm: 1820, et0_mm: 1450, precipitation_minus_et0_mm: 370 } } },
        environmental_constraints: [],
      },
    };
  }
  if (url.includes("/api/monitoring/alerts")) {
    return { count: 0, alerts: [], by_status: {}, by_category: {} };
  }
  if (url.includes("/api/economics/production/statistics")) {
    return {
      engine: "production_statistics",
      engine_version: "8.0.0",
      result: {
        cap_2025_records: [
          {
            record_id: "ECN-1",
            product_or_activity: "maize",
            reference_period: "2024-05 / 2025-04",
            value: { crop_name_es: "Maíz", harvested_area_mz: 280000, production_qq: 12000000 },
          },
        ],
        worldbank_agricultural_land_pct: { indicator: "AG.LND.AGRI.ZS", year: "2022", value_pct: 57.3 },
      },
    };
  }
  if (url.includes("/api/agriculture/crops/maize")) {
    return {
      crop_id: "maize",
      scientific_name: "Zea mays L.",
      local_names: ["maíz"],
      family: "Poaceae",
      crop_type: "basic_grain",
      lifecycle: "annual",
      growth_habit: "erect",
      cycle_days: { value: [90, 140], unit: "d", status: "REF", source: "cat", note: null },
      temperature: {},
      water: {},
      soil: {},
      nutrition: {},
      kc: { value: null, unit: "adim", status: "GAP", source: null, note: "Sin Kc local" },
      planting_months: { value: null, unit: "month", status: "GAP", source: null, note: null },
      yield_data: {},
      pests: ["fall_armyworm"],
      diseases: [],
      production_systems: ["rainfed"],
      sources: ["FAO-56"],
      confidence: "moderate",
      gaps: ["Kc local por etapa"],
    };
  }
  if (url.includes("/api/agriculture/crops")) {
    return {
      count: 1,
      types: ["basic_grain"],
      crops: [
        {
          crop_id: "maize",
          scientific_name: "Zea mays L.",
          local_names: ["maíz"],
          crop_type: "basic_grain",
          lifecycle: "annual",
          cycle_days: { value: [90, 140], unit: "d", status: "REF", source: "cat", note: null },
          parameter_status: { REF: 8, NAC: 1, GAP: 3 },
        },
      ],
    };
  }
  if (url.includes("/api/agriculture/suitability")) {
    return {
      engine: "crop_suitability",
      engine_version: "6.0.0",
      result: {
        crop_id: "maize",
        system: "rainfed",
        class: "S2",
        class_label: "moderadamente apto",
        limiting_factors: ["ph"],
        factors: [{ factor: "temperature", value: 24.5, unit: "degC", thresholds: {}, rating: "none", critical: true, note: null }],
      },
    };
  }
  if (url.includes("/api/economics/profitability")) {
    return {
      engine: "agricultural_profitability",
      engine_version: "8.0.0",
      result: {
        gross_revenue: 1980,
        gross_margin: 400,
        net_operating_margin: 160,
        profit_per_ha: 114.29,
        saleable_t: 3.94,
      },
    };
  }
  if (url.includes("/api/economics/break-even")) {
    return {
      engine: "break_even_analysis",
      engine_version: "8.0.0",
      result: {
        break_even_price_per_qq46: 19.8,
        break_even_yield_qq_mz: 40.5,
        cost_sensitivity: [{ cost_change_pct: 10, adjusted_total_cost: 2002, break_even_price_per_t: 508, break_even_yield_t_ha: 2.8 }],
      },
    };
  }
  if (url.includes("/api/economics/scenarios/run")) {
    return {
      engine: "agricultural_economic_scenario",
      engine_version: "8.0.0",
      synthetic: true,
      result: {
        baseline: { net_operating_margin: 300 },
        scenario_result: { net_operating_margin: 150 },
        delta_vs_baseline: { net_margin_delta: -150, cost_delta: 150 },
      },
    };
  }
  if (url.includes("/api/economics/scenarios")) {
    return {
      engine: "agricultural_economic_scenario",
      result: {
        count: 1,
        scenarios: [{ scenario_id: "fertilizer_shock", label: "Alza de fertilizantes (+30%)", changes: { fertilizer_cost_mult: 1.3 } }],
      },
    };
  }
  if (url.includes("/api/social/nemotron/agricultural")) {
    return {
      count: 1,
      profiles: [{ uuid: "P1", occupation: "Productor de granos básicos", department: "San Salvador", area: "Rural", age: 44, archetype_hint: "smallholder" }],
    };
  }
  if (url.includes("/api/socio/scenarios")) {
    return { scenarios: { A: { name: "Escenario A base" } } };
  }
  return {};
}

describe("Module integration with scientific transparency", () => {
  beforeEach(() => {
    clearMemoryCache();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input);
        return Promise.resolve(
          new Response(JSON.stringify(mockApiRouter(url)), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }),
    );
  });

  it("renders HomeDashboard with real environmental metrics and official CAP stats", async () => {
    render(
      <AppProvider>
        <HomeDashboard onNavigate={vi.fn()} />
      </AppProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText(/658/)).toBeInTheDocument();
      expect(screen.getByText("Maíz")).toBeInTheDocument();
    });
  });

  it("evaluates crop suitability S1-N via backend engine in CropsPage", async () => {
    render(
      <AppProvider>
        <CropsPage />
      </AppProvider>,
    );

    await waitFor(() => expect(screen.getByText("Zea mays L.")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("tab", { name: "Aptitud S1–N" }));

    await waitFor(() => {
      expect(screen.getByText("S2")).toBeInTheDocument();
      expect(screen.getByText("moderadamente apto")).toBeInTheDocument();
    });
  });

  it("surfaces incomplete cost warning and break-even outputs in ProfitabilityPage", async () => {
    render(
      <AppProvider>
        <ProfitabilityPage />
      </AppProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText(/Cálculo financiero parcial/i)).toBeInTheDocument();
      expect(screen.getByText(/19\.80/)).toBeInTheDocument();
    });
  });

  it("strictly labels Nemotron socio-agricultural profiles as synthetic", async () => {
    render(
      <AppProvider>
        <ScenariosPage />
      </AppProvider>,
    );

    fireEvent.click(screen.getByRole("tab", { name: /Socio-agrícola sintético/i }));
    await waitFor(() => {
      expect(screen.getByText(/Simulación sintética — no es un hogar real observado ni encuestado/i)).toBeInTheDocument();
      expect(screen.getByText("Productor de granos básicos")).toBeInTheDocument();
    });
  });
});
