<template>
    <div v-if="showShell" class="flex h-screen bg-[var(--bg)] overflow-hidden">
        <AppSidebar v-if="!auth.ssoActive && !auth.isCheckmkDeployment" />
        <div class="flex-1 min-w-0 flex flex-col">
            <router-view />
        </div>
        <ChangelogModal v-if="showChangelog" @close="dismissChangelog" />
    </div>
    <div v-else class="flex flex-col h-screen w-screen overflow-hidden">
        <router-view />
    </div>
    <ToastContainer />
</template>

<script setup lang="ts">
import { computed, watch } from 'vue';
import { useRoute } from 'vue-router';

import AppSidebar from '@/components/AppSidebar.vue';
import ChangelogModal from '@/components/ChangelogModal.vue';
import ToastContainer from '@/components/ToastContainer.vue';
import { useChangelog } from '@/composables/useChangelog';
import { useTheme } from '@/composables/useTheme';
import { useAuthStore } from '@/stores/auth';
import { useCapabilitiesStore } from '@/stores/capabilities';

useTheme();
const route = useRoute();
const auth = useAuthStore();
// Fetch backend capability flags as early as possible so the Login screen
// and admin views see the correct form_specs flag on first paint. Errors
// fall back to the optimistic FormSpec-available default (see store).
useCapabilitiesStore().ensureLoaded();

const showShell = computed(
    () =>
        auth.user !== null &&
        !['login', 'change-password'].includes(route.name as string) &&
        !route.meta.kiosk &&
        route.query.preview !== '1',
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
