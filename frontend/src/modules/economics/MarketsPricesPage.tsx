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

export default function MarketsPricesPage() {
  const { selectedLocation, selectedCropId, setSelectedCropId, simpleMode } = useApp();
  const [tab, setTab] = useState<"prices" | "markets">("prices");
  const [priceType, setPriceType] = useState("wholesale");
  const [unit, setUnit] = useState<"46 kg" | "t" | "kg">("46 kg");
  const [marketFilter, setMarketFilter] = useState("");

  const [prices, setPrices] = useState<PriceRecord[]>([]);
  const [priceUnavailableReason, setPriceUnavailableReason] = useState<string | null>(null);
  const [historyPoints, setHistoryPoints] = useState<Array<{ date: string; price: number }>>([]);
  const [markets, setMarkets] = useState<MarketItem[]>([]);
  const [logisticsRes, setLogisticsRes] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);

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

  const nearestMarkets = ((logisticsRes?.nearest_markets ?? []) as Array<Record<string, unknown>>);
  const nearestRoad = (logisticsRes?.nearest_osm_road ?? {}) as Record<string, unknown>;

  return (
    <div className="stack-md">
      <PageHeader
        title="Mercados, Precios y Logística (Fase 8)"
        subtitle="Series históricas normalizadas WFP/MAG El Salvador y catálogo de mercados verificados (WFP + OpenStreetMap)."
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
        <button type="button" role="tab" aria-selected={tab === "prices"} className="tab-btn" onClick={() => setTab("prices")}>
          Precios y tendencias
        </button>
        <button type="button" role="tab" aria-selected={tab === "markets"} className="tab-btn" onClick={() => setTab("markets")}>
          Mercados y logística ({markets.length})
        </button>
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
