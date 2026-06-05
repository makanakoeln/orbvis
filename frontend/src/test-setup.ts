import { config } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createI18n } from 'vue-i18n'
import { createRouter, createWebHashHistory } from 'vue-router'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [{ path: '/', component: {} }]
})

config.global.plugins = [
  createPinia(),
  createI18n({ legacy: false, locale: 'en', messages: {} }),
  router
]
config.global.stubs = {
  RouterLink: true,
  RouterView: true
}
