import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],

    // Define path aliases (similar to Create React App)
    resolve: {
        alias: {
            '@': resolve(__dirname, 'src'),
        },
    },



    // Server configuration
    server: {
        port: 3001,
        open: true,
        host: true
    },

    // Build configuration
    build: {
        outDir: 'build',
        sourcemap: true,
        // Optimize dependencies
        rollupOptions: {
            output: {
                manualChunks: {
                    vendor: ['react', 'react-dom'],
                    fluentui: ['@fluentui/react-components', '@fluentui/react-icons'],
                    router: ['react-router-dom'],
                }
            }
        }
    },

    // Handle CSS and static assets
    css: {
        modules: {
            localsConvention: 'camelCase'
        }
    },

    // Environment variables configuration
    envPrefix: 'REACT_APP_',

    // Define global constants
    define: {
        'process.env': process.env,
    },

    // Optimization
    optimizeDeps: {
        include: [
            'react',
            'react-dom',
            '@fluentui/react-components',
            '@fluentui/react-icons',
            'react-router-dom',
            'axios'
        ]
    }
})