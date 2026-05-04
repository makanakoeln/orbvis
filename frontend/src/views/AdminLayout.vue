<template>
    <div class="flex-1 flex flex-col overflow-hidden">
        <!-- Top nav bar — only visible when the sidebar is hidden (Checkmk deployment / SSO) -->
        <nav
            v-if="auth.ssoActive || auth.isCheckmkDeployment"
            class="shrink-0 bg-[var(--bg-surface)] border-b border-[var(--border)] flex items-center gap-[4px]"
            style="padding: 0 16px; height: 40px"
        >
            <router-link
                to="/"
                class="flex items-center gap-[6px] text-[13px] text-zinc-400 hover:text-[var(--text)] transition-colors border-r border-[var(--border)]"
                style="padding-right: 10px; margin-right: 8px"
            >
                <svg
                    style="width: 14px; height: 14px; flex-shrink: 0"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="1.5"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18"
                    />
                </svg>
                {{ t('nav.backToBoards') }}
            </router-link>
            <router-link
                v-for="item in adminNavItems"
                :key="item.to"
                :to="item.to"
                class="rounded text-[13px] transition-colors"
                style="padding: 4px 10px"
                :class="
                    isActive(item.to)
                        ? 'text-[var(--color-corporate-green-40)] bg-[var(--color-corporate-green-50)]/10 ring-1 ring-[var(--color-corporate-green-50)]/20'
                        : 'text-zinc-400 hover:text-[var(--text)] hover:bg-[var(--bg-hover)]'
                "
            >
                {{ item.label }}
            </router-link>
        </nav>
        <main class="flex-1 overflow-auto" style="padding: 20px 24px">
            <router-view />
        </main>
    </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';

import { useAuthStore } from '@/stores/auth';

const { t } = useI18n();
const auth = useAuthStore();
const route = useRoute();

const isCmk = auth.ssoActive || auth.isCheckmkDeployment;

const adminNavItems = [
    { to: '/admin/connections', label: t('admin.connections') },
    { to: '/admin/icons', label: t('admin.icons') },
    ...(!isCmk
        ? [
              { to: '/admin/users', label: t('admin.users') },
              { to: '/admin/roles', label: t('admin.rolesAndPermissions') },
          ]
        : []),
    { to: '/admin/settings', label: t('admin.settings') },
];

function isActive(path: string): boolean {
    return route.path === path || route.path.startsWith(path + '/');
}
</script>
