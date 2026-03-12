<template>
  <aside
    class="shrink-0 bg-[var(--bg-surface)] border-r border-[var(--border)] flex flex-col h-full overflow-hidden transition-all duration-200"
    :class="collapsed ? 'w-14' : 'w-56'"
  >

    <!-- Brand -->
    <div class="px-2 py-4 border-b border-[var(--border)] shrink-0 flex items-center" :class="collapsed ? 'justify-center' : 'justify-between px-4'">
      <router-link to="/" class="flex items-center gap-2.5 group min-w-0">
        <div class="w-7 h-7 rounded-lg bg-indigo-600/20 ring-1 ring-indigo-500/30 flex items-center justify-center shrink-0">
          <svg class="w-4 h-4 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 6.75V15m6-6v8.25m.503 3.498l4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 00-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c-.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0z" />
          </svg>
        </div>
        <span v-if="!collapsed" class="font-bold text-[var(--text)] tracking-tight group-hover:text-white transition-colors truncate">OrbVis</span>
      </router-link>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 overflow-y-auto p-2 space-y-0.5">

      <!-- Overview -->
      <NavItem to="/" :exact="true" :label="t('nav.overview')" :collapsed="collapsed">
        <template #icon>
          <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
        </template>
      </NavItem>

      <!-- Admin section -->
      <template v-if="auth.isAdmin">
        <p v-if="!collapsed" class="px-3 pt-5 pb-1 text-[10px] font-bold text-zinc-600 uppercase tracking-widest select-none">
          {{ t('nav.administration') }}
        </p>
        <div v-else class="my-3 border-t border-[var(--border)]" />

        <NavItem to="/admin/connections" :label="t('admin.connections')" :collapsed="collapsed">
          <template #icon>
            <path stroke-linecap="round" stroke-linejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 2.625c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125m16.5 5.625c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" />
          </template>
        </NavItem>

        <NavItem to="/admin/icons" :label="t('admin.icons')" :collapsed="collapsed">
          <template #icon>
            <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
          </template>
        </NavItem>

        <NavItem to="/admin/users" :label="t('admin.users')" :collapsed="collapsed">
          <template #icon>
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
          </template>
        </NavItem>

        <NavItem to="/admin/roles" :label="t('admin.rolesAndPermissions')" :collapsed="collapsed">
          <template #icon>
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
          </template>
        </NavItem>

        <NavItem to="/admin/settings" :label="t('admin.settings')" :collapsed="collapsed">
          <template #icon>
            <path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" />
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </template>
        </NavItem>
      </template>
    </nav>

    <!-- User section -->
    <div class="border-t border-[var(--border)] p-2 shrink-0">
      <!-- Toggle collapse — always at the same position -->
      <button @click="collapsed = !collapsed"
        class="w-full flex items-center rounded-lg text-sm text-zinc-600 hover:text-zinc-300 hover:bg-[var(--bg-hover)] transition-all duration-150 mb-1"
        :class="collapsed ? 'justify-center px-0 py-2' : 'gap-2.5 px-3 py-2'"
        :title="collapsed ? t('nav.expandSidebar') : t('nav.collapseSidebar')">
        <svg class="w-4 h-4 shrink-0 transition-transform duration-200" :class="collapsed ? 'rotate-180' : ''" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M11.25 9l-3 3m0 0l3 3m-3-3h7.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span v-if="!collapsed" class="text-xs">{{ t('nav.collapseSidebar') }}</span>
      </button>

      <!-- User info row -->
      <div class="flex items-center rounded-lg mb-1" :class="collapsed ? 'justify-center px-0 py-2' : 'gap-2.5 px-2 py-2'">
        <div
          class="w-7 h-7 rounded-full bg-indigo-600/20 ring-1 ring-indigo-500/30 flex items-center justify-center shrink-0 text-xs font-bold text-indigo-300 uppercase"
          :title="collapsed ? auth.user?.name : undefined"
        >
          {{ auth.user?.name?.[0] }}
        </div>
        <span v-if="!collapsed" class="text-sm text-[var(--text)] font-medium truncate flex-1">{{ auth.user?.name }}</span>
      </div>

      <!-- User settings -->
      <button @click="showSettings = true"
        class="w-full flex items-center rounded-lg text-sm text-zinc-400 hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-all duration-150"
        :class="collapsed ? 'justify-center px-0 py-2' : 'gap-2.5 px-3 py-2'"
        :title="collapsed ? t('nav.userSettings') : undefined">
        <svg class="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M17.982 18.725A7.488 7.488 0 0012 15.75a7.488 7.488 0 00-5.982 2.975m11.963 0a9 9 0 10-11.963 0m11.963 0A8.966 8.966 0 0112 21a8.966 8.966 0 01-5.982-2.275M15 9.75a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        <span v-if="!collapsed">{{ t('nav.userSettings') }}</span>
      </button>

      <!-- Logout -->
      <button v-if="!auth.ssoActive" @click="auth.logout()"
        class="w-full flex items-center rounded-lg text-sm text-zinc-400 hover:text-red-400 hover:bg-red-500/5 transition-all duration-150"
        :class="collapsed ? 'justify-center px-0 py-2' : 'gap-2.5 px-3 py-2'"
        :title="collapsed ? t('auth.logout') : undefined">
        <svg class="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9" />
        </svg>
        <span v-if="!collapsed">{{ t('auth.logout') }}</span>
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
  </aside>
</template>

<script setup lang="ts">
import { ref, watch, defineComponent, h } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useLink, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import UserSettingsPanel from '@/components/UserSettingsPanel.vue'

const { t } = useI18n()
const auth = useAuthStore()
const route = useRoute()
const showSettings = ref(false)

const LS_KEY = 'orbvis_sidebar_collapsed'
const collapsed = ref(localStorage.getItem(LS_KEY) === '1')

watch(collapsed, (val) => {
  localStorage.setItem(LS_KEY, val ? '1' : '0')
})

// NavItem: router-link wrapper with icon slot + active styling + collapsed mode
const NavItem = defineComponent({
  props: {
    to: { type: String, required: true },
    label: { type: String, required: true },
    exact: { type: Boolean, default: false },
    collapsed: { type: Boolean, default: false },
  },
  slots: Object as any,
  setup(props, { slots }) {
    const { isActive, isExactActive } = useLink({ to: props.to } as any)
    return () => {
      const active = props.exact ? isExactActive.value : isActive.value
      return h(RouterLink, {
        to: props.to,
        title: props.collapsed ? props.label : undefined,
        class: [
          'flex items-center rounded-lg text-sm transition-all duration-150',
          props.collapsed ? 'justify-center px-0 py-2' : 'gap-2.5 px-3 py-2',
          active
            ? 'text-indigo-300 bg-indigo-500/10 ring-1 ring-indigo-500/20'
            : 'text-zinc-400 hover:text-[var(--text)] hover:bg-[var(--bg-hover)]',
        ],
      }, () => [
        h('svg', { class: 'w-4 h-4 shrink-0', fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '1.5' },
          slots.icon?.()
        ),
        !props.collapsed ? h('span', { class: 'truncate' }, props.label) : null,
      ])
    }
  },
})
</script>
