# AgriculturalNotificationEngine — cola local

**Módulo:** `backend/agrosv/monitoring/alerts.py`
**Endpoints:** `GET/POST /api/monitoring/notifications`,
`POST /api/monitoring/notifications/sync`
**Versión:** 7.0.0

## Canales

`api`, `ui`, `report`, `offline_sync`. **No hay servicios de pago ni
mensajería externa obligatoria.** La entrega es una cola en memoria que puede
sincronizarse al recuperar conectividad.

## Preferencias

- áreas (texto buscado en el ámbito geográfico);
- cultivos;
- categorías;
- severidad mínima;
- canales.

Una alerta que no cumple se rechaza con `queued: false` y el motivo.

## Privacidad

- `personal_data_included: false` siempre;
- no se copian identificadores de personas ni fincas;
- con `redact=true`, las coordenadas del ámbito se eliminan y se marca
  `redacted: true`;
- no se incluye la identidad del contribuyente.

## Sincronización

`sync(channel="offline_sync")` marca `delivered_at` para los elementos
pendientes de ese canal y devuelve cuántos entregó. No elimina la cola.

## Limitaciones

1. Cola en memoria, sin persistencia entre reinicios.
2. No hay reintentos, acuses de recibo ni confirmación de lectura.
3. La entrega efectiva fuera de AGROSV depende de un cliente que consuma la cola.
4. La redacción de coordenadas reduce utilidad operativa; es una decisión del
   llamador.
