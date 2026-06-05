<template>
    <aside class="orb-sidebar" :class="{ 'orb-sidebar--collapsed': sidebarCollapsed }">
        <!-- Brand -->
        <div class="orb-sidebar__brand">
            <router-link v-if="!sidebarCollapsed" to="/" class="orb-sidebar__brand-link">
                <div class="orb-sidebar__logo">
                    <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M2 12C5 7 19 7 22 12C19 17 5 17 2 12Z"
                        />
                        <circle cx="12" cy="12" r="3.5" stroke-width="1" />
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="1.2"
                            d="M9.5 13.5L11 11L12.5 12.5L14 10"
                        />
                        <circle cx="14" cy="10" r="0.8" fill="currentColor" stroke="none" />
                    </svg>
                </div>
                <span class="orb-sidebar__brand-text">OrbVis</span>
            </router-link>
            <!-- Expand button when sidebarCollapsed -->
            <button
                v-if="sidebarCollapsed"
                class="orb-sidebar__logo orb-sidebar__expand"
                :title="t('nav.expandSidebar')"
                @click="sidebarCollapsed = false"
            >
                <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M8.25 4.5l7.5 7.5-7.5 7.5"
                    />
                </svg>
            </button>
            <!-- Collapse toggle — in header, far from logout -->
            <button
                v-if="!sidebarCollapsed"
                class="orb-sidebar__collapse"
                :title="t('nav.collapseSidebar')"
                @click="sidebarCollapsed = !sidebarCollapsed"
            >
                <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M15.75 19.5L8.25 12l7.5-7.5"
                    />
                </svg>
            </button>
        </div>

        <!-- Navigation -->
        <nav data-tour="sidebar-nav" class="orb-sidebar__nav">
            <!-- Overview -->
            <NavItem to="/" :exact="true" :label="t('nav.overview')" :collapsed="sidebarCollapsed">
                <template #icon>
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z"
                    />
                </template>
            </NavItem>

            <!-- Admin section -->
            <template v-if="auth.isAdmin || auth.canConfigure">
                <div class="orb-sidebar__divider" />
                <p v-if="!sidebarCollapsed" class="orb-sidebar__section-label">
                    {{ t('nav.administration') }}
                </p>

                <NavItem
                    v-if="auth.canConfigure"
                    to="/admin/connections"
                    :label="t('admin.connections')"
                    :collapsed="sidebarCollapsed"
                >
                    <template #icon>
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 2.625c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125m16.5 5.625c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125"
                        />
                    </template>
                </NavItem>

                <NavItem
                    v-if="auth.canConfigure"
                    to="/admin/icons"
                    :label="t('admin.icons')"
                    :collapsed="sidebarCollapsed"
                >
                    <template #icon>
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"
                        />
                    </template>
                </NavItem>

                <NavItem
                    v-if="auth.isAdmin"
                    to="/admin/users"
                    :label="t('admin.users')"
                    :collapsed="sidebarCollapsed"
                >
                    <template #icon>
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z"
                        />
                    </template>
                </NavItem>

                <NavItem
                    v-if="auth.isAdmin"
                    to="/admin/roles"
                    :label="t('admin.rolesAndPermissions')"
                    :collapsed="sidebarCollapsed"
                >
                    <template #icon>
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
                        />
                    </template>
                </NavItem>

                <NavItem
                    v-if="auth.canConfigure"
                    to="/admin/settings"
                    :label="t('admin.settings')"
                    :collapsed="sidebarCollapsed"
                >
                    <template #icon>
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z"
                        />
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                        />
                    </template>
                </NavItem>
            </template>
        </nav>

        <!-- User section -->
        <div class="orb-sidebar__user-section">
            <!-- User info + settings (combined clickable row) -->
            <button
                class="orb-sidebar__user"
                :title="sidebarCollapsed ? auth.user?.name : t('nav.userSettings')"
                @click="showSettings = true"
            >
                <div class="orb-sidebar__avatar">
                    {{ auth.user?.name?.[0] }}
                </div>
                <div v-if="!sidebarCollapsed" class="orb-sidebar__user-info">
                    <p class="orb-sidebar__user-name">
                        {{ auth.user?.name }}
                    </p>
                    <p class="orb-sidebar__user-hint">
                        {{ t('nav.userSettings') }}
                    </p>
                </div>
            </button>

            <!-- Logout -->
            <button
                v-if="!auth.ssoActive"
                class="orb-sidebar__logout"
                :title="sidebarCollapsed ? t('auth.logout') : undefined"
                @click="auth.logout()"
            >
                <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9"
                    />
                </svg>
                <span v-if="!sidebarCollapsed">{{ t('auth.logout') }}</span>
            </button>

            <!-- Version -->
            <button
                v-if="!sidebarCollapsed"
                class="orb-sidebar__version"
                @click="showChangelog = true"
            >
                v{{ appVersion }}
            </button>
        </div>

        <!-- User settings panel -->
        <UserSettingsPanel
            v-if="showSettings && auth.user"
            :user-id="auth.user.user_id"
            :user-name="auth.user.name"
            :is-self="true"
            @close="showSettings = false"
        />

        <ChangelogModal v-if="showChangelog" @close="showChangelog = false" />
    </aside>
