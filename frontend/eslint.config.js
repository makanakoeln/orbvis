import js from '@eslint/js'
import prettier from 'eslint-config-prettier'
import security from 'eslint-plugin-security'
import pluginVue from 'eslint-plugin-vue'
import globals from 'globals'
import ts from 'typescript-eslint'

export default [
  js.configs.recommended,
  security.configs.recommended,

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

  // Playwright E2E-Tests laufen in Node + nutzen Browser-Globals via Playwright API
  {
    files: ['e2e/**/*.ts', 'playwright.config.ts'],
    languageOptions: {
      globals: { ...globals.node },
    },
  },

  {
    // Disable security rules with prohibitively high false-positive rates in TypeScript:
    // detect-object-injection fires on every obj[key] bracket access (extremely common in TS).
    // detect-non-literal-fs-filename fires on build scripts with computed paths (expected).
    // detect-unsafe-regex triggers on safe regex patterns (no actual catastrophic backtracking).
    rules: {
      'security/detect-object-injection': 'off',
      'security/detect-non-literal-fs-filename': 'off',
      'security/detect-unsafe-regex': 'off',
    },
  },

  {
    rules: {
      'vue/multi-word-component-names': 'off',
      'vue/no-unused-vars': 'warn',
      'vue/no-mutating-props': 'off', // EditPanel nutzt intentionale Prop-Mutation — Refactor ausstehend
      'vue/no-v-html': 'off', // v-html wird für vertrauenswürdige Inhalte (Textbox, Templates) genutzt
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
