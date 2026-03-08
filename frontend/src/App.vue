<template>
  <router-view />
</template>

<script setup lang="ts">
import { useTheme } from '@/composables/useTheme'
useTheme()
</script>
