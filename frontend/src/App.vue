<template>
  <div v-if="showShell" class="flex h-screen bg-[var(--bg)] overflow-hidden">
    <AppSidebar />
    <div class="flex-1 min-w-0 flex flex-col overflow-hidden">
      <router-view />
    </div>
  </div>
  <router-view v-else />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useTheme } from '@/composables/useTheme'
import { useAuthStore } from '@/stores/auth'
import AppSidebar from '@/components/AppSidebar.vue'

useTheme()
const route = useRoute()
const auth = useAuthStore()

const showShell = computed(() =>
  auth.user !== null && !['login', 'change-password'].includes(route.name as string)
)
</script>
