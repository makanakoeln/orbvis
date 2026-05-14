import {
    createRouter,
    createWebHashHistory,
    type NavigationGuardNext,
    type RouteLocationNormalized,
    type RouteLocationRaw,
} from 'vue-router';

import { useAuthStore } from '@/stores/auth';

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
            path: '/boards/:name',
            name: 'board',
            component: () => import('@/views/BoardView.vue'),
            meta: { requiresAuth: true },
        },
        {
            path: '/boards/:name/view',
            name: 'board-kiosk',
            component: () => import('@/views/BoardView.vue'),
            meta: { requiresAuth: true, kiosk: true },
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
                    path: 'connections',
                    name: 'admin-connections',
                    component: () => import('@/views/admin/ConnectionsView.vue'),
                },
                {
                    path: 'settings',
                    name: 'admin-settings',
                    component: () => import('@/views/admin/GlobalSettingsView.vue'),
                },
                {
                    path: 'formspec-pilot',
                    name: 'admin-formspec-pilot',
                    component: () => import('@/views/admin/FormSpecPilotView.vue'),
                },
                {
                    path: 'connections/:id/form',
                    name: 'admin-connection-form',
                    component: () => import('@/views/admin/ConnectionFormSpecView.vue'),
                },
                {
                    path: 'icons',
                    name: 'admin-icons',
                    component: () => import('@/views/admin/ImagesView.vue'),
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
});

export async function authGuard(
    to: RouteLocationNormalized,
): Promise<RouteLocationRaw | undefined> {
    const auth = useAuthStore();
    await auth.init();

    // In Checkmk mode the CMK theme can change at any time (ajax_ui_theme).
    // Re-fetch the user profile on every navigation so the theme stays in sync.
    // Use isCheckmkDeployment (URL-based) so this also runs when SSO temporarily
    // failed and the user logged in manually.
    if (auth.ssoActive || auth.isCheckmkDeployment) {
        auth.fetchCurrentUser();
    }

    if (to.meta.requiresAuth && !auth.isAuthenticated) {
        return { name: 'login', query: { redirect: to.fullPath } };
    }
    if (to.meta.requiresAdmin && !auth.isAdmin) {
        return { name: 'home' };
    }
    if (auth.isAuthenticated && auth.user?.must_change_password && to.name !== 'change-password') {
        return { name: 'change-password' };
    }
    if (to.name === 'login' && auth.isAuthenticated) {
        return { name: 'home' };
    }
    return undefined;
}

router.beforeEach(authGuard);

// Suppress "unused" warnings for types only consumed by the guard signature.
export type { NavigationGuardNext };

export default router;
