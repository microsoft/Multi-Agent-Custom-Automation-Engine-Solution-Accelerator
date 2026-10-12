/**
 * WorkspaceEditor — Monaco Code + Diff tabs bound to the per-session workspace.
 *
 * Architecture
 * ────────────
 *   Monaco  ←→  /api/v4/workspace/{workspaceId}/files/{path}  ←→  server-side
 *   Git     ←→  /api/v4/workspace/{workspaceId}/commit|diff|restore   resolver:
 *                                                    {root}/{user_id}/{workspaceId}/
 *
 * The editor only ever knows the workspace IDENTIFIER (today: the chat
 * session id) — the server resolves it to a per-user data directory with its
 * own git repo. Identical in dev and prod; never the app source tree.
 *
 * Tabs vs actions
 * ───────────────
 *   Tab BUTTONS render only when the parent does not control `tab` (the
 *   panel header already renders Preview/Code/Diff). The ACTION buttons
 *   (Save / Commit / Revert / diff reload) always render: the parent owns
 *   tab navigation, the editor owns file actions.
 */

import Editor, { DiffEditor, type OnMount } from '@monaco-editor/react';
import { Button, Spinner, Tooltip } from '@fluentui/react-components';
import {
  Save20Regular,
  ArrowCounterclockwise20Regular,
  Checkmark20Regular,
} from '@fluentui/react-icons';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { apiClient } from '../../api/apiClient';
import { workspaceTree } from '../workspace/workspaceTreeStore';
import {
  isMonacoLanguage,
  monaco,
  monacoThemeName,
  setupMonaco,
  snapshotLanguage,
} from './monacoSetup';
import { prepareModelsFor, rescanModelsFor } from './modelRegistry';

// Monaco bundleado + workers + temas: una vez por proceso, antes del 1er render.
setupMonaco();

// Owner de markers: Monaco reemplaza atómicamente todos los markers de un owner
// en setModelMarkers(model, owner, [...]); es lo que evita mezclar/duplicar.
const DIAG_OWNER = 'macae-diagnostics';

type DiagnosticDTO = {
  line: number;
  column: number;
  end_line?: number;
  end_column?: number;
  severity: 'error' | 'warning' | 'info' | 'hint';
  message: string;
  code?: string;
  source?: string;
};

// ── helpers ────────────────────────────────────────────────────────────────

/** Map common extensions to Monaco language IDs. */
function langFromFilename(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase() ?? '';
  const MAP: Record<string, string> = {
    ts: 'typescript',
    tsx: 'typescript',
    js: 'javascript',
    jsx: 'javascript',
    py: 'python',
    pyw: 'python',
    html: 'html',
    htm: 'html',
    css: 'css',
    scss: 'scss',
    json: 'json',
    jsonc: 'json',
    yaml: 'yaml',
    yml: 'yaml',
    md: 'markdown',
    sh: 'shell',
    bash: 'shell',
    bicep: 'bicep',
    sql: 'sql',
    xml: 'xml',
    svg: 'xml',
    cs: 'csharp',
    java: 'java',
    cpp: 'cpp',
    c: 'c',
    h: 'c',
    rs: 'rust',
    go: 'go',
    toml: 'toml',
  };
  return MAP[ext] ?? 'plaintext';
}

/** Derive the workspace-relative path from an artifact title.
 *  e.g. "app/main.py" → "app/main.py", "main.py" → "main.py" */
function workspacePath(title: string): string {
  // Strip leading slash if present; keep subdirs as-is
  return title.replace(/^\/+/, '');
}

/** Encode each path segment, preserving the '/' separators the API expects. */
function encodePath(path: string): string {
  return path.split('/').map(encodeURIComponent).join('/');
}

// ── types ──────────────────────────────────────────────────────────────────

type EditorTab = 'code' | 'diff';

