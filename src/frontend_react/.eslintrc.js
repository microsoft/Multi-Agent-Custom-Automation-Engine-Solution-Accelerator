module.exports = {
    root: true,
    extends: [
        'react-app',
        'react-app/jest',
        'plugin:react/recommended',
    ],
    plugins: ['react', '@typescript-eslint'],
    parserOptions: {
        ecmaVersion: 2020,
        sourceType: 'module',
        ecmaFeatures: {
            jsx: true
        }
    },
    settings: {
        react: {
            version: 'detect'
        }
    },
    rules: {
        // Add custom rules here
        'react/react-in-jsx-scope': 'off', // Not needed in React 17+
    }
};
