<template>
  <div class="min-h-screen bg-[var(--bg)] flex">
    <!-- Sidebar -->
    <aside class="w-56 bg-[var(--bg-surface)] border-r border-[var(--border)] flex flex-col shrink-0">
      <div class="px-4 py-5 border-b border-[var(--border)]">
        <router-link to="/"
          class="flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-300 transition-colors duration-150 mb-4">
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
          </svg>
          {{ t('nav.backToMaps') }}
        </router-link>
        <p class="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">{{ t('nav.administration') }}</p>
      </div>
      <nav class="p-2.5 space-y-0.5 flex-1">
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="flex items-center px-3 py-2 rounded-lg text-sm text-zinc-400 hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-all duration-150"
          active-class="!text-indigo-300 !bg-indigo-500/10 ring-1 ring-indigo-500/20"
        >
          {{ item.label }}
        </router-link>
      </nav>
    </aside>

    <!-- Content -->
    <main class="flex-1 p-8 overflow-auto">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const navItems = computed(() => [
  { to: '/admin/users', label: t('admin.users') },
  { to: '/admin/roles', label: t('admin.rolesAndPermissions') },
  { to: '/admin/maps', label: t('admin.maps') },
  { to: '/admin/backends', label: t('admin.backends') },
])
</script>
