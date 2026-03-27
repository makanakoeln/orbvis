<template>
  <div class="fixed inset-0 z-50" :class="isPopover ? '' : 'flex items-center justify-center'">
    <!-- Backdrop: dark in modal mode, transparent dismiss layer in popover mode -->
    <div
      class="absolute inset-0 transition-all"
      :class="isPopover ? '' : 'bg-black/60 backdrop-blur-sm'"
      @click="$emit('close')"
    />
    <!-- Card: centered in modal mode, positioned at click in popover mode -->
    <Transition
      appear
      enter-from-class="opacity-0 scale-95 -translate-y-1"
      enter-active-class="transition-all duration-150 ease-out"
    >
      <div
        class="bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/60 rounded-2xl flex flex-col overflow-hidden"
        :class="isPopover ? 'absolute w-[25rem] max-h-[75vh]' : 'relative w-[36rem] max-h-[90vh]'"
        :style="isPopover ? popoverStyle : {}"
      >
        <!-- Header -->
        <div
          class="flex items-center justify-between px-6 py-4 border-b border-[var(--border)] shrink-0"
        >
          <div class="flex items-center gap-3">
            <span
              class="text-xs font-bold px-2 py-1 rounded-lg bg-[var(--bg-input)] ring-1 ring-zinc-700 text-zinc-400 capitalize"
            >
              {{ object.type }}
            </span>
            <span class="font-bold text-[var(--text)]">{{ displayName }}</span>
          </div>
          <button
            class="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-[var(--bg-hover)] transition-all"
            @click="$emit('close')"
          >
            <svg
              class="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Scrollable body -->
        <div class="overflow-y-auto overflow-x-hidden flex-1 px-6 py-5 space-y-6">
          <!-- === MONITORING OBJECT === -->
          <section
            v-if="object.type !== 'textbox' && object.type !== 'line' && object.type !== 'graph'"
          >
            <p class="section-title">{{ t('boardSettings.monitoringObject') }}</p>
            <div class="space-y-3">
              <template v-if="object.type === 'host' || object.type === 'service'">
                <div class="field-row">
                  <label class="field-label">{{ t('boardSettings.hostname') }}</label>
                  <AutocompleteInput
                    v-model="form.host_name"
                    :suggestions="hosts"
                    :loading="loadingHosts"
                    placeholder="hostname"
                    class="flex-1"
                  />
                </div>
              </template>
              <template v-if="object.type === 'service'">
                <div class="field-row">
                  <label class="field-label">{{ t('boardSettings.typeService') }}</label>
                  <AutocompleteInput
                    v-model="form.service_description"
                    :suggestions="services"
                    :loading="loadingServices"
                    placeholder="service description"
                    class="flex-1"
                  />
                </div>
              </template>
              <template v-if="object.type === 'host' || object.type === 'service'">
                <label
                  class="flex items-center gap-2.5 text-sm text-zinc-400 cursor-pointer select-none"
                >
                  <input
                    v-model="form.only_hard_states"
                    type="checkbox"
                    class="rounded accent-indigo-500 w-4 h-4"
                  />
                  {{ t('boardSettings.onlyHardStates') }}
                </label>
              </template>
              <template v-if="object.type === 'host'">
                <label
                  class="flex items-center gap-2.5 text-sm text-zinc-400 cursor-pointer select-none"
                >
                  <input
                    v-model="form.recognize_services"
                    type="checkbox"
                    class="rounded accent-indigo-500 w-4 h-4"
                  />
                  {{ t('boardSettings.recognizeServices') }}
                </label>
              </template>
              <template v-if="object.type === 'hostgroup' || object.type === 'servicegroup'">
                <div class="field-row">
                  <label class="field-label">{{ t('boardSettings.groupName') }}</label>
                  <AutocompleteInput
                    v-model="form.group_name"
                    :suggestions="groups"
                    :loading="loadingGroups"
                    placeholder="group name"
                    class="flex-1"
                  />
                </div>
              </template>
              <template v-if="object.type === 'map'">
                <div class="field-row">
                  <label class="field-label">{{ t('boardSettings.targetMap') }}</label>
                  <AutocompleteInput
                    v-model="form.map_name"
                    :suggestions="boardNames"
                    placeholder="map-name"
                    class="flex-1"
                  />
                </div>
              </template>
            </div>
          </section>

          <!-- === TEXTBOX CONTENT + STYLING === -->
          <section v-if="object.type === 'textbox'">
            <p class="section-title">{{ t('boardSettings.content') }}</p>
            <textarea
              v-model="form.label.text"
              rows="3"
              class="w-full px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all resize-none mb-3"
              :placeholder="t('boardSettings.textContent') + '…'"
            />
            <div class="space-y-3">
              <div class="grid grid-cols-2 gap-3">
                <div class="field-row">
                  <label class="field-label">{{ t('boardSettings.width') }}</label>
                  <NumberInput
                    v-model="form.textbox_width"
                    :placeholder="t('boardSettings.auto')"
                    class="flex-1"
                  />
                </div>
                <div class="field-row">
                  <label class="field-label">{{ t('boardSettings.height') }}</label>
                  <NumberInput
                    v-model="form.textbox_height"
                    :placeholder="t('boardSettings.auto')"
                    class="flex-1"
                  />
                </div>
              </div>
              <div class="field-row">
                <label class="field-label">{{ t('boardSettings.background') }}</label>
                <ColorInput
                  v-model="form.textbox_background"
                  none-label="transparent"
                  default-color="#1a1a2e"
                />
              </div>
              <div class="field-row">
                <label class="field-label">{{ t('boardSettings.borderColor') }}</label>
                <ColorInput
                  v-model="form.textbox_border"
                  none-label="default"
                  default-color="#e5e5e5"
                />
              </div>
            </div>
          </section>

          <!-- === GRAPH: Metric Source === -->
          <section v-if="object.type === 'graph'">
            <div class="flex items-center gap-2 mb-3">
              <p class="section-title !mb-0">{{ t('boardSettings.graphMetricSource') }}</p>
              <span
                class="text-[10px] font-medium px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-400 border border-amber-500/25 shrink-0"
                >experimental</span
              >
            </div>
            <div class="space-y-3">
              <div class="field-row">
                <label class="field-label">{{ t('boardSettings.hostname') }}</label>
                <AutocompleteInput
                  v-model="form.host_name"
                  :suggestions="hosts"
                  :loading="loadingHosts"
                  placeholder="hostname"
                  class="flex-1"
                />
              </div>
              <div class="field-row">
                <label class="field-label">{{ t('boardSettings.typeService') }}</label>
                <AutocompleteInput
                  v-model="form.service_description"
                  :suggestions="services"
                  :loading="loadingServices"
                  placeholder="service description"
                  class="flex-1"
                />
              </div>
              <div class="field-row">
                <label class="field-label">{{ t('boardSettings.graphSource') }}</label>
                <div class="flex gap-1 flex-1">
                  <button
                    v-for="mode in ['auto', 'metrics', 'template'] as const"
                    :key="mode"
                    class="px-2 py-1 rounded text-xs transition-all"
                    :class="
                      graphSource === mode
                        ? 'bg-indigo-600 text-white'
                        : 'bg-[var(--bg-input)] text-zinc-400 hover:text-zinc-200'
                    "
                    @click="setGraphSource(mode)"
                  >
                    {{ t(`boardSettings.graphSource_${mode}`) }}
                  </button>
                </div>
              </div>
              <div v-if="graphSource === 'metrics'" class="field-row items-start">
                <label class="field-label mt-1.5">{{ t('boardSettings.graphMetric') }}</label>
                <div class="flex-1 space-y-1.5">
                  <div v-if="form.graph_metric.length" class="flex flex-wrap gap-1">
                    <span
                      v-for="m in form.graph_metric"
                      :key="m"
                      class="flex items-center gap-1 px-2 py-0.5 rounded bg-[var(--bg-input)] text-xs text-zinc-300 ring-1 ring-zinc-700"
                    >
                      {{ metricIdToTitle[m] ?? m }}
                      <button
                        class="text-zinc-500 hover:text-red-400"
                        @click="form.graph_metric = form.graph_metric.filter((x) => x !== m)"
                      >
                        ×
                      </button>
                    </span>
                  </div>
                  <div ref="metricAddEl">
                    <AutocompleteInput
                      v-model="metricInput"
                      :suggestions="
                        metricSuggestions.filter(
                          (title) =>
                            !form.graph_metric.includes(metricTitleToId.get(title) ?? title),
                        )
                      "
                      :placeholder="t('boardSettings.graphMetricAdd')"
                      class="w-full"
                      @change="addMetric"
                    />
                  </div>
                </div>
              </div>
              <div v-if="graphSource === 'template' && graphTemplates.length" class="field-row">
                <label class="field-label">{{ t('boardSettings.graphTemplate') }}</label>
                <select v-model="form.graph_id" class="field flex-1">
                  <option :value="null">—</option>
                  <option v-for="tpl in graphTemplates" :key="tpl.id" :value="tpl.id">
                    {{ tpl.title }}
                  </option>
                </select>
              </div>
              <div class="field-row">
                <label class="field-label">{{ t('boardSettings.graphTimeWindow') }}</label>
                <select v-model="form.graph_time_window" class="field flex-1">
                  <option :value="60">1 h</option>
                  <option :value="240">4 h</option>
                  <option :value="720">12 h</option>
                  <option :value="1440">24 h</option>
                  <option :value="10080">7 d</option>
                </select>
              </div>
            </div>
          </section>

          <!-- === GRAPH: URL Embed === -->
          <section v-if="object.type === 'graph'">
            <p class="section-title">{{ t('boardSettings.graphUrlEmbed') }}</p>
            <div class="space-y-3">
              <div class="field-row">
                <label class="field-label">{{ t('boardSettings.graphUrl') }}</label>
                <input
                  v-model="form.graph_url"
                  class="field flex-1 font-mono"
                  placeholder="https://… (optional)"
                />
              </div>
              <div class="field-row">
                <label class="field-label">{{ t('boardSettings.graphEmbedType') }}</label>
                <select v-model="form.graph_embed_type" class="field flex-1">
                  <option value="img">{{ t('boardSettings.graphEmbedImg') }}</option>
                  <option value="iframe">{{ t('boardSettings.graphEmbedIframe') }}</option>
                </select>
              </div>
              <div class="grid grid-cols-2 gap-3">
                <div class="field-row">
                  <label class="field-label">{{ t('boardSettings.width') }}</label>
                  <NumberInput v-model="form.graph_width" min="50" class="flex-1" />
                </div>
                <div class="field-row">
                  <label class="field-label">{{ t('boardSettings.height') }}</label>
                  <NumberInput v-model="form.graph_height" min="30" class="flex-1" />
                </div>
              </div>
              <div class="field-row">
                <label class="field-label">{{ t('boardSettings.graphRefresh') }}</label>
                <div class="flex items-center gap-2 flex-1">
                  <NumberInput v-model="form.graph_refresh_interval" min="0" class="flex-1" />
                  <span class="text-xs text-zinc-500 shrink-0">{{
                    t('boardSettings.graphRefreshOff')
                  }}</span>
                </div>
              </div>
            </div>
          </section>

          <!-- === LINE CONFIG === -->
          <section v-if="object.type === 'line'">
            <p class="section-title">{{ t('boardSettings.monitoringObject') }}</p>
            <div class="space-y-3">
              <div class="field-row">
                <label class="field-label">{{ t('boardSettings.hostname') }}</label>
                <AutocompleteInput
                  v-model="form.host_name"
                  :suggestions="hosts"
                  :loading="loadingHosts"
                  placeholder="hostname"
                  class="flex-1"
                />
              </div>
              <div class="field-row">
                <label class="field-label">{{ t('boardSettings.typeService') }}</label>
                <AutocompleteInput
                  v-model="form.service_description"
                  :suggestions="services"
                  :loading="loadingServices"
                  placeholder="service description (optional)"
                  class="flex-1"
                />
              </div>
            </div>
          </section>
          <section v-if="object.type === 'line'">
            <p class="section-title">{{ t('boardSettings.lineSection') }}</p>
            <div class="space-y-3">
              <div class="field-row">
                <label class="field-label">{{ t('boardSettings.lineStyle') }}</label>
                <select v-model="form.line_style" class="field flex-1">
                  <option :value="null">{{ t('boardSettings.lineDefault') }}</option>
                  <option value="plain">{{ t('boardSettings.lineSimple') }}</option>
                  <option value="arrow_end">{{ t('boardSettings.lineArrowRight') }}</option>
                  <option value="arrow_start">{{ t('boardSettings.lineArrowLeft') }}</option>
                  <option value="arrow_both">{{ t('boardSettings.lineDoubleArrow') }}</option>
                  <option value="dashed">{{ t('boardSettings.lineDashed') }}</option>
                  <option value="weathermap">{{ t('boardSettings.lineWeathermap') }}</option>
                </select>
              </div>
              <!-- Weathermap metric -->
              <div v-if="form.line_style === 'weathermap'" class="field-row">
                <label class="field-label">{{ t('boardSettings.metric') }}</label>
                <AutocompleteInput
                  v-model="form.weathermap_metric"
                  :suggestions="metricSuggestions"
                  :placeholder="t('boardSettings.firstMetric')"
                  class="flex-1"
                />
              </div>
              <div class="grid grid-cols-2 gap-3">
                <div class="field-row col-span-2">
                  <label class="field-label">{{ t('boardSettings.lineColor') }}</label>
                  <ColorInput
                    v-model="form.line_color"
                    :none-label="t('boardSettings.lineColorAuto')"
                    default-color="#ffffff"
                  />
                </div>
                <div class="field-row col-span-2">
                  <label class="field-label">{{ t('boardSettings.lineColorBorder') }}</label>
                  <ColorInput
                    v-model="form.line_color_border"
                    none-label="none"
                    default-color="#000000"
                  />
                </div>
                <div class="field-row">
                  <label class="field-label">{{ t('boardSettings.startX') }}</label>
                  <NumberInput v-model="form.x" class="flex-1" />
                </div>
                <div class="field-row">
                  <label class="field-label">{{ t('boardSettings.y') }}</label>
                  <NumberInput v-model="form.y" class="flex-1" />
                </div>
                <div class="field-row">
                  <label class="field-label">{{ t('boardSettings.endX') }}</label>
                  <NumberInput v-model="form.x2" class="flex-1" />
                </div>
                <div class="field-row">
                  <label class="field-label">{{ t('boardSettings.y') }}</label>
                  <NumberInput v-model="form.y2" class="flex-1" />
                </div>
              </div>
              <!-- Label -->
              <div class="field-row">
                <label class="field-label">{{ t('boardSettings.showLabel') }}</label>
                <input v-model="form.label.show" type="checkbox" class="accent-indigo-500" />
              </div>
              <div v-if="form.label.show" class="field-row">
                <label class="field-label">{{ t('boardSettings.labelText') }}</label>
                <input
                  v-model="form.label.text"
                  class="field flex-1"
                  :placeholder="t('boardSettings.labelOnLine')"
                />
              </div>
            </div>
          </section>

          <!-- === POSITION === -->
          <section v-if="object.type !== 'line'">
            <p class="section-title">{{ t('boardSettings.position') }}</p>
            <div class="grid grid-cols-3 gap-3">
              <template v-if="mapType === 'worldmap'">
                <div class="flex items-center gap-2">
                  <label class="text-xs text-zinc-500 shrink-0">{{ t('boardSettings.lat') }}</label>
                  <NumberInput v-model="form.lat" step="any" class="flex-1" />
                </div>
                <div class="flex items-center gap-2">
                  <label class="text-xs text-zinc-500 shrink-0">{{ t('boardSettings.lng') }}</label>
                  <NumberInput v-model="form.lng" step="any" class="flex-1" />
                </div>
              </template>
              <template v-else>
                <div class="flex items-center gap-2">
                  <label class="text-xs text-zinc-500 shrink-0">{{ t('boardSettings.x') }}</label>
                  <NumberInput v-model="form.x" class="flex-1" />
                </div>
                <div class="flex items-center gap-2">
                  <label class="text-xs text-zinc-500 shrink-0">{{ t('boardSettings.y') }}</label>
                  <NumberInput v-model="form.y" class="flex-1" />
                </div>
              </template>
              <div class="flex items-center gap-2">
                <label class="text-xs text-zinc-500 shrink-0">{{ t('boardSettings.z') }}</label>
                <NumberInput v-model="form.z" min="1" max="999" class="flex-1" />
              </div>
            </div>
          </section>

          <!-- === LABEL === -->
          <section v-if="object.type !== 'line'">
            <p class="section-title">{{ t('boardSettings.label') }}</p>
            <div class="space-y-3">
              <label
                class="flex items-center gap-2.5 text-sm text-zinc-400 cursor-pointer select-none"
              >
                <input
                  v-model="form.label.show"
                  type="checkbox"
                  class="rounded accent-indigo-500 w-4 h-4"
                />
                {{ t('boardSettings.showLabel') }}
              </label>
              <div :class="!form.label.show ? 'opacity-40 pointer-events-none' : ''">
                <div class="space-y-3">
                  <div v-if="object.type !== 'textbox'" class="field-row">
                    <label class="field-label">{{ t('boardSettings.labelText') }}</label>
                    <input
                      v-model="form.label.text"
                      class="field flex-1"
                      placeholder="(auto from object)"
                    />
                  </div>
                  <div class="grid grid-cols-2 gap-3">
                    <div class="field-row">
                      <label class="field-label">{{ t('boardSettings.size') }}</label>
                      <NumberInput v-model="form.label.size" min="8" max="72" class="flex-1" />
                    </div>
                    <div class="field-row">
                      <label class="field-label">{{ t('boardSettings.color') }}</label>
                      <div class="flex gap-2 flex-1 items-center">
                        <input
                          v-model="form.label.color"
                          type="color"
                          class="w-9 h-9 rounded-lg border-0 bg-transparent cursor-pointer p-0.5"
                        />
                        <input
                          v-model="form.label.color"
                          class="field flex-1"
                          placeholder="#ffffff"
                        />
                      </div>
                    </div>
                    <div class="col-span-2">
                      <button
                        type="button"
                        class="flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-400 transition-colors"
                        @click="showLabelAdvanced = !showLabelAdvanced"
                      >
                        <svg
                          class="w-3 h-3 transition-transform"
                          :class="showLabelAdvanced ? 'rotate-90' : ''"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                          stroke-width="2.5"
                        >
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M8.25 4.5l7.5 7.5-7.5 7.5"
                          />
                        </svg>
                        {{ t('boardSettings.labelAdvanced') }}
                      </button>
                    </div>
                    <template v-if="showLabelAdvanced">
                      <div class="field-row">
                        <label class="field-label">{{ t('boardSettings.offsetX') }}</label>
                        <NumberInput v-model="form.label.x" class="flex-1" />
                      </div>
                      <div class="field-row">
                        <label class="field-label">{{ t('boardSettings.offsetY') }}</label>
                        <NumberInput v-model="form.label.y" class="flex-1" />
                      </div>
                      <div class="field-row col-span-2">
                        <label class="field-label">{{ t('boardSettings.background') }}</label>
                        <ColorInput
                          v-model="form.label.background"
                          none-label="transparent"
                          none-value="transparent"
                          default-color="#000000"
                        />
                      </div>
                      <div class="field-row col-span-2">
                        <label class="field-label">{{ t('boardSettings.borderColor') }}</label>
                        <ColorInput
                          v-model="form.label_border"
                          none-label="default"
                          default-color="#e5e5e5"
                        />
                      </div>
                      <div class="field-row col-span-2">
                        <label class="field-label">{{ t('boardSettings.maxLength') }}</label>
                        <NumberInput
                          v-model="form.label_maxlen"
                          min="0"
                          :placeholder="t('boardSettings.noLimit')"
                          class="flex-1"
                        />
                      </div>
                    </template>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <!-- === APPEARANCE === -->
          <section
            v-if="object.type !== 'line' && object.type !== 'textbox' && object.type !== 'graph'"
          >
            <p class="section-title">{{ t('boardSettings.appearance') }}</p>
            <div class="space-y-3">
              <div class="field-row">
                <label class="field-label">{{ t('boardSettings.viewType') }}</label>
                <select v-model="form.display.mode" class="field flex-1">
                  <option value="icon">{{ t('boardSettings.viewTypeIcon') }}</option>
                  <option value="text">{{ t('boardSettings.viewTypeText') }}</option>
                  <option value="gadget">{{ t('boardSettings.viewTypeGadget') }}</option>
                </select>
              </div>
              <div class="field-row">
                <label class="field-label">{{ t('boardSettings.size') }}</label>
                <NumberInput
                  v-model="form.display.image_size"
                  min="1"
                  max="512"
                  placeholder="map default"
                  class="w-24"
                />
              </div>
              <template v-if="form.display.mode === 'gadget'">
                <div class="field-row">
                  <label class="field-label">{{ t('boardSettings.gadgetType') }}</label>
                  <select v-model="form.display.gadget_type" class="field flex-1">
                    <option value="gauge">{{ t('boardSettings.gadgetGauge') }}</option>
                    <option value="bar">{{ t('boardSettings.gadgetBar') }}</option>
                    <option value="trafficlight">
                      {{ t('boardSettings.gadgetTrafficlight') }}
                    </option>
                  </select>
                </div>
                <div class="field-row">
                  <label class="field-label">{{ t('boardSettings.metric') }}</label>
                  <AutocompleteInput
                    v-model="form.display.gadget_metric"
                    :suggestions="metricSuggestions"
                    :placeholder="t('boardSettings.firstMetric')"
                    class="flex-1"
                  />
                </div>
              </template>
              <div v-if="form.display.mode !== 'gadget'" class="field-row">
                <label class="field-label">{{ t('boardSettings.customIcon') }}</label>
                <input
                  v-model="form.display.image"
                  class="field flex-1 font-mono"
                  placeholder="filename.png"
                />
              </div>
            </div>
          </section>

          <!-- === LINK === -->
          <section>
            <button
              type="button"
              class="flex items-center gap-2 w-full group mb-3"
              @click="showLink = !showLink"
            >
              <p class="section-title mb-0">{{ t('boardSettings.link') }}</p>
              <span
                v-if="form.url"
                class="text-[10px] text-indigo-400 font-mono truncate max-w-[12rem]"
                >{{ form.url }}</span
              >
              <svg
                class="w-3 h-3 text-zinc-600 group-hover:text-zinc-400 transition-all ml-auto shrink-0"
                :class="showLink ? '' : '-rotate-90'"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2.5"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M19.5 8.25l-7.5 7.5-7.5-7.5"
                />
              </svg>
            </button>
            <div v-if="showLink" class="space-y-3">
              <div class="field-row items-start">
                <label class="field-label mt-2">{{ t('boardSettings.url') }}</label>
                <div class="flex-1 space-y-1">
                  <input
                    v-model="form.url"
                    class="field w-full font-mono"
                    :placeholder="autoUrl ?? 'https://…'"
                  />
                  <p v-if="autoUrl && !form.url" class="text-[10px] text-zinc-600">
                    {{ t('boardSettings.urlAutoHint') }}
                  </p>
                </div>
              </div>
              <div class="field-row">
                <label class="field-label">{{ t('boardSettings.target') }}</label>
                <select v-model="form.url_target" class="field flex-1">
                  <option value="_blank">{{ t('boardSettings.targetNewTab') }} (_blank)</option>
                  <option value="_self">{{ t('boardSettings.targetSameTab') }} (_self)</option>
                  <option value="_top">{{ t('boardSettings.targetTopFrame') }} (_top)</option>
                </select>
              </div>
            </div>
          </section>

          <!-- === FILTER (exclude members) === -->
          <section v-if="['host', 'hostgroup', 'servicegroup', 'map'].includes(object.type)">
            <button
              type="button"
              class="flex items-center gap-2 w-full group mb-3"
              @click="showFilter = !showFilter"
            >
              <p class="section-title mb-0">{{ t('boardSettings.filterSection') }}</p>
              <svg
                class="w-3 h-3 text-zinc-600 group-hover:text-zinc-400 transition-all ml-auto shrink-0"
                :class="showFilter ? '' : '-rotate-90'"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2.5"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M19.5 8.25l-7.5 7.5-7.5-7.5"
                />
              </svg>
            </button>
            <div v-if="showFilter" class="space-y-3">
              <div class="field-row">
                <label class="field-label">{{ t('boardSettings.excludeMembers') }}</label>
                <input
                  v-model="form.exclude_members"
                  class="field flex-1 font-mono"
                  :placeholder="t('boardSettings.regexPlaceholder')"
                />
              </div>
              <div class="field-row">
                <label class="field-label">{{ t('boardSettings.excludeStates') }}</label>
                <input
                  v-model="form.exclude_member_states"
                  class="field flex-1 font-mono"
                  placeholder="DOWN,CRITICAL"
                />
              </div>
              <p class="text-xs text-zinc-600 pl-[6.75rem]">{{ t('boardSettings.excludeHint') }}</p>
            </div>
          </section>

          <!-- === TEMPLATES === -->
          <section>
            <button
              type="button"
              class="flex items-center gap-2 w-full group mb-3"
              @click="showTemplates = !showTemplates"
            >
              <p class="section-title mb-0">{{ t('boardSettings.templates') }}</p>
              <svg
                class="w-3 h-3 text-zinc-600 group-hover:text-zinc-400 transition-all ml-auto shrink-0"
                :class="showTemplates ? '' : '-rotate-90'"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2.5"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M19.5 8.25l-7.5 7.5-7.5-7.5"
                />
              </svg>
            </button>
            <div v-if="showTemplates" class="space-y-3">
              <div class="field-row">
                <label class="field-label">{{ t('board.hoverTemplate') }}</label>
                <input
                  v-model="form.hover_template"
                  class="field flex-1 font-mono"
                  :placeholder="t('board.templatePlaceholder')"
                />
              </div>
              <div class="field-row">
                <label class="field-label">{{ t('boardSettings.hoverUrl') }}</label>
                <input
                  v-model="form.hover_url"
                  class="field flex-1 font-mono"
                  placeholder="https://…"
                />
              </div>
              <div class="field-row">
                <label class="field-label">{{ t('board.contextTemplate') }}</label>
                <input
                  v-model="form.context_template"
                  class="field flex-1 font-mono"
                  :placeholder="t('board.templatePlaceholder')"
                />
              </div>
              <p class="text-xs text-zinc-600 pl-[6.75rem]">{{ t('board.templateHint') }}</p>
            </div>
          </section>

          <!-- ID (debug) -->
          <div class="text-xs text-zinc-700 font-mono pt-1 border-t border-[var(--border)]">
            ID: {{ object.id }}
          </div>
        </div>

        <!-- Footer -->
        <div
          class="flex items-center justify-between px-6 py-4 border-t border-[var(--border)] shrink-0"
        >
          <div>
            <button
              class="px-4 py-2 bg-red-600 hover:bg-red-500 rounded-lg text-sm font-semibold text-white transition-all"
              @click="confirmDelete = true"
            >
              {{ t('common.delete') }}
            </button>
            <ConfirmDialog
              v-if="confirmDelete"
              :title="t('board.deleteObject')"
              :message="t('board.cannotBeUndone')"
              :confirm-label="t('common.delete')"
              @confirm="
                confirmDelete = false;
                $emit('delete');
              "
              @cancel="confirmDelete = false"
            />
          </div>
          <div class="flex gap-3">
            <p v-if="saveError" class="text-red-400 text-xs self-center">{{ saveError }}</p>
            <button
              class="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-all"
              @click="$emit('close')"
            >
              {{ t('common.cancel') }}
            </button>
            <button
              :disabled="saving"
              class="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-lg text-sm font-semibold text-white transition-all"
              @click="save"
            >
              {{ saving ? t('common.saving') : t('common.save') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';

import { boardsApi, connectionsApi } from '@/api/client';
import ColorInput from '@/components/ColorInput.vue';
import ConfirmDialog from '@/components/ConfirmDialog.vue';
import NumberInput from '@/components/NumberInput.vue';
import { useAuthStore } from '@/stores/auth';
import { useStatesStore } from '@/stores/states';
import type { BoardObject, MetricGraphGroup, ObjectState } from '@/types/api';
import { getBoardObjectName } from '@/utils/naming';
import { parsePerfData } from '@/utils/perf';

import AutocompleteInput from './AutocompleteInput.vue';

const { t } = useI18n();

const props = defineProps<{
  object: BoardObject;
  state?: ObjectState;
  backendId: string;
  mapType?: string;
  checkmkUrl?: string | null;
  anchorRect?: { left: number; top: number; right: number; bottom: number } | null;
}>();

const emit = defineEmits<{
  close: [];
  save: [updates: Record<string, unknown>];
  delete: [];
}>();

const auth = useAuthStore();
const statesStore = useStatesStore();

// Auto-derived Checkmk URL for the current object (used as placeholder / hint in the URL field)
const autoUrl = computed((): string | null => {
  const base = props.checkmkUrl?.replace(/\/check_mk\/?$/, '').replace(/\/$/, '');
  if (!base) return null;
  const site = base.split('/').at(-1) || null;
  const p: Record<string, string> = {};
  if (site) p.site = site;
  const { type } = props.object;
  const host = form.host_name;
  const svc = form.service_description;
  const grp = form.group_name;
  if (type === 'host' && host) {
    return `${base}/check_mk/view.py?${new URLSearchParams({ ...p, view_name: 'hoststatus', host })}`;
  }
  if (type === 'service' && host && svc) {
    return `${base}/check_mk/view.py?${new URLSearchParams({ ...p, view_name: 'service', host, service: svc })}`;
  }
  if (type === 'hostgroup' && grp) {
    return `${base}/check_mk/view.py?${new URLSearchParams({ ...p, view_name: 'hostgroup', hostgroup: grp })}`;
  }
  if (type === 'servicegroup' && grp) {
    return `${base}/check_mk/view.py?${new URLSearchParams({ ...p, view_name: 'servicegroup', servicegroup: grp })}`;
  }
  return null;
});

// Popover vs centered modal
const isPopover = computed(() => !!props.anchorRect);
const popoverStyle = computed(() => {
  const r = props.anchorRect;
  if (!r) return {};
  const margin = 12;
  const cardW = 400;
  const cardMaxH = window.innerHeight * 0.75; // matches max-h-[75vh]

  // Horizontal: prefer right of object, fall back to left
  let left: number;
  if (r.right + margin + cardW <= window.innerWidth) {
    left = r.right + margin;
  } else {
    left = Math.max(margin, r.left - margin - cardW);
  }

  // Vertical: align top of card with top of object, clamp to viewport
  let top = r.top;
  // If the card would overflow the bottom, push it up
  if (top + cardMaxH + margin > window.innerHeight) {
    top = window.innerHeight - cardMaxH - margin;
  }
  top = Math.max(margin, top);

  return { left: `${left}px`, top: `${top}px` };
});

const fetchedMetrics = ref<string[]>([]);
const graphTemplates = ref<MetricGraphGroup[]>([]);
const boardNames = ref<string[]>([]);

// Metric IDs available for suggestions
const metricIdSuggestions = computed((): string[] => {
  if (fetchedMetrics.value.length) return fetchedMetrics.value;
  return parsePerfData(props.state?.perf_data ?? '').map((m) => m.label);
});

// Map metric ID → human-readable title (falls back to the ID itself)
const metricIdToTitle = computed((): Record<string, string> => {
  return statesStore.metricTitles[props.object.id] ?? {};
});

// Map display title → metric ID (for reverse lookup when user selects a suggestion)
const metricTitleToId = computed((): Map<string, string> => {
  const m = new Map<string, string>();
  for (const id of metricIdSuggestions.value) {
    m.set(metricIdToTitle.value[id] ?? id, id);
  }
  return m;
});

// Display titles for autocomplete (unique: prefer title over ID)
const metricSuggestions = computed((): string[] =>
  metricIdSuggestions.value.map((id) => metricIdToTitle.value[id] ?? id),
);

async function fetchMetrics(host: string, service?: string) {
  if (!props.backendId || !host) return;
  fetchedMetrics.value = await connectionsApi
    .perfMetrics(props.backendId, host, auth.accessToken!, service || undefined)
    .catch(() => []);
}

async function fetchGraphTemplates(host: string, service?: string) {
  if (!props.backendId || !host || props.object.type !== 'graph') return;
  graphTemplates.value = await connectionsApi
    .graphTemplates(props.backendId, host, service ?? null, auth.accessToken!)
    .catch(() => []);
}

async function fetchBoardNames() {
  if (props.object.type !== 'map' || !auth.accessToken) return;
  const boards = await boardsApi.list(auth.accessToken).catch(() => []);
  boardNames.value = boards.map((b) => b.name);
}

// ---- Graph source mode ----

function _deriveGraphSource(obj: BoardObject): 'auto' | 'metrics' | 'template' {
  if (obj.graph_id) return 'template';
  if (obj.graph_metric?.length) return 'metrics';
  return 'auto';
}

const graphSource = ref<'auto' | 'metrics' | 'template'>(_deriveGraphSource(props.object));

function setGraphSource(mode: 'auto' | 'metrics' | 'template') {
  graphSource.value = mode;
  if (mode !== 'template') form.graph_id = null;
  if (mode !== 'metrics') form.graph_metric = [];
}

const metricInput = ref('');
const metricAddEl = ref<HTMLElement | null>(null);

async function addMetric(value: string) {
  const title = value.trim();
  const id = metricTitleToId.value.get(title) ?? title;
  if (id && !form.graph_metric.includes(id)) form.graph_metric.push(id);
  metricInput.value = '';
  await nextTick();
  metricAddEl.value?.querySelector('input')?.focus();
}

// ---- Form state ----

const form = reactive({
  host_name: '',
  service_description: '',
  group_name: '',
  map_name: '',
  line_style: null as string | null,
  line_color: null as string | null,
  line_color_border: null as string | null,
  label: {
    show: true,
    text: '',
    x: 0,
    y: 0,
    size: 11,
    color: '#ffffff',
    background: 'transparent',
  },
  label_border: null as string | null,
  label_maxlen: null as number | null,
  textbox_background: null as string | null,
  textbox_border: null as string | null,
  textbox_width: null as number | null,
  textbox_height: null as number | null,
  graph_url: '',
  graph_embed_type: 'img' as 'img' | 'iframe',
  graph_width: 400,
  graph_height: 200,
  graph_refresh_interval: 0,
  graph_metric: [] as string[],
  graph_id: null as string | null,
  graph_time_window: 60 as number,
  display: {
    mode: 'icon' as 'icon' | 'text' | 'gadget',
    image: '',
    image_size: null as number | null,
    gadget_type: 'gauge' as string,
    gadget_metric: '',
  },
  weathermap_metric: '',
  only_hard_states: false,
  recognize_services: false,
  exclude_members: '',
  exclude_member_states: '',
  url: '',
  url_target: '_blank',
  hover_url: '',
  hover_template: '',
  context_template: '',
  x: 0,
  y: 0,
  lat: 0,
  lng: 0,
  z: 1,
  x2: 0,
  y2: 0,
});

const saving = ref(false);
const saveError = ref('');
const confirmDelete = ref(false);
const showLink = ref(!!props.object.url);
const showLabelAdvanced = ref(false);
const showTemplates = ref(
  !!(props.object.hover_template || props.object.context_template || props.object.hover_url),
);
const showFilter = ref(!!(props.object.exclude_members || props.object.exclude_member_states));

// Initialize form from object
watch(
  () => props.object,
  (obj) => {
    form.host_name = obj.host_name ?? '';
    form.service_description = obj.service_description ?? '';
    form.group_name = obj.group_name ?? '';
    form.map_name = obj.map_name ?? '';
    form.line_style = obj.line_style ?? null;
    form.line_color = obj.line_color ?? null;
    form.line_color_border = obj.line_color_border ?? null;
    form.label.show = obj.label?.show ?? true;
    form.label.text = obj.label?.text ?? '';
    form.label.x = obj.label?.x ?? 0;
    form.label.y = obj.label?.y ?? 0;
    form.label.size = obj.label?.size ?? 11;
    form.label.color = obj.label?.color ?? '#ffffff';
    form.label.background = obj.label?.background ?? 'transparent';
    form.label_border = obj.label_border ?? null;
    form.label_maxlen = obj.label_maxlen ?? null;
    form.textbox_background = obj.textbox_background ?? null;
    form.textbox_border = obj.textbox_border ?? null;
    form.textbox_width = obj.textbox_width ?? null;
    form.textbox_height = obj.textbox_height ?? null;
    form.graph_url = obj.graph_url ?? '';
    form.graph_embed_type = obj.graph_embed_type ?? 'img';
    form.graph_width = obj.graph_width ?? 400;
    form.graph_height = obj.graph_height ?? 200;
    form.graph_refresh_interval = obj.graph_refresh_interval ?? 0;
    form.graph_metric = obj.graph_metric ?? [];
    form.graph_id = obj.graph_id ?? null;
    graphSource.value = _deriveGraphSource(obj);
    form.graph_time_window = obj.graph_time_window ?? 60;
    form.display.mode = obj.display?.mode ?? 'icon';
    form.display.image = obj.display?.image ?? '';
    form.display.image_size = obj.display?.image_size ?? null;
    form.display.gadget_type = obj.display?.gadget_type ?? 'gauge';
    form.display.gadget_metric = obj.display?.gadget_metric ?? '';
    form.weathermap_metric = obj.weathermap_metric ?? '';
    form.only_hard_states = obj.only_hard_states ?? false;
    form.recognize_services = obj.recognize_services ?? false;
    form.exclude_members = obj.exclude_members ?? '';
    form.exclude_member_states = obj.exclude_member_states ?? '';
    form.url = obj.url ?? '';
    form.url_target = obj.url_target ?? '_blank';
    form.hover_url = obj.hover_url ?? '';
    form.hover_template = obj.hover_template ?? '';
    form.context_template = obj.context_template ?? '';
    form.x = obj.x ?? 0;
    form.y = obj.y ?? 0;
    form.lat = obj.lat ?? 0;
    form.lng = obj.lng ?? 0;
    form.z = obj.z ?? 1;
    form.x2 = obj.x2 ?? obj.x + 150;
    form.y2 = obj.y2 ?? obj.y;
    showLabelAdvanced.value = false;
    showTemplates.value = !!(obj.hover_template || obj.context_template || obj.hover_url);
    showFilter.value = !!(obj.exclude_members || obj.exclude_member_states);
  },
  { immediate: true },
);

// ---- Autocomplete ----

const hosts = ref<string[]>([]);
const services = ref<string[]>([]);
const groups = ref<string[]>([]);
const loadingHosts = ref(false);
const loadingServices = ref(false);
const loadingGroups = ref(false);

async function loadAutocomplete() {
  if (!props.backendId) return;
  const type = props.object.type;
  if (type === 'host' || type === 'service' || type === 'line' || type === 'graph') {
    loadingHosts.value = true;
    hosts.value = await connectionsApi
      .objects(props.backendId, 'host', auth.accessToken!)
      .catch(() => []);
    loadingHosts.value = false;
    if ((type === 'service' || type === 'line' || type === 'graph') && form.host_name) {
      loadingServices.value = true;
      services.value = await connectionsApi
        .objects(props.backendId, 'service', auth.accessToken!, form.host_name)
        .catch(() => []);
      loadingServices.value = false;
    }
  } else if (type === 'hostgroup') {
    loadingGroups.value = true;
    groups.value = await connectionsApi
      .objects(props.backendId, 'hostgroup', auth.accessToken!)
      .catch(() => []);
    loadingGroups.value = false;
  } else if (type === 'servicegroup') {
    loadingGroups.value = true;
    groups.value = await connectionsApi
      .objects(props.backendId, 'servicegroup', auth.accessToken!)
      .catch(() => []);
    loadingGroups.value = false;
  }
}

loadAutocomplete();

onMounted(() => {
  if (form.host_name) {
    fetchMetrics(form.host_name, form.service_description || undefined);
    fetchGraphTemplates(form.host_name, form.service_description || undefined);
  }
  if (props.object.type === 'map') fetchBoardNames();
});

watch(
  () => [form.host_name, form.service_description],
  ([host, svc]) => {
    if (host) {
      fetchMetrics(host, svc || undefined);
      fetchGraphTemplates(host, svc || undefined);
    } else {
      fetchedMetrics.value = [];
      graphTemplates.value = [];
    }
  },
);

watch(
  () => form.host_name,
  async (host) => {
    if (
      (props.object.type === 'service' ||
        props.object.type === 'line' ||
        props.object.type === 'graph') &&
      host
    ) {
      loadingServices.value = true;
      services.value = await connectionsApi
        .objects(props.backendId, 'service', auth.accessToken!, host)
        .catch(() => []);
      loadingServices.value = false;
    }
  },
);

const displayName = computed(() => getBoardObjectName(props.object));

// ---- Save ----

async function save() {
  saveError.value = '';
  saving.value = true;
  try {
    const updates: Record<string, unknown> = {
      display:
        props.object.type === 'graph' || props.object.type === 'line'
          ? null
          : {
              mode: form.display.mode,
              image: form.display.image || null,
              image_size: form.display.image_size ?? null,
              gadget_type: form.display.mode === 'gadget' ? form.display.gadget_type : null,
              gadget_metric:
                form.display.mode === 'gadget' ? form.display.gadget_metric || null : null,
            },
      label: {
        show: form.label.show,
        text: form.label.text || null,
        x: form.label.x,
        y: form.label.y,
        size: form.label.size,
        color: form.label.color,
        background: form.label.background,
      },
      label_border: form.label_border || null,
      label_maxlen: form.label_maxlen ?? null,
      textbox_background: form.textbox_background || null,
      textbox_border: form.textbox_border || null,
      textbox_width: form.textbox_width ?? null,
      textbox_height: form.textbox_height ?? null,
      graph_url: form.graph_url || null,
      graph_embed_type: form.graph_embed_type,
      graph_width: form.graph_width,
      graph_height: form.graph_height,
      graph_refresh_interval: form.graph_refresh_interval,
      graph_metric: form.graph_metric.length ? form.graph_metric : null,
      graph_id: form.graph_id || null,
      graph_time_window: form.graph_time_window,
      line_style: form.line_style,
      line_color: form.line_color || null,
      line_color_border: form.line_color_border || null,
      url: form.url || null,
      url_target: form.url_target,
      hover_url: form.hover_url || null,
      hover_template: form.hover_template || null,
      context_template: form.context_template || null,
      exclude_members: form.exclude_members || null,
      exclude_member_states: form.exclude_member_states || null,
      z: form.z,
    };

    if (props.object.type === 'host' || props.object.type === 'service') {
      updates.host_name = form.host_name || null;
      updates.only_hard_states = form.only_hard_states;
    }
    if (props.object.type === 'host') updates.recognize_services = form.recognize_services;
    if (props.object.type === 'service')
      updates.service_description = form.service_description || null;
    if (props.object.type === 'graph') {
      updates.host_name = form.host_name || null;
      updates.service_description = form.service_description || null;
    }
    if (props.object.type === 'hostgroup' || props.object.type === 'servicegroup')
      updates.group_name = form.group_name || null;
    if (props.object.type === 'map') updates.map_name = form.map_name || null;

    if (props.object.type === 'line') {
      updates.x = form.x;
      updates.y = form.y;
      updates.host_name = form.host_name || null;
      updates.service_description = form.service_description || null;
      updates.x2 = form.x2;
      updates.y2 = form.y2;
      if (form.line_style === 'weathermap')
        updates.weathermap_metric = form.weathermap_metric || null;
    } else if (props.mapType === 'worldmap') {
      updates.lat = form.lat;
      updates.lng = form.lng;
    } else {
      updates.x = form.x;
      updates.y = form.y;
    }

    emit('save', updates);
  } catch (e: unknown) {
    saveError.value = e instanceof Error ? e.message : t('boardSettings.saveFailed');
    saving.value = false;
  }
}
</script>

<style scoped>
@reference "tailwindcss";

.section-title {
  @apply text-[11px] font-semibold text-zinc-400 tracking-wide mb-3 leading-none;
}

.field-row {
  @apply flex items-center gap-3;
}

.field-label {
  @apply text-xs text-zinc-500 w-24 shrink-0;
}

.field {
  @apply w-full px-3 py-2 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all duration-150;

  appearance: textfield;
}

.field::-webkit-outer-spin-button,
.field::-webkit-inner-spin-button {
  appearance: none;
}

select.field {
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%23a1a1aa' stroke-width='2'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M19.5 8.25l-7.5 7.5-7.5-7.5'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 0.5rem center;
  background-size: 1rem;
  padding-right: 2rem;
}
</style>
