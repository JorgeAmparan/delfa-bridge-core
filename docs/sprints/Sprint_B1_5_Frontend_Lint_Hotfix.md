# Sprint Contract B1.5 — Frontend lint hotfix + migración ESLint 9 (sprint puente)

**Producto:** DOCYAN LDE — Live Document Environment by XCID
**Bloque:** B1.5 (sprint puente) | **Ejecutor:** Opus 4.8 vía Claude Code CLI
**Modo:** Una aprobación + ejecución completa + un reporte final.
**Repo:** `docyan-lde-core` | **Branch de trabajo:** `sprint/B1.5-frontend-lint`

---

## Prerequisitos

B0 + B0.5 + B1 mergeados a `main`. Estado actual del repo en main:
- Backend Fly `docyan-lde-api` ✅ deployado, health 200.
- FalkorDB Fly `docyan-lde-graph` ✅ deployado.
- BGE-M3 Fly `docyan-lde-embedder` ✅ deployado.
- Frontend Vercel `docyan-lde.vercel.app` ✅ funcional.
- 103 tests backend passing.
- CI jobs `backend` y `gen-types` verdes.
- **CI job `frontend` rojo** por incompatibilidad de `next lint` con Next.js 16.

## Contexto para Opus

El bump de Next.js 15.1.6 → 16.2.6 (commit `4b21462`, hecho pre-B1 para resolver vulnerabilidad de seguridad detectada por Vercel) introdujo un breaking change: **`next lint` fue removido en Next 16**. Ahora ese comando interpreta `lint` como directorio y falla con `Invalid project directory ... frontend/lint`.

El reporte de cierre de B1 documentó esto explícitamente como PENDIENTE DE JORGE, con el fix técnico identificado:

> Causa raíz: `next lint` fue removido en Next.js 16. En `frontend/package.json`, cambiar `"lint": "next lint"` por `"lint": "eslint ."`. Como `.eslintrc.json` es legacy y ESLint 9 usa flat config por default, o bien correr con `ESLINT_USE_FLAT_CONFIG=false eslint .` o migrar a `eslint.config.mjs` con `eslint-config-next`.

**Decisiones rectoras de este sprint** (aprobadas por el fundador antes de redactar):

1. **Mantener Tailwind 3 y shadcn/ui en sus versiones actuales.** Migración de Tailwind 4 / shadcn actualizado es trabajo aparte, no entra aquí.
2. **No migrar a Turbopack para `next dev`.** Turbopack ya es default en build (verificado en build local del 30 may 2026, salida `▲ Next.js 16.2.6 (Turbopack)`). Si causara problema, sería en build, no en lint. Fuera de scope.
3. **Arreglar todos los errores que aparezcan al correr `eslint .` con la config nueva**, salvo que alguno requiera cambios estructurales mayores (renombrar archivos, mover lógica), en cuyo caso documentar como PENDIENTE DE JORGE y continuar.

**Lo que este sprint NO hace:**
- No toca backend (cero archivos de `app/`, `tests/`, `scripts/`, `embedder/`, `fly*.toml`).
- No toca infra (no toca CI workflow más allá de verificar que pase).
- No actualiza versiones mayores de otras dependencias (Tailwind, shadcn, React, TypeScript).
- No introduce nuevas features de lint ni reglas custom — solo asegura que el lint actual corre.

## Alcance específico

### 1. Crear branch de trabajo

```bash
git checkout main
git pull origin main
git checkout -b sprint/B1.5-frontend-lint
```

Todo el trabajo en `sprint/B1.5-frontend-lint`. Push al cierre, merge a main tras revisión.

### 2. Diagnóstico inicial

Antes de tocar nada, ejecutar y reportar:

```bash
cd frontend
cat package.json | grep -E '"(lint|next|eslint)"'
ls -la .eslintrc.json eslint.config.* 2>/dev/null
cat .eslintrc.json 2>/dev/null
npx eslint --version
```

Esto confirma versión exacta de ESLint, presencia o ausencia de configs flat/legacy, y la línea actual de `lint` en package.json. Documentar en el reporte para trazabilidad.

