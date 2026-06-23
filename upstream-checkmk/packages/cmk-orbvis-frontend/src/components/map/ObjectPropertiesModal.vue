<template>
  <div class="orb-props" :class="isPopover ? '' : 'orb-props--centered'">
    <!-- Backdrop: dark in modal mode, transparent dismiss layer in popover mode -->
    <div
      class="orb-props__backdrop"
      :class="isPopover ? '' : 'orb-props__backdrop--dim'"
      @click="$emit('close')"
    />
    <!-- Card: centered in modal mode, positioned at click in popover mode -->
    <Transition
      appear
      enter-from-class="orb-props__card-enter-from"
      enter-active-class="orb-props__card-enter-active"
    >
      <div
        class="orb-props__card"
        :class="isPopover ? 'orb-props__card--popover' : 'orb-props__card--modal'"
        :style="cardStyle"
      >
        <div
          class="orb-props__header"
          :class="dragging ? 'orb-props__header--dragging' : ''"
          @pointerdown="onHeaderPointerDown"
          @pointermove="onHeaderPointerMove"
          @pointerup="onHeaderPointerUp"
          @pointercancel="onHeaderPointerUp"
        >
          <div class="orb-props__inline">
            <span class="orb-props__type-badge">
              {{ object.type }}
            </span>
            <span class="orb-props__name">{{ displayName }}</span>
          </div>
          <button class="orb-props__close" @click="$emit('close')">
            <svg
              style="width: 14px; height: 14px"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <CmkScrollContainer class="orb-props__body">
          <!-- === MONITORING OBJECT === -->
          <section
            v-if="
              object.type !== 'textbox' &&
              object.type !== 'line' &&
              object.type !== 'graph' &&
              object.type !== 'image'
            "
          >
            <p class="orb-section-title">{{ _t('Monitoring object') }}</p>
            <div class="orb-props__fields">
              <div class="field-row">
                <label class="field-label">{{ _t('Connection') }}</label>
                <CmkDropdown
                  class="orb-props__grow"
                  :selected-option="form.connection_id || ''"
                  :options="connectionDropdownOptions"
                  :width="'fill'"
                  :label="_t('Connection')"
                  @update:selected-option="form.connection_id = $event ?? ''"
                />
              </div>
              <template v-if="object.type === 'host' || object.type === 'service'">
                <div class="field-row">
                  <label class="field-label">{{ _t('Hostname') }}</label>
                  <AutocompleteInput
                    v-model="form.host_name"
                    :suggestions="hosts"
                    :loading="loadingHosts"
                    placeholder="hostname"
                    :empty-text="_t('No hosts available')"
                    class="orb-props__grow"
                  />
                </div>
              </template>
              <template v-if="object.type === 'service'">
                <div class="field-row">
                  <label class="field-label">{{ _t('Service') }}</label>
                  <AutocompleteInput
                    v-model="form.service_description"
                    :suggestions="services"
                    :loading="loadingServices"
                    placeholder="service description"
                    :empty-text="_t('No services for this host')"
                    class="orb-props__grow"
                  />
                </div>
              </template>
              <template v-if="object.type === 'host' || object.type === 'service'">
                <div class="orb-props__checks">
                  <CmkCheckbox v-model="form.only_hard_states" :label="_t('Only hard states')" />
                  <CmkCheckbox
                    v-if="object.type === 'host'"
                    v-model="form.recognize_services"
                    :label="_t('Consider services')"
                  />
                </div>
              </template>
              <template v-if="object.type === 'hostgroup' || object.type === 'servicegroup'">
                <div class="field-row">
                  <label class="field-label">{{ _t('Group name') }}</label>
                  <AutocompleteInput
                    v-model="form.group_name"
                    :suggestions="groups"
                    :loading="loadingGroups"
                    placeholder="group name"
                    :empty-text="_t('No groups available')"
                    class="orb-props__grow"
                  />
                </div>
              </template>
              <template v-if="object.type === 'dyngroup'">
                <div class="field-row">
                  <label class="field-label">Object type</label>
                  <select v-model="form.object_types" class="orb-field orb-props__grow">
                    <option value="host">host</option>
                    <option value="service">service</option>
                  </select>
                </div>
                <div class="field-row">
                  <label class="field-label">Livestatus filter</label>
                  <textarea
                    v-model="form.object_filter"
                    class="orb-field orb-props__grow orb-props__code-input"
                    rows="4"
                    spellcheck="false"
                    placeholder="Filter: host_name ~ ^web\n"
                  />
                </div>
                <p class="orb-props__note">
                  One or more <code>Filter:</code> lines, each terminated by a literal
                  <code>\n</code>. Forwarded verbatim to Livestatus against
                  <code>GET hosts/services</code>.
                </p>
              </template>
              <template v-if="object.type === 'map'">
                <div class="field-row">
                  <label class="field-label">{{ _t('Map name') }}</label>
                  <AutocompleteInput
                    v-model="form.map_name"
                    :suggestions="mapNames"
                    :display-labels="mapLabels"
                    placeholder="map-name"
                    :empty-text="_t('No other maps available')"
                    class="orb-props__grow"
                  />
                </div>
              </template>
              <template v-if="object.type === 'aggregation'">
                <div class="field-row">
                  <label class="field-label">{{ _t('BI aggregation') || 'BI aggregation' }}</label>
                  <AutocompleteInput
                    v-model="form.aggregation_id"
                    :suggestions="aggregationIds"
                    :display-labels="aggregationLabels"
                    :loading="loadingAggregations"
                    placeholder="aggregation id"
                    :empty-text="
                      _t(
                        'No BI aggregations available — none are configured in Checkmk, or your user has no permission to view them.'
                      )
                    "
                    class="orb-props__grow"
                  />
                </div>
                <div class="field-row">
                  <label class="field-label">{{ _t('Expand depth') }}</label>
                  <NumberInput
                    v-model="form.expand_depth"
                    min="0"
                    max="10"
                    class="orb-props__grow"
                    :title="_t('Show child nodes up to N levels (0 = root only).')"
                  />
                </div>
                <div v-if="(form.expand_depth ?? 0) > 0" class="field-row">
                  <label class="field-label">{{ _t('Subtree line') }}</label>
                  <ColorInput
                    v-model="form.line_color"
                    :enable-label="_t('Use color')"
                    default-color="#a1a1aa"
                  />
                </div>
                <div v-if="(form.expand_depth ?? 0) > 0" class="field-row">
                  <label class="field-label">{{ _t('Subtree width') }}</label>
                  <NumberInput
                    v-model="form.line_width"
                    :min="1"
                    :max="20"
                    :placeholder="_t('auto')"
                    class="orb-props__grow"
                  />
                </div>
              </template>
            </div>
          </section>

          <!-- === TEXTBOX CONTENT + STYLING === -->
          <section v-if="object.type === 'textbox'">
            <p class="orb-section-title">{{ _t('Content') }}</p>
            <textarea
              v-model="form.label.text"
              rows="3"
              class="orb-field orb-props__textarea"
              :placeholder="_t('Text content') + '…'"
            />
            <div class="orb-props__fields">
              <div class="field-row">
                <label class="field-label">{{ _t('Alignment') }}</label>
                <div class="orb-props__btn-group">
                  <button
                    v-for="opt in textAlignOptions"
                    :key="opt.value"
                    type="button"
                    class="orb-props__seg-btn"
                    :class="
                      (form.label.align ?? 'left') === opt.value ? 'orb-props__seg-btn--active' : ''
                    "
                    :title="opt.title"
                    :aria-label="opt.title"
                    @click="form.label.align = opt.value"
                  >
                    <svg
                      style="width: 15px; height: 15px"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path stroke-linecap="round" stroke-linejoin="round" :d="opt.icon" />
                    </svg>
                  </button>
                </div>
              </div>
              <div class="orb-props__grid-2">
                <div class="field-row">
                  <label class="field-label">{{ _t('Width') }}</label>
                  <NumberInput
                    v-model="form.textbox_width"
                    :placeholder="_t('auto')"
                    class="orb-props__grow"
                  />
                </div>
                <div class="field-row">
                  <label class="field-label">{{ _t('Height') }}</label>
                  <NumberInput
                    v-model="form.textbox_height"
                    :placeholder="_t('auto')"
                    class="orb-props__grow"
                  />
                </div>
              </div>
              <div class="field-row">
                <label class="field-label">{{ _t('Background') }}</label>
                <ColorInput
                  v-model="form.textbox_background"
                  :enable-label="_t('Use color')"
                  default-color="#1a1a2e"
                />
              </div>
              <div class="field-row">
                <label class="field-label">{{ _t('Border color') }}</label>
                <ColorInput
                  v-model="form.textbox_border"
                  :enable-label="_t('Use color')"
                  default-color="#e5e5e5"
                />
              </div>
            </div>
          </section>

          <!-- === GRAPH: Metric Source === -->
          <section v-if="object.type === 'graph'">
            <div class="orb-props__section-head">
              <p class="orb-section-title orb-section-title--flush">
                {{ _t('Metric Source') }}
              </p>
              <span class="orb-props__badge-experimental">experimental</span>
            </div>
            <div class="orb-props__fields">
              <div class="field-row">
                <label class="field-label">{{ _t('Hostname') }}</label>
                <AutocompleteInput
                  v-model="form.host_name"
                  :suggestions="hosts"
                  :loading="loadingHosts"
                  placeholder="hostname"
                  :empty-text="_t('No hosts available')"
                  class="orb-props__grow"
                />
              </div>
              <div class="field-row">
                <label class="field-label">{{ _t('Service') }}</label>
                <AutocompleteInput
                  v-model="form.service_description"
                  :suggestions="services"
                  :loading="loadingServices"
                  placeholder="service description"
                  :empty-text="_t('No services for this host')"
                  class="orb-props__grow"
                />
              </div>
              <div class="field-row">
                <label class="field-label">{{ _t('Source') }}</label>
                <div class="orb-props__btn-group">
                  <button
                    v-for="mode in ['auto', 'metrics', 'template'] as const"
                    :key="mode"
                    class="orb-props__seg-btn"
                    :class="graphSource === mode ? 'orb-props__seg-btn--active' : ''"
                    @click="setGraphSource(mode)"
                  >
                    {{ graphSourceLabel[mode] ?? mode }}
                  </button>
                </div>
              </div>
              <div v-if="graphSource === 'metrics'" class="field-row field-row--start">
                <label class="field-label field-label--offset-6">{{ _t('Metrics') }}</label>
                <div class="orb-props__metric-col">
                  <div v-if="form.graph_metric.length" class="orb-props__chips">
                    <span v-for="m in form.graph_metric" :key="m" class="orb-props__chip">
                      {{ metricIdToTitle[m] ?? m }}
                      <button
                        class="orb-props__chip-remove"
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
                            !form.graph_metric.includes(metricTitleToId.get(title) ?? title)
                        )
                      "
                      :placeholder="_t('Add metric…')"
                      :empty-text="metricSuggestions.length === 0 ? _t('No metrics available') : ''"
                      class="orb-props__full"
                      @change="addMetric"
                    />
                  </div>
                </div>
              </div>
              <div v-if="graphSource === 'template' && graphTemplates.length" class="field-row">
                <label class="field-label">{{ _t('Graph template') }}</label>
                <CmkDropdown
                  class="orb-props__grow"
                  :selected-option="form.graph_id ?? null"
                  :options="{
                    type: 'fixed',
                    suggestions: [
                      { name: null, title: '—' },
                      ...graphTemplates.map((tpl) => ({
                        name: tpl.id,
                        title: tpl.title
                      }))
                    ]
                  }"
                  label=""
                  @update:selected-option="
                    (v) => {
                      form.graph_id = v || null
                    }
                  "
                />
              </div>
              <div class="field-row">
                <label class="field-label">{{ _t('Time window') }}</label>
                <CmkDropdown
                  class="orb-props__grow"
                  :selected-option="String(form.graph_time_window)"
                  :options="{
                    type: 'fixed',
                    suggestions: [
                      { name: '60', title: '1 h' },
                      { name: '240', title: '4 h' },
                      { name: '720', title: '12 h' },
                      { name: '1440', title: '24 h' },
                      { name: '10080', title: '7 d' }
                    ]
                  }"
                  label=""
                  @update:selected-option="
                    (v) => {
                      form.graph_time_window = Number(v)
                    }
                  "
                />
              </div>
            </div>
          </section>

          <!-- === GRAPH: URL Embed === -->
          <section v-if="object.type === 'graph'">
            <p class="orb-section-title">{{ _t('URL Embed') }}</p>
            <div class="orb-props__fields">
              <div class="field-row">
                <label class="field-label">{{ _t('URL') }}</label>
                <CmkInput
                  v-model="form.graph_url"
                  placeholder="https://… (optional)"
                  field-size="FILL"
                  class="orb-props__grow"
                />
              </div>
              <div class="field-row">
                <label class="field-label">{{ _t('Embed as') }}</label>
                <CmkDropdown
                  class="orb-props__grow"
                  :selected-option="form.graph_embed_type || null"
                  :options="{
                    type: 'fixed',
                    suggestions: [
                      {
                        name: 'img',
                        title: _t('Image (img)')
                      },
                      {
                        name: 'iframe',
                        title: _t('Interactive (iframe)')
                      }
                    ]
                  }"
                  label=""
                  @update:selected-option="
                    form.graph_embed_type = ($event ?? '') as typeof form.graph_embed_type
                  "
                />
              </div>
              <div class="orb-props__grid-2">
                <div class="field-row">
                  <label class="field-label">{{ _t('Width') }}</label>
                  <NumberInput v-model="form.graph_width" min="50" class="orb-props__grow" />
                </div>
                <div class="field-row">
                  <label class="field-label">{{ _t('Height') }}</label>
                  <NumberInput v-model="form.graph_height" min="30" class="orb-props__grow" />
                </div>
              </div>
              <div class="field-row">
                <label class="field-label">{{ _t('Auto-refresh (s)') }}</label>
                <div class="orb-props__inline orb-props__grow">
                  <NumberInput
                    v-model="form.graph_refresh_interval"
                    min="0"
                    class="orb-props__grow"
                  />
                  <span class="orb-props__inline-label">{{ _t('0 = off') }}</span>
                </div>
              </div>
            </div>
          </section>

          <!-- === LINE CONFIG === -->
          <section v-if="object.type === 'line'">
            <p class="orb-section-title">{{ _t('Monitoring object') }}</p>
            <div class="orb-props__fields">
              <div class="field-row">
                <label class="field-label">{{ _t('Hostname') }}</label>
                <AutocompleteInput
                  v-model="form.host_name"
                  :suggestions="hosts"
                  :loading="loadingHosts"
                  placeholder="hostname"
                  :empty-text="_t('No hosts available')"
                  class="orb-props__grow"
                />
              </div>
              <div class="field-row">
                <label class="field-label">{{ _t('Service') }}</label>
                <AutocompleteInput
                  v-model="form.service_description"
                  :suggestions="services"
                  :loading="loadingServices"
                  placeholder="service description (optional)"
                  :empty-text="
                    form.host_name && !loadingServices ? _t('No services for this host') : ''
                  "
                  class="orb-props__grow"
                />
              </div>
            </div>
          </section>
          <section v-if="object.type === 'line' && (object.start_ref || object.end_ref)">
            <p class="orb-section-title">{{ _t('Connection') }}</p>
            <div class="orb-props__fields">
              <p class="orb-props__note">
                {{ _t('This line is attached to an object and follows it.') }}
              </p>
              <CmkButton variant="secondary" @click="$emit('detach')">
                {{ _t('Detach from object') }}
              </CmkButton>
            </div>
          </section>
          <section v-if="object.type === 'line'">
            <p class="orb-section-title">{{ _t('Line') }}</p>
            <div class="orb-props__fields">
              <div class="field-row">
                <label class="field-label">{{ _t('Z') }}</label>
                <NumberInput v-model="form.z" min="0" max="999" class="orb-props__grow" />
              </div>
              <div class="field-row">
                <label class="field-label">{{ _t('Style') }}</label>
                <CmkDropdown
                  class="orb-props__grow"
                  :selected-option="form.line_style ?? null"
                  :options="lineStyleOpts"
                  label=""
                  @update:selected-option="
                    (v) => {
                      form.line_style = v || null
                    }
                  "
                />
              </div>
              <!-- Perfdata label mode (none / percent / bandwidth / both) -->
              <div class="field-row">
                <label class="field-label">{{ _t('Perfdata label') }}</label>
                <CmkDropdown
                  class="orb-props__grow"
                  :selected-option="form.line_perfdata_label ?? 'none'"
                  :options="linePerfdataLabelOpts"
                  label=""
                  @update:selected-option="
                    (v) => {
                      form.line_perfdata_label = (v as LinePerfdataLabel) || 'none'
                    }
                  "
                />
              </div>
              <div class="field-row">
                <CmkCheckbox
                  v-model="form.line_weather_color"
                  :label="_t('Color by utilization (weathermap)')"
                />
              </div>
              <!-- Weathermap inbound metric (rendered left of the midpoint) -->
              <div
                v-if="form.line_perfdata_label !== 'none' || form.line_weather_color"
                class="field-row"
              >
                <label class="field-label">{{ _t('Metric (in)') }}</label>
                <AutocompleteInput
                  v-model="form.weathermap_metric"
                  :suggestions="metricIdSuggestions"
                  :display-labels="metricIdSuggestions.map((id) => metricIdToTitle[id] ?? id)"
                  :placeholder="_t('first metric')"
                  :empty-text="metricIdSuggestions.length === 0 ? _t('No metrics available') : ''"
                  class="orb-props__grow"
                />
              </div>
              <!-- Weathermap outbound metric (optional; right of the midpoint,
                                 drives the second gradient colour + label). Only offered once an
                                 inbound metric is set — out-only would colour the in-half from an
                                 arbitrary first perfdata metric. -->
              <div
                v-if="
                  (form.line_perfdata_label !== 'none' || form.line_weather_color) &&
                  !!form.weathermap_metric
                "
                class="field-row"
              >
                <label class="field-label">{{ _t('Metric (out)') }}</label>
                <AutocompleteInput
                  v-model="form.weathermap_metric_out"
                  :suggestions="metricIdSuggestions"
                  :display-labels="metricIdSuggestions.map((id) => metricIdToTitle[id] ?? id)"
                  :placeholder="_t('second metric (optional)')"
                  :empty-text="metricIdSuggestions.length === 0 ? _t('No metrics available') : ''"
                  class="orb-props__grow"
                />
              </div>
              <div class="orb-props__grid-2">
                <!-- Line/Border color are ignored once weather coloring
                                     drives the stroke (the renderer pulls wmColor and
                                     skips the border altogether), so hide them to keep
                                     the dialog honest about what actually takes effect. -->
                <div v-if="!form.line_weather_color" class="field-row orb-props__span-2">
                  <label class="field-label">{{ _t('Line color') }}</label>
                  <ColorInput
                    v-model="form.line_color"
                    :enable-label="_t('Use color')"
                    default-color="#ffffff"
                  />
                </div>
                <div v-if="!form.line_weather_color" class="field-row orb-props__span-2">
                  <label class="field-label">{{ _t('Border color') }}</label>
                  <ColorInput
                    v-model="form.line_color_border"
                    :enable-label="_t('Use color')"
                    default-color="#000000"
                  />
                </div>
                <div class="field-row orb-props__span-2">
                  <label class="field-label">{{ _t('Line width') }}</label>
                  <NumberInput
                    v-model="form.line_width"
                    :min="1"
                    :max="20"
                    :placeholder="_t('auto')"
                    class="orb-props__grow"
                  />
                </div>
                <template v-if="mapType !== 'worldmap'">
                  <div class="field-row">
                    <label class="field-label">{{ _t('Start X') }}</label>
                    <NumberInput v-model="form.x" min="0" max="10000" class="orb-props__grow" />
                  </div>
                  <div class="field-row">
                    <label class="field-label">{{ _t('Y') }}</label>
                    <NumberInput v-model="form.y" min="0" max="10000" class="orb-props__grow" />
                  </div>
                  <div class="field-row">
                    <label class="field-label">{{ _t('End X') }}</label>
                    <NumberInput v-model="form.x2" min="0" max="10000" class="orb-props__grow" />
                  </div>
                  <div class="field-row">
                    <label class="field-label">{{ _t('Y') }}</label>
                    <NumberInput v-model="form.y2" min="0" max="10000" class="orb-props__grow" />
                  </div>
                </template>
              </div>
              <div class="field-row">
                <label class="field-label">{{ _t('Show label') }}</label>
                <CmkCheckbox v-model="form.label.show" />
              </div>
              <div v-if="form.label.show" class="field-row">
                <label class="field-label">{{ _t('Line label') }}</label>
                <CmkInput v-model="form.label.text" field-size="FILL" class="orb-props__grow" />
              </div>
            </div>
          </section>

          <!-- === POSITION === -->
          <section v-if="object.type !== 'line'">
            <p class="orb-section-title">{{ _t('Position') }}</p>
            <div class="orb-props__grid-3">
              <template v-if="mapType === 'worldmap'">
                <div class="orb-props__inline">
                  <label class="orb-props__inline-label">{{ _t('Lat') }}</label>
                  <NumberInput v-model="form.lat" step="any" class="orb-props__grow" />
                </div>
                <div class="orb-props__inline">
                  <label class="orb-props__inline-label">{{ _t('Lng') }}</label>
                  <NumberInput v-model="form.lng" step="any" class="orb-props__grow" />
                </div>
              </template>
              <template v-else>
                <div class="orb-props__inline">
                  <label class="orb-props__inline-label">{{ _t('X') }}</label>
                  <NumberInput v-model="form.x" min="0" max="10000" class="orb-props__grow" />
                </div>
                <div class="orb-props__inline">
                  <label class="orb-props__inline-label">{{ _t('Y') }}</label>
                  <NumberInput v-model="form.y" min="0" max="10000" class="orb-props__grow" />
                </div>
              </template>
              <div class="orb-props__inline">
                <label class="orb-props__inline-label">{{ _t('Z') }}</label>
                <NumberInput v-model="form.z" min="1" max="999" class="orb-props__grow" />
              </div>
            </div>
          </section>

          <!-- === LABEL === -->
          <section v-if="object.type !== 'line'">
            <p class="orb-section-title">{{ _t('Label') }}</p>
            <div class="orb-props__fields">
              <div class="field-row">
                <label class="field-label">{{ _t('Show label') }}</label>
                <CmkCheckbox v-model="form.label.show" />
              </div>
              <div :class="!form.label.show ? 'orb-props__disabled' : ''">
                <div class="orb-props__fields">
                  <div v-if="object.type !== 'textbox'" class="field-row">
                    <label class="field-label">{{ _t('Label text') }}</label>
                    <CmkInput
                      v-model="form.label.text"
                      placeholder="(auto from object)"
                      field-size="FILL"
                      class="orb-props__grow"
                    />
                  </div>
                  <div class="orb-props__grid-2">
                    <div class="field-row">
                      <label class="field-label">{{ _t('Size') }}</label>
                      <NumberInput
                        v-model="form.label.size"
                        min="8"
                        max="72"
                        class="orb-props__grow"
                      />
                    </div>
                    <div class="field-row orb-props__span-2">
                      <label class="field-label">{{ _t('Color') }}</label>
                      <ColorInput v-model="form.label.color" default-color="#ffffff" />
                    </div>
                    <div class="field-row">
                      <label class="field-label">{{ _t('Offset X') }}</label>
                      <NumberInput v-model="form.label.x" class="orb-props__grow" />
                    </div>
                    <div class="field-row">
                      <label class="field-label">{{ _t('Offset Y') }}</label>
                      <NumberInput v-model="form.label.y" class="orb-props__grow" />
                    </div>
                    <div class="orb-props__span-2">
                      <button
                        type="button"
                        class="orb-props__toggle"
                        @click="showLabelAdvanced = !showLabelAdvanced"
                      >
                        <p class="orb-section-title orb-section-title--flush">
                          {{ _t('Background & border') }}
                        </p>
                        <svg
                          class="orb-props__chevron"
                          :class="showLabelAdvanced ? '' : 'orb-props__chevron--collapsed'"
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
                    </div>
                    <template v-if="showLabelAdvanced">
                      <div class="field-row orb-props__span-2">
                        <label class="field-label">{{ _t('Background') }}</label>
                        <ColorInput
                          v-model="form.label.background"
                          :enable-label="_t('Use color')"
                          none-value="transparent"
                          default-color="#000000"
                        />
                      </div>
                      <div class="field-row orb-props__span-2">
                        <label class="field-label">{{ _t('Border color') }}</label>
                        <ColorInput
                          v-model="form.label_border"
                          :enable-label="_t('Use color')"
                          default-color="#e5e5e5"
                        />
                      </div>
                      <div class="field-row orb-props__span-2">
                        <label class="field-label">{{ _t('Max length') }}</label>
                        <NumberInput
                          v-model="form.label_maxlen"
                          min="0"
                          :placeholder="_t('no limit')"
                          class="orb-props__grow"
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
            <p class="orb-section-title">{{ _t('Appearance') }}</p>
            <div class="orb-props__fields">
              <div class="field-row">
                <label class="field-label">{{ _t('View type') }}</label>
                <CmkDropdown
                  class="orb-props__grow"
                  :selected-option="form.display.mode || null"
                  :options="displayModeOptions"
                  label=""
                  @update:selected-option="
                    form.display.mode = ($event ?? '') as typeof form.display.mode
                  "
                />
              </div>
              <div class="field-row">
                <label class="field-label">{{ _t('Size') }}</label>
                <NumberInput
                  v-model="form.display.image_size"
                  min="1"
                  max="512"
                  :placeholder="
                    form.display.mode === 'gadget'
                      ? String(GADGET_DEFAULT_SIZE)
                      : mapIconSize != null
                        ? String(mapIconSize)
                        : _t('map default')
                  "
                  class="orb-props__size-input"
                />
              </div>
              <template v-if="form.display.mode === 'gadget'">
                <div class="field-row">
                  <label class="field-label">{{ _t('Gadget type') }}</label>
                  <CmkDropdown
                    class="orb-props__grow"
                    :selected-option="form.display.gadget_type || null"
                    :options="gadgetTypeOptions"
                    label=""
                    @update:selected-option="form.display.gadget_type = $event ?? ''"
                  />
                </div>
                <div class="field-row">
                  <label class="field-label">{{ _t('Metric') }}</label>
                  <AutocompleteInput
                    v-model="form.display.gadget_metric"
                    :suggestions="metricIdSuggestions"
                    :display-labels="metricIdSuggestions.map((id) => metricIdToTitle[id] ?? id)"
                    :placeholder="_t('first metric')"
                    :empty-text="metricIdSuggestions.length === 0 ? _t('No metrics available') : ''"
                    class="orb-props__grow"
                  />
                </div>
              </template>
              <div v-if="form.display.mode !== 'gadget'" class="field-row field-row--start">
                <label class="field-label" style="margin-top: 6px">{{ _t('Custom icon') }}</label>
                <ImagePicker v-model="form.display.image" class="orb-props__grow" />
              </div>
            </div>
          </section>

          <!-- === LINK === -->
          <section>
            <button
              type="button"
              class="orb-props__toggle orb-props__toggle--spaced"
              @click="showLink = !showLink"
            >
              <p class="orb-section-title orb-section-title--flush">
                {{ _t('Link') }}
              </p>
              <span v-if="form.url" class="orb-props__url-preview">{{ form.url }}</span>
              <svg
                class="orb-props__chevron"
                :class="showLink ? '' : 'orb-props__chevron--collapsed'"
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
            <div v-if="showLink" class="orb-props__fields">
              <div class="field-row field-row--start">
                <label class="field-label field-label--offset-8">{{ _t('URL') }}</label>
                <div class="orb-props__url-col">
                  <CmkInput
                    v-model="form.url"
                    :placeholder="autoUrl ?? 'https://…'"
                    field-size="FILL"
                  />
                  <button
                    v-if="autoUrl && !form.url"
                    type="button"
                    class="orb-props__url-auto"
                    @click="form.url = autoUrl!"
                  >
                    {{ _t('Automatically derived from Checkmk URL when left empty') }} →
                  </button>
                </div>
              </div>
              <div class="field-row">
                <label class="field-label">{{ _t('Target') }}</label>
                <CmkDropdown
                  class="orb-props__grow"
                  :selected-option="form.url_target || null"
                  :options="urlTargetOptions"
                  label=""
                  @update:selected-option="form.url_target = $event ?? ''"
                />
              </div>
            </div>
          </section>

          <!-- === FILTER (exclude members) === -->
          <section v-if="['host', 'hostgroup', 'servicegroup', 'map'].includes(object.type)">
            <button
              type="button"
              class="orb-props__toggle orb-props__toggle--spaced"
              @click="showFilter = !showFilter"
            >
              <p class="orb-section-title orb-section-title--flush">
                {{ _t('Filter') }}
              </p>
              <svg
                class="orb-props__chevron"
                :class="showFilter ? '' : 'orb-props__chevron--collapsed'"
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
            <div v-if="showFilter" class="orb-props__fields">
              <div class="field-row">
                <label class="field-label">{{ _t('Exclude members') }}</label>
                <CmkInput
                  v-model="form.exclude_members"
                  :placeholder="_t('regex pattern…')"
                  field-size="FILL"
                  class="orb-props__grow"
                />
              </div>
              <div class="field-row">
                <label class="field-label">{{ _t('Exclude states') }}</label>
                <CmkInput
                  v-model="form.exclude_member_states"
                  placeholder="DOWN,CRITICAL"
                  field-size="FILL"
                  class="orb-props__grow"
                />
              </div>
              <!--
                                Live count of leaves the regex would suppress
                                from the aggregation tree. Visual feedback
                                turns the regex from "guess" into a tracked
                                filter — operator sees immediately whether
                                their pattern matches 0, 12, or "every leaf".
                            -->
              <p
                v-if="excludeMembersFeedback"
                class="orb-props__feedback"
                :class="excludeMembersFeedback.tone"
              >
                {{ excludeMembersFeedback.text }}
              </p>
              <p class="orb-props__field-hint">
                {{ _t('Regex to exclude members / comma-separated states to ignore') }}
              </p>
            </div>
          </section>

          <!-- === TEMPLATES === -->
          <section>
            <button
              type="button"
              class="orb-props__toggle orb-props__toggle--spaced"
              @click="showTemplates = !showTemplates"
            >
              <p class="orb-section-title orb-section-title--flush">
                {{ _t('Templates') }}
              </p>
              <svg
                class="orb-props__chevron"
                :class="showTemplates ? '' : 'orb-props__chevron--collapsed'"
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
            <div v-if="showTemplates" class="orb-props__fields">
              <div class="field-row">
                <label class="field-label">{{ _t('Hover template') }}</label>
                <CmkInput
                  v-model="form.hover_template"
                  :placeholder="_t('e.g. {{name}} is {{state}}')"
                  field-size="FILL"
                  class="orb-props__grow"
                />
              </div>
              <div class="field-row">
                <label class="field-label">{{ _t('Hover URL') }}</label>
                <CmkInput
                  v-model="form.hover_url"
                  placeholder="https://…"
                  field-size="FILL"
                  class="orb-props__grow"
                />
              </div>
              <div class="field-row">
                <label class="field-label">{{ _t('Context template') }}</label>
                <CmkInput
                  v-model="form.context_template"
                  :placeholder="_t('e.g. {{name}} is {{state}}')"
                  field-size="FILL"
                  class="orb-props__grow"
                />
              </div>
              <!-- Literal {{…}} placeholders would terminate a mustache, so the
                   hint is built in script and only interpolated here. -->
              <p class="orb-props__field-hint">{{ templateHelpHint }}</p>
            </div>
          </section>
        </CmkScrollContainer>

        <div class="orb-props__footer">
          <div>
            <CmkButton variant="danger" @click="confirmDelete = true">{{ _t('Delete') }}</CmkButton>
            <OrbConfirmDialog
              :open="confirmDelete"
              :title="_t('Delete object')"
              :message="_t('This cannot be undone.')"
              :confirm-label="_t('Delete')"
              @confirm="onConfirmDelete"
              @cancel="confirmDelete = false"
            />
          </div>
          <div class="orb-props__footer-actions">
            <p v-if="saveError" class="orb-props__error">
              {{ saveError }}
            </p>
            <CmkButton variant="secondary" @click="$emit('close')">{{ _t('Cancel') }}</CmkButton>
            <CmkButton variant="primary" :disabled="saving" @click="save">
              {{ saving ? _t('Saving…') : _t('Save') }}
            </CmkButton>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'

