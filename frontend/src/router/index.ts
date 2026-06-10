import {
  type RouteLocationNormalized,
  type RouteLocationRaw,
  createRouter,
  createWebHashHistory
} from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHashHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true }
    },
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/boards/:name',
      name: 'board',
      component: () => import('@/views/BoardView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/boards/:name/view',
      name: 'board-kiosk',
      component: () => import('@/views/BoardView.vue'),
      meta: { requiresAuth: true, kiosk: true }
    },
    {
      path: '/admin',
      component: () => import('@/views/AdminLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          redirect: () => {
            const auth = useAuthStore()
            return auth.isAdmin ? '/admin/users' : '/admin/connections'
          }
        },
        {
          path: 'users',
          name: 'admin-users',
          component: () => import('@/views/admin/UsersView.vue'),
          meta: { requiresAdmin: true }
        },
        {
          path: 'roles',
          name: 'admin-roles',
          component: () => import('@/views/admin/RolesView.vue'),
          meta: { requiresAdmin: true }
        },
        {
          path: 'connections',
          name: 'admin-connections',
          component: () => import('@/views/admin/ConnectionsView.vue'),
          meta: { requiresConfigure: true }
        },
        {
          path: 'settings',
          name: 'admin-settings',
          component: () => import('@/views/admin/GlobalSettingsView.vue'),
          meta: { requiresConfigure: true }
        },
        {
          path: 'system',
          name: 'admin-system',
          component: () => import('@/views/admin/SystemSettingsView.vue'),
          meta: { requiresConfigure: true }
        },
        {
          path: 'icons',
          name: 'admin-icons',
          component: () => import('@/views/admin/ImagesView.vue'),
          meta: { requiresConfigure: true }
        }
      ]
    },
    {
      path: '/change-password',
      name: 'change-password',
      component: () => import('@/views/ChangePasswordView.vue'),
      meta: { requiresAuth: true }
    }
  ]
})

export async function authGuard(
  to: RouteLocationNormalized
): Promise<RouteLocationRaw | undefined> {
  const auth = useAuthStore()
  await auth.init()

  // In Checkmk mode the CMK theme can change at any time (ajax_ui_theme).
  // Re-fetch the user profile on every navigation so the theme stays in sync.
  // Use isCheckmkDeployment (URL-based) so this also runs when SSO temporarily
  // failed and the user logged in manually.
  if (auth.ssoActive || auth.isCheckmkDeployment) {
    auth.fetchCurrentUser()
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresAdmin && !auth.isAdmin) {
    return { name: 'home' }
  }
  if (to.meta.requiresConfigure && !auth.canConfigure) {
    return { name: 'home' }
  }
  if (auth.isAuthenticated && auth.user?.must_change_password && to.name !== 'change-password') {
    return { name: 'change-password' }
  }
  if (to.name === 'login' && auth.isAuthenticated) {
    return { name: 'home' }
  }
  return undefined
}

router.beforeEach(authGuard)

export default router
