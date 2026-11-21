import { useCallback, useEffect, useRef, useState } from "react";
import maplibregl, { type Map as MLMap, type StyleSpecification } from "maplibre-gl";

const API = import.meta.env.VITE_API ?? "";

const HILLSHADE_ATTR =
  "DEM: © DLR/Airbus — Copernicus DEM GLO-30 | Límites: geoBoundaries CC BY-SA 2.0 | " +
  "OSM © colaboradores, ODbL | Suelos: SoilGrids 2.0, CC BY 4.0";

type DeptFeatureProps = { adm1_code: string; name: string; area_km2: number };
type Bounds = [[number, number], [number, number]];

type DeptDetail = {
  code: string;
  name: string;
  area_km2: number;
  topography: Record<string, number | string>;
  soils: Record<string, number | string>;
  geometry: unknown;
};

type PointInfo = {
  lat: number;
  lon: number;
  elevation_m: number | null;
  slope_deg: number | null;
  aspect_deg: number | null;
  relief_class: number | null;
  soils: Record<string, number | null>;
};

type Meta = {
  datasets: Record<string, Record<string, unknown>>;
  attribution: Record<string, string>;
  metric_note: string;
};

const RELIEF_LABELS = ["Plano 0–2°", "Suave 2–5°", "Ondulado 5–12°",
  "Quebrado 12–25°", "Escarpado 25–45°", "Muy escarpado >45°"];
const RELIEF_COLORS = ["#e8f0e2", "#cbdeaf", "#a6c77a", "#debe5f", "#c4824a", "#964e37"];

const LAYER_META: { id: string; label: string; source: string }[] = [
  { id: "roads", label: "Caminos (OSM)", source: "roads" },
  { id: "waterways", label: "Ríos y quebradas", source: "waterways" },
  { id: "water_bodies", label: "Cuerpos de agua", source: "water_bodies" },
  { id: "settlements", label: "Asentamientos", source: "settlements" },
  { id: "infrastructure", label: "Infraestructura", source: "infrastructure" },
];

const EMPTY = { type: "FeatureCollection" as const, features: [] };

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

function fmt(v: number | string | null | undefined, digits = 1, unit = ""): string {
  if (v === null || v === undefined || v === "") return "—";
  if (typeof v === "number") return `${v.toFixed(digits)}${unit}`;
  return `${v}${unit}`;
}

