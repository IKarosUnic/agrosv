import { useCallback, useEffect, useRef, useState } from "react";
import maplibregl, { type Map as MLMap, type StyleSpecification } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { API_BASE } from "../../services/api/client";
import { agrosvApi } from "../../services/api/endpoints";
import { useApp } from "../../stores/AppContext";
import { fmtCoord, fmtNum, fmtUsd } from "../../utils/format";
import {
  DataStatusBadge,
  ErrorState,
  EvidenceBadge,
  LoadingState,
  SourceAttribution,
} from "../data-status/DataStatus";
import type { DeptDetail, DeptFeatureProps, MarketItem, SuitabilityResult } from "../../types/api";
import type { RouteId } from "../../app/routes";

const HILLSHADE_ATTR =
  "DEM: © DLR/Airbus — Copernicus DEM GLO-30 | Límites: geoBoundaries CC BY-SA 2.0 | " +
  "OSM © colaboradores, ODbL | Suelos: SoilGrids 2.0, CC BY 4.0";

const RELIEF_LABELS = [
  "Plano 0–2°",
  "Suave 2–5°",
  "Ondulado 5–12°",
  "Quebrado 12–25°",
  "Escarpado 25–45°",
  "Muy escarpado >45°",
];
const RELIEF_COLORS = ["#e8f0e2", "#cbdeaf", "#a6c77a", "#debe5f", "#c4824a", "#964e37"];

type OsmLayerId = "roads" | "waterways" | "water_bodies" | "settlements" | "infrastructure";

const OSM_LAYERS: Array<{ id: OsmLayerId; label: string; category: string; mapLayer: string }> = [
  { id: "water_bodies", label: "Cuerpos de agua (OSM)", category: "Agua", mapLayer: "water-fill" },
  { id: "waterways", label: "Ríos y quebradas (OSM)", category: "Agua", mapLayer: "water-line" },
  { id: "roads", label: "Red vial (OSM)", category: "Economía / Acceso", mapLayer: "road-line" },
  { id: "settlements", label: "Asentamientos (OSM)", category: "Territorio", mapLayer: "settlement-dot" },
  { id: "infrastructure", label: "Infraestructura (OSM)", category: "Territorio", mapLayer: "infra-dot" },
];

const EMPTY_FC = { type: "FeatureCollection" as const, features: [] };

type Bounds = [[number, number], [number, number]];

function boundsOf(geometry: unknown): Bounds | null {
  const b = new maplibregl.LngLatBounds();
  const walk = (c: unknown): void => {
    if (Array.isArray(c) && typeof c[0] === "number") {
      b.extend(c as [number, number]);
    } else if (Array.isArray(c)) {
      c.forEach(walk);
    }
  };
  walk(geometry);
  return b.isEmpty() ? null : [[b.getWest(), b.getSouth()], [b.getEast(), b.getNorth()]];
}

