/**
 * modelRegistry — el grafo de modelos que el TS worker necesita para dar
 * IntelliSense de PROYECTO (no de archivo suelto) sobre el workspace.
 *
 * Problema medido: al abrir `HtmlPreview.tsx`, el worker TS resuelve
 * `import ... from './WorkspaceTree'` contra `file:///src/.../WorkspaceTree.tsx`
 * y ese modelo NO existe porque nadie lo creó → "Cannot find module", sin
 * go-to-definition, sin hover sobre símbolos importados. Tres cosas son UNA
 * sola pieza y van juntas:
 *
 *   1. Registry + resolver: materializan la cadena de imports como
 *      `ITextModel` con la MISMA forma de URI que usa el editor
 *      (`file:///{path}`), lazy: sólo lo que el archivo activo necesita.
 *   2. `setEagerModelSync(true)`: sin esto el worker sólo sincroniza el modelo
 *      que está dentro de un editor; los dependientes existirían en memoria
 *      pero el worker seguiría sin verlos.
 *   3. `compilerOptions` (jsx, moduleResolution, paths): sin `jsx` el `.tsx`
 *      activo ya falla antes de mirar imports; sin `paths` los aliases del
 *      tsconfig no resuelven aunque el modelo exista.
 *
 * UN solo resolver para proyecto y `node_modules`. Medido en este repo:
 *   - `@fluentui/react-components/dist/index.d.ts` (198 KB) es un rollup con
 *     CERO reexports relativos pero 40+ `import … from '@fluentui/react-*'`:
 *     los tipos de `Button` viven en `@fluentui/react-button`. Inyectar sólo
 *     el entry deja `Button` como `any`. Hay que seguir el salto
 *     paquete → paquete.
 *   - `@types/react/index.d.ts` encadena `/// <reference path="global.d.ts">`
 *     + `import … from "csstype"` (895 KB) + `prop-types`. Tres formas de
 *     reexport (relativo, reference path, paquete) que el resolver sigue igual.
 *
 * Control: PRESUPUESTO, no profundidad. Un grafo casual del propio proyecto
 * tiene 3-4 niveles y es barato; el de typings puede ser llano y enorme. La
 * profundidad mide distancia, no coste. Lo que acota es:
 *   - visited por URI + dedupe de fetches en vuelo (nunca el mismo archivo 2×)
 *   - MAX_MODELS: modelos vivos por workspace
 *   - MAX_TOTAL_BYTES: bytes totales materializados
 *   - MAX_FILE_BYTES: un archivo gigante no entra (el backend ya corta en 1 MB)
 *   - MAX_PACKAGES / MAX_BYTES_PER_PACKAGE: un paquete no se come el presupuesto
 *     de los demás; agotado el suyo, el resto de ESE paquete queda sin tipos y
 *     el proyecto sigue intacto.
 * El proyecto va PRIMERO (BFS por frontera, proyecto antes que node_modules en
 * cada ola): si hay que recortar, se recorta en typings, nunca en los archivos
 * del usuario.
 *
 * Los modelos viven aquí, no en el componente (misma lección que
 * workspaceTreeStore): el editor se desmonta al cerrar un archivo y eso no
 * debe tirar el grafo. Se liberan por invalidación explícita del workspace.
 */

import { apiClient } from '../../api/apiClient';
import { monaco } from './monacoSetup';

const TS_EXTS = [
  '.ts',
  '.tsx',
  '.d.ts',
  '.mts',
  '.cts',
  '.d.mts',
  '.d.cts',
  '.js',
  '.jsx',
  '.json',
];
const DTS_EXTS = ['.d.ts', '.d.mts', '.d.cts', '.ts', '.mts', '.cts'];

/** `jsxImportSource` del compilador (default de TypeScript): de aquí sale el
 *  import implícito `<source>/jsx-runtime` de todo .tsx/.jsx. */
const JSX_IMPORT_SOURCE = 'react';

