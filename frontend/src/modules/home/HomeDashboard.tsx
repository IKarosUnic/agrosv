import { useEffect, useState } from "react";
import type { RouteId } from "../../app/routes";
import { agrosvApi } from "../../services/api/endpoints";
import { useApp } from "../../stores/AppContext";
import { fmtCoord, fmtNum } from "../../utils/format";
import { MetricCard, PageHeader } from "../../components/dashboard/MetricCard";
import {
  CacheNotice,
  DataStatusBadge,
  ErrorState,
  EvidenceBadge,
  LoadingState,
  SourceAttribution,
} from "../../components/data-status/DataStatus";
import type { AlertItem, DeptFeatureProps, HealthResponse } from "../../types/api";

export function HomeDashboard({ onNavigate }: { onNavigate: (id: RouteId) => void }) {
  const { selectedLocation, setSelectedLocation, selectedCropId, simpleMode, roleProfile, setRoleProfile } = useApp();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [depts, setDepts] = useState<DeptFeatureProps[]>([]);
  const [envData, setEnvData] = useState<Record<string, unknown> | null>(null);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [capStats, setCapStats] = useState<Array<Record<string, unknown>>>([]);
  const [wbLand, setWbLand] = useState<Record<string, unknown> | null>(null);
  const [cachedAt, setCachedAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const ac = new AbortController();
    setLoading(true);
    setError(null);
    Promise.allSettled([
      agrosvApi.health(ac.signal),
      agrosvApi.departments(0.005, ac.signal),
      agrosvApi.environmentalProfile(selectedLocation.lat, selectedLocation.lon, 6000, ac.signal),
      agrosvApi.alerts(ac.signal),
      agrosvApi.productionStatistics(undefined, "national", undefined, ac.signal),
    ]).then(([h, d, env, al, st]) => {
      if (h.status === "fulfilled") setHealth(h.value.data);
      if (d.status === "fulfilled") {
        const list = (d.value.data.features ?? []).map((f) => f.properties);
        setDepts(list.sort((a, b) => a.name.localeCompare(b.name)));
      }
      if (env.status === "fulfilled") {
        setEnvData(env.value.data.result);
        if (env.value.fromCache && env.value.cachedAt) setCachedAt(env.value.cachedAt);
      } else {
        setEnvData(null);
      }
      if (al.status === "fulfilled") setAlerts(al.value.data.alerts ?? []);
      if (st.status === "fulfilled") {
        const r = st.value.data.result as {
          cap_2025_records?: Array<Record<string, unknown>>;
          worldbank_agricultural_land_pct?: Record<string, unknown>;
        };
        setCapStats(r.cap_2025_records ?? []);
        setWbLand(r.worldbank_agricultural_land_pct ?? null);
      }
      if (h.status === "rejected" && d.status === "rejected" && env.status === "rejected") {
        setError("No se pudieron cargar los servicios base de AGROSV.");
      }
      setLoading(false);
    });
    return () => ac.abort();
  }, [selectedLocation.lat, selectedLocation.lon]);

  const terrain = (envData?.terrain ?? {}) as Record<string, unknown>;
  const soilProps = ((envData?.soil as Record<string, unknown> | undefined)?.properties ?? {}) as Record<string, { value?: number | null; unit?: string }>;
  const climate = (envData?.climate ?? {}) as Record<string, unknown>;
  const hydro = (envData?.hydrology as Record<string, unknown> | undefined)?.water_balance as Record<string, unknown> | undefined;
  const hydroMean = (hydro?.mean ?? {}) as Record<string, number | undefined>;
  const ident = (envData?.identification ?? {}) as Record<string, { name?: string } | undefined>;
  const constraints = (envData?.environmental_constraints ?? []) as Array<{ code: string; rule: string; implication: string }>;

  const DEPT_COORDS: Record<string, { lat: number; lon: number }> = {
    "SLV-AH": { lat: 13.92, lon: -89.84 },
    "SLV-CA": { lat: 13.87, lon: -88.74 },
    "SLV-CH": { lat: 14.04, lon: -88.94 },
    "SLV-CU": { lat: 13.73, lon: -89.03 },
    "SLV-LI": { lat: 13.68, lon: -89.31 },
    "SLV-MO": { lat: 13.77, lon: -88.12 },
    "SLV-PA": { lat: 13.50, lon: -88.97 },
    "SLV-SA": { lat: 13.99, lon: -89.55 },
    "SLV-SM": { lat: 13.48, lon: -88.18 },
    "SLV-SO": { lat: 13.72, lon: -89.72 },
    "SLV-SS": { lat: 13.69, lon: -89.19 },
    "SLV-SV": { lat: 13.64, lon: -88.78 },
    "SLV-UN": { lat: 13.54, lon: -87.84 },
    "SLV-US": { lat: 13.35, lon: -88.45 },
  };

  return (
    <div className="stack-md">
      <PageHeader
        title="Panorama Agrícola de El Salvador"
        subtitle={
          simpleMode
            ? "Consulta las condiciones de tu zona, revisa alertas y calcula costos o rentabilidad con datos reales."
            : "Panel integrado de inteligencia territorial, ambiental, fitosanitaria y económica (Fases 1–8)."
        }
        actions={
          <>
            <button type="button" className="btn btn-primary" onClick={() => onNavigate("map")}>
              Explorar mapa agrícola
            </button>
            <button type="button" className="btn" onClick={() => onNavigate("crops")}>
              Evaluar cultivo ({selectedCropId})
            </button>
          </>
        }
      />

      <CacheNotice cachedAt={cachedAt} />
      {error && <ErrorState message={error} />}

      {/* Selector geográfico rápido */}
      <section className="card" aria-labelledby="home-loc-title">
        <div className="card-header">
          <div>
            <h2 id="home-loc-title" className="card-title">Ubicación de análisis</h2>
            <div className="card-subtitle">
              {ident.department?.name ? `${ident.department.name}` : selectedLocation.label}
              {ident.municipality_historic?.name ? ` · Municipio histórico: ${ident.municipality_historic.name}` : ""}
              {" · "}
              <span className="tabular-nums">{fmtCoord(selectedLocation.lat, selectedLocation.lon)}</span>
            </div>
          </div>
          <DataStatusBadge
            tone={health?.status === "ok" ? "ok" : "warn"}
            label={health ? `API ${health.status === "ok" ? "operativa" : "degradada"} (v${health.version})` : "Verificando API"}
          />
        </div>

        <div className="row-wrap">
          <label className="field" style={{ minWidth: 240, flex: "1 1 240px" }}>
            <span className="field-label">Cambiar por departamento</span>
            <select
              className="select"
              value={selectedLocation.departmentCode ?? ""}
              onChange={(e) => {
                const code = e.target.value;
                const found = depts.find((d) => d.adm1_code === code);
                const coords = DEPT_COORDS[code];
                if (found && coords) {
                  setSelectedLocation({
                    lat: coords.lat,
                    lon: coords.lon,
                    label: `${found.name} (punto de referencia)`,
                    departmentCode: found.adm1_code,
                    departmentName: found.name,
                  });
                }
              }}
            >
              <option value="">Seleccionar departamento…</option>
              {depts.map((d) => (
                <option key={d.adm1_code} value={d.adm1_code}>
                  {d.name} ({d.area_km2.toFixed(0)} km²)
                </option>
              ))}
            </select>
          </label>
          <button type="button" className="btn" onClick={() => onNavigate("map")} style={{ alignSelf: "flex-end" }}>
            Elegir punto exacto en el mapa
          </button>
          <button type="button" className="btn" onClick={() => onNavigate("territory")} style={{ alignSelf: "flex-end" }}>
            Ver perfil ambiental completo
          </button>
        </div>
      </section>

      {/* Condiciones ambientales del punto activo */}
      {loading && !envData ? (
        <LoadingState message="Cargando condiciones ambientales y estadísticas disponibles…" />
      ) : (
        <section aria-labelledby="home-cond-title">
          <h2 id="home-cond-title" style={{ margin: "0 0 10px", fontSize: 16 }}>
            Condiciones ambientales en el punto seleccionado
          </h2>
          <div className="grid-4">
            <MetricCard
              label="Elevación (DEM 30 m)"
              value={fmtNum(terrain.elevation_m as number, 0)}
              unit="m s.n.m."
              detail={`Pendiente: ${fmtNum(terrain.slope_deg as number, 1, "°")}`}
              evidenceClass="modeled_prediction"
              date="2021"
            />
            <MetricCard
              label="pH del suelo (0–30 cm)"
              value={fmtNum(soilProps.ph?.value, 2)}
              detail={`Arcilla: ${fmtNum(soilProps.clay?.value, 1, "%")} · C org: ${fmtNum(soilProps.soil_organic_carbon?.value, 1, "g/kg")}`}
              evidenceClass="modeled_prediction"
              date="SoilGrids 250 m"
            />
            <MetricCard
              label="Balance climático anual"
              value={fmtNum(hydroMean.precipitation_mm, 0)}
              unit="mm P / año"
              detail={`ET0: ${fmtNum(hydroMean.et0_mm, 0, "mm")} · P−ET0: ${fmtNum(hydroMean.precipitation_minus_et0_mm, 0, "mm")}`}
              evidenceClass="reanalysis"
              date="2019–2025"
            />
            <MetricCard
              label="Alertas activas en sesión"
              value={String(alerts.length)}
              detail={
                alerts.length > 0
                  ? `${alerts[0].category} (${alerts[0].risk_level})`
                  : "Sin alertas generadas en esta sesión"
              }
              evidenceClass={alerts.length > 0 ? alerts[0].evidence_class : "unavailable"}
            />
          </div>
          <SourceAttribution
            sources={["Copernicus DEM GLO-30", "SoilGrids 2.0", "Open-Meteo / NASA POWER (reanálisis)"]}
            resolution="30 m (relieve) · 250 m (suelo) · punto cercano (clima)"
          />
        </section>
      )}

      {/* Restricciones o hallazgos ambientales */}
      {constraints.length > 0 && (
        <section className="card" aria-labelledby="home-const-title">
          <h2 id="home-const-title" className="card-title">Señales y limitaciones ambientales detectadas</h2>
          <ul style={{ margin: "10px 0 0 18px", padding: 0, display: "grid", gap: 6, fontSize: 13.5 }}>
            {constraints.slice(0, simpleMode ? 3 : 8).map((c) => (
              <li key={c.code}>
                <strong>{c.rule}</strong> — <span style={{ color: "var(--ink-secondary)" }}>{c.implication}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Producción nacional verificada + Acciones principales */}
      <div className="grid-2">
        <section className="card" aria-labelledby="home-prod-title">
          <div className="card-header">
            <div>
              <h2 id="home-prod-title" className="card-title">Estadísticas nacionales disponibles</h2>
              <div className="card-subtitle">V Censo Agropecuario 2025 (entregas públicas) y Banco Mundial</div>
            </div>
            <EvidenceBadge evidenceClass="official_statistic" />
          </div>
          {capStats.length > 0 ? (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Rubro</th>
                    <th>Superficie</th>
                    <th>Producción</th>
                    <th>Periodo</th>
                  </tr>
                </thead>
                <tbody>
                  {capStats.slice(0, 5).map((row) => {
                    const val = (row.value ?? {}) as Record<string, unknown>;
                    return (
                      <tr key={String(row.record_id)}>
                        <td><strong>{String(val.crop_name_es ?? row.product_or_activity)}</strong></td>
                        <td className="tabular-nums">{fmtNum(val.harvested_area_mz as number, 0, "mz")}</td>
                        <td className="tabular-nums">{fmtNum(val.production_qq as number, 0, "qq")}</td>
                        <td className="tabular-nums">{String(row.reference_period)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <p style={{ fontSize: 13.5, color: "var(--ink-muted)" }}>
              No hay agregados CAP cargados en este entorno.
            </p>
          )}
          {wbLand && (
            <div style={{ marginTop: 10, fontSize: 12.5, color: "var(--ink-secondary)" }}>
              Banco Mundial (<span className="mono">{String(wbLand.indicator)}</span>, {String(wbLand.year)}):{" "}
              <strong>{fmtNum(wbLand.value_pct as number, 1, "%")}</strong> tierra agrícola del territorio nacional.
            </div>
          )}
        </section>

        <section className="card" aria-labelledby="home-next-title">
          <div className="card-header">
            <div>
              <h2 id="home-next-title" className="card-title">Flujos guiados por perfil</h2>
              <div className="card-subtitle">
                Experiencia para {roleProfile === "farmer" ? "Productor / Agricultor" : roleProfile === "technician" ? "Técnico agrícola" : roleProfile === "researcher" ? "Investigador / Estudiante" : "Institucional"}
              </div>
            </div>
            <select
              className="select"
              style={{ width: "auto" }}
              aria-label="Perfil de usuario"
              value={roleProfile}
              onChange={(e) => setRoleProfile(e.target.value as "farmer" | "technician" | "researcher" | "institutional")}
            >
              <option value="farmer">Productor / Agricultor</option>
              <option value="technician">Técnico agrícola</option>
              <option value="researcher">Investigador / Estudiante</option>
              <option value="institutional">Institucional / Directivo</option>
            </select>
          </div>

          <div className="stack-sm" style={{ marginTop: 10 }}>
            {roleProfile === "farmer" && (
              <>
                <button type="button" className="btn" style={{ justifyContent: "space-between" }} onClick={() => onNavigate("crops")}>
                  <span>1. ¿Qué tan apto es mi cultivo ({selectedCropId}) en esta parcela?</span>
                  <span className="badge badge--info">Aptitud</span>
                </button>
                <button type="button" className="btn" style={{ justifyContent: "space-between" }} onClick={() => onNavigate("calendar")}>
                  <span>2. Consultar fecha de siembra y fases fenológicas</span>
                  <span className="badge badge--info">Calendario</span>
                </button>
                <button type="button" className="btn" style={{ justifyContent: "space-between" }} onClick={() => onNavigate("production")}>
                  <span>3. Calcular presupuesto de costos en manzanas o quintales</span>
                  <span className="badge badge--ok">Costos</span>
                </button>
                <button type="button" className="btn" style={{ justifyContent: "space-between" }} onClick={() => onNavigate("markets")}>
                  <span>4. ¿En qué mercado WFP me pagan mejor (retorno neto con flete)?</span>
                  <span className="badge badge--ok">Mercados</span>
                </button>
                <button type="button" className="btn" style={{ justifyContent: "space-between" }} onClick={() => onNavigate("profitability")}>
                  <span>5. Evaluar ganancias, punto de equilibrio y balance familiar</span>
                  <span className="badge badge--ok">Finanzas</span>
                </button>
                <button type="button" className="btn" style={{ justifyContent: "space-between" }} onClick={() => onNavigate("monitoring")}>
                  <span>6. Registrar una observación o sospecha de plaga en campo</span>
                  <span className="badge badge--warn">Campo</span>
                </button>
              </>
            )}

            {roleProfile === "technician" && (
              <>
                <button type="button" className="btn" style={{ justifyContent: "space-between" }} onClick={() => onNavigate("monitoring")}>
                  <span>1. Monitoreo fitosanitario: evaluar índice de riesgo de plagas/enfermedades</span>
                  <span className="badge badge--warn">Fitosanitario</span>
                </button>
                <button type="button" className="btn" style={{ justifyContent: "space-between" }} onClick={() => onNavigate("risks")}>
                  <span>2. Evaluar motores de sequía, exceso hídrico, calor y degradación</span>
                  <span className="badge badge--warn">Riesgos</span>
                </button>
                <button type="button" className="btn" style={{ justifyContent: "space-between" }} onClick={() => onNavigate("crops")}>
                  <span>3. Balance hídrico de ciclo FAO-56 y cálculo nutricional N-P-K</span>
                  <span className="badge badge--info">Cultivos</span>
                </button>
                <button type="button" className="btn" style={{ justifyContent: "space-between" }} onClick={() => onNavigate("markets")}>
                  <span>4. Mapeo de cadena de suministro y parámetros de almacenamiento poscosecha</span>
                  <span className="badge badge--ok">Cadenas</span>
                </button>
                <button type="button" className="btn" style={{ justifyContent: "space-between" }} onClick={() => onNavigate("profitability")}>
                  <span>5. Análisis financiero de inversiones (riego por goteo, reservorio, silos)</span>
                  <span className="badge badge--ok">Inversión</span>
                </button>
              </>
            )}

            {roleProfile === "researcher" && (
              <>
                <button type="button" className="btn" style={{ justifyContent: "space-between" }} onClick={() => onNavigate("territory")}>
                  <span>1. Perfil ambiental decadal ERA5, SoilGrids 250m y Copernicus DEM 30m</span>
                  <span className="badge badge--info">Territorio</span>
                </button>
                <button type="button" className="btn" style={{ justifyContent: "space-between" }} onClick={() => onNavigate("scenarios")}>
                  <span>2. Simular escenarios socioeconómicos con agentes sintéticos Nemotron</span>
                  <span className="badge badge--info">Nemotron</span>
                </button>
                <button type="button" className="btn" style={{ justifyContent: "space-between" }} onClick={() => onNavigate("research")}>
                  <span>3. Consultar catálogo de datos científicos, QC y trazabilidad SHA-256</span>
                  <span className="badge badge--primary">Catálogo</span>
                </button>
                <button type="button" className="btn" style={{ justifyContent: "space-between" }} onClick={() => onNavigate("crops")}>
                  <span>4. Simulación agronómica biofísica y balance evapotranspirativo</span>
                  <span className="badge badge--info">Biofísica</span>
                </button>
                <button type="button" className="btn" style={{ justifyContent: "space-between" }} onClick={() => onNavigate("markets")}>
                  <span>5. Análisis de márgenes de intermediación mayorista-minorista</span>
                  <span className="badge badge--ok">Econometría</span>
                </button>
              </>
            )}

            {roleProfile === "institutional" && (
              <>
                <button type="button" className="btn" style={{ justifyContent: "space-between" }} onClick={() => onNavigate("map")}>
                  <span>1. Cobertura geoespacial interactiva de los 14 departamentos</span>
                  <span className="badge badge--info">Geoespacial</span>
                </button>
                <button type="button" className="btn" style={{ justifyContent: "space-between" }} onClick={() => onNavigate("production")}>
                  <span>2. Estadísticas de producción nacional (V Censo Agropecuario 2025)</span>
                  <span className="badge badge--ok">Estadística</span>
                </button>
                <button type="button" className="btn" style={{ justifyContent: "space-between" }} onClick={() => onNavigate("risks")}>
                  <span>3. Matriz nacional de alertas agroclimáticas y gestión del riesgo</span>
                  <span className="badge badge--warn">Riesgos</span>
                </button>
                <button type="button" className="btn" style={{ justifyContent: "space-between" }} onClick={() => onNavigate("markets")}>
                  <span>4. Monitoreo de precios y abastecimiento en los 13 mercados WFP</span>
                  <span className="badge badge--ok">Mercados</span>
                </button>
                <button type="button" className="btn" style={{ justifyContent: "space-between" }} onClick={() => onNavigate("scenarios")}>
                  <span>5. Evaluación de impacto de subsidios y choques climáticos</span>
                  <span className="badge badge--primary">Políticas</span>
                </button>
              </>
            )}
          </div>

          {climate && (
            <div style={{ marginTop: 12, fontSize: 12, color: "var(--ink-muted)" }}>
              Nota de cobertura: no existen escenas satelitales archivadas ni estaciones meteorológicas nacionales en este repositorio.
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