import ColorInput from '@/components/ColorInput.vue'
import NumberInput from '@/components/NumberInput.vue'
import OrbConfirmDialog from '@/components/OrbConfirmDialog.vue'
import CmkButton from '@/components/cmk/CmkButton'
import CmkDropdown from '@/components/cmk/CmkDropdown/CmkDropdown'
import CmkScrollContainer from '@/components/cmk/CmkScrollContainer'
import CmkCheckbox from '@/components/cmk/user-input/CmkCheckbox'
import CmkInput from '@/components/cmk/user-input/CmkInput'

import { useEscapeClose } from '@/composables/useEscapeClose'
import { useExcludeMembersPreview } from '@/composables/useExcludeMembersPreview'
import { useObjectFormData } from '@/composables/useObjectFormData'
import { usePropertiesPopover } from '@/composables/usePropertiesPopover'
import type { MapObject, LinePerfdataLabel, ObjectState } from '@/types/api'
import { buildCheckmkViewUrl } from '@/utils/mapNavigation'
import { linePerfdataLabelOptions, lineStyleOptions } from '@/utils/dropdownOptions'
import { GADGET_DEFAULT_SIZE } from '@/utils/gadget'
import { getMapObjectIdentifier } from '@/utils/naming'
import usei18n from '@cmk/lib/i18n'

