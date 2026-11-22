export const MANZANA_TO_HA = 0.7;
export const HA_TO_MANZANA = 1 / MANZANA_TO_HA;
export const KG_PER_QUINTAL_SV = 46;
export const KG_PER_TON = 1000;

export function fmtNum(
  value: number | string | null | undefined,
  digits = 1,
  unit = "",
): string {
  if (value === null || value === undefined || value === "") return "No disponible";
  if (typeof value === "number") {
    if (!Number.isFinite(value)) return "No disponible";
    return `${value.toLocaleString("es-SV", {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    })}${unit ? ` ${unit}` : ""}`;
  }
  return `${value}${unit ? ` ${unit}` : ""}`;
}

export function fmtUsd(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "No disponible";
  return `$${value.toLocaleString("es-SV", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })} USD`;
}

export function fmtCoord(lat: number, lon: number): string {
  return `${lat.toFixed(4)}° N, ${Math.abs(lon).toFixed(4)}° O`;
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "Sin fecha";
  return iso.slice(0, 10);
}

export function convertArea(value: number, from: "ha" | "mz", to: "ha" | "mz"): number {
  if (from === to) return value;
  return from === "mz" ? value * MANZANA_TO_HA : value * HA_TO_MANZANA;
}

export function convertMass(
  value: number,
  from: "kg" | "qq" | "t",
  to: "kg" | "qq" | "t",
): number {
  const toKg = { kg: 1, qq: KG_PER_QUINTAL_SV, t: KG_PER_TON };
  const kg = value * toKg[from];
  return kg / toKg[to];
}

export const EVIDENCE_LABELS: Record<string, { label: string; tone: "ok" | "info" | "warn" | "crit" | "unavailable" | "synthetic" }> = {
  observed: { label: "Observado en campo/estación", tone: "ok" },
  official_statistic: { label: "Estadística oficial", tone: "ok" },
  official_observed: { label: "Oficial observado", tone: "ok" },
  reanalysis: { label: "Reanálisis climático", tone: "info" },
  satellite_estimate: { label: "Estimación satelital", tone: "info" },
  satellite_derived: { label: "Derivado satelital", tone: "info" },
  modeled_prediction: { label: "Predicción modelada", tone: "warn" },
  model_estimate: { label: "Estimación de modelo", tone: "warn" },
  derived: { label: "Cálculo derivado", tone: "info" },
  forecast: { label: "Pronóstico", tone: "warn" },
  climate_projection: { label: "Proyección climática", tone: "warn" },
  simulated: { label: "Simulación", tone: "synthetic" },
  synthetic_scenario: { label: "Escenario sintético", tone: "synthetic" },
  field_observation: { label: "Observación comunitaria (no verificada)", tone: "warn" },
  producer_reported: { label: "Reportado por productor", tone: "info" },
  institutional_reference: { label: "Referencia institucional", tone: "info" },
  commercial_quotation: { label: "Cotización comercial", tone: "info" },
  hypothetical_assumption: { label: "Supuesto hipotético", tone: "synthetic" },
  unavailable: { label: "No disponible", tone: "unavailable" },
};

export const MONTH_NAMES_ES = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];