interface WorkspaceEditorProps {
  /** Artifact title used to derive the workspace path (e.g. "src/app/main.py"). */
  title: string;
  /** Initial content from the artifact context (may be updated by streaming). */
  content: string;
  /** Monaco language override; auto-detected from title if omitted. */
  lang?: string;
  /** Workspace identifier (the chat session id). Without it the editor is
   *  read-only: there is no workspace to save into. */
  workspaceId?: string | null;
  /** Controlled active tab. When provided the parent owns tab state. */
  tab?: EditorTab;
  /** Called when the user switches tabs. Required when `tab` is provided. */
  onTabChange?: (tab: EditorTab) => void;
}

// ── component ──────────────────────────────────────────────────────────────

export const WorkspaceEditor: React.FC<WorkspaceEditorProps> = ({
  title,
  content,
  lang,
  workspaceId,
  tab: tabProp,
  onTabChange,
}) => {
  const path = workspacePath(title);
  // `lang` puede llegar como extensión cruda ("py") desde el explorador de
  // archivos: eso NO es un language id de Monaco → plaintext (sin tokens ni
  // colores). Sólo se respeta si Monaco lo reconoce; si no, se deriva del nombre.
  const language = isMonacoLanguage(lang)
    ? (lang as string)
    : langFromFilename(title);
  const theme = monacoThemeName();
  // apiClient prepends the API root, so paths start at /v4 (never '/api/v4').
  // ONE http client for the whole app: apiClient carries the principal headers
  // and refreshes the token. A private fetch here used credentials:'include',
  // which the Container Apps ingress (corsPolicy allowCredentials=false)
  // rejects at preflight — the request never left the browser ("Failed to
  // fetch", zero backend logs). Do not reintroduce a second client.
  const base = workspaceId
    ? `/v4/workspace/${encodeURIComponent(workspaceId)}`
    : null;

  const [tabInternal, setTabInternal] = useState<EditorTab>('code');
  const tab = tabProp ?? tabInternal;
  const setTab = useCallback(
    (t: EditorTab) => {
      if (onTabChange) onTabChange(t);
      else setTabInternal(t);
    },
    [onTabChange]
  );

  // ── Code tab state ──
  const [editorValue, setEditorValue] = useState(content);
  const [busy, setBusy] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);
  const lastSaved = useRef(content);
  const prevPath = useRef(path);

  // If the user switches to a different artifact/file, reset editor state even if
  // the previous file had unsaved edits.
  useEffect(() => {
    if (prevPath.current !== path) {
      prevPath.current = path;
      setTab('code');
      setEditorValue(content);
      lastSaved.current = content;
      setDirty(false);
      setSaveMsg(null);
    }
  }, [path, content, setTab]);

  // Keep editor in sync when artifact content updates (e.g. streaming finishes)
  // but do NOT overwrite unsaved user edits.
  useEffect(() => {
    if (!dirty) {
      setEditorValue(content);
      lastSaved.current = content;
    }
  }, [content, dirty]);

  const handleEditorChange = useCallback((val: string | undefined) => {
    const v = val ?? '';
    setEditorValue(v);
    setDirty(v !== lastSaved.current);
    setSaveMsg(null);
  }, []);

  const handleSave = useCallback(async () => {
    if (!base) return;
    setBusy(true);
    setSaveMsg(null);
    try {
      await apiClient.put(`${base}/files/${encodePath(path)}`, {
        content: editorValue,
      });
      lastSaved.current = editorValue;
      setDirty(false);
      setSaveMsg('Saved ✓');
      // Mutación conocida: sólo el nivel de este path (y marcas ancestrales).
      if (workspaceId) workspaceTree.invalidate(workspaceId, path);
      setTimeout(() => setSaveMsg(null), 2000);
    } catch (e) {
      setSaveMsg(`Error: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }, [base, editorValue, path, workspaceId]);

  const handleCommit = useCallback(async () => {
    if (!base) return;
    setBusy(true);
    setSaveMsg(null);
    try {
      const r: { committed: boolean; sha: string } = await apiClient.post(
        `${base}/commit`,
        { message: `Update ${path}` }
      );
      setSaveMsg(
        r.committed ? `Committed ${r.sha.slice(0, 7)} ✓` : 'Nothing to commit'
      );
      // Un commit limpia marcas M/? en cualquier nivel cargado.
      if (r.committed && workspaceId) workspaceTree.invalidateAll(workspaceId);
      setTimeout(() => setSaveMsg(null), 3000);
    } catch (e) {
      setSaveMsg(`Error: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }, [base, path, workspaceId]);

  const handleRevert = useCallback(() => {
    setEditorValue(lastSaved.current);
    setDirty(false);
    setSaveMsg(null);
  }, []);

  // ── Diagnósticos ──
  // Monaco trae language services (worker) para TS/JS/JSON/CSS/HTML. Para
  // Python NO analiza nada por sí solo: los diagnósticos vienen del backend
  // (POST /workspace/{id}/diagnostics) y se materializan como markers → red
  // squiggles + hover, igual que Problems en VS Code.
  //
  // Patrón nativo de Monaco (el mismo de sus language workers): un provider
  // atado al MODELO, no a strings. Se suscribe a model.onDidChangeContent y
  // usa model.getVersionId() —el reloj monotónico que Monaco ya mantiene— como
  // única fuente de verdad. Al volver una respuesta: si el versionId coincide
  // se publican los markers; si no, NO se descarta en silencio (eso deja un
  // marker huérfano cuando la respuesta buena llega "tarde"): se re-lanza para
  // la versión actual. Invariante: siempre existe un request para la última
  // versión, y los markers publicados siempre corresponden al texto visible.
  const editorRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(null);
  const diagDisposer = useRef<monaco.IDisposable | null>(null);
  const rescanDisposer = useRef<monaco.IDisposable | null>(null);
  const rescanKey = useRef<string>('');
  // Identidad del provider vigente: (modelo, base, path, language). Atar es
  // idempotente por esa clave: al cambiar de archivo con el editor montado,
  // onDidChangeModel y el efecto de identidad piden el MISMO provider para el
  // MISMO modelo en un mismo commit; sin esta guarda el segundo attach
  // descartaba al primero y salían dos POST /diagnostics por apertura.
  const diagKey = useRef<string>('');

  const attachDiagnostics = useCallback(
    (model: monaco.editor.ITextModel) => {
      const key = `${model.id}|${base ?? ''}|${path}|${language}`;
      if (diagDisposer.current && diagKey.current === key) return;
      diagDisposer.current?.dispose();
      diagDisposer.current = null;
      diagKey.current = key;
      if (!base || language !== 'python') {
        monaco.editor.setModelMarkers(model, DIAG_OWNER, []);
        return;
      }

      let timer: ReturnType<typeof setTimeout> | null = null;
      let inFlight = false;
      let dirtyWhileInFlight = false;
      let disposed = false;

      const sev: Record<string, monaco.MarkerSeverity> = {
        error: monaco.MarkerSeverity.Error,
        warning: monaco.MarkerSeverity.Warning,
        info: monaco.MarkerSeverity.Info,
        hint: monaco.MarkerSeverity.Hint,
      };

      const run = async () => {
        if (disposed || model.isDisposed()) return;
        if (inFlight) {
          dirtyWhileInFlight = true;
          return;
        }
        inFlight = true;
        const version = model.getVersionId();
        try {
          const r: { diagnostics: DiagnosticDTO[] } = await apiClient.post(
            `${base}/diagnostics`,
            { path, content: model.getValue(), language }
          );
          if (disposed || model.isDisposed()) return;
          if (model.getVersionId() === version) {
            monaco.editor.setModelMarkers(
              model,
              DIAG_OWNER,
              (r.diagnostics || []).map((d) => ({
                startLineNumber: d.line,
                startColumn: d.column,
                endLineNumber: d.end_line ?? d.line,
                endColumn: d.end_column ?? d.column + 1,
                severity: sev[d.severity] ?? monaco.MarkerSeverity.Warning,
                message: d.message,
                code: d.code,
                source: d.source ?? 'macae',
              }))
            );
          } else {
            dirtyWhileInFlight = true; // respuesta de una versión vieja → re-lanzar
          }
        } catch {
          /* best-effort: no romper la edición; el próximo cambio reintenta */
        } finally {
          inFlight = false;
          if (dirtyWhileInFlight && !disposed) {
            dirtyWhileInFlight = false;
            void run();
          }
        }
      };

      const schedule = () => {
        monaco.editor.setModelMarkers(model, DIAG_OWNER, []);
        if (timer) clearTimeout(timer);
        timer = setTimeout(() => void run(), 600);
      };

      const sub = model.onDidChangeContent(schedule);
      void run(); // estado inicial
      diagDisposer.current = {
        dispose: () => {
          disposed = true;
          if (timer) clearTimeout(timer);
          sub.dispose();
          if (!model.isDisposed())
            monaco.editor.setModelMarkers(model, DIAG_OWNER, []);
        },
      };
    },
    [base, path, language]
  );

  // Siempre la versión vigente de attachDiagnostics: el handler de
  // onDidChangeModel se registra una vez al montar y, sin esto, quedaría
  // atado al path/language del PRIMER archivo (closure obsoleto) y pediría
  // diagnósticos del archivo anterior para el modelo nuevo.
  const attachRef = useRef(attachDiagnostics);
  attachRef.current = attachDiagnostics;

  const handleMount: OnMount = useCallback((editor) => {
    editorRef.current = editor;
    const m = editor.getModel();
    if (m) {
      attachRef.current(m);
      attachRescanRef.current(m);
    }
    // El modelo cambia al abrir otro archivo: re-atar al nuevo.
    editor.onDidChangeModel(() => {
      const nm = editor.getModel();
      if (nm) {
        attachRef.current(nm);
        attachRescanRef.current(nm);
      }
    });
  }, []);

  // path/language/base cambian → re-atar al modelo vigente
  useEffect(() => {
    const m = editorRef.current?.getModel();
    if (m) attachDiagnostics(m);
  }, [attachDiagnostics]);

  // IntelliSense de PROYECTO: materializar la cadena de imports del archivo
  // abierto como modelos con URI real para que el TS worker los vea
  // (registry + resolver + eagerModelSync + compilerOptions: ver modelRegistry).
  // Fire-and-forget: no bloquea el render ni la apertura del archivo.
  // Con el contenido ya cargado: al montar, `content` es '' y el registry
  // adoptaría el modelo vacío del editor (cero imports, entrada visitada).
  // Medido en noVNC: el grafo moría tras leer el archivo abierto.
  useEffect(() => {
    if (workspaceId && content) prepareModelsFor(workspaceId, path);
  }, [workspaceId, path, content]);

  // El grafo se arma una vez desde `content`; `resolveGraph` marca el archivo
  // como visitado y no vuelve a leerlo. Un import añadido EN el editor (o un
  // archivo que nació vacío y nunca inicializó el registry) quedaría sin
  // materializar hasta un refresh o cambio de archivo. Suscribirse al modelo y
  // re-escanear SÓLO esa entrada (con debounce) materializa esos imports en
  // caliente. Atado al MODELO y re-atado en onDidChangeModel, igual que los
  // diagnósticos: así sigue al archivo vigente y no queda en un closure viejo.
  const attachRescan = useCallback(
    (model: monaco.editor.ITextModel) => {
      const key = `${model.id}|${workspaceId ?? ''}|${path}`;
      if (rescanDisposer.current && rescanKey.current === key) return;
      rescanDisposer.current?.dispose();
      rescanDisposer.current = null;
      rescanKey.current = key;
      if (!workspaceId) return;
      let timer: ReturnType<typeof setTimeout> | null = null;
      const sub = model.onDidChangeContent(() => {
        if (timer) clearTimeout(timer);
        timer = setTimeout(() => rescanModelsFor(workspaceId, path), 600);
      });
      rescanDisposer.current = {
        dispose: () => {
          if (timer) clearTimeout(timer);
          sub.dispose();
        },
      };
    },
    [workspaceId, path]
  );
  const attachRescanRef = useRef(attachRescan);
  attachRescanRef.current = attachRescan;

  // workspaceId/path cambian → re-atar el rescan al modelo vigente.
  useEffect(() => {
    const m = editorRef.current?.getModel();
    if (m) attachRescan(m);
  }, [attachRescan]);

  useEffect(() => () => diagDisposer.current?.dispose(), []);
  useEffect(() => () => rescanDisposer.current?.dispose(), []);

  // ── Diff tab state ──
  const [diffData, setDiffData] = useState<{
    original: string;
    modified: string;
  } | null>(null);
  const [diffLoading, setDiffLoading] = useState(false);
  const [diffError, setDiffError] = useState<string | null>(null);

  const loadDiff = useCallback(async () => {
    if (!base) return;
    setDiffLoading(true);
    setDiffError(null);
    setDiffData(null);
    try {
      const data: { original: string; modified: string } = await apiClient.get(
        `${base}/diff/${encodePath(path)}`
      );
      setDiffData(data);
    } catch (e) {
      setDiffData(null);
      setDiffError((e as Error).message);
    } finally {
      setDiffLoading(false);
    }
  }, [base, path]);

  useEffect(() => {
    if (tab === 'diff') loadDiff();
  }, [tab, loadDiff]);

  // ── render ──
  const tabBtn = (t: EditorTab, label: string) => (
    <Button
      appearance={tab === t ? 'primary' : 'subtle'}
      size="small"
      onClick={() => setTab(t)}
      style={{ minWidth: 'auto' }}
    >
      {label}
    </Button>
  );

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        width: '100%',
        minWidth: 0,
      }}
    >
      {/* Action bar: tab buttons only when uncontrolled; actions always. */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          padding: '4px 8px',
          borderBottom: '1px solid var(--colorNeutralStroke1)',
          background: 'var(--colorNeutralBackground2)',
          flexShrink: 0,
        }}
      >
        {!tabProp && (
          <>
            {tabBtn('code', 'Code')}
            {tabBtn('diff', 'Diff')}
          </>
        )}

        {!base && (
          <span
            style={{
              fontSize: '11px',
              color: 'var(--colorNeutralForeground3)',
            }}
          >
            Read-only: no active workspace for this view.
          </span>
        )}

        {tab === 'code' && base && (
          <div
            style={{
              display: 'flex',
              gap: '4px',
              marginLeft: 'auto',
              alignItems: 'center',
            }}
          >
            {saveMsg && (
              <span
                style={{
                  fontSize: '11px',
                  color: saveMsg.startsWith('Error')
                    ? 'var(--colorStatusDangerForeground1)'
                    : 'var(--colorStatusSuccessForeground1)',
                }}
              >
                {saveMsg}
              </span>
            )}
            {dirty && (
              <Tooltip content="Revert to last saved" relationship="label">
                <Button
                  appearance="subtle"
                  size="small"
                  icon={<ArrowCounterclockwise20Regular />}
                  onClick={handleRevert}
                />
              </Tooltip>
            )}
            <Tooltip content={`Save to workspace/${path}`} relationship="label">
              <Button
                appearance={dirty ? 'primary' : 'subtle'}
                size="small"
                icon={busy ? <Spinner size="tiny" /> : <Save20Regular />}
                onClick={handleSave}
                disabled={busy || !dirty}
              >
                Save
              </Button>
            </Tooltip>
            <Tooltip
              content="Commit all workspace changes to git"
              relationship="label"
            >
              <Button
                appearance="subtle"
                size="small"
                icon={<Checkmark20Regular />}
                onClick={handleCommit}
                disabled={busy || dirty}
              >
                Commit
              </Button>
            </Tooltip>
          </div>
        )}

        {tab === 'diff' && base && (
          <div style={{ marginLeft: 'auto' }}>
            <Tooltip
              content="Reload diff from git HEAD vs disk"
              relationship="label"
            >
              <Button
                appearance="subtle"
                size="small"
                icon={<ArrowCounterclockwise20Regular />}
                onClick={loadDiff}
                disabled={diffLoading}
              />
            </Tooltip>
          </div>
        )}
      </div>

      {/* Editor area. minWidth/minHeight 0: un flex item por defecto no encoge
          por debajo de su contenido, y Monaco mide su contenedor una sola vez al
          montar — sin esto el panel original del DiffEditor queda colapsado
          cuando el panel lateral se redimensiona. automaticLayout (abajo) hace
          que Monaco observe el contenedor y se ajuste al ancho real. */}
      <div
        style={{
          flex: 1,
          minHeight: 0,
          minWidth: 0,
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {tab === 'code' && (
          <Editor
            height="100%"
            theme={theme}
            language={language}
            path={path}
            value={editorValue}
            onChange={handleEditorChange}
            onMount={handleMount}
            keepCurrentModel
            options={{
              automaticLayout: true,
              readOnly: !base,
              minimap: { enabled: true, renderCharacters: false },
              fontSize: 13,
              fontFamily:
                "'Cascadia Code', 'Fira Code', Consolas, 'Courier New', monospace",
              fontLigatures: true,
              lineNumbers: 'on',
              wordWrap: 'on',
              scrollBeyondLastLine: false,
              renderWhitespace: 'boundary',
              renderLineHighlight: 'all',
              guides: { indentation: true, bracketPairs: true },
              bracketPairColorization: { enabled: true },
              folding: true,
              showFoldingControls: 'mouseover',
              smoothScrolling: true,
              cursorBlinking: 'smooth',
              cursorSmoothCaretAnimation: 'on',
              formatOnPaste: true,
              suggestOnTriggerCharacters: true,
              quickSuggestions: true,
              tabSize: language === 'python' ? 4 : 2,
              detectIndentation: true,
              stickyScroll: { enabled: true },
            }}
          />
        )}

        {tab === 'diff' && (
          <>
            {!base && (
              <div
                style={{
                  padding: '16px',
                  fontSize: '12px',
                  color: 'var(--colorNeutralForeground3)',
                }}
              >
                No active workspace — diff unavailable.
              </div>
            )}
            {diffLoading && (
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'center',
                  padding: '24px',
                }}
              >
                <Spinner size="small" label="Loading diff…" />
              </div>
            )}
            {diffError && (
              <div
                style={{
                  padding: '16px',
                  fontSize: '12px',
                  color: 'var(--colorStatusDangerForeground1)',
                }}
              >
                {diffError}
              </div>
            )}
            {diffData && !diffLoading && (
              <DiffEditor
                height="100%"
                theme={theme}
                language={language}
                // Lado modificado = EL modelo del archivo (`file:///{path}`, el
                // mismo que el tab Code y el registry): un solo modelo por
                // archivo para el worker, con sus imports resueltos. No se
                // dispone al cerrar el Diff porque no es de este editor.
                // Lado original = instantánea HEAD con el mismo tokenizer pero
                // fuera del compilador (ver snapshotLanguage).
                originalLanguage={snapshotLanguage(language)}
                originalModelPath={`git:HEAD/${path}`}
                modifiedModelPath={path}
                keepCurrentModifiedModel
                original={diffData.original}
                modified={diffData.modified}
                options={{
                  automaticLayout: true,
                  readOnly: true,
                  minimap: { enabled: false },
                  fontSize: 13,
                  fontFamily:
                    "'Cascadia Code', 'Fira Code', Consolas, 'Courier New', monospace",
                  wordWrap: 'on',
                  // Side-by-side (ORIGINAL | MODIFIED) como VS Code mientras
                  // haya ancho; inline sólo por debajo del breakpoint. El
                  // panel lateral suele medir 500–900px: con 700 casi siempre
                  // caía a inline, que es lo que se veía.
                  renderSideBySide: true,
                  useInlineViewWhenSpaceIsLimited: true,
                  renderSideBySideInlineBreakpoint: 480,
                  renderIndicators: true,
                  renderMarginRevertIcon: false,
                  renderOverviewRuler: true,
                  ignoreTrimWhitespace: false,
                  scrollBeyondLastLine: false,
                  diffWordWrap: 'on',
                  guides: { indentation: true },
                  glyphMargin: true,
                  hideUnchangedRegions: { enabled: true },
                }}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
};