import AutocompleteInput from './AutocompleteInput.vue'
import ImagePicker from './ImagePicker.vue'

const { _t } = usei18n()

const graphSourceLabel = computed<Record<string, string>>(() => ({
  auto: _t('auto'),
  metrics: _t('Metrics'),
  template: _t('Template')
}))

const props = defineProps<{
  object: MapObject
  state?: ObjectState | undefined
  connectionId: string
  mapType?: string | undefined
  mapIconSize?: number | null
  mapDefaultZ?: number
  checkmkUrl?: string | null
  anchorRect?: { left: number; top: number; right: number; bottom: number } | null
}>()

const emit = defineEmits<{
  close: []
  save: [updates: Record<string, unknown>]
  delete: []
  detach: []
}>()
useEscapeClose(() => emit('close'))

// Auto-derived Checkmk URL for the current object (used as placeholder / hint in the URL field)
const autoUrl = computed((): string | null => {
  const opts = { site: props.state?.site_id ?? null }
  const { type } = props.object
  const host = form.host_name
  const svc = form.service_description
  const grp = form.group_name
  if (type === 'host' && host) {
    return buildCheckmkViewUrl(props.checkmkUrl, 'hoststatus', { host }, opts)
  }
  if (type === 'service' && host && svc) {
    return buildCheckmkViewUrl(props.checkmkUrl, 'service', { host, service: svc }, opts)
  }
  if (type === 'hostgroup' && grp) {
    return buildCheckmkViewUrl(props.checkmkUrl, 'hostgroup', { hostgroup: grp }, opts)
  }
  if (type === 'servicegroup' && grp) {
    return buildCheckmkViewUrl(props.checkmkUrl, 'servicegroup', { servicegroup: grp }, opts)
  }
  return null
})