### 3. Migración del script `lint`

En `frontend/package.json`:

```json
"lint": "eslint ."
```

Reemplaza la línea `"lint": "next lint"` actual.

### 4. Migración de configuración ESLint legacy → flat config

ESLint 9 usa flat config (`eslint.config.mjs`) por default. El archivo `.eslintrc.json` que existe en el repo es legacy.

**Estrategia recomendada (limpia, no parche):**

Crear `frontend/eslint.config.mjs` con flat config equivalente a la legacy actual. La configuración debe incluir:

- `eslint-config-next` para reglas Next.js.
- `eslint-config-prettier` si Prettier está en uso (verificar — en B0 sí se instaló prettier).
- Reglas mínimas necesarias: TypeScript, React 19, React Hooks, JSX accessibility básica (si la legacy las tenía).

Plantilla esperable (Opus la adapta según lo que descubra):

```javascript
import next from 'eslint-config-next';

export default [
  ...next(),
  {
    rules: {
      // Reglas que estaban en .eslintrc.json legacy, si las había
    }
  }
];
```

**Si `eslint-config-next` no exporta flat config compatible con ESLint 9 todavía** (caso conocido en versiones recientes de Next):
- Alternativa A: usar `@eslint/eslintrc` compat shim para reusar la config legacy con flat config.
- Alternativa B: temporalmente correr con `ESLINT_USE_FLAT_CONFIG=false` y mantener `.eslintrc.json`, documentando como deuda técnica menor para revisar en B8.

Opus decide entre A y B según lo que el ecosistema soporte hoy, justificando con argumento técnico en el reporte. **Preferencia: A (flat config limpia). B solo si A es genuinamente bloqueador.**

Eliminar `.eslintrc.json` solo si la migración a flat config tiene éxito.

### 5. Verificación local de lint

Desde `frontend/`:

```bash
npm run lint
```

Debe ejecutar sin errores de configuración. Si aparecen errores de código (no de config), arreglarlos. Errores típicos esperables y triviales:

- `react/no-unescaped-entities` — caracteres `'` o `"` literales en JSX → escapar con `&apos;` o `&quot;` o usar template literals.
- `@typescript-eslint/no-unused-vars` — imports o variables no usadas → eliminar.
- `react-hooks/exhaustive-deps` — dependencias faltantes en `useEffect` → arreglar dependencias.
- `@next/next/no-html-link-for-pages` — usar `<Link>` de Next en lugar de `<a>` para rutas internas.

Si aparece un error que requiere **cambio estructural** (renombrar componente, mover archivo, reescribir lógica), no arreglarlo en este sprint: comentar el código con `// eslint-disable-next-line <regla> -- B1.5: requires structural change, see PENDIENTE DE JORGE` y documentar en el reporte.

### 6. Verificación de que el resto del frontend sigue funcionando

Estas verificaciones son obligatorias antes de cerrar el sprint:

```bash
cd frontend
npm run build       # build de Next 16 sigue pasando
npm test            # Vitest sigue verde
npx playwright test # E2E sigue verde
```

Si alguno falla por culpa de los cambios del sprint, arreglar. Si falla por causa ajena (preexistente), documentar PENDIENTE DE JORGE y no continuar arreglando dentro de este sprint.

### 7. Verificación de CI

Push de la rama y verificar que en GitHub Actions el job `frontend` queda verde:

```bash
git add frontend/
git commit -m "fix(B1.5): migrate frontend lint to ESLint 9 flat config, drop next lint"
git push origin sprint/B1.5-frontend-lint
```

Esperar a que CI corra (~3-5 min). Si `frontend` no pasa verde, diagnosticar la diferencia entre local y CI, arreglar, repushear. **Sprint no cierra hasta que `frontend` esté verde en CI.**

### 8. Eliminación del lock file de Claude Code en main (limpieza menor)

Verificar si `.claude/scheduled_tasks.lock` quedó accidentalmente versionado en main (proveniente del merge de B1). Si sí:

```bash
git rm --cached .claude/scheduled_tasks.lock
echo ".claude/" >> .gitignore
git add .gitignore
git commit -m "chore(B1.5): ignore .claude/ runtime files (claude code state)"
```

