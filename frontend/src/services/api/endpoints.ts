import { apiGet, apiPost } from "./client";
import type {
  AlertItem,
  CropDetail,
  CropSummary,
  DeptDetail,
  DeptFeatureProps,
  EconomicScenarioSpec,
  EngineEnvelope,
  FieldObservation,
  GeoJsonCollection,
  HealthResponse,
  MarketItem,
  PriceRecord,
  SuitabilityResult,
} from "../../types/api";

const HOUR = 3600_000;
const MIN_5 = 300_000;

export const agrosvApi = {
  // Phase 1 & 2
  health: (signal?: AbortSignal) => apiGet<HealthResponse>("/api/health", { signal, persistOffline: false }),
  meta: (signal?: AbortSignal) => apiGet<Record<string, unknown>>("/api/meta", { signal, ttlMs: HOUR }),
  departments: (simplify = 0.0015, signal?: AbortSignal) =>
    apiGet<GeoJsonCollection<DeptFeatureProps>>(`/api/territory/departments?simplify=${simplify}`, { signal, ttlMs: HOUR }),
  departmentDetail: (code: string, signal?: AbortSignal) =>
    apiGet<DeptDetail>(`/api/territory/departments/${encodeURIComponent(code)}`, { signal, ttlMs: HOUR }),
  municipalities: (department?: string, signal?: AbortSignal) =>
    apiGet<GeoJsonCollection<Record<string, unknown>>>(
      `/api/territory/municipalities${department ? `?department=${encodeURIComponent(department)}` : ""}`,
      { signal, ttlMs: HOUR },
    ),
  infrastructureLayer: (layer: string, bbox: string, limit = 5000, signal?: AbortSignal) =>
    apiGet<GeoJsonCollection<Record<string, unknown>>>(`/api/infrastructure/${layer}?${bbox}&limit=${limit}`, {
      signal,
      persistOffline: false,
    }),
  elevationPoint: (lat: number, lon: number, signal?: AbortSignal) =>
    apiGet<Record<string, unknown>>(`/api/topography/elevation?lat=${lat}&lon=${lon}`, { signal, persistOffline: false }),
  soilPointFast: (lat: number, lon: number, signal?: AbortSignal) =>
    apiGet<Record<string, unknown>>(`/api/soils/point?lat=${lat}&lon=${lon}`, { signal, persistOffline: false }),
  validationPolicy: (signal?: AbortSignal) =>
    apiGet<Record<string, unknown>>("/api/v1/validation/policy", { signal, ttlMs: HOUR }),
  v1Meta: (signal?: AbortSignal) => apiGet<Record<string, unknown>>("/api/v1/meta", { signal, ttlMs: HOUR }),
  v1Qc: (signal?: AbortSignal) => apiGet<Record<string, unknown>>("/api/v1/qc", { signal, ttlMs: MIN_5 }),

  // Phase 4
  dataCatalog: (signal?: AbortSignal) => apiGet<Record<string, unknown>>("/api/data/catalog", { signal, ttlMs: MIN_5 }),
  qualityReports: (signal?: AbortSignal) => apiGet<Record<string, unknown>>("/api/data/quality/reports", { signal, ttlMs: MIN_5 }),

  // Phase 5
  enginesDatasets: (signal?: AbortSignal) => apiGet<Record<string, unknown>>("/api/engines/datasets", { signal, ttlMs: HOUR }),
  enginesCoverage: (signal?: AbortSignal) => apiGet<Record<string, unknown>>("/api/engines/coverage", { signal, ttlMs: HOUR }),
  territorySearch: (q: string, level?: string, signal?: AbortSignal) =>
    apiGet<Record<string, unknown>>(
      `/api/engines/territory/search?q=${encodeURIComponent(q)}${level ? `&level=${encodeURIComponent(level)}` : ""}`,
      { signal, persistOffline: false },
    ),
  territorialProfile: (lat: number, lon: number, signal?: AbortSignal) =>
    apiGet<EngineEnvelope<Record<string, unknown>>>(`/api/engines/territorial?lat=${lat}&lon=${lon}`, { signal }),
  soilProfile: (lat: number, lon: number, signal?: AbortSignal) =>
    apiGet<EngineEnvelope<Record<string, unknown>>>(`/api/engines/soil?lat=${lat}&lon=${lon}`, { signal }),
  hydrologyProfile: (lat: number, lon: number, sizeM = 6000, signal?: AbortSignal) =>
    apiGet<EngineEnvelope<Record<string, unknown>>>(`/api/engines/hydrology?lat=${lat}&lon=${lon}&size_m=${sizeM}`, { signal }),
  climateProfile: (lat: number, lon: number, signal?: AbortSignal) =>
    apiGet<EngineEnvelope<Record<string, unknown>>>(`/api/engines/climate?lat=${lat}&lon=${lon}`, { signal }),
  environmentalProfile: (lat: number, lon: number, sizeM = 6000, signal?: AbortSignal) =>
    apiGet<EngineEnvelope<Record<string, unknown>>>(`/api/engines/environmental?lat=${lat}&lon=${lon}&size_m=${sizeM}`, { signal }),

  // Phase 6 Agriculture
  crops: (cropType?: string, system?: string, signal?: AbortSignal) => {
    const params = new URLSearchParams();
    if (cropType) params.set("crop_type", cropType);
    if (system) params.set("production_system", system);
    const qs = params.toString();
    return apiGet<{ count: number; crops: CropSummary[]; types?: string[] }>(
      `/api/agriculture/crops${qs ? `?${qs}` : ""}`,
      { signal, ttlMs: HOUR },
    );
  },
  cropDetail: (cropId: string, signal?: AbortSignal) =>
    apiGet<EngineEnvelope<CropDetail> & CropDetail>(`/api/agriculture/crops/${encodeURIComponent(cropId)}`, { signal, ttlMs: HOUR }),
  cropSuitability: (cropId: string, lat: number, lon: number, system = "rainfed", irrigationAvailable = false, signal?: AbortSignal) =>
    apiGet<EngineEnvelope<SuitabilityResult>>(
      `/api/agriculture/suitability?crop_id=${encodeURIComponent(cropId)}&lat=${lat}&lon=${lon}&system=${encodeURIComponent(system)}&irrigation_available=${irrigationAvailable}`,
      { signal },
    ),
  cropCalendar: (cropId: string, plantingDate?: string, signal?: AbortSignal) =>
    apiGet<EngineEnvelope<Record<string, unknown>>>(
      `/api/agriculture/calendar?crop_id=${encodeURIComponent(cropId)}${plantingDate ? `&planting_date=${encodeURIComponent(plantingDate)}` : ""}`,
      { signal },
    ),
  cropPhenology: (cropId: string, plantingDate: string, signal?: AbortSignal) =>
    apiGet<EngineEnvelope<Record<string, unknown>>>(
      `/api/agriculture/phenology?crop_id=${encodeURIComponent(cropId)}&planting_date=${encodeURIComponent(plantingDate)}`,
      { signal },
    ),
  simulationAdapters: (signal?: AbortSignal) =>
    apiGet<Record<string, unknown>>("/api/agriculture/adapters", { signal, ttlMs: HOUR }),
  simulateCrop: (body: Record<string, unknown>, signal?: AbortSignal) =>
    apiPost<EngineEnvelope<Record<string, unknown>>>("/api/agriculture/simulate", body, { signal }),
  nutrientDemand: (cropId: string, yieldTHa: number, yieldSource = "user_reference", signal?: AbortSignal) =>
    apiGet<EngineEnvelope<Record<string, unknown>>>(
      `/api/agriculture/nutrients?crop_id=${encodeURIComponent(cropId)}&yield_t_ha=${yieldTHa}&yield_source=${encodeURIComponent(yieldSource)}`,
      { signal },
    ),

  // Phase 6 Social / Socio (Nemotron)
  socialMeta: (signal?: AbortSignal) => apiGet<Record<string, unknown>>("/api/social/meta", { signal, ttlMs: HOUR }),
  nemotronProfiles: (department?: string, limit = 15, signal?: AbortSignal) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (department) params.set("department", department);
    return apiGet<Record<string, unknown>>(`/api/social/nemotron/agricultural?${params}`, { signal });
  },
  socioScenarios: (signal?: AbortSignal) => apiGet<Record<string, unknown>>("/api/socio/scenarios", { signal, ttlMs: HOUR }),
  runSocioScenario: (body: Record<string, unknown>, signal?: AbortSignal) =>
    apiPost<Record<string, unknown>>("/api/socio/scenario", body, { signal }),

  // Phase 7 Monitoring, Risks, Alerts, Onboarding
  monitoringMeta: (signal?: AbortSignal) => apiGet<Record<string, unknown>>("/api/monitoring/meta", { signal, ttlMs: HOUR }),
  monitoringSources: (signal?: AbortSignal) => apiGet<Record<string, unknown>>("/api/monitoring/sources", { signal, ttlMs: HOUR }),
  monitoringIndices: (signal?: AbortSignal) => apiGet<Record<string, unknown>>("/api/monitoring/indices", { signal, ttlMs: HOUR }),
  computeIndex: (body: Record<string, unknown>, signal?: AbortSignal) =>
    apiPost<Record<string, unknown>>("/api/monitoring/indices", body, { signal }),
  stacSearchPlan: (body: Record<string, unknown>, signal?: AbortSignal) =>
    apiPost<Record<string, unknown>>("/api/monitoring/satellite/search-plan", body, { signal }),
  monitoringStatus: (body: Record<string, unknown>, signal?: AbortSignal) =>
    apiPost<Record<string, unknown>>("/api/monitoring/status", body, { signal }),
  cropHealthAssess: (body: Record<string, unknown>, signal?: AbortSignal) =>
    apiPost<Record<string, unknown>>("/api/monitoring/crop-health", body, { signal }),
  pests: (crop?: string, signal?: AbortSignal) =>
    apiGet<Record<string, unknown>>(`/api/monitoring/pests${crop ? `?crop=${encodeURIComponent(crop)}` : ""}`, { signal, ttlMs: HOUR }),
  pestDetail: (pestId: string, signal?: AbortSignal) =>
    apiGet<Record<string, unknown>>(`/api/monitoring/pests/${encodeURIComponent(pestId)}`, { signal, ttlMs: HOUR }),
  diseases: (crop?: string, signal?: AbortSignal) =>
    apiGet<Record<string, unknown>>(`/api/monitoring/diseases${crop ? `?crop=${encodeURIComponent(crop)}` : ""}`, { signal, ttlMs: HOUR }),
  diseaseDetail: (diseaseId: string, signal?: AbortSignal) =>
    apiGet<Record<string, unknown>>(`/api/monitoring/diseases/${encodeURIComponent(diseaseId)}`, { signal, ttlMs: HOUR }),
  assessPestRisk: (body: Record<string, unknown>, signal?: AbortSignal) =>
    apiPost<Record<string, unknown>>("/api/monitoring/pest-risk", body, { signal }),
  assessDiseaseRisk: (body: Record<string, unknown>, signal?: AbortSignal) =>
    apiPost<Record<string, unknown>>("/api/monitoring/disease-risk", body, { signal }),
  assessDrought: (body: Record<string, unknown>, signal?: AbortSignal) =>
    apiPost<Record<string, unknown>>("/api/monitoring/drought", body, { signal }),
  assessFloodRisk: (body: Record<string, unknown>, signal?: AbortSignal) =>
    apiPost<Record<string, unknown>>("/api/monitoring/flood-risk", body, { signal }),
  assessHeatRisk: (body: Record<string, unknown>, signal?: AbortSignal) =>
    apiPost<Record<string, unknown>>("/api/monitoring/heat-risk", body, { signal }),
  assessSoilDegradation: (body: Record<string, unknown>, signal?: AbortSignal) =>
    apiPost<Record<string, unknown>>("/api/monitoring/soil-degradation", body, { signal }),
  assessCropLoss: (body: Record<string, unknown>, signal?: AbortSignal) =>
    apiPost<Record<string, unknown>>("/api/monitoring/crop-loss", body, { signal }),
  earlyWarning: (body: Record<string, unknown>, signal?: AbortSignal) =>
    apiPost<Record<string, unknown>>("/api/monitoring/early-warning", body, { signal }),
  alerts: (signal?: AbortSignal) =>
    apiGet<{ count: number; alerts: AlertItem[]; by_status: Record<string, number>; by_category: Record<string, number> }>(
      "/api/monitoring/alerts",
      { signal, persistOffline: true },
    ),
  createAlert: (body: Record<string, unknown>, signal?: AbortSignal) =>
    apiPost<Record<string, unknown>>("/api/monitoring/alerts", body, { signal }),
  verifyAlert: (alertId: string, body: Record<string, unknown>, signal?: AbortSignal) =>
    apiPost<Record<string, unknown>>(`/api/monitoring/alerts/${encodeURIComponent(alertId)}/verify`, body, { signal }),
  prioritizeAlerts: (body: Record<string, unknown> = {}, signal?: AbortSignal) =>
    apiPost<Record<string, unknown>>("/api/monitoring/alerts/prioritize", body, { signal }),
  transitionAlert: (alertId: string, status: string, reason: string, signal?: AbortSignal) =>
    apiPost<Record<string, unknown>>(`/api/monitoring/alerts/${encodeURIComponent(alertId)}/transition`, { status, reason }, { signal }),
  fieldObservations: (signal?: AbortSignal) =>
    apiGet<{ count: number; observations: FieldObservation[]; note?: string }>(
      "/api/monitoring/field-observations",
      { signal, persistOffline: true },
    ),
  submitFieldObservation: (body: Record<string, unknown>, signal?: AbortSignal) =>
    apiPost<FieldObservation>("/api/monitoring/field-observations", body, { signal }),
  crosswalkSummary: (signal?: AbortSignal) =>
    apiGet<Record<string, unknown>>("/api/onboarding/municipalities/summary", { signal, ttlMs: HOUR }),
  crosswalkLookup: (district: string, department?: string, signal?: AbortSignal) =>
    apiGet<Record<string, unknown>>(
      `/api/onboarding/municipalities/lookup?district=${encodeURIComponent(district)}${department ? `&department=${encodeURIComponent(department)}` : ""}`,
      { signal, persistOffline: false },
    ),

  // Phase 8 Economics
  productionStatistics: (cropId?: string, scale = "national", department?: string, signal?: AbortSignal) => {
    const params = new URLSearchParams({ scale });
    if (cropId) params.set("crop_id", cropId);
    if (department) params.set("department", department);
    return apiGet<EngineEnvelope<Record<string, unknown>>>(`/api/economics/production/statistics?${params}`, { signal, ttlMs: MIN_5 });
  },
  productionSystems: (signal?: AbortSignal) =>
    apiGet<EngineEnvelope<Record<string, unknown>>>("/api/economics/production/systems", { signal, ttlMs: HOUR }),
  aggregateCosts: (body: Record<string, unknown>, signal?: AbortSignal) =>
    apiPost<EngineEnvelope<Record<string, unknown>>>("/api/economics/costs/aggregate", body, { signal }),
  markets: (department?: string, namedOnly = false, limit = 150, signal?: AbortSignal) => {
    const params = new URLSearchParams({ limit: String(limit), named_only: String(namedOnly) });
    if (department) params.set("department", department);
    return apiGet<EngineEnvelope<{ count: number; total_catalog_size: number; markets: MarketItem[] }>>(
      `/api/economics/markets?${params}`,
      { signal, ttlMs: MIN_5 },
    );
  },
  prices: (opts?: { cropId?: string; market?: string; priceType?: string; targetUnit?: string; limit?: number }, signal?: AbortSignal) => {
    const params = new URLSearchParams({
      target_unit: opts?.targetUnit ?? "t",
      limit: String(opts?.limit ?? 100),
    });
    if (opts?.cropId) params.set("crop_id", opts.cropId);
    if (opts?.market) params.set("market", opts.market);
    if (opts?.priceType) params.set("price_type", opts.priceType);
    return apiGet<EngineEnvelope<{ available: boolean; count: number; target_unit: string; latest_observation_date: string | null; records: PriceRecord[]; reason?: string }>>(
      `/api/economics/prices?${params}`,
      { signal },
    );
  },
  priceHistory: (opts: { cropId?: string; market?: string; priceType?: string; targetUnit?: string }, signal?: AbortSignal) => {
    const params = new URLSearchParams({
      market: opts.market ?? "San Salvador",
      price_type: opts.priceType ?? "wholesale",
      target_unit: opts.targetUnit ?? "t",
    });
    if (opts.cropId) params.set("crop_id", opts.cropId);
    return apiGet<EngineEnvelope<Record<string, unknown>>>(`/api/economics/prices/history?${params}`, { signal });
  },
  logistics: (body: { lon: number; lat: number; crop_id: string; quantity_t?: number; transport_cost_per_t_km?: number }, signal?: AbortSignal) =>
    apiPost<EngineEnvelope<Record<string, unknown>>>("/api/economics/logistics", body, { signal }),
  profitability: (body: Record<string, unknown>, signal?: AbortSignal) =>
    apiPost<EngineEnvelope<Record<string, unknown>>>("/api/economics/profitability", body, { signal }),
  breakEven: (body: Record<string, unknown>, signal?: AbortSignal) =>
    apiPost<EngineEnvelope<Record<string, unknown>>>("/api/economics/break-even", body, { signal }),
  economicScenarios: (signal?: AbortSignal) =>
    apiGet<EngineEnvelope<{ count: number; scenarios: EconomicScenarioSpec[] }>>("/api/economics/scenarios", { signal, ttlMs: HOUR }),
  runEconomicScenario: (body: Record<string, unknown>, signal?: AbortSignal) =>
    apiPost<EngineEnvelope<Record<string, unknown>>>("/api/economics/scenarios/run", body, { signal }),
  valueChain: (body: Record<string, unknown>, signal?: AbortSignal) =>
    apiPost<EngineEnvelope<Record<string, unknown>>>("/api/economics/value-chain", body, { signal }),
  supplyChain: (body: { crop_id: string }, signal?: AbortSignal) =>
    apiPost<EngineEnvelope<Record<string, unknown>>>("/api/economics/supply-chain", body, { signal }),
  storage: (body: Record<string, unknown>, signal?: AbortSignal) =>
    apiPost<EngineEnvelope<Record<string, unknown>>>("/api/economics/storage", body, { signal }),
  marketCompare: (body: Record<string, unknown>, signal?: AbortSignal) =>
    apiPost<EngineEnvelope<Record<string, unknown>>>("/api/economics/markets/compare", body, { signal }),
  marketSupplyDemand: (body: Record<string, unknown>, signal?: AbortSignal) =>
    apiPost<EngineEnvelope<Record<string, unknown>>>("/api/economics/markets/supply-demand", body, { signal }),
  investment: (body: Record<string, unknown>, signal?: AbortSignal) =>
    apiPost<EngineEnvelope<Record<string, unknown>>>("/api/economics/investment", body, { signal }),
  householdEconomy: (body: Record<string, unknown> = {}, signal?: AbortSignal) =>
    apiPost<EngineEnvelope<Record<string, unknown>>>("/api/economics/household", body, { signal }),
  decisionSupport: (body: Record<string, unknown>, signal?: AbortSignal) =>
    apiPost<EngineEnvelope<Record<string, unknown>>>("/api/economics/decision-support", body, { signal }),
  economicAnalysis: (market = "San Salvador", signal?: AbortSignal) =>
    apiGet<EngineEnvelope<Record<string, unknown>>>(`/api/economics/analysis?market=${encodeURIComponent(market)}`, { signal, ttlMs: HOUR }),

};
