/**
 * monacoSetup — Monaco bundleado localmente (sin CDN) + workers + tema Fluent.
 *
 * Por defecto @monaco-editor/react descarga Monaco desde cdn.jsdelivr.net en
 * runtime. Eso implica: (a) dependencia de red/CSP en el Container App,
 * (b) los chunks de lenguaje (basic-languages/python, typescript, …) llegan
 * lazy y si uno falla el editor queda en plaintext sin avisar, (c) sin
 * MonacoEnvironment.getWorker no hay web workers → los servicios de lenguaje
 * integrados de Monaco (diagnostics/hover/completion para TS, JS, JSON, CSS,
 * HTML) NO corren. Este módulo bundlea Monaco con Vite y registra los workers,
 * y define un tema alineado a los tokens Fluent (dark/light) de la app.
 *
 * Importar UNA vez antes de renderizar cualquier <Editor>/<DiffEditor>.
 */

import { loader } from '@monaco-editor/react';
import * as monaco from 'monaco-editor';
// monaco-editor ≥0.56 publica un mapa `exports` ("./*" → "./esm/vs/*.js"):
// los subpaths se importan SIN el prefijo `esm/vs` y sin extensión. Las rutas
// `esm/vs/language/<x>` de las versiones 0.4x ya no resuelven; los language
// services viven en `languages/features/<x>`.
import editorWorker from 'monaco-editor/editor/editor.worker?worker';
import jsonWorker from 'monaco-editor/languages/features/json/json.worker?worker';
import cssWorker from 'monaco-editor/languages/features/css/css.worker?worker';
import htmlWorker from 'monaco-editor/languages/features/html/html.worker?worker';
import tsWorker from 'monaco-editor/languages/features/typescript/ts.worker?worker';
import * as tsDefinition from 'monaco-editor/languages/definitions/typescript/typescript';
import * as jsDefinition from 'monaco-editor/languages/definitions/javascript/javascript';

declare global {
  interface Window {
    MonacoEnvironment?: monaco.Environment;
  }
}

let configured = false;

/** Language ids que Monaco conoce de fábrica. Si `lang` no está aquí, hay que
 *  derivarlo del nombre de archivo — pasar "py" (extensión cruda) hace que
 *  Monaco caiga a plaintext: sin tokens, sin colores, sin indent guides. */
export function isMonacoLanguage(id: string | undefined | null): boolean {
  if (!id) return false;
  return monaco.languages.getLanguages().some((l) => l.id === id);
}

export function setupMonaco(): void {
  if (configured) return;
  configured = true;

  window.MonacoEnvironment = {
    getWorker(_moduleId: string, label: string) {
      switch (label) {
        case 'json':
          return new jsonWorker();
        case 'css':
        case 'scss':
        case 'less':
          return new cssWorker();
        case 'html':
        case 'handlebars':
        case 'razor':
          return new htmlWorker();
        case 'typescript':
        case 'javascript':
          return new tsWorker();
        default:
          return new editorWorker();
      }
    },
  };

  // Usar el Monaco bundleado en vez del loader remoto.
  loader.config({ monaco });

  // Temas alineados a Fluent (teamsDark / teamsLight). Heredan las reglas de
  // tokens de vs-dark / vs (keywords, strings, comments, numbers, types…) y
  // sólo ajustan el chrome del editor para que no rompa con el panel.
  monaco.editor.defineTheme('macae-dark', {
    base: 'vs-dark',
    inherit: true,
    rules: [],
    colors: {
      'editor.background': '#1f1f1f',
      'editorGutter.background': '#1f1f1f',
      'editorLineNumber.foreground': '#6e6e6e',
      'editorLineNumber.activeForeground': '#c8c8c8',
      'editorIndentGuide.background1': '#3a3a3a',
      'editorIndentGuide.activeBackground1': '#707070',
      'diffEditor.insertedTextBackground': '#2ea04333',
      'diffEditor.removedTextBackground': '#f8514933',
      'diffEditor.insertedLineBackground': '#2ea04322',
      'diffEditor.removedLineBackground': '#f8514922',
    },
  });
  monaco.editor.defineTheme('macae-light', {
    base: 'vs',
    inherit: true,
    rules: [],
    colors: {
      'editor.background': '#ffffff',
      'editorIndentGuide.background1': '#e5e5e5',
      'editorIndentGuide.activeBackground1': '#a0a0a0',
      'diffEditor.insertedTextBackground': '#2ea04333',
      'diffEditor.removedTextBackground': '#f8514933',
    },
  });

  // TS/JS: diagnósticos semánticos + sintácticos en el worker (red squiggles,
  // hover, completions). En monaco-editor ≥0.56 `languages.typescript` es un
  // stub `{ deprecated: true }`; la API real es el namespace de primer nivel
  // `monaco.typescript` (tipado, síncrono: la contribución TS se registra al
  // importar el entry principal, no hace falta esperar a loader.init()).
  // compilerOptions / eagerModelSync / extraLibs viven en modelRegistry: son
  // UNA sola pieza con el grafo de modelos y se aplican por workspace.
  const opts = { noSemanticValidation: false, noSyntaxValidation: false };
  monaco.typescript.typescriptDefaults.setDiagnosticsOptions(opts);
  monaco.typescript.javascriptDefaults.setDiagnosticsOptions(opts);
  // Python/otros: ver diagnostics vía backend (WorkspaceEditor).
}

/** Lenguaje "instantánea" para contenido TS/JS que NO debe entrar al
 *  compilador: mismo tokenizer y configuración (colores, brackets), ningún
 *  worker. El worker TS sincroniza y valida TODO modelo cuyo languageId sea
 *  `typescript`/`javascript` (workerManager.js:58, con eagerModelSync); el lado
 *  original del Diff (`git:HEAD/…`) con ese id resolvería sus imports contra
 *  `git:HEAD/…`, donde no existe ningún modelo, y pintaría squiggles falsos.
 *  Para los demás lenguajes no hay compilador detrás: se devuelve el mismo id. */
const SNAPSHOT_DEFINITIONS: Record<
  string,
  {
    conf: monaco.languages.LanguageConfiguration;
    language: monaco.languages.IMonarchLanguage;
  }
> = {
  typescript: tsDefinition,
  javascript: jsDefinition,
};

export function snapshotLanguage(language: string): string {
  const def = SNAPSHOT_DEFINITIONS[language];
  if (!def) return language;
  const id = `${language}-snapshot`;
  if (!isMonacoLanguage(id)) {
    monaco.languages.register({ id });
    monaco.languages.setMonarchTokensProvider(id, def.language);
    monaco.languages.setLanguageConfiguration(id, def.conf);
  }
  return id;
}

/** Tema Monaco según el esquema del SO (mismo criterio que index.tsx). */
export function monacoThemeName(): 'macae-dark' | 'macae-light' {
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches
    ? 'macae-dark'
    : 'macae-light';
}

export { monaco };
