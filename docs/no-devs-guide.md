# Delfa Bridge — Guía de Implementación
> Para equipos sin experiencia técnica

---

## ¿Qué es Delfa Bridge?

Delfa Bridge conecta tus documentos empresariales con inteligencia artificial.
En lugar de buscar información manualmente en contratos, facturas y reportes,
simplemente pregúntale a Delfa Bridge en lenguaje natural.

**Ejemplo:**
- ❌ Antes: Abrir 50 contratos para encontrar las fechas de vencimiento
- ✅ Con Delfa Bridge: "¿Cuáles contratos vencen este mes?" → respuesta inmediata

---

## ¿Cómo funciona?
```
Tus documentos → Delfa Bridge → Respuestas inteligentes
```

1. **Subes tus documentos** — PDFs, Word, Excel, o conectas tu Google Drive
2. **Delfa Bridge los procesa** — extrae toda la información relevante
3. **Preguntas en lenguaje natural** — y obtienes respuestas precisas con trazabilidad

---

## Paso 1 — Obtén tu cuenta

1. Ve a [delfa.bridge](https://delfa.bridge)
2. Selecciona tu plan
3. Recibirás tu **API Key** por email

---

## Paso 2 — Conecta tu primera fuente de datos

### Opción A — Sube documentos directamente

Ve al portal de Delfa Bridge y arrastra tus archivos.
Formatos soportados: PDF, Word (.docx), Excel (.xlsx)

### Opción B — Conecta Google Drive

1. Ve a **Conectores → Google Drive**
2. Autoriza el acceso a tu cuenta de Google
3. Selecciona la carpeta con tus documentos
4. Haz clic en **"Procesar carpeta"**

### Opción C — Conecta MicroSip

Si usas MicroSip ERP, Delfa Bridge se conecta directamente:
1. Ve a **Conectores → MicroSip**
2. Ingresa la dirección de tu servidor MicroSip
3. Ingresa tu usuario y contraseña de MicroSip
4. Haz clic en **"Conectar y procesar"**

---

## Paso 3 — Haz tu primera consulta

Una vez procesados tus documentos, ve a **Buscar** y escribe tu pregunta:

- "¿Quién firma el contrato con Empresa XYZ?"
- "¿Cuánto le debemos al proveedor ABC?"
- "¿Cuándo vence el contrato de mantenimiento?"
- "¿Cuál es la penalización por incumplimiento?"

---

## Paso 4 — Configura reglas de gobernanza

Las reglas de gobernanza protegen información sensible automáticamente.

**Ejemplos de reglas comunes:**

| Tipo de dato | Regla | Acción |
|--------------|-------|--------|
| Montos > $500,000 | Requiere aprobación | Va a cuarentena |
| Datos de personas | Redactar | Se oculta el valor |
| Cláusulas de penalización | Marcar | Se resalta para revisión |

Ve a **Gobernanza → Nueva Regla** para configurar las tuyas.

---

## Trazabilidad total

Cada respuesta de Delfa Bridge incluye:
- **Fuente** — de qué documento viene la información
- **Fecha** — cuándo fue procesada
- **Componente** — qué parte del sistema la procesó

Esto garantiza que nunca habrá respuestas inventadas.

---

## Soporte

¿Necesitas ayuda? Contáctanos:
- Email: soporte@delfa.bridge
- WhatsApp: +52 656 XXX XXXX

---

*Delfa Bridge — Tu empresa, más inteligente*
*Powered by Panohayan™*
