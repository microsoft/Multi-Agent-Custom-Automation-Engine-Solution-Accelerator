/**
 * workspaceTreeStore — estado del explorador por workspace, FUERA del árbol
 * de React.
 *
 * Por qué: el árbol vive en el "resting slot" del panel de artefactos y se
 * DESMONTA cada vez que se abre un archivo. Con el estado dentro del
 * componente, cada cierre de tab remontaba el árbol → efecto de arranque →
 * GET /entries → expansión perdida. El remount era el mecanismo de coherencia,
 * es decir, lifecycle de UI mezclado con consistencia del filesystem.
 *
 * Aquí el estado (niveles cargados + expansión) persiste entre montajes, y la
 * coherencia con Azure Files se obtiene por invalidación EXPLÍCITA:
 *   - invalidate(ws, dir)   → un nivel (mutación conocida: create/delete/rename/save)
 *   - invalidateAll(ws)     → todo, conservando expansión y lo ya cargado en
 *                             pantalla hasta que llega la relectura (Refresh / turno / foco)
 *   - expandir una carpeta  → carga si no está en caché
 * Nunca por (des)montaje. Mismo patrón que WebSocketService / useVoiceLive:
 * singleton de módulo + suscripción, sin hooks dentro del store.
 *
 * Tres invariantes que el contrato (harness Playwright) verifica:
 *   1. Un error del backend NO es verdad sobre el filesystem: no se cachea como
 *      nivel vacío; el próximo expand reintenta.
 *   2. Las respuestas se aplican por IDENTIDAD de lectura (secuencia por
 *      nivel), no por orden de llegada: una lectura vieja que llega tarde no
 *      pisa a la nueva. Sin ventanas de reloj.
 *   3. invalidateAll descarta los niveles cargados pero colapsados: al
 *      re-expandir se releen, nunca se muestra caché anterior al refresh.
 */
import { useSyncExternalStore } from 'react';
import { apiClient } from '../../api/apiClient';
import { invalidateModels, reconcileModels } from '../content/modelRegistry';

export interface DirEntry {
  name: string;
  type: 'directory' | 'file';
  size?: number | null;
  status?: string | null; // "M" | "?" | null
}

export type Level = DirEntry[] | 'loading';

interface WsState {
  levels: Record<string, Level>; // key: dir relativo ('' = raíz)
  expanded: Set<string>;
}

const EMPTY: WsState = { levels: {}, expanded: new Set() };
const states = new Map<string, WsState>();
const listeners = new Set<() => void>();
// Secuencia de lectura por workspace y por nivel: identifica la ÚLTIMA lectura
// pedida de ese nivel. Una respuesta sólo se aplica si pertenece a esa lectura.
// Mapa anidado (no una clave compuesta con separador): un dir puede contener
// cualquier carácter y el archivo debe seguir siendo texto plano para git.
const readSeq = new Map<string, Map<string, number>>();

function bumpSeq(ws: string, dir: string): number {
  let byDir = readSeq.get(ws);
  if (!byDir) {
    byDir = new Map<string, number>();
    readSeq.set(ws, byDir);
  }
  const next = (byDir.get(dir) ?? 0) + 1;
  byDir.set(dir, next);
  return next;
}

function currentSeq(ws: string, dir: string): number {
  return readSeq.get(ws)?.get(dir) ?? 0;
}

function get(ws: string): WsState {
  return states.get(ws) ?? EMPTY;
}

function set(ws: string, next: WsState): void {
  states.set(ws, next);
  listeners.forEach((l) => l());
}

function parentOf(path: string): string {
  const i = path.lastIndexOf('/');
  return i < 0 ? '' : path.slice(0, i);
}

async function load(ws: string, dir: string): Promise<void> {
  const mine = bumpSeq(ws, dir);
  const cur = get(ws);
  // Relectura de un nivel ya cargado: lo cargado sigue en pantalla hasta que
  // llega lo nuevo. Ponerlo en 'loading' vaciaba el explorador entero al
  // terminar cada respuesta (invalidateAll) y lo dejaba en spinner mientras
  // el proxy respondía (medido: decenas de segundos por turno).
  const prev = cur.levels[dir];
  if (!Array.isArray(prev)) {
    set(ws, { ...cur, levels: { ...cur.levels, [dir]: 'loading' } });
  }
  let entries: DirEntry[] | null = null;
  try {
    const r: { entries?: DirEntry[] } = await apiClient.get(
      `/v4/workspace/${encodeURIComponent(ws)}/entries`,
      { params: dir ? { path: dir } : undefined }
    );
    entries = r.entries ?? [];
  } catch {
    entries = null; // error: sin caché → el próximo expand reintenta
  }
  // Llegó una lectura más nueva de este nivel mientras esta estaba en vuelo:
  // esta respuesta ya no representa el estado pedido más recientemente.
  if (currentSeq(ws, dir) !== mine) return;
  const now = get(ws);
  const levels = { ...now.levels };
  if (entries === null) delete levels[dir];
  else levels[dir] = entries;
  set(ws, { ...now, levels });
}

