# Campos faltantes — endpoint `/vehicle-invoice/`

Auditoría del payload (`InvoiceData`) contra el PDF tipo invoice (template `templates/intecsa/vehicles.html`).
Estos campos **el frontend del PDF los usa pero el backend NO los manda** (o no existían en el modelo). Pedir al backend incluirlos en el JSON.

## 1. `payment_method` — Forma de pago  ⚠️ FALTABA

- **Dónde sale:** tarjeta Facturación → fila "Forma de pago".
- **Antes:** se renderizaba siempre `—` (no existía el campo).
- **Ahora:** agregado a `InvoiceData.payment_method: Optional[str]`.
- **Backend debe mandar:** string. Ej: `"Efectivo"`, `"Transferencia"`, `"Crédito 30 días"`.

```json
{ "payment_method": "Transferencia" }
```

## 2. `description.planName` — Plan  ⚠️ FALTABA

- **Dónde sale:** tarjeta Vehículo → fila "Plan".
- **Problema:** el template leía `description.planName` pero el modelo `Description` solo tenía `planDescription`/`planPrice`. Pydantic descartaba el campo → "Plan" salía vacío.
- **Ahora:** agregado `Description.planName: Optional[str]`.
- **Backend debe mandar:** dentro de `description`.

```json
{ "description": { "planName": "Renta de unidad" } }
```

## 3. `vehicle.unit_code` y `vehicle.driver_address`  ⚠️ FALTABAN en el modelo

- **unit_code:** tarjeta Vehículo → "Unidad" (ej `NEA604A`). Sin él hace fallback a `placas`.
- **driver_address:** tarjeta Operativo → fila "Dirección" (solo se muestra si viene).
- **Ahora:** ambos agregados a `VehicleInfo`.

```json
{ "vehicle": { "unit_code": "NEA604A", "driver_address": "Raúl Zárate Machuca 11..." } }
```

## 4. `cost_breakdown` — Desglose de Facturación (requerido para que se vea como la imagen)

Sin `cost_breakdown` el PDF cae al modo simple (`subtotal_travel`) y NO muestra el desglose.
Para que aparezca Casetas / Operador / Viáticos / Renta / Subtotal / Utilidad / Indirectos / IVA, el backend debe mandar:

```json
{
  "cost_breakdown": {
    "casetas_amount": 2000,
    "operator_rate": 839.22, "operator_days": 2,
    "per_diem_rate": 285,    "per_diem_days": 2,
    "gasoline_rate": 0,      "gasoline_km": 0,
    "unit_rent_amount": 1600, "unit_rent_period": "dia",
    "profit_amount": 467.88,
    "indirect_amount": 701.81
  },
  "profit_pct": 8,
  "indirect_pct": 12
}
```

### Lógica de totales (referencia)
- `Subtotal` = suma de conceptos base (casetas + operador + viáticos + gasolina + renta). **NO incluye utilidad ni indirectos.**
- `IVA 16%` se calcula sobre `Subtotal + Utilidad + Indirectos`.
- `Total` = `Subtotal + Utilidad + Indirectos + IVA`.
- `unit_rent_period` acepta: `"dia"` → "Renta por día", `"semana"` → "Renta por semana", `"mes"` → "Renta por mes".

---

## Resumen para backend

| Campo | Ubicación | Estado |
|-------|-----------|--------|
| `payment_method` | raíz | **NUEVO — mandar** |
| `description.planName` | objeto `description` | **NUEVO — mandar** |
| `vehicle.unit_code` | objeto `vehicle` | mandar (antes faltaba en modelo) |
| `vehicle.driver_address` | objeto `vehicle` | opcional |
| `cost_breakdown` | raíz | requerido para el desglose |