// Popover placement + drag-to-move (grab the header)
const {
  isPopover,
  cardStyle,
  dragging,
  onHeaderPointerDown,
  onHeaderPointerMove,
  onHeaderPointerUp
} = usePropertiesPopover({
  anchorRect: () => props.anchorRect,
  object: () => props.object
})

const lineStyleOpts = computed(() => ({
  type: 'fixed' as const,
  suggestions: lineStyleOptions(_t)
}))
const linePerfdataLabelOpts = computed(() => ({
  type: 'fixed' as const,
  suggestions: linePerfdataLabelOptions(_t)
}))
const displayModeOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'icon', title: _t('Icon') },
    { name: 'text', title: _t('Text only') },
    { name: 'gadget', title: _t('Gadget') }
  ]
}))
const gadgetTypeOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'gauge', title: _t('Gauge') },
    { name: 'bar', title: _t('Bar') },
    { name: 'trafficlight', title: _t('Traffic light') },
    { name: 'value', title: _t('Value') }
  ]
}))
const urlTargetOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: '_blank', title: _t('New tab') + ' (_blank)' },
    { name: '_self', title: _t('Same tab') + ' (_self)' },
    { name: '_top', title: _t('Top frame') + ' (_top)' }
  ]
}))

const textAlignOptions = computed(() => [
  {
    value: 'left' as const,
    title: _t('Left'),
    icon: 'M3.75 6.75h16.5M3.75 12h10.5M3.75 17.25h13.5'
  },
  {
    value: 'center' as const,
    title: _t('Center'),
    icon: 'M3.75 6.75h16.5M6.75 12h10.5M5.25 17.25h13.5'
  },
  {
    value: 'right' as const,
    title: _t('Right'),
    icon: 'M3.75 6.75h16.5M9.75 12h10.5M6.75 17.25h13.5'
  }
])

