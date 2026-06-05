import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import { i18n } from './i18n'
import router from './router'
import './style.css'

// Checkmk-embedded deployments are served under /<site>/orbvis/. Mark the root
// so the stylesheet can adopt Checkmk's own status palette there (the standalone
// build keeps OrbVis-native colours). URL-derived → available before first paint.
if (/^\/[^/]+\/orbvis(\/|$)/.test(window.location.pathname)) {
  document.documentElement.classList.add('cmk-deployment')
}

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(i18n)

app.mount('#app')