</template>

<script setup lang="ts">
import { defineComponent, h, ref, type SlotsType, type VNode, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { RouterLink, useLink } from 'vue-router';

import ChangelogModal from '@/components/ChangelogModal.vue';
import UserSettingsPanel from '@/components/UserSettingsPanel.vue';
import { useAuthStore } from '@/stores/auth';

const { t } = useI18n();
const auth = useAuthStore();
const showSettings = ref(false);
const showChangelog = ref(false);
const appVersion = __APP_VERSION__;

const LS_KEY = 'orbvis_sidebar_collapsed';
const sidebarCollapsed = ref(localStorage.getItem(LS_KEY) === '1');

watch(sidebarCollapsed, (val) => {
    localStorage.setItem(LS_KEY, val ? '1' : '0');
});

// NavItem: router-link wrapper with icon slot + active styling + collapsed mode
const NavItem = defineComponent({
    props: {
        to: { type: String, required: true },
        label: { type: String, required: true },
        exact: { type: Boolean, default: false },
        collapsed: { type: Boolean, default: false },
    },
    slots: Object as SlotsType<{ icon?: () => VNode[] }>,
    setup(props, { slots }) {
        const { isActive, isExactActive } = useLink({ to: props.to });
        return () => {
            const active = props.exact ? isExactActive.value : isActive.value;
            // NavItem renders without the SFC scope id — its classes are
            // styled via :deep() in the scoped block below.
            return h(
                RouterLink,
                {
                    to: props.to,
                    title: props.collapsed ? props.label : undefined,
                    class: [
                        'orb-sidebar__nav-item',
                        props.collapsed ? 'orb-sidebar__nav-item--collapsed' : '',
                        active ? 'orb-sidebar__nav-item--active' : '',
                    ],
                },
                () => [
                    h(
                        'svg',
                        {
                            class: 'orb-sidebar__nav-icon',
                            fill: 'none',
                            viewBox: '0 0 24 24',
                            stroke: 'currentColor',
                            'stroke-width': '1.5',
                        },
                        slots.icon?.(),
                    ),
                    !props.collapsed
                        ? h('span', { class: 'orb-sidebar__nav-label' }, props.label)
                        : null,
                ],
            );
        };
    },
});
</script>

<style scoped>
.orb-sidebar {
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
    width: 220px;
    height: 100%;
    overflow: hidden;
    background: var(--default-nav-bg-color);
    border-right: 1px solid var(--default-nav-border-color);
    transition: all 0.2s;
}

.orb-sidebar--collapsed {
    width: 48px;
}

.orb-sidebar__brand {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-shrink: 0;
    padding: var(--dimension-4) 10px;
    border-bottom: 1px solid var(--default-nav-border-color);
}

.orb-sidebar--collapsed .orb-sidebar__brand {
    justify-content: center;
}

.orb-sidebar__brand-link {
    display: flex;
    align-items: center;
    gap: var(--dimension-4);
    min-width: 0;
}

.orb-sidebar__logo {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    width: 28px;
    height: 28px;
    color: var(--color-corporate-green-50);
    background: color-mix(in srgb, var(--color-corporate-green-50) 20%, transparent);
    border-radius: 8px;
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-corporate-green-50) 30%, transparent);
}

.orb-sidebar__logo svg {
    width: 20px;
    height: 20px;
}

.orb-sidebar__expand {
    cursor: pointer;
    transition: all 0.15s;
}

.orb-sidebar__expand:hover {
    background: color-mix(in srgb, var(--color-corporate-green-50) 30%, transparent);
}

