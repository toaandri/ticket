import parser from '@typescript-eslint/parser';
import typescript from '@typescript-eslint/eslint-plugin';
import hooks from 'eslint-plugin-react-hooks';
import globals from 'globals';
export default [{ ignores: ['dist/**', 'node_modules/**'] }, {
  files: ['src/**/*.{ts,tsx}'],
  languageOptions: { parser, parserOptions: { ecmaVersion: 'latest', sourceType: 'module', ecmaFeatures: { jsx: true } }, globals: { ...globals.browser, ...globals.node } },
  plugins: { '@typescript-eslint': typescript, 'react-hooks': hooks },
  rules: { ...typescript.configs.recommended.rules, 'react-hooks/rules-of-hooks': 'error', 'react-hooks/exhaustive-deps': 'warn' },
}];
