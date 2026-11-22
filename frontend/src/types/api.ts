export type EvidenceClass =
  | "observed"
  | "official_statistic"
  | "official_observed"
  | "reanalysis"
  | "satellite_estimate"
  | "satellite_derived"
  | "modeled_prediction"
  | "model_estimate"
  | "derived"
  | "forecast"
  | "climate_projection"
  | "simulated"
  | "synthetic_scenario"
  | "field_observation"
  | "producer_reported"
  | "institutional_reference"
  | "commercial_quotation"
  | "hypothetical_assumption"
  | "unavailable";

export interface HealthResponse {
  status: "ok" | "degraded";
  missing: string[];
  version: string;
}

export interface DeptFeatureProps {
  adm1_code: string;
  name: string;
  area_km2: number;
}

export interface GeoJsonFeature<P = Record<string, unknown>> {
  type: "Feature";
  properties: P;
  geometry: unknown;
}

export interface GeoJsonCollection<P = Record<string, unknown>> {
  type: "FeatureCollection";
  features: GeoJsonFeature<P>[];
  metadata?: Record<string, unknown>;
}

export interface DeptDetail {
  code: string;
  name: string;
  area_km2: number;
  topography: Record<string, number | string>;
  soils: Record<string, number | string>;
  geometry: unknown;
}

export interface EngineEnvelope<T = Record<string, unknown>> {
  engine: string;
  engine_version: string;
  generated_at?: string;
  timestamp_utc?: string;
  evidence_class?: EvidenceClass;
  synthetic?: boolean;
  llm_used?: boolean;
  query?: Record<string, unknown>;
  result: T;
  sources?: Array<Record<string, unknown> | string>;
  assumptions?: string[];
  limitations?: string[];
  coverage?: Record<string, unknown>;
  processing_history?: Array<Record<string, unknown>>;
  uncertainty?: Record<string, unknown>;
  uncertainty_policy?: Record<string, unknown>;
  cache?: { hit: boolean; key?: string };
}

export interface CropParam<T = unknown> {
  value: T | null;
  unit: string;
  status: "REF" | "NAC" | "GAP" | "MODEL_DERIVED" | "SCENARIO";
  source: string | null;
  note: string | null;
}

export interface CropSummary {
  crop_id: string;
  scientific_name: string;
  local_names: string[];
  crop_type: string;
  lifecycle: string;
  cycle_days: CropParam<[number, number]>;
  parameter_status: Record<string, number>;
}

export interface CropDetail {
  crop_id: string;
  scientific_name: string;
  local_names: string[];
  family: string;
  crop_type: string;
  lifecycle: string;
  growth_habit: string;
  cycle_days: CropParam<[number, number]>;
  temperature: Record<string, CropParam>;
  water: Record<string, CropParam>;
  soil: Record<string, CropParam>;
  nutrition: Record<string, CropParam>;
  kc: CropParam;
  planting_months: CropParam;
  yield_data: Record<string, CropParam>;
  pests: string[];
  diseases: string[];
  production_systems: string[];
  sources: Array<Record<string, unknown> | string>;
  confidence: string;
  gaps: string[];
  varieties?: Array<Record<string, unknown>>;
}

export interface SuitabilityFactor {
  factor: string;
  value: unknown;
  unit: string;
  thresholds: unknown;
  rating: "none" | "moderate" | "severe" | "not_evaluated" | null;
  critical: boolean;
  note: string | null;
}

export interface SuitabilityResult {
  crop_id: string;
  system: string;
  class: "S1" | "S2" | "S3" | "N" | "not_evaluated";
  class_label: string;
  limiting_factors: string[];
  factors: SuitabilityFactor[];
  growing_window_months?: number[];
  confidence?: string;
}

export interface AlertItem {
  alert_id: string;
  category: string;
  geographic_scope: Record<string, unknown>;
  crop_id: string | null;
  detected_at: string;
  observation_period: Record<string, string>;
  source_datasets: string[];
  detection_method: string;
  risk_level: "low" | "moderate" | "high" | "very_high";
  evidence: Array<Record<string, unknown>>;
  evidence_class: EvidenceClass;
  confidence: string;
  uncertainty: string | null;
  recommended_verification: string;
  expires_at: string;
  status: string;
  history: Array<Record<string, unknown>>;
  verification_events: Array<Record<string, unknown>>;
}

export interface FieldObservation {
  observation_id: string;
  observation_type: string;
  latitude: number;
  longitude: number;
  observed_on: string;
  crop_id: string | null;
  crop_stage: string | null;
  severity: string | null;
  notes: string | null;
  photos: string[];
  contributor_id: string;
  contributor_type: string;
  status: string;
  warnings: string[];
  evidence_class: "field_observation";
  verified_scientific_record: boolean;
  submitted_at: string;
}

export interface MarketItem {
  market_id: string;
  name: string;
  department: string | null;
  municipality: string | null;
  latitude: number | null;
  longitude: number | null;
  market_type: string;
  products_traded: string[];
  infrastructure: string;
  source: string;
  verification_status: string;
  last_verification_date: string;
}

export interface PriceRecord {
  record_id: string;
  product_or_activity: string;
  geography: string;
  observation_date: string;
  reference_period: string;
  currency: string;
  unit: string;
  value: number;
  source: string;
  methodology: string;
  verification_status: string;
  evidence_class: EvidenceClass;
  crop_id: string | null;
  price_type: string;
  market: string;
  department: string | null;
  normalized_price: number;
  normalized_unit: string;
  normalized_usd_per_kg: number | null;
  normalized_usd_per_qq46: number | null;
  normalized_usd_per_t: number | null;
}

export interface EconomicScenarioSpec {
  scenario_id: string;
  label: string;
  description?: string;
  changes: Record<string, number>;
}