export default function App() {
  const mapEl = useRef<HTMLDivElement>(null);
  const map = useRef<MLMap | null>(null);
  const [ready, setReady] = useState(false);
  const [depts, setDepts] = useState<DeptFeatureProps[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [detail, setDetail] = useState<DeptDetail | null>(null);
  const [point, setPoint] = useState<PointInfo | null>(null);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [active, setActive] = useState<string[]>(["water_bodies"]);
  const [overlay, setOverlay] = useState<"none" | "slope" | "relief">("none");
  const [status, setStatus] = useState("Cargando capas…");

  // --- Inicialización del mapa --------------------------------------------
  useEffect(() => {
    if (!mapEl.current || map.current) return;
    const style: StyleSpecification = {
      version: 8,
      sources: {
        hillshade: {
          type: "raster",
          tiles: [`${API}/api/tiles/hillshade/{z}/{x}/{y}.png`],
          tileSize: 256,
          minzoom: 7,
          maxzoom: 14,
          attribution: HILLSHADE_ATTR,
        },
        slope: {
          type: "raster",
          tiles: [`${API}/api/tiles/slope/{z}/{x}/{y}.png`],
          tileSize: 256,
          minzoom: 7,
          maxzoom: 14,
        },
        relief: {
          type: "raster",
          tiles: [`${API}/api/tiles/relief/{z}/{x}/{y}.png`],
          tileSize: 256,
          minzoom: 7,
          maxzoom: 14,
        },
        depts: { type: "geojson", data: EMPTY },
        roads: { type: "geojson", data: EMPTY },
        waterways: { type: "geojson", data: EMPTY },
        water_bodies: { type: "geojson", data: EMPTY },
        settlements: { type: "geojson", data: EMPTY },
        infrastructure: { type: "geojson", data: EMPTY },
      },
      layers: [
        { id: "bg", type: "background", paint: { "background-color": "#eef1ea" } },
        {
          id: "hillshade", type: "raster", source: "hillshade",
          paint: { "raster-opacity": 0.92, "raster-resampling": "linear" },
        },
        {
          id: "slope", type: "raster", source: "slope",
          layout: { visibility: "none" },
          paint: { "raster-opacity": 0.72, "raster-resampling": "nearest" },
        },
        {
          id: "relief", type: "raster", source: "relief",
          layout: { visibility: "none" },
          paint: { "raster-opacity": 0.72, "raster-resampling": "nearest" },
        },
        {
          id: "water-fill", type: "fill", source: "water_bodies",
          layout: { visibility: "none" },
          paint: { "fill-color": "#7ea9c9", "fill-opacity": 0.85 },
        },
        {
          id: "water-line", type: "line", source: "waterways",
          layout: { visibility: "none" },
          paint: { "line-color": "#4a7fa5", "line-width": ["interpolate", ["linear"], ["zoom"], 8, 0.4, 13, 1.6] },
        },
        {
          id: "road-line", type: "line", source: "roads",
          layout: { visibility: "none", "line-cap": "round" },
          paint: {
            "line-color": ["match", ["get", "road_class"],
              "arterial", "#b0592f", "colectora", "#c98a4b",
              "local", "#8d8d8d", "pista", "#a58f6f", "#b5b5b5"],
            "line-width": ["interpolate", ["linear"], ["zoom"], 8, 0.3, 14, 2.2],
            "line-opacity": 0.75,
          },
        },
        {
          id: "settlement-dot", type: "circle", source: "settlements",
          layout: { visibility: "none" },
          paint: {
            "circle-radius": ["interpolate", ["linear"], ["zoom"], 8, 1.8, 13, 4.5],
            "circle-color": "#3b3b3b", "circle-opacity": 0.8,
            "circle-stroke-color": "#ffffff", "circle-stroke-width": 0.6,
          },
        },
        {
          id: "infra-dot", type: "circle", source: "infrastructure",
          layout: { visibility: "none" },
          paint: {
            "circle-radius": ["interpolate", ["linear"], ["zoom"], 8, 2.5, 13, 6],
            "circle-color": ["match", ["get", "category"],
              "salud", "#c0392b", "educación", "#2c6e9b", "transporte", "#7d5ba6",
              "energía", "#d68910", "agua", "#1f8f7a", "#7a7a7a"],
            "circle-opacity": 0.85, "circle-stroke-color": "#ffffff",
            "circle-stroke-width": 0.8,
          },
        },
        {
          id: "dept-line", type: "line", source: "depts",
          paint: { "line-color": "#4b5b4b", "line-width": 1.1, "line-opacity": 0.75 },
        },
      ],
    };

    const m = new maplibregl.Map({
      container: mapEl.current,
      style,
      center: [-88.86, 13.68],
      zoom: 8.1,
      minZoom: 7,
      maxZoom: 14,
      attributionControl: false,
      dragRotate: false,
      pitchWithRotate: false,
    });
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    m.addControl(new maplibregl.AttributionControl({ compact: true, customAttribution: HILLSHADE_ATTR }));
    map.current = m;
    m.on("load", () => setReady(true));
    return () => {
      m.remove();
      map.current = null;
    };
  }, []);

  // --- Carga inicial de datos --------------------------------------------
  useEffect(() => {
    fetch(`${API}/api/territory/departments?simplify=0.0015`)
      .then((r) => r.json())
      .then((fc) => {
        const feats = (fc.features ?? []).map((f: { properties: DeptFeatureProps }) => f.properties);
        setDepts(feats.sort((a: DeptFeatureProps, b: DeptFeatureProps) => a.name.localeCompare(b.name)));
        if (map.current) {
          (map.current.getSource("depts") as maplibregl.GeoJSONSource | undefined)?.setData(fc);
        }
      })
      .catch(() => setStatus("No se pudo cargar el territorio"));
    fetch(`${API}/api/meta`).then((r) => r.json()).then(setMeta).catch(() => undefined);
  }, []);

  // --- Capas OSM bajo demanda, por extensión visible ----------------------
  const loadLayers = useCallback(() => {
    const m = map.current;
    if (!m || !ready) return;
    const b = m.getBounds();
    const bbox = `west=${b.getWest()}&south=${b.getSouth()}&east=${b.getEast()}&north=${b.getNorth()}`;
    for (const id of active) {
      const src = m.getSource(id) as maplibregl.GeoJSONSource | undefined;
      if (!src) continue;
      fetch(`${API}/api/infrastructure/${id}?${bbox}&limit=6000`)
        .then((r) => r.json())
        .then((fc) => src.setData(fc))
        .catch(() => undefined);
    }
  }, [active, ready]);

  useEffect(() => {
    const m = map.current;
    if (!m || !ready) return;
    for (const { id, source } of LAYER_META) {
      const visible = active.includes(source);
      const layerId =
        source === "roads" ? "road-line" :
        source === "waterways" ? "water-line" :
        source === "water_bodies" ? "water-fill" :
        source === "settlements" ? "settlement-dot" : "infra-dot";
      m.setLayoutProperty(layerId, "visibility", visible ? "visible" : "none");
      if (!visible) {
        (m.getSource(id) as maplibregl.GeoJSONSource | undefined)?.setData(EMPTY);
      }
    }
    loadLayers();
  }, [active, ready, loadLayers]);

  useEffect(() => {
    const m = map.current;
    if (!m || !ready) return;
    const handler = () => {
      loadLayers();
      setStatus(`Vista ${m.getZoom().toFixed(1)} · ${new Date().toLocaleTimeString()}`);
    };
    m.on("moveend", handler);
    return () => {
      m.off("moveend", handler);
    };
  }, [ready, loadLayers]);

  // --- Overlays de pendiente / relieve ------------------------------------
  useEffect(() => {
    const m = map.current;
    if (!m || !ready) return;
    m.setLayoutProperty("slope", "visibility", overlay === "slope" ? "visible" : "none");
    m.setLayoutProperty("relief", "visibility", overlay === "relief" ? "visible" : "none");
  }, [overlay, ready]);

  // --- Consulta de punto ---------------------------------------------------
  useEffect(() => {
    const m = map.current;
    if (!m || !ready) return;
    const onClick = (e: maplibregl.MapMouseEvent) => {
      const { lat, lng } = e.lngLat;
      Promise.all([
        fetch(`${API}/api/topography/elevation?lat=${lat}&lon=${lng}`).then((r) => r.json()),
        fetch(`${API}/api/soils/point?lat=${lat}&lon=${lng}`).then((r) => r.json()),
      ])
        .then(([topo, soil]) => {
          setPoint({
            lat, lon: lng,
            elevation_m: topo.elevation_m,
            slope_deg: topo.slope_deg,
            aspect_deg: topo.aspect_deg,
            relief_class: topo.relief_class,
            soils: {
              pH: soil.phh2o, "C orgánico (g/kg)": soil.soc,
              "N total (g/kg)": soil.nitrogen, "Arcilla (%)": soil.clay,
              "Arena (%)": soil.sand, "Limo (%)": soil.silt,
            },
          });
        })
        .catch(() => setPoint(null));
      new maplibregl.Marker({ color: "#2f6b3f" }).setLngLat(e.lngLat).addTo(m);
    };
    m.on("click", onClick);
    return () => {
      m.off("click", onClick);
    };
  }, [ready]);

  // --- Selección de departamento ------------------------------------------
  const chooseDept = useCallback((code: string) => {
    setSelected(code);
    if (!code) {
      setDetail(null);
      return;
    }
    fetch(`${API}/api/territory/departments/${code}`)
      .then((r) => r.json())
      .then((d: DeptDetail) => {
        setDetail(d);
        const b = boundsOf(d.geometry);
        if (b && map.current) {
          map.current.fitBounds(b, { padding: 60, duration: 700, maxZoom: 11 });
        }
      })
      .catch(() => setDetail(null));
  }, []);

  const toggle = (id: string) => {
    setActive((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const topo = detail?.topography ?? {};
  const soils = detail?.soils ?? {};

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="mark">AGROSV</span>
          <span className="tag">Fundación geoespacial · Fase 1</span>
        </div>
        <div className="status">{status}</div>
      </header>

      <main className="layout">
        <aside className="panel">
          <section>
            <h2>Territorio</h2>
            <label className="field">
              <span>Departamento</span>
              <select value={selected} onChange={(e) => chooseDept(e.target.value)}>
                <option value="">Todo el país</option>
                {depts.map((d) => (
                  <option key={d.adm1_code} value={d.adm1_code}>{d.name}</option>
                ))}
              </select>
            </label>

            {detail ? (
              <dl className="kv">
                <div><dt>Departamento</dt><dd>{detail.name}</dd></div>
                <div><dt>Superficie</dt><dd>{fmt(detail.area_km2, 1, " km²")}</dd></div>
                <div><dt>Elevación mín.–máx.</dt><dd>{fmt(topo.elev_min_m, 0)} – {fmt(topo.elev_max_m, 0)} m</dd></div>
                <div><dt>Elevación media</dt><dd>{fmt(topo.elev_mean_m, 0, " m")}</dd></div>
                <div><dt>Pendiente media</dt><dd>{fmt(topo.slope_mean_deg, 1, "°")}</dd></div>
                <div><dt>Pendiente P90</dt><dd>{fmt(topo.slope_p90_deg, 1, "°")}</dd></div>
                <div><dt>Relieve pronunciado</dt><dd>{fmt(topo.pronounced_relief_pct, 1, " %")}</dd></div>
                <div><dt>pH (0–30 cm)</dt><dd>{fmt(soils.phh2o as number, 2)}</dd></div>
                <div><dt>C orgánico</dt><dd>{fmt(soils.soc as number, 1, " g/kg")}</dd></div>
                <div><dt>Arcilla</dt><dd>{fmt(soils.clay as number, 1, " %")}</dd></div>
              </dl>
            ) : (
              <p className="hint">
                {depts.length} departamentos disponibles. Elige uno para ver sus indicadores
                y acercar el mapa.
              </p>
            )}
          </section>

          <section>
            <h2>Capas</h2>
            <div className="chips">
              {LAYER_META.map(({ id, label, source }) => (
                <button
                  key={id}
                  className={active.includes(source) ? "chip on" : "chip"}
                  onClick={() => toggle(source)}
                  aria-pressed={active.includes(source)}
                >
                  {label}
                </button>
              ))}
            </div>

            <div className="radios" role="group" aria-label="Capa de fondo">
              {(["none", "slope", "relief"] as const).map((k) => (
                <label key={k}>
                  <input type="radio" name="overlay" checked={overlay === k}
                    onChange={() => setOverlay(k)} />
                  {k === "none" ? "Sombreado" : k === "slope" ? "Pendiente" : "Clases de relieve"}
                </label>
              ))}
            </div>

            {overlay !== "none" && (
              <ul className="legend">
                {RELIEF_LABELS.map((lab, i) => (
                  <li key={lab}>
                    <i style={{ background: RELIEF_COLORS[i] }} />
                    {lab}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section>
            <h2>Consulta de punto</h2>
            {point ? (
              <dl className="kv">
                <div><dt>Coordenadas</dt><dd>{point.lat.toFixed(4)}, {point.lon.toFixed(4)}</dd></div>
                <div><dt>Elevación</dt><dd>{fmt(point.elevation_m, 0, " m")}</dd></div>
                <div><dt>Pendiente</dt><dd>{fmt(point.slope_deg, 1, "°")}</dd></div>
                <div><dt>Orientación</dt><dd>{fmt(point.aspect_deg, 0, "°")}</dd></div>
                <div><dt>Clase de relieve</dt>
                  <dd>{point.relief_class !== null ? RELIEF_LABELS[point.relief_class] ?? "—" : "—"}</dd></div>
                {Object.entries(point.soils).map(([k, v]) => (
                  <div key={k}><dt>{k}</dt><dd>{fmt(v, 2)}</dd></div>
                ))}
              </dl>
            ) : (
              <p className="hint">Haz clic en el mapa para leer elevación, pendiente y suelo.</p>
            )}
          </section>

          <section>
            <h2>Calidad y procedencia</h2>
            {meta ? (
              <ul className="quality">
                <li><b>Topografía</b> · {String(meta.datasets.topography.source)} · 30 m · DSM</li>
                <li><b>Territorio</b> · {String(meta.datasets.territory.source)} · ADM2 histórico</li>
                <li><b>OSM</b> · {String(meta.datasets.infrastructure.source)} · ODbL</li>
                <li><b>Suelos</b> · SoilGrids 250 m · predicción, no laboratorio</li>
                <li><b>Proyecciones</b> · {meta.metric_note}</li>
              </ul>
            ) : (
              <p className="hint">Metadatos no disponibles.</p>
            )}
            <p className="hint small">
              Fuentes y licencias completas en <code>docs/DATA_PROVENANCE.md</code>;
              limitaciones en <code>docs/LIMITATIONS.md</code> (también en <a href={`${API}/api/limitations`}>/api/limitations</a>).
            </p>
          </section>
        </aside>

        <div className="map" ref={mapEl} role="application" aria-label="Mapa de El Salvador" />
      </main>
    </div>
  );
}
