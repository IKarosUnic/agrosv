import { useEffect, useState } from "react";
import { agrosvApi } from "../../services/api/endpoints";
import { useApp } from "../../stores/AppContext";
import { fmtNum, fmtUsd } from "../../utils/format";
import { PageHeader } from "../../components/dashboard/MetricCard";
import {
  DataStatusBadge,
  EmptyState,
  EvidenceBadge,
  LoadingState,
  UncertaintyPanel,
} from "../../components/data-status/DataStatus";
import { ChartFrame, SvgLineChart } from "../../components/charts/Charts";
import type { MarketItem, PriceRecord } from "../../types/api";

type TabId = "prices" | "markets" | "compare" | "value_chain" | "storage";

export default function MarketsPricesPage() {
  const { selectedLocation, selectedCropId, setSelectedCropId, simpleMode } = useApp();
  const [tab, setTab] = useState<TabId>("prices");
  const [priceType, setPriceType] = useState("wholesale");
  const [unit, setUnit] = useState<"46 kg" | "t" | "kg">("46 kg");
  const [marketFilter, setMarketFilter] = useState("");

  const [prices, setPrices] = useState<PriceRecord[]>([]);
  const [priceUnavailableReason, setPriceUnavailableReason] = useState<string | null>(null);
  const [historyPoints, setHistoryPoints] = useState<Array<{ date: string; price: number }>>([]);
  const [markets, setMarkets] = useState<MarketItem[]>([]);
  const [logisticsRes, setLogisticsRes] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);

  // Market comparison
  const [compareQty, setCompareQty] = useState("5.0");
  const [compareRes, setCompareRes] = useState<Record<string, unknown> | null>(null);
  const [compareLoading, setCompareLoading] = useState(false);

  // Value chain
  const [vcRes, setVcRes] = useState<Record<string, unknown> | null>(null);
  const [vcLoading, setVcLoading] = useState(false);

  // Storage
  const [storageQty, setStorageQty] = useState("10.0");
  const [storageDays, setStorageDays] = useState("30");
  const [storageMoisture, setStorageMoisture] = useState("13.5");
  const [storageRes, setStorageRes] = useState<Record<string, unknown> | null>(null);
  const [storageLoading, setStorageLoading] = useState(false);

  useEffect(() => {
    const ac = new AbortController();
    setLoading(true);
    setPriceUnavailableReason(null);

    Promise.allSettled([
      agrosvApi.prices({
        cropId: selectedCropId,
        market: marketFilter || undefined,
        priceType: priceType || undefined,
        targetUnit: unit,
        limit: 40,
      }, ac.signal),
      agrosvApi.priceHistory({
        cropId: selectedCropId,
        market: marketFilter || "San Salvador",
        priceType: priceType || "wholesale",
        targetUnit: unit,
      }, ac.signal),
      agrosvApi.markets(undefined, false, 80, ac.signal),
      agrosvApi.logistics({ lon: selectedLocation.lon, lat: selectedLocation.lat, crop_id: selectedCropId, quantity_t: 1 }, ac.signal),
    ]).then(([pr, ph, mk, lg]) => {
      if (pr.status === "fulfilled") {
        const res = pr.value.data.result;
        setPrices(res.records ?? []);
        if (!res.available && res.reason) setPriceUnavailableReason(res.reason);
      }
      if (ph.status === "fulfilled") {
        const series = (ph.value.data.result?.series ?? []) as Array<{ date: string; price: number }>;
        setHistoryPoints(series.slice(-36));
      } else {
        setHistoryPoints([]);
      }
      if (mk.status === "fulfilled") {
        setMarkets(mk.value.data.result?.markets ?? []);
      }
      if (lg.status === "fulfilled") {
        setLogisticsRes(lg.value.result);
      }
      setLoading(false);
    });
    return () => ac.abort();
  }, [selectedCropId, marketFilter, priceType, unit, selectedLocation.lat, selectedLocation.lon]);

  const runMarketCompare = async (e?: React.FormEvent) => {
    e?.preventDefault();
    setCompareLoading(true);
    try {
      const res = await agrosvApi.marketCompare({
        crop_id: selectedCropId,
        quantity_t: Number(compareQty) || 5.0,
        origin_lon: selectedLocation.lon,
        origin_lat: selectedLocation.lat,
      });
      setCompareRes(res.result);
    } catch {
      setCompareRes(null);
    } finally {
      setCompareLoading(false);
    }
  };

  const runStorageEval = async (e?: React.FormEvent) => {
    e?.preventDefault();
    setStorageLoading(true);
    try {
      const res = await agrosvApi.storage({
        crop_id: selectedCropId,
        quantity_t: Number(storageQty) || 10.0,
        storage_days: Number(storageDays) || 30,
        observed_moisture_pct: Number(storageMoisture) || undefined,
      });
      setStorageRes(res.result);
    } catch {
      setStorageRes(null);
    } finally {
      setStorageLoading(false);
    }
  };

  useEffect(() => {
    if (tab === "compare") {
      runMarketCompare();
    } else if (tab === "value_chain") {
      setVcLoading(true);
      agrosvApi.valueChain({ crop_id: selectedCropId, market: "San Salvador" })
        .then((env) => setVcRes(env.result as Record<string, unknown>))
        .catch(() => setVcRes(null))
        .finally(() => setVcLoading(false));
    } else if (tab === "storage") {
      runStorageEval();
    }
  }, [tab, selectedCropId, selectedLocation.lat, selectedLocation.lon]);

  const nearestMarkets = ((logisticsRes?.nearest_markets ?? []) as Array<Record<string, unknown>>);
  const nearestRoad = (logisticsRes?.nearest_osm_road ?? {}) as Record<string, unknown>;

  return (
    <div className="stack-md">
      <PageHeader
        title="Mercados, Precios y Logística (Fase 8)"
        subtitle="Series históricas normalizadas WFP/MAG El Salvador, catálogo de mercados, retorno neto comparativo y poscosecha."
        actions={
          <div className="row-wrap">
            <select className="select" style={{ width: "auto" }} aria-label="Producto agrícola" value={selectedCropId} onChange={(e) => setSelectedCropId(e.target.value)}>
              <option value="maize">Maíz blanco (maize)</option>
              <option value="beans">Frijol rojo / seda (beans)</option>
              <option value="rice">Arroz (rice)</option>
              <option value="sorghum">Sorgo (sorghum)</option>
              <option value="coffee">Café (sin serie WFP)</option>
              <option value="tomato">Tomate (sin serie WFP)</option>
            </select>
            <select className="select" style={{ width: "auto" }} aria-label="Unidad de precio" value={unit} onChange={(e) => setUnit(e.target.value as typeof unit)}>
              <option value="46 kg">USD / quintal (46 kg)</option>
              <option value="t">USD / tonelada</option>
              <option value="kg">USD / kg</option>
            </select>
          </div>
        }
      />

      <div className="callout callout--warn">
        <strong>Distinción de precios:</strong> los precios de WFP corresponden a monitoreo <strong>mayorista o minorista de plaza</strong> con fecha histórica declarada; no equivalen automáticamente al precio recibido en finca.
      </div>

      <div className="tabs" role="tablist">
        {[
          ["prices", "Precios y tendencias"],
          ["compare", "Comparador de retorno neto"],
          ["markets", `Mercados y logística (${markets.length})`],
          ["value_chain", "Cadena de valor (WFP)"],
          ["storage", "Poscosecha y almacenamiento"],
        ].map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={tab === id}
            className="tab-btn"
            onClick={() => setTab(id as typeof tab)}
          >
            {label}
          </button>
        ))}
      </div>

      {loading ? (
        <LoadingState />
      ) : tab === "prices" ? (
        <div className="stack-md">
          <div className="row-wrap">
            <select className="select" style={{ width: "auto" }} aria-label="Tipo de precio" value={priceType} onChange={(e) => setPriceType(e.target.value)}>
              <option value="wholesale">Mayorista (wholesale)</option>
              <option value="retail">Minorista (retail)</option>
              <option value="">Todos los tipos</option>
            </select>
            <input
              className="input"
              style={{ width: 220 }}
              placeholder="Filtrar mercado (ej. San Salvador)"
              value={marketFilter}
              onChange={(e) => setMarketFilter(e.target.value)}
            />
          </div>

          {priceUnavailableReason ? (
            <EmptyState
              title={`Sin serie histórica WFP para "${selectedCropId}"`}
              description={priceUnavailableReason}
            />
          ) : (
            <>
              {historyPoints.length > 1 && (
                <ChartFrame
                  title={`Evolución histórica de precios (${selectedCropId} · ${marketFilter || "San Salvador"})`}
                  unit={`USD / ${unit}`}
                  dateRange={`${historyPoints[0].date} a ${historyPoints[historyPoints.length - 1].date}`}
                  source="WFP / HDX Food Prices El Salvador (CC BY-IGO)"
                  rows={historyPoints.map((p) => ({ Fecha: p.date, [`Precio (USD/${unit})`]: p.price }))}
                >
                  <SvgLineChart
                    data={historyPoints.map((p) => ({ label: p.date.slice(0, 7), value: p.price }))}
                    unit={`USD/${unit}`}
                    primaryLabel={`Precio ${priceType || "observado"}`}
                  />
                </ChartFrame>
              )}

              <section className="card">
                <div className="row-wrap" style={{ justifyContent: "space-between", marginBottom: 10 }}>
                  <h2 className="card-title">Registros recientes observados</h2>
                  <EvidenceBadge evidenceClass="official_statistic" />
                </div>
                <div className="table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr><th>Fecha observación</th><th>Producto</th><th>Mercado</th><th>Tipo</th><th>Precio original</th><th>Normalizado ({unit})</th></tr>
                    </thead>
                    <tbody>
                      {prices.slice(0, 20).map((r) => (
                        <tr key={r.record_id}>
                          <td className="tabular-nums"><strong>{r.observation_date}</strong></td>
                          <td>{r.product_or_activity}</td>
                          <td>{r.market}</td>
                          <td><DataStatusBadge tone="info" label={r.price_type} /></td>
                          <td className="tabular-nums">{fmtUsd(r.value)} / {r.unit}</td>
                          <td className="tabular-nums"><strong>{fmtUsd(r.normalized_price)}</strong></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            </>
          )}
        </div>
      ) : tab === "compare" ? (
        <div className="stack-md">
          <form onSubmit={runMarketCompare} className="card row-wrap" style={{ alignItems: "center", gap: 12 }}>
            <label className="field" style={{ minWidth: 200 }}>
              <span className="field-label">Volumen a comercializar (t)</span>
              <input
                type="number"
                step="0.5"
                min="0.5"
                className="input"
                value={compareQty}
                onChange={(e) => setCompareQty(e.target.value)}
              />
            </label>
            <div style={{ marginTop: 22 }}>
              <button type="submit" className="btn btn-primary" disabled={compareLoading}>
                {compareLoading ? "Comparando mercados…" : "Recalcular retorno neto"}
              </button>
            </div>
            <div style={{ marginTop: 22, fontSize: 13, color: "var(--ink-muted)" }}>
              Origen: {selectedLocation.label} (Flete de referencia $0.25 USD/(t·km))
            </div>
          </form>

          {compareRes ? (() => {
            const alts = (compareRes.alternatives ?? []) as Array<Record<string, unknown>>;
            const best = String(compareRes.highest_net_market ?? "");
            return (
              <div className="stack-md">
                <div className="card">
                  <div className="row-wrap" style={{ justifyContent: "space-between", marginBottom: 12 }}>
                    <div>
                      <h2 className="card-title">Retorno neto comparado para {compareQty} t de {selectedCropId}</h2>
                      <p className="card-subtitle">
                        Mercado con mayor retorno neto: <strong>{best}</strong> (descontando costo de transporte por distancia vial estimada).
                      </p>
                    </div>
                    <EvidenceBadge evidenceClass="model_estimate" />
                  </div>

                  <div className="table-wrap">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Mercado</th>
                          <th>Distancia vial est.</th>
                          <th>Precio bruto USD/t</th>
                          <th>Flete est. USD/t</th>
                          <th>Precio neto al productor</th>
                          <th>Ingreso neto total</th>
                          <th>Última fecha WFP</th>
                        </tr>
                      </thead>
                      <tbody>
                        {alts.map((a) => {
                          const isBest = a.market === best;
                          return (
                            <tr key={String(a.market)} style={{ background: isBest ? "var(--accent-soft)" : undefined }}>
                              <td>
                                <strong>{String(a.market)}</strong> {isBest && <span className="badge badge-ok" style={{ marginLeft: 6 }}>Mejor opción</span>}
                              </td>
                              <td className="tabular-nums">{fmtNum(a.distance_km as number, 1, "km")}</td>
                              <td className="tabular-nums">{fmtUsd(a.gross_price_per_t as number)}</td>
                              <td className="tabular-nums">{fmtUsd(a.transport_cost_per_t as number)}</td>
                              <td className="tabular-nums"><strong>{fmtUsd(a.net_producer_price_per_t as number)} / t</strong></td>
                              <td className="tabular-nums" style={{ color: "var(--accent-primary)", fontWeight: 700 }}>
                                {fmtUsd(a.net_revenue_usd as number)}
                              </td>
                              <td className="tabular-nums" style={{ fontSize: 12 }}>{String(a.observation_date ?? "—")}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="callout callout--info" style={{ fontSize: 13 }}>
                  <strong>Aviso de comercialización:</strong> Los precios de plaza mayorista no garantizan absorción del volumen ofertado ni compras en firme; las tarifas de flete son estimaciones geodésicas (×1.3) y no sustituyen cotizaciones de transportistas locales.
                </div>
              </div>
            );
          })() : (
            <div className="card">
              <p style={{ fontSize: 13, color: "var(--ink-muted)" }}>
                No hay series de precios vigentes en WFP para el cultivo seleccionado ({selectedCropId}).
              </p>
            </div>
          )}
        </div>
      ) : tab === "value_chain" ? (
        <div className="stack-md">
          {vcLoading ? (
            <LoadingState message="Consultando series mayorista y minorista WFP…" />
          ) : vcRes ? (() => {
            const spread = vcRes.wholesale_to_retail_spread_per_t as number | null;
            const wShare = vcRes.wholesale_share_of_retail as number | null;
            return (
              <div className="stack-md">
                <div className="card stack-sm">
                  <div className="row-wrap" style={{ justifyContent: "space-between" }}>
                    <h2 className="card-title">Margen de intermediación mayorista vs minorista ({selectedCropId})</h2>
                    <EvidenceBadge evidenceClass="official_statistic" />
                  </div>
                  <div className="grid-3" style={{ marginTop: 8 }}>
                    <div className="metric-card">
                      <div className="metric-label">Precio mayorista WFP (t)</div>
                      <div className="metric-value" style={{ fontSize: 20 }}>{fmtUsd(vcRes.wholesale_price_per_t as number)}</div>
                      <div className="metric-detail">Mercado San Salvador</div>
                    </div>
                    <div className="metric-card">
                      <div className="metric-label">Precio minorista WFP (t)</div>
                      <div className="metric-value" style={{ fontSize: 20 }}>{fmtUsd(vcRes.retail_price_per_t as number)}</div>
                      <div className="metric-detail">Mercado San Salvador</div>
                    </div>
                    <div className="metric-card">
                      <div className="metric-label">Margen de plaza (Spread)</div>
                      <div className="metric-value" style={{ fontSize: 20 }}>{fmtUsd(spread ?? 0)} / t</div>
                      <div className="metric-detail">Mayorista representa {wShare ? `${(wShare * 100).toFixed(1)}%` : "—"} del precio minorista</div>
                    </div>
                  </div>
                  <div className="callout callout--info" style={{ fontSize: 13, marginTop: 10 }}>
                    <strong>Regla científica de interpretación:</strong> {String(vcRes.interpretation_rule)}
                  </div>
                </div>
              </div>
            );
          })() : (
            <div className="card">
              <p style={{ fontSize: 13, color: "var(--ink-muted)" }}>
                Sin datos comparables de cadena de valor para {selectedCropId}.
              </p>
            </div>
          )}
        </div>
      ) : tab === "storage" ? (
        <div className="stack-md">
          <form onSubmit={runStorageEval} className="card stack-sm">
            <h2 className="card-title">Evaluador de condiciones de almacenamiento y poscosecha ({selectedCropId})</h2>
            <div className="grid-3">
              <label className="field">
                <span className="field-label">Volumen cosechado (t)</span>
                <input type="number" step="1" className="input" value={storageQty} onChange={(e) => setStorageQty(e.target.value)} />
              </label>
              <label className="field">
                <span className="field-label">Días de almacenamiento previstos</span>
                <input type="number" step="5" min="5" max="365" className="input" value={storageDays} onChange={(e) => setStorageDays(e.target.value)} />
              </label>
              <label className="field">
                <span className="field-label">Humedad del grano cosechado (%)</span>
                <input type="number" step="0.5" className="input" value={storageMoisture} onChange={(e) => setStorageMoisture(e.target.value)} />
              </label>
            </div>
            <div>
              <button type="submit" className="btn btn-primary btn-sm" disabled={storageLoading}>
                {storageLoading ? "Evaluando…" : "Verificar umbrales de conservación"}
              </button>
            </div>
          </form>

          {storageRes && (() => {
            const ref = (storageRes.reference_parameters ?? {}) as Record<string, unknown>;
            const safeM = ref.safe_moisture_pct as number | undefined;
            const shelfLife = ref.shelf_life_days_ambient as number | undefined;
            return (
              <div className="stack-md">
                <div className="card stack-sm">
                  <div className="row-wrap" style={{ justifyContent: "space-between" }}>
                    <h3 className="card-title">Parámetros técnicos de referencia poscosecha</h3>
                    <EvidenceBadge evidenceClass="institutional_reference" />
                  </div>
                  <div className="grid-3" style={{ marginTop: 8 }}>
                    <div className="metric-card">
                      <div className="metric-label">Humedad segura máxima</div>
                      <div className="metric-value" style={{ fontSize: 20 }}>{safeM != null ? `${safeM}%` : "No declarada"}</div>
                      <div className="metric-detail">
                        Humedad aportada: {storageMoisture}% · {Number(storageMoisture) > (safeM ?? 13) ? "Riesgo de hongos y gorgojo" : "Dentro de rango seguro"}
                      </div>
                    </div>
                    <div className="metric-card">
                      <div className="metric-label">Vida útil ambiental estimada</div>
                      <div className="metric-value" style={{ fontSize: 20 }}>{shelfLife != null ? `${shelfLife} días` : "—"}</div>
                      <div className="metric-detail">Días de almacenaje previstos: {storageDays} días</div>
                    </div>
                    <div className="metric-card">
                      <div className="metric-label">Perecibilidad del cultivo</div>
                      <div className="metric-value" style={{ fontSize: 20 }}>{String(ref.perishability ?? "media")}</div>
                      <div className="metric-detail">Temperatura óptima: {String(ref.temp_c ?? "15-25")} °C</div>
                    </div>
                  </div>
                  <div className="callout callout--info" style={{ fontSize: 13, marginTop: 10 }}>
                    <strong>Recomendación agronómica:</strong> El uso de silos metálicos herméticos (tecnología validada en El Salvador por CENTA) reduce las pérdidas poscosecha a menos del 1%, en comparación con bodegas tradicionales o sacos abiertos donde las pérdidas pueden superar el 15%.
                  </div>
                </div>
              </div>
            );
          })()}
        </div>
      ) : (
        <div className="stack-md">
          <div className="card">
            <h2 className="card-title">Logística estimada desde ubicación activa ({selectedLocation.label})</h2>
            <p className="card-subtitle">
              Vía OSM más cercana: {fmtNum(nearestRoad.nearest_road_m as number, 0, "m")} · {String(logisticsRes?.travel_time_note ?? "")}
            </p>
            <div className="table-wrap" style={{ marginTop: 10 }}>
              <table className="data-table">
                <thead>
                  <tr><th>Mercado cercano</th><th>Fuente</th><th>Dist. geodésica</th><th>Dist. vial est. (×1.3)</th><th>Flete est. (1 t)</th></tr>
                </thead>
                <tbody>
                  {nearestMarkets.map((m) => (
                    <tr key={String(m.market_id)}>
                      <td><strong>{String(m.name)}</strong></td>
                      <td className="mono">{String(m.source)}</td>
                      <td className="tabular-nums">{fmtNum(m.geodesic_km as number, 1, "km")}</td>
                      <td className="tabular-nums">{fmtNum(m.estimated_road_km_detour_1_3 as number, 1, "km")}</td>
                      <td className="tabular-nums">{fmtUsd(m.estimated_transport_cost_usd as number)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <UncertaintyPanel
              collapsedByDefault={simpleMode}
              limitations={["No se muestran compradores privados ni acuerdos comerciales ficticios."]}
            />
          </div>
        </div>
      )}
    </div>
  );
}
