// ESLint 9 flat config — DOCYAN LDE™ frontend (B1.5).
//
// Migración desde .eslintrc.json legacy: Next.js 16 removió `next lint`, y
// ESLint 9 usa flat config por default. En Next 16 `eslint-config-next` YA
// exporta flat config (un array que agrupa `next/core-web-vitals` +
// `next/typescript`, con los plugins next/react/react-hooks/import/jsx-a11y +
// typescript-eslint), así que se compone directamente — NO con FlatCompat
// (que espera formato legacy y rompe con referencias circulares de los plugins).
//
// Equivale 1:1 al `"extends": ["next/core-web-vitals", "next/typescript"]` previo.
import next from "eslint-config-next";

const eslintConfig = [
  ...next,
  // Equivale al `"ignorePatterns"` legacy. `src/types/api.ts` se genera desde el
  // OpenAPI del backend (gen-types) — no se lintea.
  {
    ignores: ["node_modules/**", ".next/**", "src/types/api.ts"],
  },
];

export default eslintConfig;
