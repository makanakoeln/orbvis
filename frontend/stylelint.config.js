// OrbVis-only dev tooling: upstream cmk-frontend-vue lints with eslint +
// prettier + tsc and has no stylelint. Once OrbVis ships as a built-in
// Checkmk package this config must stay self-contained (no custom plugins,
// no rules their pipeline would have to adopt) or be droppable without
// touching the sources.
export default {
  extends: ['stylelint-config-standard', 'stylelint-config-html/vue'],
  ignoreFiles: ['src/vendor/**'],
  rules: {
    // Tailwind-Direktiven (@tailwind, @apply, @layer) sowie Tailwind v4 (@theme, @custom-variant, @reference)
    'at-rule-no-unknown': [
      true,
      {
        ignoreAtRules: [
          'tailwind',
          'apply',
          'layer',
          'variants',
          'responsive',
          'screen',
          'theme',
          'custom-variant',
          'reference',
          'source',
          'utility',
          'variant',
        ],
      },
    ],
    // Tailwind nutzt eigene Properties (--tw-ring-color etc.) und Modifier-Klassen (.hover\:...)
    'property-no-unknown': [true, { ignoreProperties: ['/^--tw-/', 'ring-color'] }],
    'selector-class-pattern': null,
    'selector-pseudo-class-no-unknown': [
      true,
      { ignorePseudoClasses: ['deep', 'global', 'slotted'] },
    ],
    // Keine hardcodierten Farbwerte in <style>-Blöcken (CSS vars nutzen)
    'declaration-property-value-disallowed-list': {
      color: ['/^#/', '/^rgb/', '/^hsl/'],
      'background-color': ['/^#/', '/^rgb/', '/^hsl/'],
      'border-color': ['/^#/', '/^rgb/', '/^hsl/'],
    },
    // Tailwind v4 uses bare @import "tailwindcss" (no url())
    'import-notation': 'string',
  },
  overrides: [
    {
      // style.css ist die Quelle der CSS-Vars und des @theme-Blocks — dort sind hex-Werte erlaubt
      files: ['src/style.css'],
      rules: {
        'declaration-property-value-disallowed-list': null,
        'color-hex-length': null,
      },
    },
    {
      files: ['**/*.vue'],
      customSyntax: 'postcss-html',
    },
  ],
}
