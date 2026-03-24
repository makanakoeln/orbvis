<template>
  <div v-if="showShell" class="flex h-screen bg-[var(--bg)] overflow-hidden">
    <AppSidebar v-if="!auth.ssoActive && !auth.isCheckmkDeployment" />
    <div class="flex-1 min-w-0 flex flex-col overflow-hidden">
      <router-view />
    </div>
    <ChangelogModal v-if="showChangelog" @close="dismissChangelog" />
  </div>
  <router-view v-else />
</template>

<script setup lang="ts">
import { computed, watch, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useTheme } from '@/composables/useTheme'
import { useAuthStore } from '@/stores/auth'
import AppSidebar from '@/components/AppSidebar.vue'
import ChangelogModal from '@/components/ChangelogModal.vue'

useTheme()
const route = useRoute()
const auth = useAuthStore()

const showShell = computed(() =>
  auth.user !== null && !['login', 'change-password'].includes(route.name as string)
)

const LS_KEY = 'orbvis_changelog_seen'
const showChangelog = ref(false)

watch(showShell, (val) => {
  if (val && localStorage.getItem(LS_KEY) !== __APP_VERSION__) {
    showChangelog.value = true
  }
}, { immediate: true })

function dismissChangelog() {
  localStorage.setItem(LS_KEY, __APP_VERSION__)
  showChangelog.value = false
}
</script>
