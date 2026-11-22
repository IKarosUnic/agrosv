# Validación científica y socioeconómica

**Fase 6 · Estado: validación de software y de fuentes; validación agronómica y socioeconómica NO realizada**

## Lo que sí se verificó

| Objeto | Verificación | Resultado |
|---|---|---|
| Suite existente | 373 pruebas de Fase 1–5 | pasan |
| Suite Fase 6 | 96 pruebas nuevas | pasan |
| Catálogo | estados por parámetro, GAP = `null`, unicidad | consistente |
| Fenología | aritmética GDD, series incompletas | consistente |
| Aptitud | NoData ⇒ `not_evaluated` | consistente |
| Balance FAO-56 | TAW/RAW/Ks, estrés, riego | consistente |
| Adaptadores | externos no ejecutables | rechazo explícito |
| Capas sintéticas | separación automática | válida |
| Reproducibilidad | misma semilla ⇒ misma población e historial | válida |
| API | contratos, errores 400/404 | válida |

Esto es **verificación de software**. No demuestra que un parámetro sea correcto
para El Salvador.

## Lo que no se validó

### Agronómico

* No hay ensayos locales de variedades, Kc, fenología ni rendimiento.
* No hay comparación con parcelas experimentales de CENTA/MAG.
* No hay datos de humedad de suelo para calibrar el balance.
* El rendimiento nacional del maíz (2,4 t/ha) es un agregado, no un objetivo de
  calibración.
* La aptitud no se contrastó con mapas oficiales ni con producción observada.

### Socioeconómico

* No hay microdatos del CAP 2025 (solo agregados departamentales/nacionales).
* No hay encuesta de hogares agrícolas con ingreso, crédito y tenencia.
* No hay precios de mercado en formato tabular reutilizable.
* No hay datos de adopción tecnológica por arquetipo.
* Los arquetipos no se calibraron contra superficie, tenencia ni sistema
  productivo.

## Evidencia real disponible en el repositorio

* CAP 2025: 401.101 productores de maíz, ~2,4 t/ha; 214.738 de frijol;
  agregados de superficie y producción.
* Nemotron: 148.000 personas sintéticas, 12,13 % en división 01.
* Fase 5: clima de reanálisis 2019–2025 en dos puntos; SoilGrids 0–30 cm;
  Copernicus DEM 30 m.

Esa evidencia permite **contexto**, no calibración.

## Protocolo mínimo para validar (Fase 7+)

1. Obtener microdatos o tabulados municipales del CAP 2025 con acceso legal.
2. Seleccionar 3–5 sistemas productivos y 2–3 departamentos.
3. Calibrar arquetipos (superficie, tenencia, riego, capital) por máxima
   verosimilitud o ajuste por márgenes.
4. Obtener Kc y ciclos varietales de ensayos CENTA/MAG o literatura local.
5. Comparar ETa/ETm simulado con humedad de suelo medida.
6. Comparar decisiones simuladas con encuestas de intención, no con adopción
   observada únicamente.
7. Reportar error, sesgo y intervalos; no solo correlación.

## Declaración

Ningún resultado de Fase 6 debe citarse como medición, pronóstico ni
clasificación oficial. La integridad científica exige declarar esta ausencia,
no compensarla con más funcionalidades.