.orb-sidebar__brand-text {
    overflow: hidden;
    font-weight: 700;
    color: var(--text);
    letter-spacing: -0.025em;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.orb-sidebar__collapse {
    flex-shrink: 0;
    padding: 6px;
    color: var(--text-muted);
    border-radius: 8px;
    transition: all 0.15s;
}

.orb-sidebar__collapse:hover {
    color: var(--text);
    background: var(--bg-hover);
}

.orb-sidebar__collapse svg {
    width: 20px;
    height: 20px;
}

.orb-sidebar__nav {
    flex: 1;
    padding: 6px;
    overflow-y: auto;
}

.orb-sidebar__nav > :deep(* + *) {
    margin-top: var(--dimension-2);
}

.orb-sidebar__divider {
    margin: 10px 6px 6px;
    border-top: 1px solid var(--default-nav-border-color);
}

.orb-sidebar__section-label {
    padding: 0 var(--dimension-4) var(--dimension-3);
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    user-select: none;
}

.orb-sidebar :deep(.orb-sidebar__nav-item) {
    display: flex;
    align-items: center;
    gap: var(--dimension-4);
    padding: 6px 10px;
    font-size: var(--font-size-large);
    line-height: 20px;
    color: var(--font-color-dimmed, #71717a);
    border-radius: 8px;
    transition: all 0.15s;
}

.orb-sidebar :deep(.orb-sidebar__nav-item:hover) {
    color: var(--font-color, #f4f4f5);
    background: var(--input-hover-bg-color, rgb(39 39 42 / 60%));
}

.orb-sidebar :deep(.orb-sidebar__nav-item--collapsed) {
    justify-content: center;
    padding-right: 0;
    padding-left: 0;
}

.orb-sidebar :deep(.orb-sidebar__nav-item--active),
.orb-sidebar :deep(.orb-sidebar__nav-item--active:hover) {
    color: var(--success);
    background: var(--ux-theme-1, #18181b);
    border-left: 2px solid var(--success);
    padding-left: calc(0.75rem - 2px);
}

.orb-sidebar :deep(.orb-sidebar__nav-item--active.orb-sidebar__nav-item--collapsed) {
    padding-left: 0;
}

.orb-sidebar :deep(.orb-sidebar__nav-icon) {
    flex-shrink: 0;
    width: 20px;
    height: 20px;
}

.orb-sidebar :deep(.orb-sidebar__nav-label) {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.orb-sidebar__user-section {
    flex-shrink: 0;
    padding: 6px;
    border-top: 1px solid var(--default-nav-border-color);
}

.orb-sidebar__user-section > * + * {
    margin-top: var(--dimension-2);
}

.orb-sidebar__user {
    display: flex;
    align-items: center;
    gap: var(--dimension-4);
    width: 100%;
    padding: 6px var(--dimension-4);
    border-radius: 8px;
    transition: all 0.15s;
}

.orb-sidebar__user:hover {
    background: var(--bg-hover);
}

.orb-sidebar--collapsed .orb-sidebar__user {
    justify-content: center;
    padding-right: 0;
    padding-left: 0;
}

.orb-sidebar__avatar {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    width: 24px;
    height: 24px;
    font-size: 11px;
    font-weight: 700;
    color: var(--color-corporate-green-40);
    text-transform: uppercase;
    background: color-mix(in srgb, var(--color-corporate-green-50) 20%, transparent);
    border-radius: 9999px;
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-corporate-green-50) 30%, transparent);
}

.orb-sidebar__user-info {
    flex: 1;
    min-width: 0;
    text-align: left;
}

.orb-sidebar__user-name {
    overflow: hidden;
    font-size: var(--font-size-large);
    font-weight: 500;
    line-height: 1.25;
    color: var(--text);
    text-overflow: ellipsis;
    white-space: nowrap;
}

.orb-sidebar__user-hint {
    font-size: var(--font-size-normal);
    line-height: 1.25;
    color: var(--text-muted);
}

.orb-sidebar__logout {
    display: flex;
    align-items: center;
    gap: var(--dimension-4);
    width: 100%;
    padding: 6px var(--dimension-4);
    font-size: var(--font-size-large);
    color: var(--text-muted);
    border-radius: 8px;
    transition: all 0.15s;
}

.orb-sidebar__logout:hover {
    color: var(--color-light-red-40);
    background: color-mix(in srgb, var(--color-light-red-50) 5%, transparent);
}

.orb-sidebar--collapsed .orb-sidebar__logout {
    justify-content: center;
    padding-right: 0;
    padding-left: 0;
}

.orb-sidebar__logout svg {
    flex-shrink: 0;
    width: 20px;
    height: 20px;
}

.orb-sidebar__version {
    width: 100%;
    padding: var(--dimension-2) var(--dimension-4);
    font-size: 10px;
    color: var(--text-muted);
    text-align: left;
}
</style>
