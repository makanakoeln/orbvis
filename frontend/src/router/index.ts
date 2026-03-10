import { createRouter, createWebHashHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHashHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/maps/:name',
      name: 'map',
      component: () => import('@/views/MapView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/admin',
      component: () => import('@/views/AdminLayout.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
      children: [
        {
          path: '',
          redirect: '/admin/users',
        },
        {
          path: 'users',
          name: 'admin-users',
          component: () => import('@/views/admin/UsersView.vue'),
        },
        {
          path: 'roles',
          name: 'admin-roles',
          component: () => import('@/views/admin/RolesView.vue'),
        },
        {
          path: 'maps',
          name: 'admin-maps',
          component: () => import('@/views/admin/MapsAdminView.vue'),
        },
        {
          path: 'backends',
          name: 'admin-backends',
          component: () => import('@/views/admin/BackendsView.vue'),
        },
        {
          path: 'settings',
          name: 'admin-settings',
          component: () => import('@/views/admin/GlobalSettingsView.vue'),
        },
        {
          path: 'icons',
          name: 'admin-icons',
          component: () => import('@/views/admin/IconsView.vue'),
        },
      ],
    },
    {
      path: '/change-password',
      name: 'change-password',
      component: () => import('@/views/ChangePasswordView.vue'),
      meta: { requiresAuth: true },
    },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.init()

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresAdmin && !auth.isAdmin) {
    return { name: 'home' }
  }
  if (auth.isAuthenticated && auth.user?.must_change_password && to.name !== 'change-password') {
    return { name: 'change-password' }
  }
  if (to.name === 'login' && auth.isAuthenticated) {
    return { name: 'home' }
  }
})

export default router
