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
import { computed, watch } from 'vue';
import { useRoute } from 'vue-router';

import AppSidebar from '@/components/AppSidebar.vue';
import ChangelogModal from '@/components/ChangelogModal.vue';
import { useChangelog } from '@/composables/useChangelog';
import { useTheme } from '@/composables/useTheme';
import { useAuthStore } from '@/stores/auth';

useTheme();
const route = useRoute();
const auth = useAuthStore();

const showShell = computed(
  () => auth.user !== null && !['login', 'change-password'].includes(route.name as string),
);

const { changelogVisible: showChangelog, checkChangelog, dismissChangelog } = useChangelog();

watch(
  showShell,
  (val) => {
    if (val) checkChangelog();
  },
  { immediate: true },
);
</script>
