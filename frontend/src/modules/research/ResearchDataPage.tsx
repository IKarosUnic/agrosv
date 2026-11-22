import React, { useEffect, useState } from "react";
import { API_BASE } from "../../services/api/client";
import { agrosvApi } from "../../services/api/endpoints";
import { downloadJson } from "../../utils/csv";
import { PageHeader } from "../../components/dashboard/MetricCard";
import {
  DataStatusBadge,
  LoadingState,
} from "../../components/data-status/DataStatus";

export default function ResearchDataPage() {
  const [catalog, setCatalog] = useState<Array<Record<string, unknown>>>([]);
  const [datasetsV5, setDatasetsV5] = useState<Array<Record<string, unknown>>>([]);
  const [policy, setPolicy] = useState<Record<string, unknown> | null>(null);
  const [crosswalk, setCrosswalk] = useState<Record<string, unknown> | null>(null);
  const [districtQuery, setDistrictQuery] = useState("Soyapango");
  const [lookupRes, setLookupRes] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const ac = new AbortController();
    Promise.allSettled([
      agrosvApi.dataCatalog(ac.signal),
      agrosvApi.enginesDatasets(ac.signal),
      agrosvApi.validationPolicy(ac.signal),
      agrosvApi.crosswalkSummary(ac.signal),
    ]).then(([cat, d5, pol, cw]) => {
      if (cat.status === "fulfilled") setCatalog((cat.value.data.datasets as Array<Record<string, unknown>>) ?? []);
      if (d5.status === "fulfilled") setDatasetsV5((d5.value.data.sources as Array<Record<string, unknown>>) ?? []);
      if (pol.status === "fulfilled") setPolicy(pol.value.data);
      if (cw.status === "fulfilled") setCrosswalk(cw.value.data);
      setLoading(false);
    });
    return () => ac.abort();
  }, []);

  const lookupDistrict = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!districtQuery.trim()) return;
    try {
      const { data } = await agrosvApi.crosswalkLookup(districtQuery.trim());
      setLookupRes(data);
    } catch {
      setLookupRes(null);
    }
  };

  const DEPTS = [
    ["SLV-AH", "Ahuachapán"], ["SLV-CA", "Cabañas"], ["SLV-CH", "Chalatenango"],
    ["SLV-CU", "Cuscatlán"], ["SLV-LI", "La Libertad"], ["SLV-PA", "La Paz"],
    ["SLV-UN", "La Unión"], ["SLV-MO", "Morazán"], ["SLV-SM", "San Miguel"],
    ["SLV-SS", "San Salvador"], ["SLV-SV", "San Vicente"], ["SLV-SA", "Santa Ana"],
    ["SLV-SO", "Sonsonate"], ["SLV-US", "Usulután"],
  ];

  return (
    <div className="stack-md">
      <PageHeader
        title="Datos, Procedencia, Validación e Investigación"
        subtitle="Catálogo nacional (Fase 4), niveles de evidencia V0–V4 (Fase 2), correspondencia municipal 2023 y paquetes offline ZIP."
        actions={
          <button
            type="button"
            className="btn"
            onClick={() => downloadJson("agrosv_datasets_catalog.json", { catalog, datasetsV5, policy })}
          >
            Exportar metadatos JSON
          </button>
        }
      />

      {loading ? (
        <LoadingState />
      ) : (
        <div className="stack-md">
          {/* Paquetes offline por departamento */}
          <section className="card">
            <h2 className="card-title">Paquetes territoriales offline (.zip)</h2>
            <p className="card-subtitle">
              Incluyen límites departamentales, municipios históricos, resumen topográfico y de suelos (excluye capas ODbL OSM y datos privados).
            </p>
            <div className="row-wrap" style={{ marginTop: 10 }}>
              {DEPTS.map(([code, name]) => (
                <a
                  key={code}
                  className="btn btn-sm"
                  href={`${API_BASE}/api/v1/offline/${code}.zip`}
                  download
                >
                  {name} ({code})
                </a>
              ))}
            </div>
          </section>

          {/* Correspondencia municipal 2023 */}
          <section className="card stack-sm">
            <h2 className="card-title">Correspondencia territorial 2023 (14 departamentos · 44 municipios · 262 distritos)</h2>
            {crosswalk && (
              <div style={{ fontSize: 13, color: "var(--ink-secondary)" }}>
                Registros verificados: {JSON.stringify(crosswalk.counts ?? crosswalk)}
              </div>
            )}
            <form onSubmit={lookupDistrict} className="row-wrap">
              <input className="input" style={{ maxWidth: 260 }} value={districtQuery} onChange={(e) => setDistrictQuery(e.target.value)} placeholder="Buscar distrito histórico…" />
              <button type="submit" className="btn btn-primary btn-sm">Consultar municipio vigente</button>
            </form>
            {lookupRes && (
              <pre style={{ margin: 0, padding: 10, borderRadius: 8, background: "var(--bg-subtle)", fontSize: 12 }}>
                {JSON.stringify(lookupRes, null, 2)}
              </pre>
            )}
          </section>

          {/* Política de validación V0-V4 */}
          {policy && (
            <section className="card">
              <h2 className="card-title">Estado de validación científica (V0–V4)</h2>
              <div className="table-wrap" style={{ marginTop: 10 }}>
                <table className="data-table">
                  <thead>
                    <tr><th>Módulo</th><th>Estado actual</th></tr>
                  </thead>
                  <tbody>
                    {Object.entries((policy.current_status as Record<string, string>) ?? {}).map(([k, v]) => (
                      <tr key={k}>
                        <td><strong>{k}</strong></td>
                        <td><DataStatusBadge tone={v.startsWith("V1") ? "info" : "warn"} label={v} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* Catálogo de datasets */}
          <section className="card">
            <h2 className="card-title">Catálogo nacional de datasets ({catalog.length})</h2>
            <div className="table-wrap" style={{ marginTop: 10 }}>
              <table className="data-table">
                <thead>
                  <tr><th>Dataset ID</th><th>Dominio</th><th>Estado</th><th>Evidencia</th><th>Licencia</th></tr>
                </thead>
                <tbody>
                  {catalog.map((d) => (
                    <tr key={String(d.dataset_id)}>
                      <td className="mono">{String(d.dataset_id)}</td>
                      <td>{String(d.domain)}</td>
                      <td><DataStatusBadge tone={d.state === "INTEGRATED" ? "ok" : "warn"} label={String(d.state)} /></td>
                      <td>{String(d.evidence_level ?? "—")}</td>
                      <td style={{ fontSize: 12 }}>{String(d.license ?? "—")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