const MAX_MODELS = 160;
const MAX_TOTAL_BYTES = 4 * 1024 * 1024; // 4 MB en memoria del worker
const MAX_FILE_BYTES = 1 * 1024 * 1024; // mismo tope que el backend
const MAX_PACKAGES = 24;
const MAX_BYTES_PER_PACKAGE = 1 * 1024 * 1024; // csstype (895 KB) cabe; 2 no
/** Nada se adivina contra el servidor. Medido en el log del backend con el
 *  primer borrador: `/tsconfig.json` 404 antes del real, `/node_modules/x`
 *  404 antes de `src/frontend/node_modules/x`, `.ts` 404 antes de `.tsx` por
 *  cada import relativo, y `@types/react/[object Object].d.ts` porque
 *  `exports["."].types` es un objeto de condiciones. El backend ya responde
 *  cada pregunta sin tantear:
 *   - `GET /search?q=tsconfig.json` (git ls-files): TODOS los tsconfig en una
 *     llamada → el más cercano al archivo abierto es el proyecto, y de ahí
 *     sale el `node_modules` que se consulta primero.
 *   - `GET /entries?path=dir`: el listado del directorio (una lectura por
 *     directorio, cacheada) decide qué extensión existe; sólo se lee lo que
 *     está en el listado.
 *   - `package.json` se lee por ruta exacta: un 404 ahí significa "no está
 *     instalado en esa raíz", una vez por paquete y raíz. */

/** Especificadores: `from '…'`, `import '…'`, `import('…')`, `export … from`,
 *  `require('…')`, `import type … from`, `/// <reference path="…">`,
 *  `/// <reference types="…">`. */