Esta es limpieza colateral aprovechando el sprint. No es bloqueador del cierre; si Opus prefiere dejarlo para otra ocasión, también válido.

### 9. Documentación

- Actualizar `README.md` si menciona `next lint`.
- Actualizar `CLAUDE.md` con la línea correcta del comando de lint.
- No crear documentación adicional — este sprint es un fix técnico acotado.

## Componentes a construir o modificar

- `frontend/eslint.config.mjs` — **nuevo** (flat config ESLint 9).
- `frontend/.eslintrc.json` — **eliminado** (si la migración a flat tuvo éxito).
- `frontend/package.json` — `"lint"` script actualizado.
- `frontend/src/` — posibles fixes de lint en archivos existentes (esperable: ninguno o muy pocos, código del frontend es minimalista).
- `.gitignore` — agregar `.claude/` (opcional).
- `README.md`, `CLAUDE.md` — actualización menor de referencias a comando de lint.

## Tests automatizados requeridos

No se requieren tests nuevos. Los existentes deben seguir verdes:

- 103 tests backend siguen passing (no se tocan).
- Tests Vitest frontend siguen verdes (`boot.test.tsx`).
- Tests Playwright frontend siguen verdes (`boot.spec.ts`).

## Salida verificable (criterio de cierre)

- ✅ `npm run lint` ejecuta desde `frontend/` sin error de configuración.
- ✅ `npm run build` ejecuta desde `frontend/` sin errores.
- ✅ `npm test` ejecuta desde `frontend/` sin errores.
- ✅ `npx playwright test` ejecuta desde `frontend/` sin errores.
- ✅ CI en GitHub Actions sobre `sprint/B1.5-frontend-lint`: **los tres jobs verdes** (`backend`, `gen-types`, `frontend`).
- ✅ Backend Fly sigue desplegado y respondiendo health 200 (invariante, B1.5 no toca backend).
- ✅ Frontend Vercel sigue desplegado y respondiendo 200 (Vercel también debe poder buildear con la nueva config — verificar opcionalmente con `vercel --prod` desde `frontend/` o esperar al merge a main).

## Notas para Opus sobre integración con código existente

- B1 ya cerró el backend infra (DKG + multi-tenant + embedder). **No tocar nada de `app/`, `tests/`, `scripts/`, `embedder/`, `fly*.toml`, `docker-compose.yml`.**
- El comando `npm run lint` se ejecuta desde `frontend/`, no desde la raíz. Confirmar que el script raíz del monorepo (`package.json` en raíz) que orquesta tareas no rompa por este cambio.
- `frontend/scripts/generate-types.sh` debe seguir funcionando (es parte de gen-types CI job).
- shadcn/ui ya está instalado con sus componentes (`button.tsx`). Las reglas de lint no deben romper esos componentes auto-generados de shadcn.
- React 19 + Next 16 + Tailwind 3 es la combinación actual. No cambiar versiones mayores.

## Reglas de ejecución

- Trabajar exclusivamente sobre la rama `sprint/B1.5-frontend-lint`. No commitear a main directamente.
- No tocar backend, infra, ni stack que no sea frontend. Si hay tentación, parar y verificar contra este contrato.
- Si un error de lint requiere cambio estructural mayor, **suprimirlo con `eslint-disable-next-line` documentado** y reportar como PENDIENTE DE JORGE. No invadir scope ajeno.
- Verdad operacional: reportar exactamente qué errores aparecieron, cuáles se arreglaron, cuáles se suprimieron. No proyectar "se arregló todo" si no se arregló todo.
- Si flat config no funciona y se cae a la alternativa B (compat shim o `ESLINT_USE_FLAT_CONFIG=false`), reportar la razón técnica concreta — no es bloqueador del sprint pero sí debe quedar documentado para retomar en B8.

---

**Referencias:** reporte de cierre de B1 del 30 may 2026 (PENDIENTE DE JORGE — frontend lint), commit `4b21462` (bump Next 16), doc 10 (Stack Técnico).

---

*Fin del Sprint Contract B1.5.*