export const workspaceTree = {
  subscribe(l: () => void): () => void {
    listeners.add(l);
    return () => listeners.delete(l);
  },
  getSnapshot(ws: string): WsState {
    return get(ws);
  },

  /** Garantiza que un nivel esté cargado (no recarga si ya está en caché). */
  ensure(ws: string, dir = ''): void {
    if (get(ws).levels[dir] === undefined) void load(ws, dir);
  },

  toggle(ws: string, dir: string): void {
    const cur = get(ws);
    const expanded = new Set(cur.expanded);
    if (expanded.has(dir)) expanded.delete(dir);
    else expanded.add(dir);
    set(ws, { ...cur, expanded });
    if (!cur.expanded.has(dir)) workspaceTree.ensure(ws, dir);
  },

  /**
   * Invalida el nivel que contiene `path` (o `path` mismo si es un dir
   * cargado). Para create/delete/rename/save originados por MACAE: el
   * cliente conoce el path, así que releer UN nivel basta y las marcas git
   * (M/?) del nivel y sus ancestros vuelven correctas.
   */
  invalidate(ws: string, path: string): void {
    const cur = get(ws);
    const dirs = new Set<string>([parentOf(path)]);
    if (cur.levels[path] !== undefined) dirs.add(path);
    // Ancestros cargados: sus marcas agregadas (M/?) también cambian.
    let p = parentOf(path);
    while (p) {
      p = parentOf(p);
      dirs.add(p);
    }
    dirs.forEach((d) => {
      if (cur.levels[d] !== undefined) void load(ws, d);
    });
  },

  /**
   * Reconciliación completa contra el filesystem real: relee la raíz y TODOS
   * los niveles actualmente expandidos, conservando la expansión para no
   * perderle la posición al usuario. Los niveles cargados pero colapsados se
   * descartan (y se anula cualquier lectura suya en vuelo): al expandirlos se
   * releen. Es lo que hace el botón Refresh, el cierre de un turno de chat con
   * actividad de tools y la recuperación de visibilidad.
   */
  invalidateAll(ws: string): void {
    // Los modelos dependientes que el TS worker ve son una lectura del mismo
    // filesystem: si el árbol se relee, ellos también quedan obsoletos. Se
    // RECONCILIAN (re-resolver desde las entradas activas releyendo el disco)
    // sin recrear los ITextModel abiertos: disponer el grafo quitaría el
    // IntelliSense de proyecto del archivo abierto, porque el efecto del editor
    // no vuelve a correr (su workspace, path y contenido no cambian).
    reconcileModels(ws);
    const cur = get(ws);
    const keep = new Set<string>(['']);
    cur.expanded.forEach((d) => keep.add(d));
    const levels: Record<string, Level> = {};
    Object.keys(cur.levels).forEach((d) => {
      if (keep.has(d)) levels[d] = cur.levels[d];
      else bumpSeq(ws, d);
    });
    set(ws, { ...cur, levels });
    keep.forEach((d) => void load(ws, d));
  },

  /** Cambio de workspace: descarta el estado de ese ws (raro; explícito). */
  reset(ws: string): void {
    invalidateModels(ws);
    states.delete(ws);
    readSeq.delete(ws);
    listeners.forEach((l) => l());
  },
};

// Cambios externos (otra pestaña, el share SMB, un agente fuera de un turno de
// chat) se reconcilian al recuperar visibilidad. El listener vive AQUÍ y no en
// WorkspaceTree: el árbol está desmontado mientras hay un archivo abierto, y un
// listener de componente no existe justo cuando el usuario vuelve con un
// archivo abierto → al cerrarlo, el árbol mostraría caché vieja. Se registra
// una vez por módulo y reconcilia todos los workspaces con estado cargado.
if (typeof document !== 'undefined') {
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState !== 'visible') return;
    states.forEach((_state, ws) => workspaceTree.invalidateAll(ws));
  });
}

/** Vista React del store para un workspace. */
export function useWorkspaceTree(ws: string): WsState {
  return useSyncExternalStore(
    workspaceTree.subscribe,
    () => workspaceTree.getSnapshot(ws),
    () => workspaceTree.getSnapshot(ws)
  );
}
