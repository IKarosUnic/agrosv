import React, { useId, useState } from "react";

export interface ChartPoint {
  label: string;
  value: number | null;
  secondary?: number | null;
}

export function ChartFrame({
  title,
  unit,
  dateRange,
  source,
  methodology,
  rows,
  children,
}: {
  title: string;
  unit: string;
  dateRange?: string;
  source: string;
  methodology?: string;
  rows: Array<Record<string, string | number | null>>;
  children: React.ReactNode;
}) {
  const [showTable, setShowTable] = useState(false);

  return (
    <figure className="card" style={{ margin: 0 }}>
      <div className="card-header">
        <div>
          <figcaption className="card-title">{title}</figcaption>
          <div className="card-subtitle">
            Unidad: <strong>{unit}</strong>
            {dateRange ? ` · Periodo: ${dateRange}` : ""}
          </div>
        </div>
        <button
          type="button"
          className="btn btn-sm"
          onClick={() => setShowTable((v) => !v)}
          aria-expanded={showTable}
        >
          {showTable ? "Ver gráfico" : "Tabla accesible"}
        </button>
      </div>

      {showTable ? (
        <div className="table-wrap" style={{ maxHeight: 280 }}>
          <table className="data-table">
            <thead>
              <tr>
                {rows[0] && Object.keys(rows[0]).map((col) => <th key={col}>{col}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, idx) => (
                <tr key={idx}>
                  {Object.values(r).map((v, j) => (
                    <td key={j} className="tabular-nums">{v === null ? "Sin dato" : String(v)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div>{children}</div>
      )}

      <div style={{ marginTop: 10, fontSize: 12, color: "var(--ink-muted)" }}>
        <strong>Fuente:</strong> {source}
        {methodology && <span> · <strong>Método:</strong> {methodology}</span>}
      </div>
    </figure>
  );
}

export function SvgBarChart({
  data,
  unit,
  color = "var(--accent-primary)",
  height = 220,
}: {
  data: ChartPoint[];
  unit: string;
  color?: string;
  height?: number;
}) {
  const titleId = useId();
  const width = 620;
  const pad = { top: 18, right: 16, bottom: 44, left: 52 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  const validVals = data.map((d) => d.value).filter((v): v is number => v !== null && Number.isFinite(v));
  const maxVal = validVals.length ? Math.max(...validVals, 0) : 1;
  const minVal = validVals.length ? Math.min(0, ...validVals) : 0;
  const span = maxVal - minVal || 1;
  const zeroY = pad.top + ((maxVal - 0) / span) * plotH;
  const barStep = plotW / Math.max(data.length, 1);
  const barW = Math.max(8, Math.min(34, barStep * 0.68));

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-labelledby={titleId}
      style={{ width: "100%", height: "auto", display: "block" }}
    >
      <title id={titleId}>Gráfico de barras en {unit}</title>
      {[0, 0.25, 0.5, 0.75, 1].map((t) => {
        const y = pad.top + t * plotH;
        const val = maxVal - t * span;
        return (
          <g key={t}>
            <line x1={pad.left} x2={width - pad.right} y1={y} y2={y} stroke="var(--border-subtle)" strokeDasharray="3 3" />
            <text x={pad.left - 6} y={y + 4} textAnchor="end" fontSize="10" fill="var(--ink-muted)">
              {val.toFixed(Math.abs(span) < 10 ? 1 : 0)}
            </text>
          </g>
        );
      })}
      <line x1={pad.left} x2={width - pad.right} y1={zeroY} y2={zeroY} stroke="var(--border-strong)" />

      {data.map((d, i) => {
        const cx = pad.left + i * barStep + barStep / 2;
        if (d.value === null) {
          return (
            <text key={d.label + i} x={cx} y={height - 10} textAnchor="middle" fontSize="9.5" fill="var(--ink-muted)">
              {d.label.slice(0, 7)}
            </text>
          );
        }
        const yVal = pad.top + ((maxVal - d.value) / span) * plotH;
        const barTop = Math.min(yVal, zeroY);
        const barH = Math.max(1.5, Math.abs(zeroY - yVal));
        return (
          <g key={d.label + i}>
            <rect x={cx - barW / 2} y={barTop} width={barW} height={barH} rx={3} fill={color} opacity={0.9}>
              <title>{`${d.label}: ${d.value} ${unit}`}</title>
            </rect>
            {(data.length <= 14 || i % Math.ceil(data.length / 8) === 0) && (
              <text x={cx} y={height - 10} textAnchor="middle" fontSize="9.5" fill="var(--ink-muted)">
                {d.label.slice(0, 8)}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}

export function SvgLineChart({
  data,
  unit,
  primaryLabel = "Serie",
  secondaryLabel,
  height = 220,
  startAtZero = false,
}: {
  data: ChartPoint[];
  unit: string;
  primaryLabel?: string;
  secondaryLabel?: string;
  height?: number;
  startAtZero?: boolean;
}) {
  const titleId = useId();
  const width = 620;
  const pad = { top: 20, right: 16, bottom: 42, left: 54 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  const allVals = data
    .flatMap((d) => [d.value, d.secondary ?? null])
    .filter((v): v is number => v !== null && Number.isFinite(v));
  const rawMax = allVals.length ? Math.max(...allVals) : 1;
  const rawMin = startAtZero ? Math.min(0, ...(allVals.length ? allVals : [0])) : (allVals.length ? Math.min(...allVals) : 0);
  const span = rawMax - rawMin || 1;

  const buildSegments = (accessor: (d: ChartPoint) => number | null): string[] => {
    const segments: string[] = [];
    let current = "";
    data.forEach((d, i) => {
      const v = accessor(d);
      if (v === null) {
        if (current) {
          segments.push(current);
          current = "";
        }
        return;
      }
      const x = pad.left + (data.length === 1 ? plotW / 2 : (i / (data.length - 1)) * plotW);
      const y = pad.top + ((rawMax - v) / span) * plotH;
      current += `${current ? " L" : "M"} ${x.toFixed(1)} ${y.toFixed(1)}`;
    });
    if (current) segments.push(current);
    return segments;
  };

  const pSegs = buildSegments((d) => d.value);
  const sSegs = secondaryLabel ? buildSegments((d) => d.secondary ?? null) : [];

  return (
    <div>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-labelledby={titleId}
        style={{ width: "100%", height: "auto", display: "block" }}
      >
        <title id={titleId}>{`${primaryLabel} (${unit})`}</title>
        {[0, 0.25, 0.5, 0.75, 1].map((t) => {
          const y = pad.top + t * plotH;
          const val = rawMax - t * span;
          return (
            <g key={t}>
              <line x1={pad.left} x2={width - pad.right} y1={y} y2={y} stroke="var(--border-subtle)" strokeDasharray="3 3" />
              <text x={pad.left - 6} y={y + 4} textAnchor="end" fontSize="10" fill="var(--ink-muted)">
                {val.toFixed(Math.abs(span) < 10 ? 1 : 0)}
              </text>
            </g>
          );
        })}

        {pSegs.map((d, i) => (
          <path key={`p${i}`} d={d} fill="none" stroke="var(--accent-primary)" strokeWidth={2.2} />
        ))}
        {sSegs.map((d, i) => (
          <path key={`s${i}`} d={d} fill="none" stroke="var(--domain-water)" strokeWidth={2} strokeDasharray="5 3" />
        ))}

        {data.map((d, i) => {
          const x = pad.left + (data.length === 1 ? plotW / 2 : (i / (data.length - 1)) * plotW);
          return (
            <g key={d.label + i}>
              {d.value !== null && data.length <= 28 && (
                <circle
                  cx={x}
                  cy={pad.top + ((rawMax - d.value) / span) * plotH}
                  r={3}
                  fill="var(--accent-primary)"
                >
                  <title>{`${d.label}: ${d.value} ${unit}`}</title>
                </circle>
              )}
              {(data.length <= 12 || i % Math.ceil(data.length / 7) === 0 || i === data.length - 1) && (
                <text x={x} y={height - 10} textAnchor="middle" fontSize="9.5" fill="var(--ink-muted)">
                  {d.label.slice(0, 10)}
                </text>
              )}
            </g>
          );
        })}
      </svg>
      <div className="row-wrap" style={{ fontSize: 12, color: "var(--ink-secondary)", marginTop: 4 }}>
        <span className="row-wrap" style={{ gap: 5 }}>
          <span style={{ width: 14, height: 3, background: "var(--accent-primary)", display: "inline-block" }} />
          {primaryLabel}
        </span>
        {secondaryLabel && (
          <span className="row-wrap" style={{ gap: 5 }}>
            <span style={{ width: 14, height: 3, background: "var(--domain-water)", display: "inline-block" }} />
            {secondaryLabel}
          </span>
        )}
      </div>
    </div>
  );
}