// ---- Form state ----

const form = reactive({
  connection_id: '' as string,
  host_name: '',
  service_description: '',
  group_name: '',
  map_name: '',
  aggregation_id: '',
  object_types: 'host' as 'host' | 'service',
  object_filter: '',
  expand_depth: 0,
  line_style: null as string | null,
  line_color: null as string | null,
  line_color_border: null as string | null,
  line_width: null as number | null,
  line_perfdata_label: 'none' as LinePerfdataLabel,
  line_weather_color: false,
  label: {
    show: true,
    text: '',
    x: 0,
    y: 0,
    size: 11,
    color: '#ffffff',
    background: 'transparent',
    align: null as 'left' | 'center' | 'right' | null
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
    gadget_metric: ''
  },
  weathermap_metric: '',
  weathermap_metric_out: '',
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
  y2: 0
})

// Remote data + suggestion model (metrics, graph templates, map names,
// host/service/group/aggregation autocomplete, connection override list).
const metricAddEl = ref<HTMLElement | null>(null)
const {
  graphTemplates,
  mapNames,
  mapLabels,
  metricIdSuggestions,
  metricIdToTitle,
  metricTitleToId,
  metricSuggestions,
  graphSource,
  deriveGraphSource,
  setGraphSource,
  metricInput,
  addMetric,
  connectionDropdownOptions,
  hosts,
  services,
  groups,
  aggregationIds,
  aggregationLabels,
  loadingHosts,
  loadingServices,
  loadingGroups,
  loadingAggregations
} = useObjectFormData({
  form,
  object: () => props.object,
  state: () => props.state,
  connectionId: () => props.connectionId,
  metricAddEl
})

