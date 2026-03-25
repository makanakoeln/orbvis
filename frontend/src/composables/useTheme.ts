import { watch } from 'vue';

import { useAuthStore } from '@/stores/auth';

export function applyTheme(theme: string, ssoActive: boolean, cmkTheme?: string | null) {
  let dark: boolean;
  if (theme === 'dark') {
    dark = true;
  } else if (theme === 'light') {
    dark = false;
  } else {
    // 'system': follow CMK theme (from ui_theme.mk via backend) or default to dark.
    dark = cmkTheme !== 'light';
  }

  const root = document.documentElement;
  if (dark) {
    root.classList.remove('light');
    root.classList.add('dark');
  } else {
    root.classList.remove('dark');
    root.classList.add('light');
  }
}

export function useTheme() {
  const auth = useAuthStore();

  // Watch both theme and ssoActive so we re-apply whenever either changes.
  // Skip the very first fire if auth hasn't resolved yet (user still null and
  // ssoActive still false) — the index.html dark class already covers that gap.
  watch(
    () => [auth.user?.theme, auth.user?.cmk_theme, auth.ssoActive] as const,
    ([theme]) => {
      if (auth.user === null && !auth.ssoActive) return;
      applyTheme(theme ?? 'system', auth.ssoActive, auth.user?.cmk_theme);
    },
    { immediate: true },
  );
}
