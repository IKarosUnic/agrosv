# AgriculturalDecisionEngine

**Fase 6 · Subsistema C · Estado: implementado; decisión determinista con restricciones científicas**

Código: `backend/agrosv/socio/decision.py`
API: `POST /api/socio/decision`

## Flujo

1. Toma el estado agrícola sintético del agente y, si existe, el hogar.
2. Para cada cultivo del agente evalúa **aptitud** en el punto (con caché por
   cultivo y coordenada).
3. Excluye cultivos con clase `N` o `not_evaluated` si
   `require_evaluated=true` (por defecto).
4. Construye opciones con retorno proxy y riesgo por clase:

| Clase | Retorno proxy | Riesgo |
|---|---|---|
| S1 | 1,0 | 0,15 |
| S2 | 0,7 | 0,30 |
| S3 | 0,4 | 0,50 |

5. Aplica `FarmerBehaviorEngine.choose` con restricciones duras de capital,
   agua, trabajo y aptitud.
6. Publica decisión, ranking, pesos, razones, evidencia científica y
   `llm_used: false`.

## Retorno proxy, no economía

`expected_return` **no** es ingreso ni margen. Sin hoja de precios no hay
economía. La decisión responde a «qué opción es agronómicamente viable y
compatible con las preferencias y recursos sintéticos», no a «qué opción es más
rentable».

## Restricciones

* Capital insuficiente.
* Aptitud `N` (nunca se compensa con preferencias).
* Agua del escenario insuficiente.
* Mano de obra insuficiente.
* Si ningún cultivo es evaluable: `no_evaluable_options`; no se decide con
  datos faltantes.

## Reproducibilidad

Sin aleatoriedad. Las pruebas verifican que dos llamadas con el mismo agente y
punto devuelven la misma decisión.

## Cobertura de tipos de decisión

El motor acepta opciones arbitrarias (variedad, fecha de siembra, riego,
inversión en fertilizante, diversificación, participación de mercado,
adaptación), pero el **generador por defecto solo construye opciones de
cultivo** a partir de la aptitud. Las demás requieren que el llamador aporte
retorno esperado, riesgo y requisitos de recursos; no hay un generador
económico porque no hay precios.

## Límites

No modela precios, crédito, seguros, contratos, asistencia técnica ni
aprendizaje entre rondas. La aptitud es una regla AGROSV sin validación local.
Una decisión simulada no predice la decisión de una persona real.
