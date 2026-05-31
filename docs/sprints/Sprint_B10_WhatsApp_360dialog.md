# Sprint Contract B9 — WhatsApp + Adaptador de canal + 360dialog

**Producto:** DOCYAN LDE — Live Document Environment by XCID
**Bloque:** B9 | **Ejecutor:** Opus 4.8 vía Claude Code CLI
**Modo:** Una aprobación + ejecución completa + un reporte final.

---

## Prerequisitos
B7, B8 completos. WhatsApp es canal secundario sobre consulta funcional vía PWA.

## Contexto para Opus
WhatsApp es canal secundario activado desde PWA (no exclusivo ni alternativo). BSP: 360dialog único (decisión #8), acceso directo API sin markup. El mismo MO sirve PWA y WhatsApp; la transición preservando sesión se construyó en B3 (`transferir_sesion`).

Estado (auditoría): `app/connectors/whatsapp.py` es stub genérico, NO integra 360dialog.

## Alcance específico

1. **Integración 360dialog** (acceso directo API). Cliente.

2. **Plantillas WhatsApp Business pre-aprobadas multilingües** por idioma activo del tenant.

3. **Adaptaciones por tipo de intención al canal (doc 14):**
   - T1: texto breve + botón de cita a documento fuente.
   - T2: lista numerada de pasos + advertencias inline.
   - T3: imagen del diagrama (etiquetas burned-in) + texto.
   - T4: enlace a video con marca de tiempo.
   - T5: nodos del árbol diagnóstico secuenciales con botones interactivos.
   - T6: texto resumen + link a PWA para vista completa.
   - T7: texto con acción requerida.
   - T8: resumen + link a PWA para diff completo.

4. **Resolución de idioma del operador** en WhatsApp.

5. **Sesiones persistentes troubleshooting** (TTL 2h, Session Manager B3).

6. **División de mensajes >4096 caracteres** (límite WhatsApp).

7. **Adaptador de canal unificado** PWA/WhatsApp para el MO. Webhook receptor de mensajes entrantes. Transición WhatsApp↔PWA preservando sesión.

## Componentes a construir
- `app/channels/whatsapp_360dialog.py` (evoluciona el stub `whatsapp.py`)
- `app/api/routers/webhooks_whatsapp.py`
- `app/channels/channel_adapter.py` (interfaz unificada PWA/WhatsApp)

## Tests automatizados requeridos
- Webhook: mensaje entrante de 360dialog parseado correctamente.
- Respuesta: mensaje saliente en formato WhatsApp esperado.
- Adaptación por tipo: al menos T1 (texto+cita), T2 (lista), T5 (nodos con botones).
- División de mensajes >4096 caracteres.
- Transición de canal: sesión iniciada en WhatsApp continúa en PWA preservando contexto.
- E2E con sandbox 360dialog si disponible.

## Salida verificable
Operador escanea QR, conversa con DOCYAN en WhatsApp en su idioma, recibe respuestas adaptadas al canal por tipo de intención, puede continuar la sesión en PWA.

## Notas para Opus sobre integración con código existente
- Stub `whatsapp.py` se evoluciona a integración 360dialog real.
- Transición de canal usa `transferir_sesion` del Session Manager (B3).
- MO (B3) ya tiene interfaz para canales; channel_adapter la implementa para WhatsApp.
- Pipelines de intención (B7) se invocan igual que en PWA; el canal es transporte.
- Si no hay sandbox 360dialog disponible para E2E, marcar PENDIENTE DE JORGE (requiere cuenta 360dialog) y dejar el test preparado. (Esto NO reduce alcance: el código se construye completo; solo el test E2E depende de credencial externa.)

## Reglas de ejecución
- No stubs (el stub actual se reemplaza por integración real), no mocks (excepto tests), no hardcoded.
- Verdad operacional. PENDIENTE DE JORGE solo para credencial externa 360dialog.

**Referencias:** doc 05 (MO interfaces), doc 04 (UIs sección WhatsApp), doc 14 (B9, adaptaciones por tipo).
