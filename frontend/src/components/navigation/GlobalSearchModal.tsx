import { useEffect, useMemo, useRef, useState } from "react";
import { agrosvApi } from "../../services/api/endpoints";
import { useApp } from "../../stores/AppContext";
import type { CropSummary, DeptFeatureProps, MarketItem } from "../../types/api";
import type { RouteId } from "../../app/routes";
import { IconSearch } from "../icons/Icons";

interface SearchHit {
  kind: "Departamento" | "Cultivo" | "Plaga/Enfermedad" | "Mercado" | "Capa";
  title: string;
  subtitle: string;
  action: () => void;
}

const STATIC_LAYERS = [
  { id: "hillshade", name: "Sombreado topográfico (Copernicus DEM 30 m)" },
  { id: "slope", name: "Pendiente del terreno (grados)" },
  { id: "relief", name: "Clases de relieve" },
  { id: "waterways", name: "Ríos y quebradas (OSM)" },
  { id: "roads", name: "Red vial (OSM)" },
  { id: "markets", name: "Mercados WFP y OSM" },
];

export function GlobalSearchModal({
  open,
  onClose,
  onNavigate,
}: {
  open: boolean;
  onClose: () => void;
  onNavigate: (route: RouteId) => void;
}) {
  const { setSelectedLocation, setSelectedCropId } = useApp();
  const [query, setQuery] = useState("");
  const [depts, setDepts] = useState<DeptFeatureProps[]>([]);
  const [crops, setCrops] = useState<CropSummary[]>([]);
  const [markets, setMarkets] = useState<MarketItem[]>([]);
  const [pests, setPests] = useState<Array<{ pest_id: string; common_names: string[]; scientific_name: string }>>([]);
  const [territoryHits, setTerritoryHits] = useState<Array<{ name: string; level: string; source_code?: string }>>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    setTimeout(() => inputRef.current?.focus(), 20);
    const ac = new AbortController();
    Promise.allSettled([
      agrosvApi.departments(0.01, ac.signal),
      agrosvApi.crops(undefined, undefined, ac.signal),
      agrosvApi.markets(undefined, true, 60, ac.signal),
      agrosvApi.pests(undefined, ac.signal),
    ]).then(([d, c, m, p]) => {
      if (d.status === "fulfilled") {
        setDepts((d.value.data.features ?? []).map((f) => f.properties));
      }
      if (c.status === "fulfilled") {
        setCrops(c.value.data.crops ?? []);
      }
      if (m.status === "fulfilled") {
        setMarkets(m.value.data.result?.markets ?? []);
      }
      if (p.status === "fulfilled") {
        setPests((p.value.data.pests as typeof pests) ?? []);
      }
    });
    return () => ac.abort();
  }, [open]);

  useEffect(() => {
    if (!open || query.trim().length < 2) {
      setTerritoryHits([]);
      return;
    }
    const ac = new AbortController();
    agrosvApi.territorySearch(query.trim(), undefined, ac.signal)
      .then((res) => {
        const d = res.data;
        if (d.resolved && d.territory) {
          const t = d.territory as { name: string; level: string; source_code?: string };
          setTerritoryHits([t]);
        } else if (d.ambiguous && Array.isArray(d.candidates)) {
          setTerritoryHits((d.candidates as Array<{ name: string; level: string; source_code?: string }>).slice(0, 5));
        } else {
          setTerritoryHits([]);
        }
      })
      .catch(() => setTerritoryHits([]));
    return () => ac.abort();
  }, [open, query]);

  const results = useMemo<SearchHit[]>(() => {
    const q = query.trim().toLowerCase();
    const hits: SearchHit[] = [];

    for (const t of territoryHits) {
      hits.push({
        kind: "Departamento",
        title: t.name,
        subtitle: `${t.level}${t.source_code ? ` · ${t.source_code}` : ""} — Explorar territorio`,
        action: () => {
          onNavigate("territory");
          onClose();
        },
      });
    }

    for (const d of depts) {
      if (!q || d.name.toLowerCase().includes(q) || d.adm1_code.toLowerCase().includes(q)) {
        hits.push({
          kind: "Departamento",
          title: d.name,
          subtitle: `${d.adm1_code} · ${d.area_km2.toFixed(0)} km² — Ver en mapa`,
          action: () => {
            setSelectedLocation({
              lat: 13.69,
              lon: -88.9,
              label: `Departamento de ${d.name}`,
              departmentCode: d.adm1_code,
              departmentName: d.name,
            });
            onNavigate("map");
            onClose();
          },
        });
      }
    }

    for (const c of crops) {
      const hay = `${c.crop_id} ${c.scientific_name} ${c.local_names.join(" ")}`.toLowerCase();
      if (!q || hay.includes(q)) {
        hits.push({
          kind: "Cultivo",
          title: c.local_names[0] ?? c.crop_id,
          subtitle: `${c.scientific_name} · ${c.crop_type}`,
          action: () => {
            setSelectedCropId(c.crop_id);
            onNavigate("crops");
            onClose();
          },
        });
      }
    }

    for (const m of markets) {
      if (q && `${m.name} ${m.department ?? ""}`.toLowerCase().includes(q)) {
        hits.push({
          kind: "Mercado",
          title: m.name,
          subtitle: `${m.department ?? "El Salvador"} · ${m.source}`,
          action: () => {
            if (m.latitude && m.longitude) {
              setSelectedLocation({
                lat: m.latitude,
                lon: m.longitude,
                label: m.name,
                departmentName: m.department ?? undefined,
              });
            }
            onNavigate("markets");
            onClose();
          },
        });
      }
    }

    for (const p of pests) {
      const hay = `${p.pest_id} ${p.scientific_name} ${p.common_names.join(" ")}`.toLowerCase();
      if (q && hay.includes(q)) {
        hits.push({
          kind: "Plaga/Enfermedad",
          title: p.common_names[0] ?? p.pest_id,
          subtitle: p.scientific_name,
          action: () => {
            onNavigate("monitoring");
            onClose();
          },
        });
      }
    }

    for (const l of STATIC_LAYERS) {
      if (q && l.name.toLowerCase().includes(q)) {
        hits.push({
          kind: "Capa",
          title: l.name,
          subtitle: "Capa del mapa agrícola",
          action: () => {
            onNavigate("map");
            onClose();
          },
        });
      }
    }

    return hits.slice(0, 14);
  }, [query, territoryHits, depts, crops, markets, pests, onNavigate, onClose, setSelectedLocation, setSelectedCropId]);

  if (!open) return null;

  return (
    <div
      className="modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-label="Búsqueda global de AGROSV"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="modal-panel">
        <div className="row-wrap" style={{ justifyContent: "space-between", marginBottom: 10 }}>
          <strong style={{ fontSize: 15 }}>Buscar ubicación, cultivo, mercado o capa</strong>
          <button type="button" className="btn btn-sm" onClick={onClose}>Cerrar (Esc)</button>
        </div>

        <label className="field">
          <span className="field-label" style={{ display: "none" }}>Término de búsqueda</span>
          <div style={{ position: "relative" }}>
            <input
              ref={inputRef}
              type="search"
              className="input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ej. maíz, Santa Ana, café, San Salvador, cogollero, pendiente…"
            />
          </div>
        </label>

        <ul style={{ listStyle: "none", margin: "12px 0 0", padding: 0, display: "grid", gap: 6, maxHeight: 380, overflowY: "auto" }}>
          {results.length === 0 ? (
            <li style={{ color: "var(--ink-muted)", fontSize: 13.5, padding: 12 }}>
              Sin coincidencias locales para “{query}”. Prueba con un departamento, cultivo o mercado.
            </li>
          ) : (
            results.map((hit, idx) => (
              <li key={`${hit.kind}-${hit.title}-${idx}`}>
                <button
                  type="button"
                  className="btn"
                  onClick={hit.action}
                  style={{ width: "100%", justifyContent: "space-between", textAlign: "left" }}
                >
                  <span>
                    <IconSearch size={14} />{" "}
                    <strong>{hit.title}</strong>{" "}
                    <span style={{ color: "var(--ink-muted)", fontWeight: 400 }}>— {hit.subtitle}</span>
                  </span>
                  <span className="badge badge--info">{hit.kind}</span>
                </button>
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );
}