export function AgriculturalMapExperience({ onNavigate }: { onNavigate: (id: RouteId) => void }) {
  const { resolvedTheme, selectedLocation, setSelectedLocation, selectedCropId } = useApp();
  const mapEl = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MLMap | null>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);

  const [ready, setReady] = useState(false);
  const [depts, setDepts] = useState<DeptFeatureProps[]>([]);
  const [selectedDept, setSelectedDept] = useState(selectedLocation.departmentCode ?? "");
  const [deptDetail, setDeptDetail] = useState<DeptDetail | null>(null);

  const [activeOsm, setActiveOsm] = useState<OsmLayerId[]>(["water_bodies"]);
  const [showHistoricMunis, setShowHistoricMunis] = useState(false);
  const [showMarkets, setShowMarkets] = useState(true);
  const [overlay, setOverlay] = useState<"none" | "slope" | "relief">("none");
  const [overlayOpacity, setOverlayOpacity] = useState(0.72);
  const [hoverCoord, setHoverCoord] = useState<{ lat: number; lon: number } | null>(null);
  const [manualLat, setManualLat] = useState(String(selectedLocation.lat));
  const [manualLon, setManualLon] = useState(String(selectedLocation.lon));

  const [profileOpen, setProfileOpen] = useState(false);
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [envProfile, setEnvProfile] = useState<Record<string, unknown> | null>(null);
  const [suitability, setSuitability] = useState<SuitabilityResult | null>(null);
  const [logistics, setLogistics] = useState<Record<string, unknown> | null>(null);
  const [mapStatus, setMapStatus] = useState("Inicializando visor geoespacial…");

  // Initialize MapLibre
  useEffect(() => {
    if (!mapEl.current || mapRef.current) return;
    const style: StyleSpecification = {
      version: 8,
      sources: {
        hillshade: {
          type: "raster",
          tiles: [`${API_BASE}/api/tiles/hillshade/{z}/{x}/{y}.png`],
          tileSize: 256,
          minzoom: 7,
          maxzoom: 14,
          attribution: HILLSHADE_ATTR,
        },
        slope: {
          type: "raster",
          tiles: [`${API_BASE}/api/tiles/slope/{z}/{x}/{y}.png`],
          tileSize: 256,
          minzoom: 7,
          maxzoom: 14,
        },
        relief: {
          type: "raster",
          tiles: [`${API_BASE}/api/tiles/relief/{z}/{x}/{y}.png`],
          tileSize: 256,
          minzoom: 7,
          maxzoom: 14,
        },
        depts: { type: "geojson", data: EMPTY_FC },
        munis: { type: "geojson", data: EMPTY_FC },
        roads: { type: "geojson", data: EMPTY_FC },
        waterways: { type: "geojson", data: EMPTY_FC },
        water_bodies: { type: "geojson", data: EMPTY_FC },
        settlements: { type: "geojson", data: EMPTY_FC },
        infrastructure: { type: "geojson", data: EMPTY_FC },
        markets: { type: "geojson", data: EMPTY_FC },
      },
      layers: [
        { id: "bg", type: "background", paint: { "background-color": resolvedTheme === "dark" ? "#111915" : "#e8ede5" } },
        { id: "hillshade", type: "raster", source: "hillshade", paint: { "raster-opacity": 0.9, "raster-resampling": "linear" } },
        { id: "slope", type: "raster", source: "slope", layout: { visibility: "none" }, paint: { "raster-opacity": 0.72, "raster-resampling": "nearest" } },
        { id: "relief", type: "raster", source: "relief", layout: { visibility: "none" }, paint: { "raster-opacity": 0.72, "raster-resampling": "nearest" } },
        { id: "water-fill", type: "fill", source: "water_bodies", layout: { visibility: "none" }, paint: { "fill-color": "#4f8db8", "fill-opacity": 0.8 } },
        { id: "water-line", type: "line", source: "waterways", layout: { visibility: "none" }, paint: { "line-color": "#2f74a3", "line-width": ["interpolate", ["linear"], ["zoom"], 8, 0.5, 13, 1.8] } },
        {
          id: "road-line",
          type: "line",
          source: "roads",
          layout: { visibility: "none", "line-cap": "round" },
          paint: {
            "line-color": ["match", ["get", "road_class"], "arterial", "#b0592f", "colectora", "#c98a4b", "local", "#8d8d8d", "#a8a8a8"],
            "line-width": ["interpolate", ["linear"], ["zoom"], 8, 0.4, 14, 2.2],
            "line-opacity": 0.78,
          },
        },
        {
          id: "settlement-dot",
          type: "circle",
          source: "settlements",
          layout: { visibility: "none" },
          paint: {
            "circle-radius": ["interpolate", ["linear"], ["zoom"], 8, 2, 13, 4.5],
            "circle-color": "#3c463e",
            "circle-stroke-color": "#ffffff",
            "circle-stroke-width": 0.6,
          },
        },
        {
          id: "infra-dot",
          type: "circle",
          source: "infrastructure",
          layout: { visibility: "none" },
          paint: {
            "circle-radius": ["interpolate", ["linear"], ["zoom"], 8, 2.5, 13, 5.5],
            "circle-color": ["match", ["get", "category"], "salud", "#c0392b", "educación", "#2c6e9b", "transporte", "#7d5ba6", "agua", "#1f8f7a", "#7a7a7a"],
            "circle-stroke-color": "#ffffff",
            "circle-stroke-width": 0.7,
          },
        },
        {
          id: "muni-line",
          type: "line",
          source: "munis",
          layout: { visibility: "none" },
          paint: { "line-color": "#6e7a6d", "line-width": 0.7, "line-dasharray": [2, 2], "line-opacity": 0.7 },
        },
        {
          id: "dept-line",
          type: "line",
          source: "depts",
          paint: { "line-color": "#2f4734", "line-width": 1.3, "line-opacity": 0.85 },
        },
        {
          id: "market-dot",
          type: "circle",
          source: "markets",
          layout: { visibility: "visible" },
          paint: {
            "circle-radius": ["interpolate", ["linear"], ["zoom"], 7, 4, 12, 7.5],
            "circle-color": "#b87414",
            "circle-stroke-color": "#ffffff",
            "circle-stroke-width": 1.4,
          },
        },
      ],
    };

    const m = new maplibregl.Map({
      container: mapEl.current,
      style,
      center: [selectedLocation.lon, selectedLocation.lat],
      zoom: 8.3,
      minZoom: 7,
      maxZoom: 14,
      attributionControl: false,
      dragRotate: false,
      pitchWithRotate: false,
    });
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    m.addControl(new maplibregl.AttributionControl({ compact: true, customAttribution: HILLSHADE_ATTR }));
    mapRef.current = m;
    m.on("load", () => {
      setReady(true);
      setMapStatus("Listo · Haz clic en el mapa para consultar un punto");
    });
    m.on("mousemove", (e) => {
      setHoverCoord({ lat: e.lngLat.lat, lon: e.lngLat.lng });
    });

    return () => {
      markerRef.current?.remove();
      markerRef.current = null;
      m.remove();
      mapRef.current = null;
      setReady(false);
    };
  }, []);

  // Sync map background color with theme
  useEffect(() => {
    const m = mapRef.current;
    if (!m || !ready) return;
    m.setPaintProperty("bg", "background-color", resolvedTheme === "dark" ? "#111915" : "#e8ede5");
    m.setPaintProperty("dept-line", "line-color", resolvedTheme === "dark" ? "#8bb899" : "#2f4734");
  }, [resolvedTheme, ready]);

  // Initial departments & markets load
  useEffect(() => {
    const ac = new AbortController();
    agrosvApi.departments(0.0015, ac.signal)
      .then(({ data }) => {
        const list = (data.features ?? []).map((f) => f.properties);
        setDepts(list.sort((a, b) => a.name.localeCompare(b.name)));
        const src = mapRef.current?.getSource("depts") as maplibregl.GeoJSONSource | undefined;
        src?.setData(data as unknown as GeoJSON.FeatureCollection);
      })
      .catch(() => setMapStatus("Error cargando límites departamentales"));

    agrosvApi.markets(undefined, true, 120, ac.signal)
      .then(({ data }) => {
        const features = (data.result?.markets ?? [])
          .filter((m: MarketItem) => m.latitude !== null && m.longitude !== null)
          .map((m: MarketItem) => ({
            type: "Feature" as const,
            properties: {
              market_id: m.market_id,
              name: m.name,
              source: m.source,
              department: m.department ?? "",
            },
            geometry: {
              type: "Point" as const,
              coordinates: [m.longitude!, m.latitude!],
            },
          }));
        const src = mapRef.current?.getSource("markets") as maplibregl.GeoJSONSource | undefined;
        src?.setData({ type: "FeatureCollection", features });
      })
      .catch(() => undefined);

    return () => ac.abort();
  }, [ready]);

  // Historic municipalities toggle
  useEffect(() => {
    const m = mapRef.current;
    if (!m || !ready) return;
    m.setLayoutProperty("muni-line", "visibility", showHistoricMunis ? "visible" : "none");
    if (showHistoricMunis) {
      agrosvApi.municipalities(selectedDept || undefined)
        .then(({ data }) => {
          const src = m.getSource("munis") as maplibregl.GeoJSONSource | undefined;
          src?.setData(data as unknown as GeoJSON.FeatureCollection);
        })
        .catch(() => undefined);
    }
  }, [showHistoricMunis, selectedDept, ready]);

  // Markets layer visibility
  useEffect(() => {
    const m = mapRef.current;
    if (!m || !ready) return;
    m.setLayoutProperty("market-dot", "visibility", showMarkets ? "visible" : "none");
  }, [showMarkets, ready]);

  // Load OSM layers on demand by bbox
  const loadOsmLayers = useCallback(() => {
    const m = mapRef.current;
    if (!m || !ready || activeOsm.length === 0) return;
    const b = m.getBounds();
    const bbox = `west=${b.getWest()}&south=${b.getSouth()}&east=${b.getEast()}&north=${b.getNorth()}`;
    for (const id of activeOsm) {
      const src = m.getSource(id) as maplibregl.GeoJSONSource | undefined;
      if (!src) continue;
      agrosvApi.infrastructureLayer(id, bbox, 5000)
        .then(({ data }) => src.setData(data as unknown as GeoJSON.FeatureCollection))
        .catch(() => undefined);
    }
  }, [activeOsm, ready]);

  useEffect(() => {
    const m = mapRef.current;
    if (!m || !ready) return;
    for (const { id, mapLayer } of OSM_LAYERS) {
      const vis = activeOsm.includes(id);
      m.setLayoutProperty(mapLayer, "visibility", vis ? "visible" : "none");
      if (!vis) {
        (m.getSource(id) as maplibregl.GeoJSONSource | undefined)?.setData(EMPTY_FC);
      }
    }
    loadOsmLayers();
  }, [activeOsm, ready, loadOsmLayers]);

  useEffect(() => {
    const m = mapRef.current;
    if (!m || !ready) return;
    const onMoveEnd = () => {
      loadOsmLayers();
      setMapStatus(`Zoom ${m.getZoom().toFixed(1)} · ${activeOsm.length} capa(s) OSM activas`);
    };
    m.on("moveend", onMoveEnd);
    return () => {
      m.off("moveend", onMoveEnd);
    };
  }, [ready, loadOsmLayers, activeOsm.length]);

  // Raster overlay & opacity
  useEffect(() => {
    const m = mapRef.current;
    if (!m || !ready) return;
    m.setLayoutProperty("slope", "visibility", overlay === "slope" ? "visible" : "none");
    m.setLayoutProperty("relief", "visibility", overlay === "relief" ? "visible" : "none");
    m.setPaintProperty("slope", "raster-opacity", overlayOpacity);
    m.setPaintProperty("relief", "raster-opacity", overlayOpacity);
  }, [overlay, overlayOpacity, ready]);

  // Integrated Location Query (Phases 5-8)
  const inspectPoint = useCallback(async (lat: number, lon: number, customLabel?: string) => {
    setManualLat(lat.toFixed(4));
    setManualLon(lon.toFixed(4));
    setProfileOpen(true);
    setProfileLoading(true);
    setProfileError(null);

    if (mapRef.current) {
      markerRef.current?.remove();
      markerRef.current = new maplibregl.Marker({ color: "#1f5c37" })
        .setLngLat([lon, lat])
        .addTo(mapRef.current);
    }

    const [envRes, suitRes, logRes] = await Promise.allSettled([
      agrosvApi.environmentalProfile(lat, lon, 6000),
      agrosvApi.cropSuitability(selectedCropId, lat, lon, "rainfed", false),
      agrosvApi.logistics({ lon, lat, crop_id: selectedCropId, quantity_t: 1 }),
    ]);

    if (envRes.status === "fulfilled") {
      const result = envRes.value.data.result as Record<string, unknown>;
      setEnvProfile(result);
      const ident = (result.identification ?? {}) as Record<string, { name?: string; source_code?: string } | undefined>;
      setSelectedLocation({
        lat,
        lon,
        label: customLabel ?? `${ident.municipality_historic?.name ?? "Punto"} (${ident.department?.name ?? "El Salvador"})`,
        departmentCode: ident.department?.source_code,
        departmentName: ident.department?.name,
        municipalityName: ident.municipality_historic?.name,
      });
    } else {
      setEnvProfile(null);
      setProfileError(envRes.reason instanceof Error ? envRes.reason.message : "Coordenada fuera de cobertura");
    }

    setSuitability(suitRes.status === "fulfilled" ? suitRes.value.data.result : null);
    setLogistics(logRes.status === "fulfilled" ? logRes.value.result : null);
    setProfileLoading(false);
  }, [selectedCropId, setSelectedLocation]);

  useEffect(() => {
    const m = mapRef.current;
    if (!m || !ready) return;
    const onClick = (e: maplibregl.MapMouseEvent) => {
      const marketFeats = m.queryRenderedFeatures(e.point, { layers: ["market-dot"] });
      if (marketFeats.length > 0) {
        const props = marketFeats[0].properties as { name?: string };
        inspectPoint(e.lngLat.lat, e.lngLat.lng, props?.name ? `Mercado: ${props.name}` : undefined);
        return;
      }
      inspectPoint(e.lngLat.lat, e.lngLat.lng);
    };
    m.on("click", onClick);
    return () => {
      m.off("click", onClick);
    };
  }, [ready, inspectPoint]);

  const chooseDepartment = useCallback((code: string) => {
    setSelectedDept(code);
    if (!code) {
      setDeptDetail(null);
      return;
    }
    agrosvApi.departmentDetail(code)
      .then(({ data }) => {
        setDeptDetail(data);
        const b = boundsOf(data.geometry);
        if (b && mapRef.current) {
          mapRef.current.fitBounds(b, { padding: 50, duration: 650, maxZoom: 11 });
        }
      })
      .catch(() => setDeptDetail(null));
  }, []);

  const toggleOsm = (id: OsmLayerId) => {
    setActiveOsm((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const lat = Number(manualLat);
    const lon = Number(manualLon);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
    mapRef.current?.flyTo({ center: [lon, lat], zoom: Math.max(mapRef.current.getZoom(), 10) });
    inspectPoint(lat, lon);
  };

  const terrain = (envProfile?.terrain ?? {}) as Record<string, unknown>;
  const soilProps = ((envProfile?.soil as Record<string, unknown> | undefined)?.properties ?? {}) as Record<string, { value?: number | null }>;
  const soilDerived = ((envProfile?.soil as Record<string, unknown> | undefined)?.derived ?? {}) as Record<string, Record<string, unknown> | undefined>;
  const hydroMean = (((envProfile?.hydrology as Record<string, unknown> | undefined)?.water_balance as Record<string, unknown> | undefined)?.mean ?? {}) as Record<string, number | undefined>;
  const nearestMarkets = (logistics?.nearest_markets ?? []) as Array<{ name: string; geodesic_km: number; estimated_transport_cost_usd: number }>;

  return (
    <div className="map-workspace">
      <aside className="map-sidebar" aria-label="Control de capas y consulta territorial">
        <div>
          <h1 style={{ margin: 0, fontSize: 16 }}>Mapa Agrícola de El Salvador</h1>
          <div style={{ fontSize: 12, color: "var(--ink-muted)", marginTop: 2 }}>{mapStatus}</div>
        </div>

        {/* Territorio */}
        <section className="stack-sm">
          <label className="field">
            <span className="field-label">Enfocar departamento</span>
            <select className="select" value={selectedDept} onChange={(e) => chooseDepartment(e.target.value)}>
              <option value="">Todo El Salvador</option>
              {depts.map((d) => (
                <option key={d.adm1_code} value={d.adm1_code}>{d.name}</option>
              ))}
            </select>
          </label>

          {deptDetail && (
            <dl className="kv-list" style={{ background: "var(--bg-subtle)", padding: 10, borderRadius: 8 }}>
              <div className="kv-row"><dt>Área</dt><dd>{fmtNum(deptDetail.area_km2, 1, "km²")}</dd></div>
              <div className="kv-row"><dt>Elevación media</dt><dd>{fmtNum(deptDetail.topography.elev_mean_m, 0, "m")}</dd></div>
              <div className="kv-row"><dt>Pendiente media</dt><dd>{fmtNum(deptDetail.topography.slope_mean_deg, 1, "°")}</dd></div>
              <div className="kv-row"><dt>pH suelo (0–30 cm)</dt><dd>{fmtNum(deptDetail.soils.phh2o, 2)}</dd></div>
            </dl>
          )}
        </section>

        {/* Coordenada accesible por teclado */}
        <form onSubmit={handleManualSubmit} className="stack-sm" style={{ paddingTop: 10, borderTop: "1px solid var(--border-subtle)" }}>
          <div className="field-label">Consultar coordenada exacta (EPSG:4326)</div>
          <div className="row-wrap">
            <input
              className="input"
              style={{ flex: 1, minWidth: 90 }}
              aria-label="Latitud"
              value={manualLat}
              onChange={(e) => setManualLat(e.target.value)}
              placeholder="Lat (ej. 13.69)"
            />
            <input
              className="input"
              style={{ flex: 1, minWidth: 90 }}
              aria-label="Longitud"
              value={manualLon}
              onChange={(e) => setManualLon(e.target.value)}
              placeholder="Lon (ej. -89.19)"
            />
            <button type="submit" className="btn btn-primary btn-sm">Ir</button>
          </div>
        </form>

        {/* Gestor de capas */}
        <section className="stack-sm" style={{ paddingTop: 10, borderTop: "1px solid var(--border-subtle)" }}>
          <div className="field-label">Capas ráster de terreno (Copernicus DEM 30 m)</div>
          <div className="row-wrap" role="radiogroup" aria-label="Capa ráster de terreno">
            {(["none", "slope", "relief"] as const).map((k) => (
              <label key={k} style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 12.5 }}>
                <input type="radio" name="map-overlay" checked={overlay === k} onChange={() => setOverlay(k)} />
                <span>{k === "none" ? "Sombreado" : k === "slope" ? "Pendiente" : "Relieve"}</span>
              </label>
            ))}
          </div>

          {overlay !== "none" && (
            <div>
              <label className="field">
                <span style={{ fontSize: 12, color: "var(--ink-muted)" }}>
                  Opacidad: {Math.round(overlayOpacity * 100)}%
                </span>
                <input
                  type="range"
                  min={0.15}
                  max={1}
                  step={0.05}
                  value={overlayOpacity}
                  onChange={(e) => setOverlayOpacity(Number(e.target.value))}
                />
              </label>
              <ul style={{ listStyle: "none", margin: "8px 0 0", padding: 0, display: "grid", gap: 4, fontSize: 12 }}>
                {RELIEF_LABELS.map((lab, i) => (
                  <li key={lab} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ width: 14, height: 10, background: RELIEF_COLORS[i], border: "1px solid var(--border-strong)", borderRadius: 2 }} />
                    <span>{lab}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="field-label" style={{ marginTop: 6 }}>Capas vectoriales integradas</div>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
            <input type="checkbox" checked={showMarkets} onChange={(e) => setShowMarkets(e.target.checked)} />
            <span>Mercados WFP y OSM (puntos naranjas)</span>
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
            <input type="checkbox" checked={showHistoricMunis} onChange={(e) => setShowHistoricMunis(e.target.checked)} />
            <span>Municipios históricos (262 pre-2023)</span>
          </label>
          {OSM_LAYERS.map((l) => (
            <label key={l.id} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
              <input
                type="checkbox"
                checked={activeOsm.includes(l.id)}
                onChange={() => toggleOsm(l.id)}
              />
              <span>{l.label}</span>
            </label>
          ))}

          <div className="callout" style={{ fontSize: 11.5, marginTop: 6 }}>
            <DataStatusBadge tone="unavailable" label="Satélite sin escenas" />
            <span>No hay teselas Sentinel/Landsat archivadas en el servidor; no se simulan capas satelitales.</span>
          </div>
        </section>

        <SourceAttribution
          sources={["Copernicus DEM GLO-30", "geoBoundaries ADM1/ADM2", "OpenStreetMap ODbL", "WFP Markets"]}
          resolution="30 m (DEM) · 250 m (SoilGrids en consulta)"
        />
      </aside>

      <div className="map-stage">
        <div
          ref={mapEl}
          className="map-canvas"
          role="application"
          aria-label="Mapa geoespacial interactivo de El Salvador"
        />

        <div className="map-coords-bar tabular-nums" aria-live="polite">
          {hoverCoord ? fmtCoord(hoverCoord.lat, hoverCoord.lon) : fmtCoord(selectedLocation.lat, selectedLocation.lon)}
        </div>

        {profileOpen && (
          <aside className="map-profile-drawer" aria-label="Perfil geográfico integrado">
            <div className="row-wrap" style={{ justifyContent: "space-between", marginBottom: 8 }}>
              <strong style={{ fontSize: 14.5 }}>Perfil integrado del punto</strong>
              <button type="button" className="btn btn-sm" onClick={() => setProfileOpen(false)}>Cerrar</button>
            </div>

            {profileLoading ? (
              <LoadingState message="Consultando motores Fase 5, 6 y 8…" />
            ) : profileError ? (
              <ErrorState title="Fuera de cobertura" message={profileError} />
            ) : (
              <div className="stack-sm">
                <div>
                  <div style={{ fontWeight: 650, fontSize: 14 }}>{selectedLocation.label}</div>
                  <div className="tabular-nums" style={{ fontSize: 12, color: "var(--ink-muted)" }}>
                    {fmtCoord(selectedLocation.lat, selectedLocation.lon)}
                  </div>
                </div>

                <dl className="kv-list" style={{ background: "var(--bg-subtle)", padding: 10, borderRadius: 8 }}>
                  <div className="kv-row"><dt>Elevación</dt><dd>{fmtNum(terrain.elevation_m as number, 0, "m")}</dd></div>
                  <div className="kv-row"><dt>Pendiente</dt><dd>{fmtNum(terrain.slope_deg as number, 1, "°")}</dd></div>
                  <div className="kv-row"><dt>pH suelo (0–30 cm)</dt><dd>{fmtNum(soilProps.ph?.value, 2)}</dd></div>
                  <div className="kv-row"><dt>Textura USDA</dt><dd>{String(soilDerived.texture_class?.usda_class ?? "No disponible")}</dd></div>
                  <div className="kv-row"><dt>P − ET0 anual</dt><dd>{fmtNum(hydroMean.precipitation_minus_et0_mm, 0, "mm")}</dd></div>
                </dl>

                {suitability && (
                  <div className="card" style={{ padding: 10 }}>
                    <div className="row-wrap" style={{ justifyContent: "space-between" }}>
                      <strong style={{ fontSize: 13 }}>Aptitud ({suitability.crop_id})</strong>
                      <DataStatusBadge
                        tone={suitability.class === "S1" ? "ok" : suitability.class === "S2" ? "info" : suitability.class === "S3" ? "warn" : "crit"}
                        label={`${suitability.class} · ${suitability.class_label}`}
                      />
                    </div>
                    {suitability.limiting_factors.length > 0 && (
                      <div style={{ fontSize: 12, color: "var(--ink-muted)", marginTop: 4 }}>
                        Limitantes: {suitability.limiting_factors.join(", ")}
                      </div>
                    )}
                  </div>
                )}

                {nearestMarkets.length > 0 && (
                  <div className="card" style={{ padding: 10 }}>
                    <strong style={{ fontSize: 13 }}>Mercado más cercano</strong>
                    <div style={{ fontSize: 12.5, marginTop: 4 }}>
                      {nearestMarkets[0].name} ({fmtNum(nearestMarkets[0].geodesic_km, 1, "km")} · est. flete {fmtUsd(nearestMarkets[0].estimated_transport_cost_usd)}/t)
                    </div>
                  </div>
                )}

                <div className="row-wrap">
                  <EvidenceBadge evidenceClass="modeled_prediction" />
                  <EvidenceBadge evidenceClass="reanalysis" />
                </div>

                <div className="row-wrap" style={{ marginTop: 6 }}>
                  <button type="button" className="btn btn-sm btn-primary" onClick={() => onNavigate("territory")}>
                    Suelo, agua y clima
                  </button>
                  <button type="button" className="btn btn-sm" onClick={() => onNavigate("crops")}>
                    Evaluar cultivos
                  </button>
                  <button type="button" className="btn btn-sm" onClick={() => onNavigate("production")}>
                    Costos
                  </button>
                </div>
              </div>
            )}
          </aside>
        )}
      </div>
    </div>
  );
}
