<template>
    <div class="orb-admin">
        <!-- Top header — only visible when sidebar is hidden (Checkmk deployment / SSO) -->
        <template v-if="isCmk">
            <div class="orb-admin__header">
                <CmkBreadcrumb :items="breadcrumbItems" />
            </div>
            <nav class="cmk-tab-bar">
                <router-link
                    v-for="item in adminNavItems"
                    :key="item.to"
                    :to="item.to"
                    class="cmk-tab"
                    :class="{ 'cmk-tab--active': isActive(item.to) }"
                >
                    {{ item.label }}
                </router-link>
            </nav>
        </template>
        <main class="orb-admin__main">
            <router-view />
        </main>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';

import type { BreadcrumbItem } from '@/components/cmk/CmkBreadcrumb.vue';
import CmkBreadcrumb from '@/components/cmk/CmkBreadcrumb.vue';
import { useAuthStore } from '@/stores/auth';

const { t } = useI18n();
const auth = useAuthStore();
const route = useRoute();

const isCmk = computed(() => auth.ssoActive || auth.isCheckmkDeployment);

const adminNavItems = computed(() => [
    { to: '/admin/connections', label: t('admin.connections') },
    { to: '/admin/icons', label: t('admin.icons') },
    ...(!isCmk.value
        ? [
              { to: '/admin/users', label: t('admin.users') },
              { to: '/admin/roles', label: t('admin.rolesAndPermissions') },
          ]
        : []),
    { to: '/admin/settings', label: t('admin.settings') },
    { to: '/admin/system', label: t('admin.system') },
]);

function isActive(path: string): boolean {
    return route.path === path || route.path.startsWith(path + '/');
}

const breadcrumbItems = computed<BreadcrumbItem[]>(() => {
    const current = adminNavItems.value.find((item) => isActive(item.to));
    const items: BreadcrumbItem[] = [
        { title: t('home.title'), to: '/' },
        { title: t('nav.administration') },
    ];
    if (current) items.push({ title: current.label });
    return items;
});
</script>

<style scoped>
.orb-admin {
    display: flex;
    flex: 1;
    flex-direction: column;
    overflow: hidden;
}

.orb-admin__header {
    display: flex;
    flex-shrink: 0;
    align-items: center;
    height: 32px;
    padding: 0 var(--dimension-6);
    background: var(--bg-surface);
    border-bottom: 1px solid var(--border);
}

.orb-admin__main {
    flex: 1;
    padding: var(--dimension-7) var(--dimension-8);
    overflow: auto;
}

.cmk-tab-bar {
    display: flex;
    flex-shrink: 0;
    align-items: center;
    height: 32px;
    padding: 0 var(--dimension-6);
    background-color: var(--ux-theme-4);
    border-bottom: 1px solid var(--border);
}

.cmk-tab {
    display: inline-flex;
    align-items: center;
    height: 100%;
    padding: 0 10px;
    font-size: 13px;
    color: var(--font-color-breadcrumb-interactive);
    text-decoration: none;
    border-bottom: 2px solid transparent;
    transition:
        color 120ms,
        border-color 120ms;
}

.cmk-tab:hover {
    border-bottom-color: var(--color-corporate-green-50);
    color: var(--text);
}

.cmk-tab--active {
    border-bottom-color: var(--color-corporate-green-50);
    color: var(--text);
    font-weight: 500;
}
</style>
