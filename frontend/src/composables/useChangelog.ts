import { ref } from 'vue';

const LS_KEY = 'orbvis_changelog_seen';

// Module-level ref — shared across all component instances
const visible = ref(false);

export function useChangelog() {
  function check() {
    visible.value = localStorage.getItem(LS_KEY) !== __APP_VERSION__;
  }

  function dismiss() {
    localStorage.setItem(LS_KEY, __APP_VERSION__);
    visible.value = false;
  }

  return { changelogVisible: visible, checkChangelog: check, dismissChangelog: dismiss };
}