const saving = ref(false)
const saveError = ref('')
const confirmDelete = ref(false)
const showLink = ref(!!props.object.url)
const showLabelAdvanced = ref(false)
const showTemplates = ref(
  !!(props.object.hover_template || props.object.context_template || props.object.hover_url)
)
const showFilter = ref(!!(props.object.exclude_members || props.object.exclude_member_states))

const templateHelpHint = computed(() =>
  _t(
    'Available: {{name}}, {{state}}, {{output}}, {{host}}, {{service}}, {{address}}, {{state_type}}, {{attempts}}, {{last_check}}, {{state_duration}}, {{acknowledged}}, {{in_downtime}}, {{stale}}'
  )
)

// Initialize form from object
watch(
  () => props.object,
  (obj) => {
    form.connection_id = obj.connection_id ?? ''
    form.host_name = obj.host_name ?? ''
    form.service_description = obj.service_description ?? ''
    form.group_name = obj.group_name ?? ''
    form.map_name = obj.map_name ?? ''
    form.aggregation_id = obj.aggregation_id ?? ''
    form.object_types = obj.object_types ?? 'host'
    form.object_filter = obj.object_filter ?? ''
    form.expand_depth = obj.expand_depth ?? 0
    form.line_style = obj.line_style ?? null
    form.line_color = obj.line_color ?? null
    form.line_color_border = obj.line_color_border ?? null
    form.line_width = obj.line_width ?? null
    form.line_perfdata_label = obj.line_perfdata_label ?? 'none'
    form.line_weather_color = obj.line_weather_color ?? false
    form.label.show = obj.label?.show ?? true
    form.label.text = obj.label?.text ?? ''
    form.label.x = obj.label?.x ?? 0
    form.label.y = obj.label?.y ?? 0
    form.label.size = obj.label?.size ?? 11
    form.label.color = obj.label?.color ?? '#ffffff'
    form.label.background = obj.label?.background ?? 'transparent'
    form.label.align = (obj.label?.align as 'left' | 'center' | 'right' | null) ?? null
    form.label_border = obj.label_border ?? null
    form.label_maxlen = obj.label_maxlen ?? null
    form.textbox_background = obj.textbox_background ?? null
    form.textbox_border = obj.textbox_border ?? null
    form.textbox_width = obj.textbox_width ?? null
    form.textbox_height = obj.textbox_height ?? null
    form.graph_url = obj.graph_url ?? ''
    form.graph_embed_type = obj.graph_embed_type ?? 'img'
    form.graph_width = obj.graph_width ?? 400
    form.graph_height = obj.graph_height ?? 200
    form.graph_refresh_interval = obj.graph_refresh_interval ?? 0
    form.graph_metric = obj.graph_metric ?? []
    form.graph_id = obj.graph_id ?? null
    graphSource.value = deriveGraphSource(obj)
    form.graph_time_window = obj.graph_time_window ?? 60
    form.display.mode = obj.display?.mode ?? 'icon'
    form.display.image = obj.display?.image ?? ''
    form.display.image_size = obj.display?.image_size ?? null
    form.display.gadget_type = obj.display?.gadget_type ?? 'gauge'
    form.display.gadget_metric = obj.display?.gadget_metric ?? ''
    form.weathermap_metric = obj.weathermap_metric ?? ''
    form.weathermap_metric_out = obj.weathermap_metric_out ?? ''
    form.only_hard_states = obj.only_hard_states ?? false
    form.recognize_services = obj.recognize_services ?? false
    form.exclude_members = obj.exclude_members ?? ''
    form.exclude_member_states = obj.exclude_member_states ?? ''
    form.url = obj.url ?? ''
    form.url_target = obj.url_target ?? '_blank'
    form.hover_url = obj.hover_url ?? ''
    form.hover_template = obj.hover_template ?? ''
    form.context_template = obj.context_template ?? ''
    form.x = obj.x ?? 0
    form.y = obj.y ?? 0
    form.lat = obj.lat ?? 0
    form.lng = obj.lng ?? 0
    form.z = obj.z ?? props.mapDefaultZ ?? 1
    form.x2 = obj.x2 ?? obj.x + 150
    form.y2 = obj.y2 ?? obj.y
    showLabelAdvanced.value = false
    showTemplates.value = !!(obj.hover_template || obj.context_template || obj.hover_url)
    showFilter.value = !!(obj.exclude_members || obj.exclude_member_states)
  },
  { immediate: true }
)

