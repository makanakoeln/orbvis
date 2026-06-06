export default {
  input: {
    path: './',
    include: ['src/**/*.js', 'src/**/*.ts', 'src/**/*.vue'],
    // cmk-additions hosts files vendored INTO this package from
    // cmk-frontend-vue; their strings are translated upstream.
    exclude: ['src/cmk-additions/**/*'],
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
