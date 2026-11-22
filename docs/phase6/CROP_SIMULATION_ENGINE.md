# CropSimulationEngine

**Fase 6 · Subsistema A · Estado: un adaptador ejecutable; tres detectados, no integrados**

Código: `backend/agrosv/agriculture/simulation.py`
Pruebas: detección, rechazo de adaptadores, rendimiento condicional
API: `POST /api/agriculture/simulate`, `GET /api/agriculture/adapters`

## Arquitectura de adaptadores

| Adaptador | Licencia | Estado en Fase 6 | Motivo |
|---|---|---|---|
| `agrosv_water_balance` | AGROSV | **ejecutable** | balance FAO-56 determinista |
| `aquacrop_ospy` | Apache-2.0 | detectado, no integrado | faltan parámetros de cultivo locales |
| `pcse_wofost` | EUPL-1.2 | detectado, no integrado | sin variedades salvadoreñas; obligaciones de licencia |
| `dssat_csm` | BSD-3-Clause | detectado, no integrado | coeficientes genéticos y binario Fortran |

`detect()` usa `importlib.util.find_spec` / `shutil.which` y reporta
`implemented`, `executable`, `status` y requisitos. Detectar una dependencia no
la integra: si el adaptador externo se solicita, se lanza `AdapterUnavailable`
con la lista de requisitos.

## Adaptador AGROSV

Ejecuta el balance hídrico de `CropWaterNutrientEngine` y la fenología térmica.
No simula biomasa, nitrógeno ni crecimiento.

Salida: agua del suelo, ETa/ETm, días de estrés, demanda de riego, etapas y
`yield` opcional. Cada respuesta incluye:

```json
{
  "model": {"name": "...", "version": "6.0.0",
            "calibration_status": "uncalibrated",
            "validation_status": "not_validated"},
  "calibration_status": "uncalibrated",
  "validation_status": "not_validated",
  "is_forecast": false
}
```

## Entradas no implementadas

`variety` se acepta para fenología; **no** se modelan prácticas de manejo,
estado nutricional del suelo ni fertilización. El adaptador no recibe un
perfil de nutrientes porque AGROSV no tiene análisis de suelo.

## Rendimiento

Solo se calcula si el llamador aporta **potencial y Ky juntos**, con
`ky_source`:

```
Ya = Ym × (1 − Ky × (1 − ETa/ETm))
```

El resultado se marca `model_estimated_uncalibrated`. Sin ambos, `yield.value_t_ha`
es `null` y la razón se publica. No se usa el rendimiento nacional del CAP como
«potencial»: 2,4 t/ha es un promedio observado, no un potencial alcanzable.

## Por qué no se integraron los modelos externos

1. **Parámetros**: AquaCrop, PCSE y DSSAT requieren coeficientes de cultivo o
   variedad que AGROSV no posee para El Salvador.
2. **Calibración**: sin ensayos locales, ejecutar el modelo produciría cifras
   con apariencia de validez pero sin calibración.
3. **Costo de integración**: DSSAT exige binario Fortran y archivos `.SOL/.WTH/.CUL`;
   PCSE arrastra dependencias y EUPL-1.2; AquaCrop-OSPy es el candidato más
   razonable para una fase futura.
4. **Regla de la fase**: no clonar ni integrar repositorios completos.

## Límites

El balance no es un modelo de cultivo. No hay validación, ni intervalos de
confianza, ni análisis de sensibilidad cuantitativo. Cualquier rendimiento es
una estimación condicionada a entradas del usuario y **no un pronóstico**.
