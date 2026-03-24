import js from '@eslint/js'
import prettier from 'eslint-config-prettier'
import simpleImportSort from 'eslint-plugin-simple-import-sort'
import pluginVue from 'eslint-plugin-vue'
import globals from 'globals'
import ts from 'typescript-eslint'

export default [
  js.configs.recommended,

  // TypeScript-Unterstützung (Plugin + Basis-Regeln für alle Dateien)
  ...ts.configs.recommended,

  // Vue: vue-eslint-parser als Haupt-Parser, TypeScript-Parser für <script>
  ...pluginVue.configs['flat/recommended'],
  {
    files: ['**/*.vue', '**/*.ts', '**/*.tsx'],
    languageOptions: {
      globals: {
        ...globals.browser,
        __APP_VERSION__: 'readonly', // Vite define-Variable
      },
    },
  },
  {
    files: ['**/*.vue'],
    languageOptions: {
      parserOptions: {
        parser: ts.parser,
        sourceType: 'module',
      },
    },
  },

  // Node.js-Skripte dürfen console/process nutzen
  {
    files: ['scripts/**/*.js'],
    languageOptions: { globals: globals.node },
  },

  {
    plugins: { 'simple-import-sort': simpleImportSort },
    rules: {
      'simple-import-sort/imports': 'warn',
      'simple-import-sort/exports': 'warn',
      'vue/multi-word-component-names': 'off',
      'vue/no-unused-vars': 'warn',
      'vue/no-mutating-props': 'warn', // wird schrittweise refactored
      'no-empty': ['error', { allowEmptyCatch: true }],
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/no-unused-vars': [
        'warn',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
    },
  },

  prettier,
  { ignores: ['dist/**', 'node_modules/**', 'src/vite-env.d.ts'] },
]
