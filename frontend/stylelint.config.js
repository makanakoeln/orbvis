export default {
  extends: ['stylelint-config-standard', 'stylelint-config-html/vue'],
  rules: {
    // Tailwind-Direktiven (@tailwind, @apply, @layer) sind kein Standard-CSS
    'at-rule-no-unknown': [true, { ignoreAtRules: ['tailwind', 'apply', 'layer', 'variants', 'responsive', 'screen'] }],
    // Tailwind nutzt eigene Properties (--tw-ring-color etc.) und Modifier-Klassen (.hover\:...)
    'property-no-unknown': [true, { ignoreProperties: ['/^--tw-/', 'ring-color'] }],
    'selector-class-pattern': null,
    // Keine hardcodierten Farbwerte in <style>-Blöcken (CSS vars nutzen)
    'declaration-property-value-disallowed-list': {
      color: ['/^#/', '/^rgb/', '/^hsl/'],
      'background-color': ['/^#/', '/^rgb/', '/^hsl/'],
      'border-color': ['/^#/', '/^rgb/', '/^hsl/'],
    },
  },
  overrides: [
    {
      // style.css ist die Quelle der CSS-Vars — dort sind hex-Werte erlaubt
      files: ['src/style.css'],
      rules: { 'declaration-property-value-disallowed-list': null },
    },
    {
      files: ['**/*.vue'],
      customSyntax: 'postcss-html',
    },
  ],
}
