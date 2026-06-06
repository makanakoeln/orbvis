import { config } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createRouter, createWebHashHistory } from 'vue-router'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [{ path: '/', component: {} }]
})

config.global.plugins = [createPinia(), router]
config.global.stubs = {
  RouterLink: true,
  RouterView: true
}