const IMPORT_RE =
  /(?:import|export)\s+(?:type\s+)?(?:[^'"]*?\s+from\s+)?['"]([^'"]+)['"]|import\s*\(\s*['"]([^'"]+)['"]\s*\)|require\s*\(\s*['"]([^'"]+)['"]\s*\)|\/\/\/\s*<reference\s+path=['"]([^'"]+)['"]|\/\/\/\s*<reference\s+types=['"]([^'"]+)['"]/g;

type SpecKind = 'module' | 'path' | 'types';

interface Budget {
  models: number;
  bytes: number;
  packages: Set<string>;
  bytesPerPackage: Map<string, number>;
}

interface Registry {
  workspaceId: string;
  /** path → modelo materializado (o `null` si no existe / no cabe). */
  models: Map<string, monaco.editor.ITextModel | null>;
  /** path → fetch en curso: nunca dos lecturas del mismo archivo. */
  inflight: Map<string, Promise<monaco.editor.ITextModel | null>>;
  /** Archivos ya recorridos (sus imports ya se encolaron). */
  visited: Set<string>;
  /** Paquete → entry .d.ts resuelto, o `null` si no está en el workspace. */
  packageEntries: Map<string, Promise<string | null>>;
  /** Paquete → raíz (`node_modules/x` o `node_modules/@types/x`). */
  packageRoots: Map<string, string>;
  /** dir → listado (nombre → tipo y tamaño). Una lectura por directorio. */
  dirListings: Map<string, Promise<Map<string, DirEntryInfo>>>;
  tsconfigApplied: boolean;
  tsconfigPaths: Record<string, string[]> | null;
  tsconfigBaseDir: string;
  /** Directorio del tsconfig más cercano al primer archivo abierto ('' si no
   *  hay): de aquí sale el `node_modules` que se consulta primero. */
  projectRoot: string;
  nodeModulesRoots: string[];
  budget: Budget;
}

type DirKind = 'file' | 'directory';
interface DirEntryInfo {
  type: DirKind;
  size: number | null;
}

/** Requests del grafo en vuelo a la vez. El grafo es trabajo de fondo: no
 *  puede competir con la lectura del archivo que el usuario abrió ni con el
 *  diff/diagnósticos. Medido: una ola con decenas de requests en paralelo
 *  contra el proxy de Vite (segundos por request) dejaba la apertura del
 *  archivo en la misma cola. */
const MAX_INFLIGHT = 4;
let inflightCount = 0;
const waiting: Array<() => void> = [];

async function throttled<T>(fn: () => Promise<T>): Promise<T> {
  if (inflightCount >= MAX_INFLIGHT) {
    await new Promise<void>((resolve) => waiting.push(resolve));
  }
  inflightCount += 1;
  try {
    return await fn();
  } finally {
    inflightCount -= 1;
    waiting.shift()?.();
  }
}

let current: Registry | null = null;
let tsDefaultsConfigured = false;

/** URI con la MISMA forma que `@monaco-editor/react` usa para `path={p}`:
 *  `Uri.parse("src/x.tsx")` → `file:///src/x.tsx`. Es la única manera de
 *  que el `./X` del activo resuelva al modelo que el resolver creó. */
export function modelUri(path: string): monaco.Uri {
  return monaco.Uri.parse(`file:///${path.replace(/^\/+/, '')}`);
}

function isTsLike(path: string): boolean {
  return /\.(tsx?|jsx?|mts|cts|json)$/i.test(path);
}

function dirname(path: string): string {
  const i = path.lastIndexOf('/');
  return i < 0 ? '' : path.slice(0, i);
}

function basename(path: string): string {
  return path.slice(path.lastIndexOf('/') + 1);
}

/** `a` es `b` o un ancestro de `b` ('' es ancestro de todo). */
function isAncestor(a: string, b: string): boolean {
  return a === '' || a === b || b.startsWith(`${a}/`);
}

/** Normaliza `a/b/../c/./d` → `a/c/d` sin salirse del workspace. */
function normalize(path: string): string {
  const out: string[] = [];
  for (const seg of path.split('/')) {
    if (!seg || seg === '.') continue;
    if (seg === '..') {
      out.pop();
      continue;
    }
    out.push(seg);
  }
  return out.join('/');
}

function languageFor(path: string): string {
  if (/\.json$/i.test(path)) return 'json';
  if (/\.(jsx?|mjs|cjs)$/i.test(path)) return 'javascript';
  return 'typescript';
}

/** Nombre de paquete de un especificador: `@scope/pkg/sub` → `@scope/pkg`,
 *  `pkg/sub` → `pkg`. `null` si es relativo/absoluto. */
function packageOf(spec: string): string | null {
  if (spec.startsWith('.') || spec.startsWith('/')) return null;
  const m = spec.match(/^(@[^/]+\/[^/]+|[^/]+)/);
  return m ? m[1] : null;
}

/** Paquete al que pertenece un path del workspace, si está en node_modules. */
function packageOfPath(path: string): string | null {
  const m = path.match(/node_modules\/(@[^/]+\/[^/]+|[^/]+)\//);
  return m ? m[1] : null;
}

function isInNodeModules(path: string): boolean {
  return /(^|\/)node_modules\//.test(path);
}

/** `react` → `react`; `@fluentui/react-button` → `fluentui__react-button`
 *  (convención DefinitelyTyped). */
function typesPackageName(pkg: string): string {
  return pkg.replace(/^@/, '').replace('/', '__');
}

/** Compiler options del worker: espejo del tsconfig del workspace con lo que
 *  Monaco 0.56 soporta. `ModuleResolutionKind` sólo tiene Classic|NodeJs (no
 *  existe Bundler): NodeJs resuelve relativos sin extensión y honra `paths`. */
function configureTsDefaults(
  paths?: Record<string, string[]> | null,
  baseDir = ''
): void {
  const ts = monaco.typescript;
  const options: Parameters<
    typeof ts.typescriptDefaults.setCompilerOptions
  >[0] = {
    target: ts.ScriptTarget.ES2020,
    module: ts.ModuleKind.ESNext,
    moduleResolution: ts.ModuleResolutionKind.NodeJs,
    jsx: ts.JsxEmit.ReactJSX,
    allowJs: true,
    esModuleInterop: true,
    allowSyntheticDefaultImports: true,
    resolveJsonModule: true,
    isolatedModules: true,
    skipLibCheck: true,
    strict: true,
    noEmit: true,
    baseUrl: `file:///${baseDir}`,
    ...(paths ? { paths } : {}),
  };
  ts.typescriptDefaults.setCompilerOptions(options);
  ts.javascriptDefaults.setCompilerOptions(options);
  if (!tsDefaultsConfigured) {
    tsDefaultsConfigured = true;
    // Clave: el worker ve TODOS los modelos TS/JS, no sólo el del editor.
    ts.typescriptDefaults.setEagerModelSync(true);
    ts.javascriptDefaults.setEagerModelSync(true);
  }
}

async function readFile(
  workspaceId: string,
  path: string
): Promise<string | null> {
  try {
    const encoded = path.split('/').map(encodeURIComponent).join('/');
    const r: { content?: string } = await throttled(() =>
      apiClient.get(
        `/v4/workspace/${encodeURIComponent(workspaceId)}/files/${encoded}`
      )
    );
    return typeof r.content === 'string' ? r.content : null;
  } catch {
    // binario, >1MB, inexistente o no autorizado: el backend lo rechaza.
    return null;
  }
}

/** Listado de UN directorio (nombre → tipo y tamaño), una lectura por
 *  directorio. Un directorio inexistente (400) se recuerda como vacío. */
function listDir(
  reg: Registry,
  dir: string
): Promise<Map<string, DirEntryInfo>> {
  const cached = reg.dirListings.get(dir);
  if (cached) return cached;
  const p = (async () => {
    const out = new Map<string, DirEntryInfo>();
    try {
      const r: {
        entries?: Array<{ name: string; type: DirKind; size?: number | null }>;
      } = await throttled(() =>
        apiClient.get(
          `/v4/workspace/${encodeURIComponent(reg.workspaceId)}/entries`,
          { params: dir ? { path: dir } : undefined }
        )
      );
      for (const e of r.entries ?? []) {
        out.set(e.name, { type: e.type, size: e.size ?? null });
      }
    } catch {
      /* no existe o no autorizado: vacío */
    }
    return out;
  })();
  reg.dirListings.set(dir, p);
  return p;
}

/** Un path base → el archivo que EXISTE, decidido con el listado de su
 *  directorio: `base.ext` para cada extensión en orden, y si `base` es un
 *  directorio, `base/index.ext`. Con extensión explícita sólo se comprueba.
 *  `./foo.js` en un .d.ts ESM apunta a `./foo.d.ts`. */
async function resolveBase(
  reg: Registry,
  base: string,
  exts: string[]
): Promise<string | null> {
  // Sólo .ts/.tsx/.mts/.cts/.d.ts/.d.mts/.d.cts/.json son explícitas.
  // `.js`/`.mjs`/`.cjs`/`.jsx` NO:
  // un `./x.js` (ESM) nombra al `.d.ts`/`.ts` de `x`, nunca al JS en sí
  // (medido: se leían los .js de monaco-editor como si fueran tipos).
  if (/\.(d\.[mc]?ts|[mc]ts|tsx?|json)$/i.test(base)) {
    const names = await listDir(reg, dirname(base));
    return names.get(basename(base))?.type === 'file' ? base : null;
  }
  const stripped = base.replace(/\.(m|c)?jsx?$/i, '');
  const name = basename(stripped);
  const siblings = await listDir(reg, dirname(stripped));
  for (const e of exts) {
    if (siblings.get(`${name}${e}`)?.type === 'file') return `${stripped}${e}`;
  }
  if (siblings.get(name)?.type === 'directory') {
    const inside = await listDir(reg, stripped);
    for (const e of exts) {
      if (inside.get(`index${e}`)?.type === 'file') {
        return `${stripped}/index${e}`;
      }
    }
  }
  return null;
}

/** El `tsconfig.json` más cercano al archivo abierto (como hace TypeScript),
 *  encontrado con UNA búsqueda por nombre; de su directorio salen `paths` y
 *  el `node_modules` del proyecto. Una vez por workspace. */
async function applyTsconfig(reg: Registry, entry: string): Promise<void> {
  if (reg.tsconfigApplied) return;
  reg.tsconfigApplied = true;
  let found: string[] = [];
  try {
    const r: { matches?: string[] } = await apiClient.get(
      `/v4/workspace/${encodeURIComponent(reg.workspaceId)}/search`,
      { params: { q: 'tsconfig.json' } }
    );
    found = (r.matches ?? []).filter((m) => basename(m) === 'tsconfig.json');
  } catch {
    /* sin búsqueda: sin proyecto */
  }
  const entryDir = dirname(entry);
  const nearest = found
    .filter((m) => isAncestor(dirname(m), entryDir))
    .sort((a, b) => b.length - a.length)[0];
  reg.projectRoot = nearest ? dirname(nearest) : '';
  reg.nodeModulesRoots = Array.from(
    new Set([
      normalize(`${reg.projectRoot}/node_modules`),
      'node_modules',
    ])
  );
  if (!nearest) return;
  const raw = await readFile(reg.workspaceId, nearest);
  if (!raw) return;
  try {
    // tsconfig admite comentarios y comas finales.
    const json = JSON.parse(
      raw
        .replace(/\/\*[\s\S]*?\*\/|\/\/.*$/gm, '')
        .replace(/,\s*([}\]])/g, '$1')
    );
    const paths = json?.compilerOptions?.paths as
      | Record<string, string[]>
      | undefined;
    const baseUrl = String(json?.compilerOptions?.baseUrl ?? '.');
    reg.tsconfigBaseDir = normalize(`${reg.projectRoot}/${baseUrl}`);
    if (paths) {
      reg.tsconfigPaths = paths;
      configureTsDefaults(paths, reg.tsconfigBaseDir);
    }
  } catch {
    /* tsconfig ilegible: seguir con defaults */
  }
}

