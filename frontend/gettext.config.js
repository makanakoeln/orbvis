export default {
  input: {
    path: './',
    include: ['src/**/*.js', 'src/**/*.ts', 'src/**/*.vue'],
    exclude: ['src/vendor/**/*', 'src/cmk/**/*'],
    parserOptions: {
      mapping: {
        simple: ['_t'],
        plural: ['_tn'],
        ctx: ['_tp'],
        ctxPlural: ['_tnp']
      }
    }
  },
  output: {
    path: './locale',
    potPath: './messages.pot',
    jsonPath: '../src/assets/locale/',
    locales: ['de'],
    splitJson: true,
    flat: true,
    linguas: false
  }
}
