/// <reference types="vite/client" />

interface ImportMetaEnv {
    readonly REACT_APP_API_URL?: string
    readonly REACT_APP_ENVIRONMENT?: string
    // Add more environment variables as needed
}

interface ImportMeta {
    readonly env: ImportMetaEnv
}

// Las definiciones Monarch de monaco-editor (`languages/definitions/<x>/<x>`)
// se publican sin .d.ts. Exportan el tokenizer y la configuración del lenguaje.
declare module 'monaco-editor/languages/definitions/*' {
    import type { languages } from 'monaco-editor'
    export const conf: languages.LanguageConfiguration
    export const language: languages.IMonarchLanguage
}