/** `@/x` y demás aliases del tsconfig → paths base reales del workspace. */
function aliasBases(reg: Registry, spec: string): string[] {
  if (!reg.tsconfigPaths) return [];
  const out: string[] = [];
  for (const [pattern, targets] of Object.entries(reg.tsconfigPaths)) {
    const star = pattern.indexOf('*');
    let rest: string | null = null;
    if (star < 0) {
      if (spec === pattern) rest = '';
    } else {
      const pre = pattern.slice(0, star);
      const post = pattern.slice(star + 1);
      if (spec.startsWith(pre) && spec.endsWith(post)) {
        rest = spec.slice(pre.length, spec.length - post.length);
      }
    }
    if (rest === null) continue;
    for (const t of targets) {
      out.push(normalize(`${reg.tsconfigBaseDir}/${t.replace(/\*/g, rest)}`));
    }
  }
  return out;
}

/** `exports["."]`, `types` y `typings` pueden ser un string o un objeto de
 *  condiciones anidadas (`{ types: { default: "./index.d.ts" } }`, como
 *  @types/react; `{ import: { types: … } }` en otros). Primer string
 *  alcanzable por `types` → `import` → `default` → `require`. Con
 *  `needTypes` sólo cuenta un string alcanzado a través de una clave `types`. */
