# CropWaterNutrientEngine

**Fase 6 · Subsistema A · Estado: implementado; agua con entradas del usuario**

Código: `backend/agrosv/agriculture/water_nutrient.py`
Pruebas: balance, estrés, Kc, lluvia efectiva, remoción de nutrientes
API: `POST /api/agriculture/water`, `GET /api/agriculture/nutrients`

## Agua

Balance diario FAO-56 en la zona radicular:

```
TAW = AWC × Zr
RAW = p × TAW
Ks  = (TAW − Dr) / (TAW − RAW)   si Dr > RAW, si no 1
ETa = Ks × ETc
Dr,i = Dr,i−1 − (P − RO) − I + ETa + DP
```

`RO = 0` (declarado). No hay capilaridad, flujo lateral ni salinidad.

### Entradas obligatorias

| Entrada | Origen | Nota |
|---|---|---|
| `awc_mm_per_m` | usuario | AGROSV no tiene AWC |
| `root_depth_cm` | usuario | constante durante el ciclo |
| `initial_depletion_mm` | usuario | por defecto 0, declarado |
| `kc` | usuario o `allow_reference_kc` | Kc 1,0 es superficie de referencia |
| `p_depletion` | usuario | 0,5 por defecto |
| clima P/ET0 | Open-Meteo | punto de reanálisis |

Sin AWC, profundidad y Kc (o la autorización explícita) el balance **no se
ejecuta**. `allow_reference_kc=true` usa Kc = 1,0 en todas las etapas y marca
`status = SCENARIO`; el resultado no describe un cultivo específico.

### Lluvia efectiva

FAO-56 no prescribe una fórmula única. AGROSV ofrece:

* `min_p_etc` (por defecto): `min(P, ETc)`, cota superior conservadora;
* `fixed_fraction`: `P × f` (opt-in, por defecto 0,8);
* `none`: 0.

Ninguna es «el método FAO». La elección se declara en la respuesta.

### Salidas

Totales de P, lluvia efectiva, riego, ET0, ETm, ETa y percolación; días de
estrés y de déficit; relación ETa/ETm; serie diaria (P, Ks, ETc, ETa, Dr) y
avisos de truncamiento si la serie no cubre el ciclo completo.

`irrigation_schedule()` calcula el riego mínimo para mantener `Dr ≤ RAW` y
aplica una eficiencia declarada. No incluye costos, energía ni turnos.

## Nutrientes

La demanda es **remoción**:

```
N_kg/ha = coeficiente_kg/t × rendimiento_t/ha
```

para N, P₂O₅ y K₂O, con coeficientes `REF` del catálogo. El rendimiento y su
fuente son obligatorios. La respuesta incluye
`is_fertilizer_recommendation: false` y la advertencia de que una dosis exige
análisis de suelo, eficiencia de uso y contexto de manejo.

`nutrient_balance()` responde `available: false`: SoilGrids aporta nitrógeno
**total**, no disponible; no hay P, K, CEC ni análisis de suelo.

## Ejemplo verificado

Maíz, AWC 150 mm/m, raíz 60 cm, Kc de referencia, siembra 2024-05-15: TAW 90 mm,
RAW 45 mm, ETa/ETm 0,868, 56 días de estrés. Depende por completo de la AWC y el
Kc aportados; no es una recomendación de riego.

## Límites

No es AquaCrop ni DSSAT, no simula crecimiento, no produce rendimiento y no
valida Kc local. La lluvia efectiva es una convención declarada, no un método
oficial.