// Live "N of M leaves hidden" preview for the BI exclude_members filter.
const { excludeMembersFeedback } = useExcludeMembersPreview({
  connectionId: () => props.connectionId,
  aggregationId: () => form.aggregation_id,
  excludeMembers: () => form.exclude_members,
  excludeMemberStates: () => form.exclude_member_states
})

const displayName = computed(() => getMapObjectIdentifier(props.object))

// ---- Save ----

async function save() {
  saveError.value = ''
  if (props.object.type === 'line' && form.line_weather_color && !form.weathermap_metric.trim()) {
    saveError.value = _t('Pick a metric — weather coloring needs one to colorize the line.')
    return
  }
  saving.value = true
  try {
    const updates: Record<string, unknown> = {
      connection_id: form.connection_id || null,
      display:
        props.object.type === 'graph' || props.object.type === 'line'
          ? null
          : {
              mode: form.display.mode,
              image: form.display.image || null,
              image_size: form.display.image_size ?? null,
              gadget_type: form.display.mode === 'gadget' ? form.display.gadget_type : null,
              gadget_metric:
                form.display.mode === 'gadget' ? form.display.gadget_metric || null : null
            },
      label: {
        show: form.label.show,
        text: form.label.text || null,
        x: form.label.x,
        y: form.label.y,
        size: form.label.size,
        color: form.label.color,
        background: form.label.background,
        align: form.label.align
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
      line_width: form.line_width,
      line_perfdata_label: form.line_perfdata_label,
      line_weather_color: form.line_weather_color,
      url: form.url || null,
      url_target: form.url_target,
      hover_url: form.hover_url || null,
      hover_template: form.hover_template || null,
      context_template: form.context_template || null,
      exclude_members: form.exclude_members || null,
      exclude_member_states: form.exclude_member_states || null,
      z: form.z
    }

    if (props.object.type === 'host' || props.object.type === 'service') {
      updates.host_name = form.host_name || null
      updates.only_hard_states = form.only_hard_states
    }
    if (props.object.type === 'host') updates.recognize_services = form.recognize_services
    if (props.object.type === 'service')
      updates.service_description = form.service_description || null
    if (props.object.type === 'graph') {
      updates.host_name = form.host_name || null
      updates.service_description = form.service_description || null
    }
    if (props.object.type === 'hostgroup' || props.object.type === 'servicegroup')
      updates.group_name = form.group_name || null
    if (props.object.type === 'map') updates.map_name = form.map_name || null
    if (props.object.type === 'aggregation') {
      updates.aggregation_id = form.aggregation_id || null
      updates.expand_depth = form.expand_depth ?? 0
    }
    if (props.object.type === 'dyngroup') {
      updates.object_types = form.object_types
      updates.object_filter = form.object_filter || null
    }

    if (props.object.type === 'line') {
      updates.host_name = form.host_name || null
      updates.service_description = form.service_description || null
      // Persist the metric whenever the line shows perfdata labels or
      // uses weather-coloring — both modes need it to look up perfdata.
      if (form.line_perfdata_label !== 'none' || form.line_weather_color) {
        updates.weathermap_metric = form.weathermap_metric || null
        // Outbound only makes sense alongside an inbound metric (it's the
        // second direction); never persist it on its own.
        updates.weathermap_metric_out =
          (form.weathermap_metric && form.weathermap_metric_out) || null
      }
      if (props.mapType !== 'worldmap') {
        updates.x = form.x
        updates.y = form.y
        updates.x2 = form.x2
        updates.y2 = form.y2
      }
    } else if (props.mapType === 'worldmap') {
      updates.lat = form.lat
      updates.lng = form.lng
    } else {
      updates.x = form.x
      updates.y = form.y
    }

    emit('save', updates)
  } catch (e: unknown) {
    saveError.value = e instanceof Error ? e.message : _t('Save failed')
    saving.value = false
  }
}

function onConfirmDelete(): void {
  confirmDelete.value = false
  emit('delete')
}
</script>

<style scoped>
.field-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.field-label {
  flex-shrink: 0;
  width: 88px;
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
}

/* Number inputs here hide the native spinner (custom +/- handling). */
.orb-field {
  appearance: textfield;
}

.orb-field::-webkit-outer-spin-button,
.orb-field::-webkit-inner-spin-button {
  appearance: none;
}

.orb-props {
  position: fixed;
  inset: 0;
  z-index: 50;
}

.orb-props--centered {
  display: flex;
  align-items: center;
  justify-content: center;
}

.orb-props__backdrop {
  position: absolute;
  inset: 0;
  transition: all 0.15s;
}

.orb-props__backdrop--dim {
  background: rgb(0 0 0 / 60%);
  backdrop-filter: blur(4px);
}

.orb-props__card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg-surface);
  border-radius: 16px;
  box-shadow:
    0 0 0 1px var(--border),
    0 25px 50px -12px rgb(0 0 0 / 60%);
}

