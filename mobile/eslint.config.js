const parser = require('@typescript-eslint/parser');
const typescript = require('@typescript-eslint/eslint-plugin');
const globals = require('globals');
module.exports = [{ ignores: ['node_modules/**', '.expo/**', 'dist/**'] }, {
  files: ['app/**/*.{ts,tsx}', 'src/**/*.{ts,tsx}'],
  languageOptions: { parser, parserOptions: { ecmaVersion: 'latest', sourceType: 'module', ecmaFeatures: { jsx: true } }, globals: { ...globals.browser, ...globals.node, ...globals.jest } },
  plugins: { '@typescript-eslint': typescript }, rules: { ...typescript.configs.recommended.rules },
}];
