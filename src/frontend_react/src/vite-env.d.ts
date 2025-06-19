/// <reference types="vite/client" />

interface ImportMetaEnv {
    readonly REACT_APP_API_URL?: string
    readonly REACT_APP_ENVIRONMENT?: string
    // Add more environment variables as needed
}

interface ImportMeta {
    readonly env: ImportMetaEnv
}