.orb-props__card--popover {
  position: absolute;
  width: 25rem;
  max-height: 75vh;
}

.orb-props__card--modal {
  position: relative;
  width: 36rem;
  max-height: 90vh;
}

.orb-props__card-enter-from {
  opacity: 0;
  transform: translateY(-4px) scale(0.95);
}

.orb-props__card-enter-active {
  transition: all 0.15s cubic-bezier(0, 0, 0.2, 1);
}

.orb-props__header {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: space-between;
  padding: 10px var(--dimension-6);
  cursor: grab;
  user-select: none;
  touch-action: none;
  border-bottom: 1px solid var(--border);
}

.orb-props__header--dragging {
  cursor: grabbing;
}

.orb-props__inline {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
}

.orb-props__type-badge {
  padding: var(--dimension-2) 6px;
  font-size: var(--font-size-normal);
  font-weight: 600;
  line-height: 16px;
  color: var(--text-muted);
  text-transform: capitalize;
  background: var(--default-form-element-bg-color);
  border-radius: 6px;
  box-shadow: 0 0 0 1px var(--default-form-element-border-color);
}

.orb-props__name {
  font-size: var(--font-size-large);
  font-weight: 700;
  line-height: 20px;
  color: var(--text);
}

.orb-props__close {
  padding: 5px;
  color: var(--text-muted);
  border-radius: 8px;
  transition: all 0.15s;
}

.orb-props__close:hover {
  color: var(--text);
  background: var(--bg-hover);
}

.orb-props__body {
  flex: 1 1 0%;
  min-height: 0;
  padding: 10px var(--dimension-6);
}

.orb-props__body > * + * {
  margin-top: 14px;
}

.orb-props__fields > * + * {
  margin-top: var(--dimension-4);
}

.orb-props__grid-2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--dimension-4);
}

.orb-props__grid-3 {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--dimension-4);
}

.orb-props__span-2 {
  grid-column: span 2 / span 2;
}

.orb-props__grow {
  flex: 1 1 0%;
}

.orb-props__full {
  width: 100%;
}

.orb-props__checks {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.orb-props__code-input {
  font-family:
    ui-monospace, sfmono-regular, menlo, monaco, consolas, 'Liberation Mono', 'Courier New',
    monospace;
  font-size: var(--font-size-normal);
  line-height: 16px;
}

.orb-props__note {
  margin-top: var(--dimension-3);
  font-size: var(--font-size-normal);
  line-height: 16px;
  color: var(--text-muted);
}

.orb-props__textarea {
  margin-bottom: var(--dimension-4);
  resize: none;
}

.orb-props__section-head {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  margin-bottom: var(--dimension-4);
}

.orb-props__badge-experimental {
  flex-shrink: 0;
  padding: var(--dimension-2) 6px;
  font-size: 10px;
  font-weight: 500;
  color: var(--color-yellow-50);
  background: color-mix(in srgb, var(--color-warning) 15%, transparent);
  border: 1px solid color-mix(in srgb, var(--color-warning) 25%, transparent);
  border-radius: 4px;
}

.orb-props__btn-group {
  display: flex;
  flex: 1 1 0%;
  gap: var(--dimension-3);
}

.orb-props__seg-btn {
  padding: var(--dimension-3) var(--dimension-4);
  font-size: var(--font-size-normal);
  line-height: 16px;
  color: var(--text-muted);
  background: var(--default-form-element-bg-color);
  border-radius: 4px;
  transition: all 0.15s;
}

.orb-props__seg-btn:hover {
  color: var(--text);
}

.orb-props__seg-btn--active,
.orb-props__seg-btn--active:hover {
  color: var(--button-primary-text-color, #000);
  background: var(--color-corporate-green-50);
}

.field-row--start {
  align-items: flex-start;
}

.field-label--offset-6 {
  margin-top: 6px;
}

.field-label--offset-8 {
  margin-top: var(--dimension-4);
}

.orb-props__metric-col {
  flex: 1 1 0%;
}

.orb-props__metric-col > * + * {
  margin-top: 6px;
}

.orb-props__chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--dimension-3);
}

.orb-props__chip {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  padding: var(--dimension-2) var(--dimension-4);
  font-size: var(--font-size-normal);
  line-height: 16px;
  color: var(--text);
  background: var(--default-form-element-bg-color);
  border-radius: 4px;
  box-shadow: 0 0 0 1px var(--default-border-color);
}

.orb-props__chip-remove {
  color: var(--text-muted);
}

.orb-props__chip-remove:hover {
  color: var(--color-light-red-40);
}

.orb-props__inline-label {
  flex-shrink: 0;
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
}

.orb-props__size-input {
  width: 6rem;
}

.orb-props__disabled {
  pointer-events: none;
  opacity: 0.4;
}

.orb-props__toggle {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  width: 100%;
}

.orb-props__toggle--spaced {
  margin-bottom: var(--dimension-4);
}

.orb-props__chevron {
  flex-shrink: 0;
  width: 12px;
  height: 12px;
  margin-left: auto;
  color: var(--text-muted);
  transition: all 0.15s;
}

.orb-props__chevron--collapsed {
  transform: rotate(-90deg);
}

.orb-props__url-preview {
  max-width: 12rem;
  overflow: hidden;
  font-family:
    ui-monospace, sfmono-regular, menlo, monaco, consolas, 'Liberation Mono', 'Courier New',
    monospace;
  font-size: 10px;
  color: var(--color-corporate-green-50);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.orb-props__url-col {
  flex: 1 1 0%;
}

.orb-props__url-col > * + * {
  margin-top: var(--dimension-3);
}

.orb-props__url-auto {
  font-size: 10px;
  color: var(--text-muted);
  text-align: left;
  transition:
    color 0.15s,
    background-color 0.15s;
}

.orb-props__url-auto:hover {
  color: var(--color-corporate-green-50);
  text-decoration: underline;
}

.orb-props__feedback {
  padding-left: 6.75rem;
  font-size: var(--font-size-normal);
  line-height: 16px;
}

.orb-props__feedback--invalid {
  color: var(--color-light-red-30);
}

.orb-props__feedback--muted {
  color: var(--text-muted);
}

.orb-props__feedback--warn {
  color: var(--color-yellow-50);
}

.orb-props__feedback--matched {
  color: var(--text);
}

.orb-props__field-hint {
  padding-left: 6.75rem;
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
}

.orb-props__footer {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: space-between;
  gap: var(--dimension-4);
  padding: 10px var(--dimension-6);
  border-top: 1px solid var(--border);
}

.orb-props__footer-actions {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
}

.orb-props__error {
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--color-light-red-40);
}
</style>