function conditionTarget(v: unknown, needTypes: boolean): string | null {
  if (typeof v === 'string') return needTypes ? null : v;
  if (Array.isArray(v)) {
    for (const x of v) {
      const r = conditionTarget(x, needTypes);
      if (r) return r;
    }
    return null;
  }
  if (v && typeof v === 'object') {
    for (const k of ['types', 'import', 'default', 'require']) {
      if (!(k in v)) continue;
      const r = conditionTarget(
        (v as Record<string, unknown>)[k],
        needTypes && k !== 'types'
      );
      if (r) return r;
    }
  }
  return null;
}

/** Entry `.d.ts` de un paquete en el workspace: `exports["."].types` →
 *  `types`/`typings` → `index.d.ts`; si el paquete no trae tipos,
 *  `@types/<pkg>`. Una resolución por paquete (cacheada como promesa para
 *  que dos imports concurrentes no la repitan). */
function packageEntry(reg: Registry, pkg: string): Promise<string | null> {
  const cached = reg.packageEntries.get(pkg);
  if (cached) return cached;
  // Tope de paquetes ANTES de leer nada: un paquete nuevo cuando el cupo está
  // lleno no gasta ni el package.json (medido: el barrel de
  // @fluentui/react-components arrastraba 60 package.json de react-*).
  if (
    !reg.budget.packages.has(pkg) &&
    reg.budget.packages.size >= MAX_PACKAGES
  ) {
    const none = Promise.resolve<string | null>(null);
    reg.packageEntries.set(pkg, none);
    return none;
  }
  // Cuenta desde que se empieza a resolver, no desde el primer .d.ts que
  // cabe: si no, los package.json de toda la cola pasan el tope.
  reg.budget.packages.add(pkg);
  const p = (async (): Promise<string | null> => {
    for (const nm of reg.nodeModulesRoots) {
      const own = await entryFromRoot(reg, `${nm}/${pkg}`);
      if (own) {
        reg.packageRoots.set(pkg, `${nm}/${pkg}`);
        return own;
      }
      const typesRoot = `${nm}/@types/${typesPackageName(pkg)}`;
      const types = await entryFromRoot(reg, typesRoot);
      if (types) {
        reg.packageRoots.set(pkg, typesRoot);
        return types;
      }
    }
    return null;
  })();
  reg.packageEntries.set(pkg, p);
  return p;
}

/** Lee `root/package.json`; devuelve el `.d.ts` de entrada si existe.
 *  Registra el package.json como extraLib para que el worker TS lo vea. */
