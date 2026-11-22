import React, { useEffect, useState } from "react";
import { agrosvApi } from "../../services/api/endpoints";
import { useApp } from "../../stores/AppContext";
import { fmtCoord, fmtNum, MONTH_NAMES_ES } from "../../utils/format";
import { MetricCard, PageHeader } from "../../components/dashboard/MetricCard";
import {
  CacheNotice,
  DataStatusBadge,
  ErrorState,
  EvidenceBadge,
  LoadingState,
  SourceAttribution,
  UncertaintyPanel,
} from "../../components/data-status/DataStatus";
import { ChartFrame, SvgBarChart, SvgLineChart } from "../../components/charts/Charts";
import type { EngineEnvelope } from "../../types/api";

type TabId = "integrated" | "territorial" | "soil" | "hydrology" | "climate";

export default function TerritoryPage() {
  const { selectedLocation, setSelectedLocation, simpleMode } = useApp();
  const [tab, setTab] = useState<TabId>("integrated");
  const [latInput, setLatInput] = useState(String(selectedLocation.lat));
  const [lonInput, setLonInput] = useState(String(selectedLocation.lon));

  const [envEnv, setEnvEnv] = useState<EngineEnvelope<Record<string, unknown>> | null>(null);
  const [soilEnv, setSoilEnv] = useState<EngineEnvelope<Record<string, unknown>> | null>(null);
  const [hydroEnv, setHydroEnv] = useState<EngineEnvelope<Record<string, unknown>> | null>(null);
  const [climateEnv, setClimateEnv] = useState<EngineEnvelope<Record<string, unknown>> | null>(null);
  const [cachedAt, setCachedAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLatInput(selectedLocation.lat.toFixed(4));
    setLonInput(selectedLocation.lon.toFixed(4));
  }, [selectedLocation.lat, selectedLocation.lon]);

  useEffect(() => {
    const ac = new AbortController();
    setLoading(true);
    setError(null);
    Promise.allSettled([
      agrosvApi.environmentalProfile(selectedLocation.lat, selectedLocation.lon, 6000, ac.signal),
      agrosvApi.soilProfile(selectedLocation.lat, selectedLocation.lon, ac.signal),
      agrosvApi.hydrologyProfile(selectedLocation.lat, selectedLocation.lon, 6000, ac.signal),
      agrosvApi.climateProfile(selectedLocation.lat, selectedLocation.lon, ac.signal),
    ]).then(([e, s, h, c]) => {
      if (e.status === "fulfilled") {
        setEnvEnv(e.value.data);
        if (e.value.fromCache && e.value.cachedAt) setCachedAt(e.value.cachedAt);
      } else {
        setError(e.reason instanceof Error ? e.reason.message : "Error cargando perfil ambiental");
      }
      if (s.status === "fulfilled") setSoilEnv(s.value.data);
      if (h.status === "fulfilled") setHydroEnv(h.value.data);
      if (c.status === "fulfilled") setClimateEnv(c.value.data);
      setLoading(false);
    });
    return () => ac.abort();
  }, [selectedLocation.lat, selectedLocation.lon]);

  const applyCoords = (e: React.FormEvent) => {
    e.preventDefault();
    const lat = Number(latInput);
    const lon = Number(lonInput);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
    setSelectedLocation({
      lat,
      lon,
      label: `Coordenada (${lat.toFixed(3)}, ${lon.toFixed(3)})`,
    });
  };

  const env = (envEnv?.result ?? {}) as Record<string, unknown>;
  const ident = (env.identification ?? {}) as Record<string, Record<string, unknown> | undefined>;
  const terrain = (env.terrain ?? {}) as Record<string, unknown>;
  const dataCov = (env.data_coverage ?? {}) as Record<string, Record<string, unknown>>;
  const constraints = (env.environmental_constraints ?? []) as Array<{ code: string; rule: string; implication: string; domains?: string[] }>;

  const soil = (soilEnv?.result ?? {}) as Record<string, unknown>;
  const soilProps = (soil.properties ?? {}) as Record<string, { value: number | null; unit: string; label: string; available: boolean }>;
  const soilDerived = (soil.derived ?? {}) as Record<string, Record<string, unknown> | undefined>;
  const soilLimits = (soil.limitations_found ?? []) as Array<{ code: string; variable: string; value: number; threshold: unknown; implication: string }>;
  const soilMissing = (soil.not_available ?? {}) as Record<string, { reason?: string }>;

  const hydro = (hydroEnv?.result ?? {}) as Record<string, unknown>;
  const surfaceWater = (hydro.surface_water ?? {}) as Record<string, unknown>;
  const basin = (hydro.local_watershed ?? {}) as Record<string, unknown>;
  const wb = (hydro.water_balance ?? {}) as Record<string, unknown>;
  const wbMean = (wb.mean ?? {}) as Record<string, number | undefined>;
  const wbAnnual = (wb.annual ?? []) as Array<{ year: number; precipitation_mm: number; et0_mm: number; precipitation_minus_et0_mm: number }>;
  const gw = (hydro.groundwater ?? {}) as Record<string, unknown>;

  const clim = (climateEnv?.result ?? {}) as Record<string, unknown>;
  const climPoints = (clim.nearest_points ?? {}) as Record<string, Record<string, unknown>>;
  const seasonality = ((clim.seasonality as Record<string, unknown> | undefined)?.months ?? []) as Array<{
    month: number;
    precipitation_mm: number | null;
    temperature_mean_c: number | null;
    walter_lieth_humid: boolean | null;
  }>;
  const drought = (clim.drought_indicator ?? {}) as Record<string, unknown>;
  const etccdi = ((clim.extremes as Record<string, unknown> | undefined)?.years ?? []) as Array<Record<string, number | string>>;

  return (
    <div className="stack-md">
      <PageHeader
        title="Territorio y Recursos Ambientales (Fase 5)"
        subtitle={`Ubicación analizada: ${selectedLocation.label} · ${fmtCoord(selectedLocation.lat, selectedLocation.lon)}`}
        actions={
          <form onSubmit={applyCoords} className="row-wrap">
            <input className="input" style={{ width: 110 }} aria-label="Latitud" value={latInput} onChange={(e) => setLatInput(e.target.value)} />
            <input className="input" style={{ width: 115 }} aria-label="Longitud" value={lonInput} onChange={(e) => setLonInput(e.target.value)} />
            <button type="submit" className="btn btn-primary btn-sm">Actualizar punto</button>
          </form>
        }
      />

      <CacheNotice cachedAt={cachedAt} />
      {error && <ErrorState title="Error en consulta territorial" message={error} />}

      <div className="tabs" role="tablist" aria-label="Secciones ambientales">
        {([
          ["integrated", "Perfil integrado"],
          ["territorial", "Territorio y terreno"],
          ["soil", "Suelo (0–30 cm)"],
          ["hydrology", "Hidrología"],
          ["climate", "Clima (Reanálisis)"],
        ] as [TabId, string][]).map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={tab === id}
            className="tab-btn"
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </div>

      {loading && !envEnv ? (
        <LoadingState />
      ) : (
        <>
          {tab === "integrated" && (
            <div className="stack-md">
              <div className="callout callout--info">
                <strong>Sin índice ambiental compuesto:</strong> AGROSV no suma pendiente, pH y lluvia en un puntaje único porque no existen pesos validados en campo. Se presentan cada variable y las reglas de interacción detectadas.
              </div>

              <div className="grid-4">
                <MetricCard label="Departamento" value={String(ident.department?.name ?? "No disponible")} detail={`Municipio hist.: ${String(ident.municipality_historic?.name ?? "—")}`} evidenceClass="official_statistic" />
                <MetricCard label="Elevación / Pendiente" value={fmtNum(terrain.elevation_m as number, 0, "m")} detail={`Pendiente: ${fmtNum(terrain.slope_deg as number, 1, "°")}`} evidenceClass="modeled_prediction" />
                <MetricCard label="pH / Textura suelo" value={fmtNum(soilProps.ph?.value, 2)} detail={String(soilDerived.texture_class?.usda_class ?? "Sin clase")} evidenceClass="modeled_prediction" />
                <MetricCard label="Balance P − ET0" value={fmtNum(wbMean.precipitation_minus_et0_mm, 0, "mm/año")} detail={`Aridez P/ET0: ${fmtNum(wbMean.aridity_index_p_over_et0, 2)}`} evidenceClass="reanalysis" />
              </div>

              <div className="grid-2">
                <section className="card">
                  <h2 className="card-title">Reglas de interacción ambiental</h2>
                  {constraints.length > 0 ? (
                    <ul style={{ margin: "10px 0 0 18px", padding: 0, display: "grid", gap: 8, fontSize: 13.5 }}>
                      {constraints.map((c) => (
                        <li key={c.code}>
                          <strong>{c.rule}</strong>
                          <div style={{ color: "var(--ink-secondary)" }}>{c.implication}</div>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p style={{ color: "var(--ink-muted)", fontSize: 13.5 }}>No se activaron restricciones críticas con las reglas actuales.</p>
                  )}
                </section>

                <section className="card">
                  <h2 className="card-title">Cobertura real de datos en este punto</h2>
                  <div className="table-wrap" style={{ marginTop: 10 }}>
                    <table className="data-table">
                      <thead>
                        <tr><th>Componente</th><th>Estado</th><th>Detalle</th></tr>
                      </thead>
                      <tbody>
                        {Object.entries(dataCov).filter(([k]) => k !== "failed_components").map(([k, v]) => (
                          <tr key={k}>
                            <td><strong>{k}</strong></td>
                            <td>
                              <DataStatusBadge tone={v.available ? "ok" : "unavailable"} label={v.available ? "Disponible" : "No disponible"} />
                            </td>
                            <td style={{ fontSize: 12.5 }}>{String(v.note ?? v.reason ?? v.resolution ?? "—")}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              </div>

              <UncertaintyPanel
                collapsedByDefault={simpleMode}
                limitations={envEnv?.limitations}
                uncertainty={envEnv?.uncertainty}
              />
            </div>
          )}

          {tab === "territorial" && (
            <div className="stack-md">
              <div className="callout callout--warn">
                <strong>Nota sobre municipios:</strong> los polígonos municipales disponibles corresponden a los 262 municipios anteriores a la reforma territorial de 2023 (<code>official: false</code>). Consulta la correspondencia 2023 en <em>Datos e investigación</em>.
              </div>
              <div className="grid-2">
                <section className="card">
                  <h2 className="card-title">Identificación territorial</h2>
                  <dl className="kv-list" style={{ marginTop: 10 }}>
                    <div className="kv-row"><dt>País</dt><dd>{String(ident.country?.name ?? "El Salvador")}</dd></div>
                    <div className="kv-row"><dt>Departamento</dt><dd>{String(ident.department?.name ?? "No disponible")}</dd></div>
                    <div className="kv-row"><dt>Código ADM1</dt><dd className="mono">{String(ident.department?.source_code ?? "—")}</dd></div>
                    <div className="kv-row"><dt>Municipio histórico</dt><dd>{String(ident.municipality_historic?.name ?? "No disponible")}</dd></div>
                    <div className="kv-row"><dt>En tierra firme</dt><dd>{ident.inside_land ? "Sí" : "No"}</dd></div>
                  </dl>
                </section>
                <section className="card">
                  <h2 className="card-title">Morfometría del terreno (Copernicus DEM 30 m)</h2>
                  <dl className="kv-list" style={{ marginTop: 10 }}>
                    <div className="kv-row"><dt>Elevación</dt><dd>{fmtNum(terrain.elevation_m as number, 1, "m")}</dd></div>
                    <div className="kv-row"><dt>Pendiente</dt><dd>{fmtNum(terrain.slope_deg as number, 2, "°")}</dd></div>
                    <div className="kv-row"><dt>Orientación (Aspect)</dt><dd>{fmtNum(terrain.aspect_deg as number, 1, "°")}</dd></div>
                    <div className="kv-row"><dt>TRI (rugosidad)</dt><dd>{fmtNum(terrain.tri_m as number, 2, "m")}</dd></div>
                    <div className="kv-row"><dt>TPI (posición topográfica)</dt><dd>{fmtNum(terrain.tpi_m as number, 2, "m")}</dd></div>
                  </dl>
                  <SourceAttribution sources={["Copernicus DEM GLO-30 (DSM ~30 m)"]} />
                </section>
              </div>
            </div>
          )}

          {tab === "soil" && (
            <div className="stack-md">
              <div className="callout callout--warn">
                <strong>Predicción global SoilGrids 2.0 (250 m, 0–30 cm):</strong> son estimaciones modeladas, no análisis de laboratorio ni cartografía nacional CENTA.
              </div>
              <div className="grid-3">
                {Object.entries(soilProps).map(([k, p]) => (
                  <MetricCard
                    key={k}
                    label={p.label}
                    value={fmtNum(p.value, 2)}
                    unit={p.unit}
                    evidenceClass={p.available ? "modeled_prediction" : "unavailable"}
                  />
                ))}
              </div>
              <div className="grid-2">
                <section className="card">
                  <h2 className="card-title">Textura USDA y limitaciones detectadas</h2>
                  <p style={{ fontSize: 13.5 }}>
                    Clase textural derivada: <strong>{String(soilDerived.texture_class?.usda_class ?? "No disponible")}</strong>
                    {" · "}Materia orgánica estimada: <strong>{fmtNum(soilDerived.organic_matter?.value as number, 2, "%")}</strong>
                  </p>
                  {soilLimits.length > 0 ? (
                    <ul style={{ margin: "8px 0 0 18px", padding: 0, fontSize: 13 }}>
                      {soilLimits.map((l) => (
                        <li key={l.code}><strong>{l.variable}</strong> ({l.value}): {l.implication}</li>
                      ))}
                    </ul>
                  ) : (
                    <p style={{ fontSize: 13, color: "var(--ink-muted)" }}>Sin alertas de umbral SoilEngine en esta celda.</p>
                  )}
                </section>
                <section className="card">
                  <h2 className="card-title">Variables de suelo NO disponibles</h2>
                  <p className="card-subtitle">No se extrapolan ni se imputan horizontes profundos</p>
                  <ul style={{ margin: "10px 0 0 18px", padding: 0, fontSize: 12.5, display: "grid", gap: 4 }}>
                    {Object.entries(soilMissing).map(([k, info]) => (
                      <li key={k}><span className="mono">{k}</span>: {info?.reason ?? "No disponible en el repositorio"}</li>
                    ))}
                  </ul>
                </section>
              </div>
              <UncertaintyPanel collapsedByDefault={simpleMode} limitations={soilEnv?.limitations} />
            </div>
          )}

          {tab === "hydrology" && (
            <div className="stack-md">
              <div className="callout callout--info">
                <strong>Proximidad ≠ disponibilidad:</strong> estar cerca de un río mapeado en OSM no significa que tenga caudal permanente, agua aprovechable ni concesión autorizada.
              </div>
              <div className="grid-3">
                <MetricCard
                  label="Cauce más cercano (OSM)"
                  value={fmtNum((surfaceWater.nearest_any as Record<string, number> | undefined)?.distance_km, 2, "km")}
                  detail={String((surfaceWater.nearest_any as Record<string, string> | undefined)?.name ?? "Sin nombre en OSM")}
                  evidenceClass="observed"
                />
                <MetricCard
                  label="Cuenca local D8 (DEM 30 m)"
                  value={fmtNum(basin.upstream_area_km2 as number, 2, "km²")}
                  detail={basin.truncated ? "Truncada por borde de ventana" : "Contenida en ventana de 6 km"}
                  evidenceClass="derived"
                />
                <MetricCard
                  label="Escorrentía Budyko (ω=2.0)"
                  value={fmtNum(wbMean.budyko_runoff_mm, 0, "mm/año")}
                  detail="Cota macroclimática no calibrada (V0)"
                  evidenceClass="modeled_prediction"
                />
              </div>

              {wbAnnual.length > 0 && (
                <ChartFrame
                  title="Balance hídrico climático anual (P vs ET0)"
                  unit="mm/año"
                  dateRange={`${wbAnnual[0].year}–${wbAnnual[wbAnnual.length - 1].year}`}
                  source="Open-Meteo / NASA POWER (reanálisis)"
                  methodology="Diferencia anual P − ET0; sin almacenamiento de suelo"
                  rows={wbAnnual.map((r) => ({
                    Año: r.year,
                    "Precipitación (mm)": r.precipitation_mm,
                    "ET0 (mm)": r.et0_mm,
                    "P − ET0 (mm)": r.precipitation_minus_et0_mm,
                  }))}
                >
                  <SvgLineChart
                    data={wbAnnual.map((r) => ({
                      label: String(r.year),
                      value: r.precipitation_mm,
                      secondary: r.et0_mm,
                    }))}
                    unit="mm"
                    primaryLabel="Precipitación anual (mm)"
                    secondaryLabel="ET0 anual (mm)"
                    startAtZero
                  />
                </ChartFrame>
              )}

              <section className="card">
                <div className="row-wrap" style={{ justifyContent: "space-between" }}>
                  <h2 className="card-title">Agua subterránea y acuíferos</h2>
                  <EvidenceBadge evidenceClass="unavailable" />
                </div>
                <p style={{ fontSize: 13.5, color: "var(--ink-secondary)", marginTop: 8 }}>
                  {String(gw.note ?? "Sin datos de acuíferos, niveles piezométricos ni derechos de agua en el repositorio.")}
                </p>
              </section>
              <UncertaintyPanel collapsedByDefault={simpleMode} limitations={hydroEnv?.limitations} />
            </div>
          )}

          {tab === "climate" && (
            <div className="stack-md">
              <div className="callout callout--warn">
                <strong>Reanálisis 2019–2025 (no es estación SNET/MARN ni pronóstico):</strong> no se interpola entre puntos; se muestran los puntos climáticos integrados y la distancia a tu coordenada.
              </div>
              <div className="grid-3">
                {Object.entries(climPoints).map(([ds, info]) => (
                  <MetricCard
                    key={ds}
                    label={`Punto ${ds}`}
                    value={fmtNum(info.distance_km as number, 1, "km")}
                    detail={`${String(info.start)} a ${String(info.end)} (${String(info.n)} días)`}
                    evidenceClass="reanalysis"
                  />
                ))}
                <MetricCard
                  label="Indicador sequía 3 meses"
                  value={`${fmtNum(drought.percentile as number, 1, "%ile")}`}
                  detail={`Categoría: ${String(drought.category ?? "—")} (${String(drought.latest_window_end ?? "")})`}
                  evidenceClass="reanalysis"
                />
              </div>

              {seasonality.length > 0 && (
                <div className="grid-2">
                  <ChartFrame
                    title="Estacionalidad mensual de precipitación (2019–2025)"
                    unit="mm/mes"
                    dateRange="2019–2025"
                    source="Open-Meteo (reanálisis)"
                    rows={seasonality.map((m) => ({
                      Mes: MONTH_NAMES_ES[m.month - 1],
                      "Precipitación media (mm)": m.precipitation_mm,
                      "Temp media (°C)": m.temperature_mean_c,
                    }))}
                  >
                    <SvgBarChart
                      data={seasonality.map((m) => ({
                        label: MONTH_NAMES_ES[m.month - 1].slice(0, 3),
                        value: m.precipitation_mm,
                      }))}
                      unit="mm"
                      color="var(--domain-water)"
                    />
                  </ChartFrame>

                  <ChartFrame
                    title="Temperatura media mensual (2019–2025)"
                    unit="°C"
                    dateRange="2019–2025"
                    source="NASA POWER (reanálisis)"
                    rows={seasonality.map((m) => ({
                      Mes: MONTH_NAMES_ES[m.month - 1],
                      "Temp media (°C)": m.temperature_mean_c,
                    }))}
                  >
                    <SvgLineChart
                      data={seasonality.map((m) => ({
                        label: MONTH_NAMES_ES[m.month - 1].slice(0, 3),
                        value: m.temperature_mean_c,
                      }))}
                      unit="°C"
                      primaryLabel="Temperatura media mensual (°C)"
                    />
                  </ChartFrame>
                </div>
              )}

              {etccdi.length > 0 && (
                <section className="card">
                  <h2 className="card-title">Índices ETCCDI anuales</h2>
                  <div className="table-wrap" style={{ marginTop: 10 }}>
                    <table className="data-table">
                      <thead>
                        <tr><th>Año</th><th>PRCPTOT (mm)</th><th>Rx1day (mm)</th><th>Rx5day (mm)</th><th>CDD (días secos)</th><th>CWD (días húmedos)</th></tr>
                      </thead>
                      <tbody>
                        {etccdi.map((row) => (
                          <tr key={String(row.year)}>
                            <td className="tabular-nums"><strong>{String(row.year)}</strong></td>
                            <td className="tabular-nums">{fmtNum(row.prcptot as number, 1)}</td>
                            <td className="tabular-nums">{fmtNum(row.rx1day as number, 1)}</td>
                            <td className="tabular-nums">{fmtNum(row.rx5day as number, 1)}</td>
                            <td className="tabular-nums">{fmtNum(row.cdd as number, 0)}</td>
                            <td className="tabular-nums">{fmtNum(row.cwd as number, 0)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              )}

              <UncertaintyPanel collapsedByDefault={simpleMode} limitations={climateEnv?.limitations} />
            </div>
          )}
        </>
      )}
    </div>
  );
}
