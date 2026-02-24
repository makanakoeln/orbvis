import { config } from '@vue/test-utils'

// Global test setup
config.global.stubs = {
  RouterLink: true,
  RouterView: true,
}