async function entryFromRoot(
  reg: Registry,
  root: string
): Promise<string | null> {
  const pkgPath = `${root}/package.json`;
  const raw = await readFile(reg.workspaceId, pkgPath);
  if (raw === null) return null;
  // Registrar el package.json como extraLib: el worker TS lo necesita para
  // resolver el campo types/typings cuando hace fileExists/readFile.
  // La clave es el string SIN codificar (`toString(true)`): el worker arma la
  // ruta concatenando el directorio con el especificador literal del import
  // (`@fluentui/x`), y `fileName in extraLibs` compara strings exactos.
  // `toString()` codifica `@` como `%40` y ningún paquete con scope se
  // encontraría. (Los modelos no sufren esto: `_getModel` acepta ambas formas.)
  const ts = monaco.typescript;
  const pkgUri = modelUri(pkgPath).toString(true);
  ts.typescriptDefaults.addExtraLib(raw, pkgUri);
  ts.javascriptDefaults.addExtraLib(raw, pkgUri);
  let types = 'index.d.ts';
  try {
    const pj = JSON.parse(raw);
    const dot = pj.exports?.['.'];
    types = (
      conditionTarget(dot, true) ??
      conditionTarget(pj.types, false) ??
      conditionTarget(pj.typings, false) ??
      conditionTarget(dot, false) ??
      types
    ).replace(/^\.\//, '');
  } catch {
    /* package.json ilegible: index.d.ts */
  }
  // `types` puede ser `index.d.ts`, `dist/index` o incluso `index.js`.
  const file = await resolveBase(reg, normalize(`${root}/${types}`), DTS_EXTS);
  if (!file) return null;
  return (await materialize(reg, file)) ? file : null;
}

/** ¿Cabe este archivo en el presupuesto? Reserva si cabe. */
function reserve(reg: Registry, path: string, bytes: number): boolean {
  const b = reg.budget;
  if (bytes > MAX_FILE_BYTES) return false;
  if (b.models >= MAX_MODELS) return false;
  if (b.bytes + bytes > MAX_TOTAL_BYTES) return false;
  const pkg = packageOfPath(path);
  if (pkg) {
    if (!b.packages.has(pkg)) {
      if (b.packages.size >= MAX_PACKAGES) return false;
      b.packages.add(pkg);
    }
    const used = b.bytesPerPackage.get(pkg) ?? 0;
    if (used + bytes > MAX_BYTES_PER_PACKAGE) return false;
    b.bytesPerPackage.set(pkg, used + bytes);
  }
  b.models += 1;
  b.bytes += bytes;
  return true;
}

/** Materializa `path` como modelo (lee del workspace si hace falta).
 *  `null` = no existe o no cabe; se recuerda para no volver a pedirlo. */
async function materialize(
  reg: Registry,
  path: string
): Promise<monaco.editor.ITextModel | null> {
  if (reg.models.has(path)) return reg.models.get(path) ?? null;
  const pending = reg.inflight.get(path);
  if (pending) return pending;

  const p = (async () => {
    // Ya existe (p.ej. lo creó el editor al abrirlo): adoptarlo, no duplicar.
    const existing = monaco.editor.getModel(modelUri(path));
    if (existing) {
      reg.models.set(path, existing);
      return existing;
    }
    // Presupuesto ANTES de descargar: el listado del directorio (cacheado)
    // trae el tamaño; lo que no cabe no se pide (medido: cada chunk-N.d.ts de
    // react-icons se bajaba entero para rechazarse después).
    const info = (await listDir(reg, dirname(path))).get(basename(path));
    if (info?.type !== 'file') {
      reg.models.set(path, null);
      return null;
    }
    const known = info.size ?? null;
    if (known !== null && !reserve(reg, path, known)) {
      reg.models.set(path, null);
      return null;
    }
    const content = await readFile(reg.workspaceId, path);
    if (
      content === null ||
      (known === null && !reserve(reg, path, content.length))
    ) {
      reg.models.set(path, null);
      return null;
    }
    // Carrera: otro camino pudo crearlo mientras leíamos.
    const again = monaco.editor.getModel(modelUri(path));
    const model =
      again ??
      monaco.editor.createModel(content, languageFor(path), modelUri(path));
    reg.models.set(path, model);
    return model;
  })();
  reg.inflight.set(path, p);
  try {
    return await p;
  } finally {
    reg.inflight.delete(path);
  }
}

/** Para un especificador en `fromPath`, el archivo del workspace que lo
 *  satisface, o `null`. Cada decisión sale de un listado o de un
 *  `package.json` leído por ruta exacta; nunca de probar rutas. */
async function resolveSpec(
  reg: Registry,
  fromPath: string,
  spec: string,
  kind: SpecKind
): Promise<string | null> {
  const relative = normalize(`${dirname(fromPath)}/${spec}`);
  // /// <reference path="…"> es siempre relativo al archivo.
  if (kind === 'path') return resolveBase(reg, relative, DTS_EXTS);
  // /// <reference types="x"> → paquete x (o @types/x).
  if (kind === 'types') return packageEntry(reg, spec);
  if (spec.startsWith('.')) {
    // Dentro de un .d.ts preferir .d.ts; en código del proyecto, todo.
    return resolveBase(
      reg,
      relative,
      isInNodeModules(fromPath) ? DTS_EXTS : TS_EXTS
    );
  }
  const aliases = aliasBases(reg, spec);
  if (aliases.length) {
    for (const base of aliases) {
      const r = await resolveBase(reg, base, TS_EXTS);
      if (r) return r;
    }
    return null; // un alias que no resuelve no es un paquete
  }
  const pkg = packageOf(spec);
  if (!pkg) return null;
  const entry = await packageEntry(reg, pkg);
  if (!entry) return null;
  // Subpath (`react/jsx-runtime`): `root/sub(.d.ts|/index.d.ts)`, si no, entry.
  const sub = spec.slice(pkg.length).replace(/^\//, '');
  const root = reg.packageRoots.get(pkg);
  if (sub && root) {
    const r = await resolveBase(reg, normalize(`${root}/${sub}`), DTS_EXTS);
    if (r) return r;
  }
  return entry;
}

/** Un especificador que puede ser una ruta: sin espacios, sin `…` ni otros
 *  caracteres que ningún import real lleva. Lo que venga tras `?` (Vite:
 *  `x.worker?worker`) no es parte del módulo. */
function cleanSpec(raw: string): string | null {
  const s = raw.split('?')[0].trim();
  return s && /^[\w@./\-+~#:$]+$/.test(s) ? s : null;
}

function extractSpecs(text: string): Array<[string, SpecKind]> {
  const specs: Array<[string, SpecKind]> = [];
  // Comentarios fuera: el regex no distingue `import … from '@x/y'` dentro
  // de un bloque de documentación de un import real (medido: el encabezado
  // de este archivo generó un `…/package.json` 404). Las triple-slash
  // `/// <reference …>` se conservan.
  const code = text.replace(
    /\/\*[\s\S]*?\*\/|(^|[^:/])\/\/(?!\/)[^\n]*/g,
    (m, pre: string | undefined) => (m.startsWith('/*') ? '' : (pre ?? ''))
  );
  for (const mt of code.matchAll(IMPORT_RE)) {
    const kind: SpecKind = mt[4] ? 'path' : mt[5] ? 'types' : 'module';
    const s = cleanSpec(mt[4] ?? mt[5] ?? mt[1] ?? mt[2] ?? mt[3] ?? '');
    if (s) specs.push([s, kind]);
  }
  return specs;
}

/** BFS por frontera: cada ola procesa proyecto antes que node_modules. Sin
 *  límite de profundidad — lo que corta es el presupuesto en `reserve`, y
 *  `visited`/`inflight` garantizan que ningún archivo se lea dos veces. */
async function resolveGraph(reg: Registry, entry: string): Promise<void> {
  let frontier: string[] = [entry];
  while (frontier.length) {
    const next: string[] = [];
    frontier.sort(
      (a, b) => Number(isInNodeModules(a)) - Number(isInNodeModules(b))
    );
    await Promise.all(
      frontier.map(async (path) => {
        if (reg.visited.has(path)) return;
        reg.visited.add(path);
        const model = await materialize(reg, path);
        if (!model || !isTsLike(path) || /\.json$/i.test(path)) return;
        const text = model.getValue();
        if (!text) {
          // Modelo adoptado antes de que el editor cargue su contenido: no
          // hay nada que recorrer todavía y no debe quedar como visitado.
          reg.visited.delete(path);
          return;
        }

        const specs = extractSpecs(text);
        // Import implícito del compilador: con `jsx: react-jsx` cada .tsx/.jsx
        // importa `<jsxImportSource>/jsx-runtime` sin escribirlo (medido: sin
        // ese módulo, cada etiqueta JSX del archivo es un error).
        if (/\.(tsx|jsx)$/i.test(path)) {
          specs.push([`${JSX_IMPORT_SOURCE}/jsx-runtime`, 'module']);
        }
        await Promise.all(
          specs.map(async ([spec, kind]) => {
            const c = await resolveSpec(reg, path, spec, kind);
            if (!c || reg.models.get(c) === null) return; // no existe / no cabe
            const m = await materialize(reg, c);
            if (m && !reg.visited.has(c)) next.push(c);
          })
        );
      })
    );
    frontier = next;
  }
}

/** Punto de entrada: el editor abrió `path` en `workspaceId`. Materializa el
 *  grafo que ese archivo necesita. Idempotente y barato en repetición: lo ya
 *  cargado no se vuelve a pedir. No bloquea el render: fire-and-forget. */
export function prepareModelsFor(workspaceId: string, path: string): void {
  if (!isTsLike(path)) return; // Python/otros: no pasan por el TS worker
  if (!current || current.workspaceId !== workspaceId) {
    disposeRegistry();
    current = {
      workspaceId,
      models: new Map(),
      inflight: new Map(),
      visited: new Set(),
      packageEntries: new Map(),
      packageRoots: new Map(),
      dirListings: new Map(),
      tsconfigApplied: false,
      tsconfigPaths: null,
      projectRoot: '',
      nodeModulesRoots: ['node_modules'],
      tsconfigBaseDir: '',
      budget: {
        models: 0,
        bytes: 0,
        packages: new Set(),
        bytesPerPackage: new Map(),
      },
    };
    configureTsDefaults();
  }
  const reg = current;
  const entry = path.replace(/^\/+/, '');
  void (async () => {
    await applyTsconfig(reg, entry);
    const before = reg.budget.models;
    await resolveGraph(reg, entry);
    // Medido en monaco 0.56 (workerManager.js): `eagerModelSync` sincroniza
    // los modelos que EXISTEN al crear el cliente del worker; después sólo se
    // sincroniza el modelo que pide el editor. Los modelos materializados aquí
    // nacen con el worker ya vivo y no entran solos. Lo que reconstruye el
    // worker con todos los modelos es un cambio de defaults
    // (`setCompilerOptions` → onDidChange → _stopWorker), y el mismo evento
    // recalcula los diagnósticos de todos los modelos (languageFeatures.js).
    // Una vez por grafo, y sólo si el grafo añadió modelos.
    if (reg.budget.models > before) {
      configureTsDefaults(reg.tsconfigPaths, reg.tsconfigBaseDir);
    }
  })();
}

/** El editor cambió `path`: su contenido pudo ganar imports nuevos. Re-escanea
 *  SÓLO esa entrada —la saca de `visited` para que `resolveGraph` relea el texto
 *  ya editado— y materializa las dependencias añadidas mientras se edita, sin
 *  tirar el grafo ya cargado. Idempotente: con `debounce` en el editor. Si no
 *  hay grafo todavía (archivo que nació vacío) o es de otro workspace, delega en
 *  `prepareModelsFor` para construirlo desde cero. */
export function rescanModelsFor(workspaceId: string, path: string): void {
  if (!isTsLike(path)) return;
  if (!current || current.workspaceId !== workspaceId) {
    prepareModelsFor(workspaceId, path);
    return;
  }
  const reg = current;
  const entry = path.replace(/^\/+/, '');
  reg.visited.delete(entry);
  void (async () => {
    const before = reg.budget.models;
    await resolveGraph(reg, entry);
    // Mismo motivo que en `prepareModelsFor`: sólo si el grafo añadió modelos,
    // reconstruir el worker con todos y recalcular diagnósticos.
    if (reg.budget.models > before) {
      configureTsDefaults(reg.tsconfigPaths, reg.tsconfigBaseDir);
    }
  })();
}

/** El workspace cambió fuera del editor (otro tab, agente, commit): tirar el
 *  grafo para que el próximo `prepareModelsFor` relea. No toca el modelo que
 *  el editor tiene abierto (ese lo gobierna @monaco-editor/react). */
export function invalidateModels(workspaceId?: string): void {
  if (!current) return;
  if (workspaceId && current.workspaceId !== workspaceId) return;
  disposeRegistry();
}

function disposeRegistry(): void {
  if (!current) return;
  for (const m of current.models.values()) {
    if (m && !m.isDisposed() && !m.isAttachedToEditor()) m.dispose();
  }
  current = null;
}
