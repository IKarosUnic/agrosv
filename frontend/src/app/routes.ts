export type RouteId =
  | "home"
  | "map"
  | "territory"
  | "crops"
  | "calendar"
  | "monitoring"
  | "risks"
  | "production"
  | "markets"
  | "profitability"
  | "scenarios"
  | "research";

export interface RouteDef {
  id: RouteId;
  path: string;
  label: string;
  shortLabel: string;
  group: "Explorar" | "Agronomía y Clima" | "Vigilancia" | "Economía" | "Ciencia";
  description: string;
  helpTips: string[];
}

export const ROUTES: RouteDef[] = [
  {
    id: "home",
    path: "/",
    label: "Inicio",
    shortLabel: "Inicio",
    group: "Explorar",
    description: "Panorama agrícola de El Salvador, estado de ubicación activa y accesos rápidos.",
    helpTips: [
      "Elige una ubicación de El Salvador en el buscador global o en el mapa para personalizar los módulos.",
      "Cambia entre modo Simple (productor) y modo Avanzado (técnico/investigador) en la barra superior.",
    ],
  },
  {
    id: "map",
    path: "/mapa",
    label: "Mapa agrícola",
    shortLabel: "Mapa",
    group: "Explorar",
    description: "Exploración geoespacial interactiva de El Salvador con capas reales y perfil de ubicación.",
    helpTips: [
      "Haz clic en cualquier punto dentro de El Salvador para consultar topografía, suelo, clima, riesgo y acceso a mercados.",
      "Activa capas vectoriales (ríos, caminos, mercados) o capas ráster (pendiente, relieve) desde el panel izquierdo.",
    ],
  },
  {
    id: "territory",
    path: "/territorio",
    label: "Territorio y recursos",
    shortLabel: "Territorio",
    group: "Agronomía y Clima",
    description: "Fase 5: perfil territorial, suelos (0–30 cm), hidrología D8/Budyko y clima de reanálisis.",
    helpTips: [
      "SoilGrids 2.0 es una predicción a 250 m, no sustituye análisis de laboratorio.",
      "El clima proviene de dos puntos de reanálisis (2019–2025), no de estaciones meteorológicas nacionales.",
    ],
  },
  {
    id: "crops",
    path: "/cultivos",
    label: "Cultivos",
    shortLabel: "Cultivos",
    group: "Agronomía y Clima",
    description: "Fase 6: catálogo de 22 cultivos, requisitos, aptitud S1–N y simulación hídrica FAO-56.",
    helpTips: [
      "La aptitud S1/S2/S3/N muestra explícitamente cada factor limitante evaluado.",
      "Los parámetros faltantes se declaran como GAP (sin dato) en lugar de inventarse.",
    ],
  },
  {
    id: "calendar",
    path: "/calendario",
    label: "Calendario agrícola",
    shortLabel: "Calendario",
    group: "Agronomía y Clima",
    description: "Ventanas derivadas de siembra, fenología térmica (GDD) y riesgos por etapa.",
    helpTips: [
      "Las fechas mostradas son estimaciones derivadas de climatología 2019–2025, no recomendaciones oficiales CENTA/MAG.",
    ],
  },
  {
    id: "monitoring",
    path: "/monitoreo",
    label: "Monitoreo",
    shortLabel: "Monitoreo",
    group: "Vigilancia",
    description: "Fase 7: estado satelital, índices espectrales, sanidad, plagas/enfermedades y reporte de campo.",
    helpTips: [
      "Las observaciones de campo enviadas quedan en revisión; no constituyen confirmación científica automática.",
      "Los borradores creados sin conexión se guardan localmente y se sincronizan al recuperar señal.",
    ],
  },
  {
    id: "risks",
    path: "/riesgos",
    label: "Riesgos y alertas",
    shortLabel: "Riesgos",
    group: "Vigilancia",
    description: "Evaluadores de sequía, exceso de lluvia y calor, centro de alertas y verificación.",
    helpTips: [
      "Las alertas algorítmicas muestran su evidencia y nivel de confianza; no reemplazan avisos oficiales de Protección Civil o MARN.",
    ],
  },
  {
    id: "production",
    path: "/produccion",
    label: "Producción y costos",
    shortLabel: "Costos",
    group: "Economía",
    description: "Estadísticas nacionales CAP 2025 y calculadora guiada de costos en manzanas o hectáreas.",
    helpTips: [
      "Puedes trabajar en manzanas (1 mz = 0.70 ha) o hectáreas, y en quintales (46 kg) o toneladas.",
      "Guarda presupuestos localmente para compararlos o usarlos en la calculadora de rentabilidad.",
    ],
  },
  {
    id: "markets",
    path: "/mercados",
    label: "Mercados y precios",
    shortLabel: "Mercados",
    group: "Economía",
    description: "Catálogo de mercados WFP/OSM, precios históricos WFP El Salvador y logística vial.",
    helpTips: [
      "Verifica siempre la fecha de observación del precio y distingue precio mayorista/minorista de precio en finca.",
    ],
  },
  {
    id: "profitability",
    path: "/rentabilidad",
    label: "Rentabilidad",
    shortLabel: "Rentabilidad",
    group: "Economía",
    description: "Cálculo guiado de ingresos, márgenes, punto de equilibrio y sensibilidad de costos.",
    helpTips: [
      "Los rubros no ingresados se declaran incompletos para no sobreestimar la utilidad neta.",
    ],
  },
  {
    id: "scenarios",
    path: "/escenarios",
    label: "Escenarios",
    shortLabel: "Escenarios",
    group: "Economía",
    description: "15 escenarios económicos condicionales y análisis socio-agrícola sintético (Nemotron).",
    helpTips: [
      "Todos los resultados de escenarios y perfiles Nemotron son simulaciones condicionales o sintéticas, nunca pronósticos garantizados ni censos reales.",
    ],
  },
  {
    id: "research",
    path: "/datos",
    label: "Datos e investigación",
    shortLabel: "Datos",
    group: "Ciencia",
    description: "Catálogo nacional, calidad QC, política de validación V0–V4, paquetes ZIP offline y crosswalk 2023.",
    helpTips: [
      "Descarga paquetes territoriales ZIP por departamento para trabajo desconectado.",
    ],
  },
];

export function routeById(id: RouteId): RouteDef {
  return ROUTES.find((r) => r.id === id) ?? ROUTES[0];
}
