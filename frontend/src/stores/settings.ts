import { defineStore } from 'pinia';
import { ref } from 'vue';

import { settingsApi, systemSettingsApi } from '@/api/client';
import { useAuthStore } from '@/stores/auth';
import type { GlobalSettings, SystemSettings } from '@/types/api';

function token() {
    return useAuthStore().accessToken ?? '';
}

export const SETTINGS_DEFAULTS: GlobalSettings = {
    icon_size: 30,
    view_type: 'icon',
    label_show: true,
    label_size: 11,
    label_color: '#ffffff',
    label_background: 'transparent',
    label_x: 0,
    label_y: 0,
    url_target: '_blank',
    z: 1,
    line_style: null,
    default_backend_id: 'live_1',
    default_map_type: 'static',
    hover_template: null,
    context_template: null,
};

export const SYSTEM_DEFAULTS: SystemSettings = {
    log_level: null,
    checkmk_url: null,
};

export const useSettingsStore = defineStore('settings', () => {
    const settings = ref<GlobalSettings>({ ...SETTINGS_DEFAULTS });
    const system = ref<SystemSettings>({ ...SYSTEM_DEFAULTS });
    const loading = ref(false);

    async function load(): Promise<void> {
        if (!token()) return;
        loading.value = true;
        try {
            const [global, sys] = await Promise.all([
                settingsApi.get(token()),
                systemSettingsApi.get(token()),
            ]);
            settings.value = global;
            system.value = sys;
        } catch {
            // Fall back to built-in defaults
        } finally {
            loading.value = false;
        }
    }

    async function save(data: GlobalSettings): Promise<void> {
        settings.value = await settingsApi.update(data, token());
    }

    async function saveSystem(data: SystemSettings): Promise<void> {
        system.value = await systemSettingsApi.update(data, token());
    }

    return { settings, system, loading, load, save, saveSystem };
});
