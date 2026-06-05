<!--
OrbVis stub for cmk-frontend-vue/src/form/private/FormAutocompleter/FormAutocompleter.vue.

The upstream component pulls in axios/ajax-backed suggestion loading
that isn't wired in OrbVis. The Pilot forms never set
``spec.autocompleter``, so the component only exists to satisfy
FormString.vue's static import — it never renders.

Wired up via ``CMK_STUBS`` in ``frontend/vite.config.ts``.
-->
<template>
  <span />
</template>
