# AgriculturalScenarioEngine

**Fase 6 · Subsistema C · Estado: siete escenarios ejecutables; ninguno es pronóstico**

Código: `backend/agrosv/socio/scenario.py`
API: `GET /api/socio/scenarios`, `POST /api/socio/scenario`

## Escenarios

| ID | Nombre | Sobrescritura | Práctica |
|---|---|---|---|
| `A_drought` | Sequía | agua × 0,6; choque `drought` | — |
| `B_technology` | Adopción tecnológica | información + 0,10 | goteo; semilla y asesoría como secundarias |
| `C_production_costs` | Costos | capital × 0,85; costos × 1,30 | — |
| `D_market_shock` | Mercado | precio × 0,70 | — |
| `E_diversification` | Diversificación | añade un segundo cultivo | — |
| `F_climate_variability` | Variabilidad climática | agua × 0,8; siembra +15 días | — |
| `G_support_program` | Apoyo | capital + 500; crédito + 0,20; información + 0,15 | conservación de suelo |

`F` **no** es un escenario climático modelado: es un multiplicador declarado.
`G` no representa un programa real: es una intervención hipotética.

## Ejecución

1. Genera población sintética con semilla y `scenario_id`.
2. Aplica sobrescrituras en una **nueva** capa
   `SYNTHETIC_AGRICULTURAL_STATE` con padre y método.
3. Compone hogares.
4. Decide por agente con aptitud calculada una vez por cultivo y punto.
5. Evalúa adopción y resiliencia si el escenario lo indica.
6. Calcula economía solo si recibe costos, precios y rendimiento.
7. Verifica separación de capas y publica métricas.

## Métricas

`n_agents`, `decisions_count`, distribución de decisiones, estados,
`adoption.fraction_considering`, `mean_impact_index`, bloque económico y agua
asumida del escenario.

## Límites operativos

* Tamaño máximo 500 por corrida; por defecto 60.
* Tiempo medido: 50 agentes ≈ 3,2 s; 25 ≈ 1,6 s; 10 ≈ 1,9 s (primera corrida
  con importaciones perezosas).
* Sin hojas económicas, `economic.available = false`.

## Advertencia

Los resultados dependen de arquetipos, umbrales, semilla y ubicación. No son
predicciones, no son proyecciones y no representan a El Salvador.
