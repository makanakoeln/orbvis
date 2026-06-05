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
                <!-- Header -->
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
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="M6 18L18 6M6 6l12 12"
                            />
                        </svg>
                    </button>
                </div>

                <!-- Scrollable body -->
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
                        <p class="orb-section-title">{{ t('boardSettings.monitoringObject') }}</p>
                        <div class="orb-props__fields">
                            <div class="field-row">
                                <label class="field-label">{{
                                    t('boardSettings.connection')
                                }}</label>
                                <CmkDropdown
                                    class="orb-props__grow"
                                    :selected-option="form.connection_id || ''"
                                    :options="connectionDropdownOptions"
                                    :width="'fill'"
                                    :label="t('boardSettings.connection')"
                                    @update:selected-option="form.connection_id = $event ?? ''"
                                />
                            </div>
                            <template v-if="object.type === 'host' || object.type === 'service'">
                                <div class="field-row">
                                    <label class="field-label">{{
                                        t('boardSettings.hostname')
                                    }}</label>
                                    <AutocompleteInput
                                        v-model="form.host_name"
                                        :suggestions="hosts"
                                        :loading="loadingHosts"
                                        placeholder="hostname"
                                        :empty-text="t('boardSettings.noHosts')"
                                        class="orb-props__grow"
                                    />
                                </div>
                            </template>
                            <template v-if="object.type === 'service'">
                                <div class="field-row">
                                    <label class="field-label">{{
                                        t('boardSettings.typeService')
                                    }}</label>
                                    <AutocompleteInput
                                        v-model="form.service_description"
                                        :suggestions="services"
                                        :loading="loadingServices"
                                        placeholder="service description"
                                        :empty-text="t('boardSettings.noServices')"
                                        class="orb-props__grow"
                                    />
                                </div>
                            </template>
                            <template v-if="object.type === 'host' || object.type === 'service'">
                                <div class="orb-props__checks">
                                    <CmkCheckbox
                                        v-model="form.only_hard_states"
                                        :label="t('boardSettings.onlyHardStates')"
                                    />
                                    <CmkCheckbox
                                        v-if="object.type === 'host'"
                                        v-model="form.recognize_services"
                                        :label="t('boardSettings.recognizeServices')"
                                    />
                                </div>
                            </template>
                            <template
                                v-if="object.type === 'hostgroup' || object.type === 'servicegroup'"
                            >
                                <div class="field-row">
                                    <label class="field-label">{{
                                        t('boardSettings.groupName')
                                    }}</label>
                                    <AutocompleteInput
                                        v-model="form.group_name"
                                        :suggestions="groups"
                                        :loading="loadingGroups"
                                        placeholder="group name"
                                        :empty-text="t('boardSettings.noGroups')"
                                        class="orb-props__grow"
                                    />
                                </div>
                            </template>
                            <template v-if="object.type === 'dyngroup'">
                                <div class="field-row">
                                    <label class="field-label">Object type</label>
                                    <select
                                        v-model="form.object_types"
                                        class="orb-field orb-props__grow"
                                    >
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
                                    One or more <code>Filter:</code> lines, each terminated by a
                                    literal <code>\n</code>. Forwarded verbatim to Livestatus
                                    against <code>GET hosts/services</code>.
                                </p>
                            </template>
                            <template v-if="object.type === 'map'">
                                <div class="field-row">
                                    <label class="field-label">{{
                                        t('boardSettings.boardName')
                                    }}</label>
                                    <AutocompleteInput
                                        v-model="form.map_name"
                                        :suggestions="boardNames"
                                        :display-labels="boardLabels"
                                        placeholder="map-name"
                                        :empty-text="t('boardSettings.noBoards')"
                                        class="orb-props__grow"
                                    />
                                </div>
                            </template>
                            <template v-if="object.type === 'aggregation'">
                                <div class="field-row">
                                    <label class="field-label">{{
                                        t('boardSettings.aggregationId') || 'BI aggregation'
                                    }}</label>
                                    <AutocompleteInput
                                        v-model="form.aggregation_id"
                                        :suggestions="aggregationIds"
                                        :display-labels="aggregationLabels"
                                        :loading="loadingAggregations"
                                        placeholder="aggregation id"
                                        :empty-text="t('boardSettings.noAggregations')"
                                        class="orb-props__grow"
                                    />
                                </div>
                                <div class="field-row">
                                    <label class="field-label">{{
                                        t('boardSettings.expandDepth')
                                    }}</label>
                                    <NumberInput
                                        v-model="form.expand_depth"
                                        min="0"
                                        max="10"
                                        class="orb-props__grow"
                                        :title="t('boardSettings.expandDepthHelp')"
                                    />
                                </div>
                                <div v-if="(form.expand_depth ?? 0) > 0" class="field-row">
                                    <label class="field-label">{{
                                        t('boardSettings.biLineColor')
                                    }}</label>
                                    <ColorInput
                                        v-model="form.line_color"
                                        :enable-label="t('common.useColor')"
                                        default-color="#a1a1aa"
                                    />
                                </div>
                                <div v-if="(form.expand_depth ?? 0) > 0" class="field-row">
                                    <label class="field-label">{{
                                        t('boardSettings.biLineWidth')
                                    }}</label>
                                    <NumberInput
                                        v-model="form.line_width"
                                        :min="1"
                                        :max="20"
                                        :placeholder="t('boardSettings.lineWidthDefault')"
                                        class="orb-props__grow"
                                    />
                                </div>
                            </template>
                        </div>
                    </section>

                    <!-- === TEXTBOX CONTENT + STYLING === -->
                    <section v-if="object.type === 'textbox'">
                        <p class="orb-section-title">{{ t('boardSettings.content') }}</p>
                        <textarea
                            v-model="form.label.text"
                            rows="3"
                            class="orb-field orb-props__textarea"
                            :placeholder="t('boardSettings.textContent') + '…'"
                        />
                        <div class="orb-props__fields">
                            <div class="orb-props__grid-2">
                                <div class="field-row">
                                    <label class="field-label">{{
                                        t('boardSettings.width')
                                    }}</label>
                                    <NumberInput
                                        v-model="form.textbox_width"
                                        :placeholder="t('boardSettings.auto')"
                                        class="orb-props__grow"
                                    />
                                </div>
                                <div class="field-row">
                                    <label class="field-label">{{
                                        t('boardSettings.height')
                                    }}</label>
                                    <NumberInput
                                        v-model="form.textbox_height"
                                        :placeholder="t('boardSettings.auto')"
                                        class="orb-props__grow"
                                    />
                                </div>
                            </div>
                            <div class="field-row">
                                <label class="field-label">{{
                                    t('boardSettings.background')
                                }}</label>
                                <ColorInput
                                    v-model="form.textbox_background"
                                    :enable-label="t('common.useColor')"
                                    default-color="#1a1a2e"
                                />
                            </div>
                            <div class="field-row">
                                <label class="field-label">{{
                                    t('boardSettings.borderColor')
                                }}</label>
                                <ColorInput
                                    v-model="form.textbox_border"
                                    :enable-label="t('common.useColor')"
                                    default-color="#e5e5e5"
                                />
                            </div>
                        </div>
                    </section>

                    <!-- === GRAPH: Metric Source === -->
                    <section v-if="object.type === 'graph'">
                        <div class="orb-props__section-head">
                            <p class="orb-section-title orb-section-title--flush">
                                {{ t('boardSettings.graphMetricSource') }}
                            </p>
                            <span class="orb-props__badge-experimental">experimental</span>
                        </div>
                        <div class="orb-props__fields">
                            <div class="field-row">
                                <label class="field-label">{{ t('boardSettings.hostname') }}</label>
                                <AutocompleteInput
                                    v-model="form.host_name"
                                    :suggestions="hosts"
                                    :loading="loadingHosts"
                                    placeholder="hostname"
                                    :empty-text="t('boardSettings.noHosts')"
                                    class="orb-props__grow"
                                />
                            </div>
                            <div class="field-row">
                                <label class="field-label">{{
                                    t('boardSettings.typeService')
                                }}</label>
                                <AutocompleteInput
                                    v-model="form.service_description"
                                    :suggestions="services"
                                    :loading="loadingServices"
                                    placeholder="service description"
                                    :empty-text="t('boardSettings.noServices')"
                                    class="orb-props__grow"
                                />
                            </div>
                            <div class="field-row">
                                <label class="field-label">{{
                                    t('boardSettings.graphSource')
                                }}</label>
                                <div class="orb-props__btn-group">
                                    <button
                                        v-for="mode in ['auto', 'metrics', 'template'] as const"
                                        :key="mode"
                                        class="orb-props__seg-btn"
                                        :class="
                                            graphSource === mode ? 'orb-props__seg-btn--active' : ''
                                        "
                                        @click="setGraphSource(mode)"
                                    >
                                        {{ t(`boardSettings.graphSource_${mode}`) }}
                                    </button>
                                </div>
                            </div>
                            <div
                                v-if="graphSource === 'metrics'"
                                class="field-row field-row--start"
                            >
                                <label class="field-label field-label--offset-6">{{
                                    t('boardSettings.graphMetric')
                                }}</label>
                                <div class="orb-props__metric-col">
                                    <div v-if="form.graph_metric.length" class="orb-props__chips">
                                        <span
                                            v-for="m in form.graph_metric"
                                            :key="m"
                                            class="orb-props__chip"
                                        >
                                            {{ metricIdToTitle[m] ?? m }}
                                            <button
                                                class="orb-props__chip-remove"
                                                @click="
                                                    form.graph_metric = form.graph_metric.filter(
                                                        (x) => x !== m,
                                                    )
                                                "
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
                                                        !form.graph_metric.includes(
                                                            metricTitleToId.get(title) ?? title,
                                                        ),
                                                )
                                            "
                                            :placeholder="t('boardSettings.graphMetricAdd')"
                                            :empty-text="
                                                metricSuggestions.length === 0
                                                    ? t('boardSettings.noMetrics')
                                                    : ''
                                            "
                                            class="orb-props__full"
                                            @change="addMetric"
                                        />
                                    </div>
                                </div>
                            </div>
                            <div
                                v-if="graphSource === 'template' && graphTemplates.length"
                                class="field-row"
                            >
                                <label class="field-label">{{
                                    t('boardSettings.graphTemplate')
                                }}</label>
                                <CmkDropdown
                                    class="orb-props__grow"
                                    :selected-option="form.graph_id ?? null"
                                    :options="{
                                        type: 'fixed',
                                        suggestions: [
                                            { name: null, title: '—' },
                                            ...graphTemplates.map((tpl) => ({
                                                name: tpl.id,
                                                title: tpl.title,
                                            })),
                                        ],
                                    }"
                                    label=""
                                    @update:selected-option="
                                        (v) => {
                                            form.graph_id = v || null;
                                        }
                                    "
                                />
                            </div>
                            <div class="field-row">
                                <label class="field-label">{{
                                    t('boardSettings.graphTimeWindow')
                                }}</label>
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
                                            { name: '10080', title: '7 d' },
                                        ],
                                    }"
                                    label=""
                                    @update:selected-option="
                                        (v) => {
                                            form.graph_time_window = Number(v);
                                        }
                                    "
                                />
                            </div>
                        </div>
                    </section>

                    <!-- === GRAPH: URL Embed === -->
                    <section v-if="object.type === 'graph'">
                        <p class="orb-section-title">{{ t('boardSettings.graphUrlEmbed') }}</p>
                        <div class="orb-props__fields">
                            <div class="field-row">
                                <label class="field-label">{{ t('boardSettings.graphUrl') }}</label>
                                <CmkInput
                                    v-model="form.graph_url"
                                    placeholder="https://… (optional)"
                                    field-size="FILL"
                                    class="orb-props__grow"
                                />
                            </div>
                            <div class="field-row">
                                <label class="field-label">{{
                                    t('boardSettings.graphEmbedType')
                                }}</label>
                                <CmkDropdown
                                    class="orb-props__grow"
                                    :selected-option="form.graph_embed_type || null"
                                    :options="{
                                        type: 'fixed',
                                        suggestions: [
                                            {
                                                name: 'img',
                                                title: t('boardSettings.graphEmbedImg'),
                                            },
                                            {
                                                name: 'iframe',
                                                title: t('boardSettings.graphEmbedIframe'),
                                            },
                                        ],
                                    }"
                                    label=""
                                    @update:selected-option="
                                        form.graph_embed_type = ($event ??
                                            '') as typeof form.graph_embed_type
                                    "
                                />
                            </div>
                            <div class="orb-props__grid-2">
                                <div class="field-row">
                                    <label class="field-label">{{
                                        t('boardSettings.width')
                                    }}</label>
                                    <NumberInput
                                        v-model="form.graph_width"
                                        min="50"
                                        class="orb-props__grow"
                                    />
                                </div>
                                <div class="field-row">
                                    <label class="field-label">{{
                                        t('boardSettings.height')
                                    }}</label>
                                    <NumberInput
                                        v-model="form.graph_height"
                                        min="30"
                                        class="orb-props__grow"
                                    />
                                </div>
                            </div>
                            <div class="field-row">
                                <label class="field-label">{{
                                    t('boardSettings.graphRefresh')
                                }}</label>
                                <div class="orb-props__inline orb-props__grow">
                                    <NumberInput
                                        v-model="form.graph_refresh_interval"
                                        min="0"
                                        class="orb-props__grow"
                                    />
                                    <span class="orb-props__inline-label">{{
                                        t('boardSettings.graphRefreshOff')
                                    }}</span>
                                </div>
                            </div>
                        </div>
                    </section>

                    <!-- === LINE CONFIG === -->
                    <section v-if="object.type === 'line'">
                        <p class="orb-section-title">{{ t('boardSettings.monitoringObject') }}</p>
                        <div class="orb-props__fields">
                            <div class="field-row">
                                <label class="field-label">{{ t('boardSettings.hostname') }}</label>
                                <AutocompleteInput
                                    v-model="form.host_name"
                                    :suggestions="hosts"
                                    :loading="loadingHosts"
                                    placeholder="hostname"
                                    :empty-text="t('boardSettings.noHosts')"
                                    class="orb-props__grow"
                                />
                            </div>
                            <div class="field-row">
                                <label class="field-label">{{
                                    t('boardSettings.typeService')
                                }}</label>
                                <AutocompleteInput
                                    v-model="form.service_description"
                                    :suggestions="services"
                                    :loading="loadingServices"
                                    placeholder="service description (optional)"
                                    :empty-text="
                                        form.host_name && !loadingServices
                                            ? t('boardSettings.noServices')
                                            : ''
                                    "
                                    class="orb-props__grow"
                                />
                            </div>
                        </div>
                    </section>
                    <section v-if="object.type === 'line'">
                        <p class="orb-section-title">{{ t('boardSettings.lineSection') }}</p>
                        <div class="orb-props__fields">
                            <div class="field-row">
                                <label class="field-label">{{ t('boardSettings.z') }}</label>
                                <NumberInput
                                    v-model="form.z"
                                    min="0"
                                    max="999"
                                    class="orb-props__grow"
                                />
                            </div>
                            <div class="field-row">
                                <label class="field-label">{{
                                    t('boardSettings.lineStyle')
                                }}</label>
                                <CmkDropdown
                                    class="orb-props__grow"
                                    :selected-option="form.line_style ?? null"
                                    :options="lineStyleOpts"
                                    label=""
                                    @update:selected-option="
                                        (v) => {
                                            form.line_style = v || null;
                                        }
                                    "
                                />
                            </div>
                            <!-- Perfdata label mode (none / percent / bandwidth / both) -->
                            <div class="field-row">
                                <label class="field-label">{{
                                    t('boardSettings.linePerfdataLabel')
                                }}</label>
                                <CmkDropdown
                                    class="orb-props__grow"
                                    :selected-option="form.line_perfdata_label ?? 'none'"
                                    :options="linePerfdataLabelOpts"
                                    label=""
                                    @update:selected-option="
                                        (v) => {
                                            form.line_perfdata_label =
                                                (v as LinePerfdataLabel) || 'none';
                                        }
                                    "
                                />
                            </div>
                            <!-- Weather-color toggle -->
                            <div class="field-row">
                                <CmkCheckbox
                                    v-model="form.line_weather_color"
                                    :label="t('boardSettings.lineWeatherColor')"
                                />
                            </div>
                            <!-- Weathermap inbound metric (rendered left of the midpoint) -->
                            <div
                                v-if="
                                    form.line_perfdata_label !== 'none' || form.line_weather_color
                                "
                                class="field-row"
                            >
                                <label class="field-label">{{ t('boardSettings.metricIn') }}</label>
                                <AutocompleteInput
                                    v-model="form.weathermap_metric"
                                    :suggestions="metricSuggestions"
                                    :placeholder="t('boardSettings.firstMetric')"
                                    :empty-text="
                                        metricSuggestions.length === 0
                                            ? t('boardSettings.noMetrics')
                                            : ''
                                    "
                                    class="orb-props__grow"
                                />
                            </div>
                            <!-- Weathermap outbound metric (optional; right of the midpoint,
                                 drives the second gradient colour + label). Only offered once an
                                 inbound metric is set — out-only would colour the in-half from an
                                 arbitrary first perfdata metric. -->
                            <div
                                v-if="
                                    (form.line_perfdata_label !== 'none' ||
                                        form.line_weather_color) &&
                                    !!form.weathermap_metric
                                "
                                class="field-row"
                            >
                                <label class="field-label">{{
                                    t('boardSettings.metricOut')
                                }}</label>
                                <AutocompleteInput
                                    v-model="form.weathermap_metric_out"
                                    :suggestions="metricSuggestions"
                                    :placeholder="t('boardSettings.secondMetric')"
                                    :empty-text="
                                        metricSuggestions.length === 0
                                            ? t('boardSettings.noMetrics')
                                            : ''
                                    "
                                    class="orb-props__grow"
                                />
                            </div>
                            <div class="orb-props__grid-2">
                                <!-- Line/Border color are ignored once weather coloring
                                     drives the stroke (the renderer pulls wmColor and
                                     skips the border altogether), so hide them to keep
                                     the dialog honest about what actually takes effect. -->
                                <div
                                    v-if="!form.line_weather_color"
                                    class="field-row orb-props__span-2"
                                >
                                    <label class="field-label">{{
                                        t('boardSettings.lineColor')
                                    }}</label>
                                    <ColorInput
                                        v-model="form.line_color"
                                        :enable-label="t('common.useColor')"
                                        default-color="#ffffff"
                                    />
                                </div>
                                <div
                                    v-if="!form.line_weather_color"
                                    class="field-row orb-props__span-2"
                                >
                                    <label class="field-label">{{
                                        t('boardSettings.lineColorBorder')
                                    }}</label>
                                    <ColorInput
                                        v-model="form.line_color_border"
                                        :enable-label="t('common.useColor')"
                                        default-color="#000000"
                                    />
                                </div>
                                <div class="field-row orb-props__span-2">
                                    <label class="field-label">{{
                                        t('boardSettings.lineWidth')
                                    }}</label>
                                    <NumberInput
                                        v-model="form.line_width"
                                        :min="1"
                                        :max="20"
                                        :placeholder="t('boardSettings.lineWidthDefault')"
                                        class="orb-props__grow"
                                    />
                                </div>
                                <template v-if="mapType !== 'worldmap'">
                                    <div class="field-row">
                                        <label class="field-label">{{
                                            t('boardSettings.startX')
                                        }}</label>
                                        <NumberInput
                                            v-model="form.x"
                                            min="0"
                                            max="10000"
                                            class="orb-props__grow"
                                        />
                                    </div>
                                    <div class="field-row">
                                        <label class="field-label">{{
                                            t('boardSettings.y')
                                        }}</label>
                                        <NumberInput
                                            v-model="form.y"
                                            min="0"
                                            max="10000"
                                            class="orb-props__grow"
                                        />
                                    </div>
                                    <div class="field-row">
                                        <label class="field-label">{{
                                            t('boardSettings.endX')
                                        }}</label>
                                        <NumberInput
                                            v-model="form.x2"
                                            min="0"
                                            max="10000"
                                            class="orb-props__grow"
                                        />
                                    </div>
                                    <div class="field-row">
                                        <label class="field-label">{{
                                            t('boardSettings.y')
                                        }}</label>
                                        <NumberInput
                                            v-model="form.y2"
                                            min="0"
                                            max="10000"
                                            class="orb-props__grow"
                                        />
                                    </div>
                                </template>
                            </div>
                            <!-- Label -->
                            <div class="field-row">
                                <label class="field-label">{{
                                    t('boardSettings.showLabel')
                                }}</label>
                                <CmkCheckbox v-model="form.label.show" />
                            </div>
                            <div v-if="form.label.show" class="field-row">
                                <label class="field-label">{{
                                    t('boardSettings.lineLabel')
                                }}</label>
                                <CmkInput
                                    v-model="form.label.text"
                                    field-size="FILL"
                                    class="orb-props__grow"
                                />
                            </div>
                        </div>
                    </section>

                    <!-- === POSITION === -->
                    <section v-if="object.type !== 'line'">
                        <p class="orb-section-title">{{ t('boardSettings.position') }}</p>
                        <div class="orb-props__grid-3">
                            <template v-if="mapType === 'worldmap'">
                                <div class="orb-props__inline">
                                    <label class="orb-props__inline-label">{{
                                        t('boardSettings.lat')
                                    }}</label>
                                    <NumberInput
                                        v-model="form.lat"
                                        step="any"
                                        class="orb-props__grow"
                                    />
                                </div>
                                <div class="orb-props__inline">
                                    <label class="orb-props__inline-label">{{
                                        t('boardSettings.lng')
                                    }}</label>
                                    <NumberInput
                                        v-model="form.lng"
                                        step="any"
                                        class="orb-props__grow"
                                    />
                                </div>
                            </template>
                            <template v-else>
                                <div class="orb-props__inline">
                                    <label class="orb-props__inline-label">{{
                                        t('boardSettings.x')
                                    }}</label>
                                    <NumberInput
                                        v-model="form.x"
                                        min="0"
                                        max="10000"
                                        class="orb-props__grow"
                                    />
                                </div>
                                <div class="orb-props__inline">
                                    <label class="orb-props__inline-label">{{
                                        t('boardSettings.y')
                                    }}</label>
                                    <NumberInput
                                        v-model="form.y"
                                        min="0"
                                        max="10000"
                                        class="orb-props__grow"
                                    />
                                </div>
                            </template>
                            <div class="orb-props__inline">
                                <label class="orb-props__inline-label">{{
                                    t('boardSettings.z')
                                }}</label>
                                <NumberInput
                                    v-model="form.z"
                                    min="1"
                                    max="999"
                                    class="orb-props__grow"
                                />
                            </div>
                        </div>
                    </section>

                    <!-- === LABEL === -->
                    <section v-if="object.type !== 'line'">
                        <p class="orb-section-title">{{ t('boardSettings.label') }}</p>
                        <div class="orb-props__fields">
                            <div class="field-row">
                                <label class="field-label">{{
                                    t('boardSettings.showLabel')
                                }}</label>
                                <CmkCheckbox v-model="form.label.show" />
                            </div>
                            <div :class="!form.label.show ? 'orb-props__disabled' : ''">
                                <div class="orb-props__fields">
                                    <div v-if="object.type !== 'textbox'" class="field-row">
                                        <label class="field-label">{{
                                            t('boardSettings.labelText')
                                        }}</label>
                                        <CmkInput
                                            v-model="form.label.text"
                                            placeholder="(auto from object)"
                                            field-size="FILL"
                                            class="orb-props__grow"
                                        />
                                    </div>
                                    <div class="orb-props__grid-2">
                                        <div class="field-row">
                                            <label class="field-label">{{
                                                t('boardSettings.size')
                                            }}</label>
                                            <NumberInput
                                                v-model="form.label.size"
                                                min="8"
                                                max="72"
                                                class="orb-props__grow"
                                            />
                                        </div>
                                        <div class="field-row orb-props__span-2">
                                            <label class="field-label">{{
                                                t('boardSettings.color')
                                            }}</label>
                                            <ColorInput
                                                v-model="form.label.color"
                                                default-color="#ffffff"
                                            />
                                        </div>
                                        <div class="field-row">
                                            <label class="field-label">{{
                                                t('boardSettings.offsetX')
                                            }}</label>
                                            <NumberInput
                                                v-model="form.label.x"
                                                class="orb-props__grow"
                                            />
                                        </div>
                                        <div class="field-row">
                                            <label class="field-label">{{
                                                t('boardSettings.offsetY')
                                            }}</label>
                                            <NumberInput
                                                v-model="form.label.y"
                                                class="orb-props__grow"
                                            />
                                        </div>
                                        <div class="orb-props__span-2">
                                            <button
                                                type="button"
                                                class="orb-props__toggle"
                                                @click="showLabelAdvanced = !showLabelAdvanced"
                                            >
                                                <p
                                                    class="orb-section-title orb-section-title--flush"
                                                >
                                                    {{ t('boardSettings.labelAdvanced') }}
                                                </p>
                                                <svg
                                                    class="orb-props__chevron"
                                                    :class="
                                                        showLabelAdvanced
                                                            ? ''
                                                            : 'orb-props__chevron--collapsed'
                                                    "
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
                                                <label class="field-label">{{
                                                    t('boardSettings.background')
                                                }}</label>
                                                <ColorInput
                                                    v-model="form.label.background"
                                                    :enable-label="t('common.useColor')"
                                                    none-value="transparent"
                                                    default-color="#000000"
                                                />
                                            </div>
                                            <div class="field-row orb-props__span-2">
                                                <label class="field-label">{{
                                                    t('boardSettings.borderColor')
                                                }}</label>
                                                <ColorInput
                                                    v-model="form.label_border"
                                                    :enable-label="t('common.useColor')"
                                                    default-color="#e5e5e5"
                                                />
                                            </div>
                                            <div class="field-row orb-props__span-2">
                                                <label class="field-label">{{
                                                    t('boardSettings.maxLength')
                                                }}</label>
                                                <NumberInput
                                                    v-model="form.label_maxlen"
                                                    min="0"
                                                    :placeholder="t('boardSettings.noLimit')"
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
                        v-if="
                            object.type !== 'line' &&
                            object.type !== 'textbox' &&
                            object.type !== 'graph'
                        "
                    >
                        <p class="orb-section-title">{{ t('boardSettings.appearance') }}</p>
                        <div class="orb-props__fields">
                            <div class="field-row">
                                <label class="field-label">{{ t('boardSettings.viewType') }}</label>
                                <CmkDropdown
                                    class="orb-props__grow"
                                    :selected-option="form.display.mode || null"
                                    :options="displayModeOptions"
                                    label=""
                                    @update:selected-option="
                                        form.display.mode = ($event ??
                                            '') as typeof form.display.mode
                                    "
                                />
                            </div>
                            <div class="field-row">
                                <label class="field-label">{{ t('boardSettings.size') }}</label>
                                <NumberInput
                                    v-model="form.display.image_size"
                                    min="1"
                                    max="512"
                                    :placeholder="
                                        form.display.mode === 'gadget'
                                            ? String(GADGET_DEFAULT_SIZE)
                                            : boardIconSize != null
                                              ? String(boardIconSize)
                                              : t('boardSettings.mapDefault')
                                    "
                                    class="orb-props__size-input"
                                />
                            </div>
                            <template v-if="form.display.mode === 'gadget'">
                                <div class="field-row">
                                    <label class="field-label">{{
                                        t('boardSettings.gadgetType')
                                    }}</label>
                                    <CmkDropdown
                                        class="orb-props__grow"
                                        :selected-option="form.display.gadget_type || null"
                                        :options="gadgetTypeOptions"
                                        label=""
                                        @update:selected-option="
                                            form.display.gadget_type = $event ?? ''
                                        "
                                    />
                                </div>
                                <div class="field-row">
                                    <label class="field-label">{{
                                        t('boardSettings.metric')
                                    }}</label>
                                    <AutocompleteInput
                                        v-model="form.display.gadget_metric"
                                        :suggestions="metricSuggestions"
                                        :placeholder="t('boardSettings.firstMetric')"
                                        :empty-text="
                                            metricSuggestions.length === 0
                                                ? t('boardSettings.noMetrics')
                                                : ''
                                        "
                                        class="orb-props__grow"
                                    />
                                </div>
                            </template>
                            <div
                                v-if="form.display.mode !== 'gadget'"
                                class="field-row field-row--start"
                            >
                                <label class="field-label" style="margin-top: 6px">{{
                                    t('boardSettings.customIcon')
                                }}</label>
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
                                {{ t('boardSettings.link') }}
                            </p>
                            <span v-if="form.url" class="orb-props__url-preview">{{
                                form.url
                            }}</span>
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
                                <label class="field-label field-label--offset-8">{{
                                    t('boardSettings.url')
                                }}</label>
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
                                        {{ t('boardSettings.urlAutoHint') }} →
                                    </button>
                                </div>
                            </div>
                            <div class="field-row">
                                <label class="field-label">{{ t('boardSettings.target') }}</label>
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
                    <section
                        v-if="['host', 'hostgroup', 'servicegroup', 'map'].includes(object.type)"
                    >
                        <button
                            type="button"
                            class="orb-props__toggle orb-props__toggle--spaced"
                            @click="showFilter = !showFilter"
                        >
                            <p class="orb-section-title orb-section-title--flush">
                                {{ t('boardSettings.filterSection') }}
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
                                <label class="field-label">{{
                                    t('boardSettings.excludeMembers')
                                }}</label>
                                <CmkInput
                                    v-model="form.exclude_members"
                                    :placeholder="t('boardSettings.regexPlaceholder')"
                                    field-size="FILL"
                                    class="orb-props__grow"
                                />
                            </div>
                            <div class="field-row">
                                <label class="field-label">{{
                                    t('boardSettings.excludeStates')
                                }}</label>
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
                                {{ t('boardSettings.excludeHint') }}
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
                                {{ t('boardSettings.templates') }}
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
                                <label class="field-label">{{ t('board.hoverTemplate') }}</label>
                                <CmkInput
                                    v-model="form.hover_template"
                                    :placeholder="t('board.templatePlaceholder')"
                                    field-size="FILL"
                                    class="orb-props__grow"
                                />
                            </div>
                            <div class="field-row">
                                <label class="field-label">{{ t('boardSettings.hoverUrl') }}</label>
                                <CmkInput
                                    v-model="form.hover_url"
                                    placeholder="https://…"
                                    field-size="FILL"
                                    class="orb-props__grow"
                                />
                            </div>
                            <div class="field-row">
                                <label class="field-label">{{ t('board.contextTemplate') }}</label>
                                <CmkInput
                                    v-model="form.context_template"
                                    :placeholder="t('board.templatePlaceholder')"
                                    field-size="FILL"
                                    class="orb-props__grow"
                                />
                            </div>
                            <p class="orb-props__field-hint">
                                {{ t('board.templateHint') }}
                            </p>
                        </div>
                    </section>
                </CmkScrollContainer>

                <!-- Footer -->
                <div class="orb-props__footer">
                    <div>
                        <CmkButton variant="danger" @click="confirmDelete = true">{{
                            t('common.delete')
                        }}</CmkButton>
                        <OrbConfirmDialog
                            :open="confirmDelete"
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
                    <div class="orb-props__footer-actions">
                        <p v-if="saveError" class="orb-props__error">
                            {{ saveError }}
                        </p>
                        <CmkButton variant="secondary" @click="$emit('close')">{{
                            t('common.cancel')
                        }}</CmkButton>
                        <CmkButton variant="primary" :disabled="saving" @click="save">
                            {{ saving ? t('common.saving') : t('common.save') }}
                        </CmkButton>
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
import CmkButton from '@/components/cmk/CmkButton';
import CmkDropdown from '@/components/cmk/CmkDropdown/CmkDropdown';
import CmkScrollContainer from '@/components/cmk/CmkScrollContainer';
import CmkCheckbox from '@/components/cmk/user-input/CmkCheckbox';
import CmkInput from '@/components/cmk/user-input/CmkInput';
import ColorInput from '@/components/ColorInput.vue';
import NumberInput from '@/components/NumberInput.vue';
import OrbConfirmDialog from '@/components/OrbConfirmDialog.vue';
import { useEscapeClose } from '@/composables/useEscapeClose';
import { useAuthStore } from '@/stores/auth';
import { useStatesStore } from '@/stores/states';
import type {
    AggregationNode,
    BoardObject,
    LinePerfdataLabel,
    MetricGraphGroup,
    ObjectState,
} from '@/types/api';
import {
    aggregationLeafId,
    BI_STATE_LABEL,
    flattenAggregationLeaves,
} from '@/utils/aggregationTree';
import { linePerfdataLabelOptions, lineStyleOptions } from '@/utils/dropdownOptions';
import { GADGET_DEFAULT_SIZE } from '@/utils/gadget';
import { getBoardObjectIdentifier } from '@/utils/naming';
import { parsePerfData } from '@/utils/perf';
import { compileRegex } from '@/utils/regex';

import AutocompleteInput from './AutocompleteInput.vue';
import ImagePicker from './ImagePicker.vue';

const { t } = useI18n();

const props = defineProps<{
    object: BoardObject;
    state?: ObjectState | undefined;
    connectionId: string;
    mapType?: string | undefined;
    boardIconSize?: number | null;
    boardDefaultZ?: number;
    checkmkUrl?: string | null;
    anchorRect?: { left: number; top: number; right: number; bottom: number } | null;
}>();

const emit = defineEmits<{
    close: [];
    save: [updates: Record<string, unknown>];
    delete: [];
}>();
useEscapeClose(() => emit('close'));

const auth = useAuthStore();
const statesStore = useStatesStore();

// Auto-derived Checkmk URL for the current object (used as placeholder / hint in the URL field)
const autoUrl = computed((): string | null => {
    const base = props.checkmkUrl?.replace(/\/check_mk\/?$/, '').replace(/\/$/, '');
    if (!base) return null;
    const p: Record<string, string> = {};
    if (props.state?.site_id) p.site = props.state.site_id;
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

// Drag-to-move (grab the header)
const dragOffset = ref({ dx: 0, dy: 0 });
const dragStart = ref<{ px: number; py: number; ox: number; oy: number } | null>(null);
const dragging = ref(false);

const cardStyle = computed<Record<string, string>>(() => {
    const base: Record<string, string> = isPopover.value
        ? { ...(popoverStyle.value as Record<string, string>) }
        : {};
    if (dragOffset.value.dx !== 0 || dragOffset.value.dy !== 0) {
        base.transform = `translate(${dragOffset.value.dx}px, ${dragOffset.value.dy}px)`;
    }
    return base;
});

function onHeaderPointerDown(e: PointerEvent) {
    if (e.button !== 0) return;
    // Don't start a drag from interactive children (the close button etc.).
    if ((e.target as HTMLElement).closest('button')) return;
    dragStart.value = {
        px: e.clientX,
        py: e.clientY,
        ox: dragOffset.value.dx,
        oy: dragOffset.value.dy,
    };
}

function onHeaderPointerMove(e: PointerEvent) {
    const s = dragStart.value;
    if (!s) return;
    const dx = s.ox + (e.clientX - s.px);
    const dy = s.oy + (e.clientY - s.py);
    if (!dragging.value && Math.abs(dx - s.ox) < 4 && Math.abs(dy - s.oy) < 4) {
        return; // below threshold: don't engage drag yet (preserves click on header)
    }
    if (!dragging.value) {
        dragging.value = true;
        const target = e.currentTarget as HTMLElement;
        try {
            target.setPointerCapture(e.pointerId);
        } catch {
            // pointer may have ended
        }
    }
    dragOffset.value = { dx, dy };
}

function onHeaderPointerUp() {
    dragStart.value = null;
    dragging.value = false;
}

watch(
    () => props.object,
    () => {
        dragOffset.value = { dx: 0, dy: 0 };
        dragStart.value = null;
    },
);

const fetchedMetrics = ref<string[]>([]);
const graphTemplates = ref<MetricGraphGroup[]>([]);
const boardNames = ref<string[]>([]);
const boardLabels = ref<string[]>([]);

const lineStyleOpts = computed(() => ({
    type: 'fixed' as const,
    suggestions: lineStyleOptions(t),
}));
const linePerfdataLabelOpts = computed(() => ({
    type: 'fixed' as const,
    suggestions: linePerfdataLabelOptions(t),
}));
const displayModeOptions = computed(() => ({
    type: 'fixed' as const,
    suggestions: [
        { name: 'icon', title: t('boardSettings.viewTypeIcon') },
        { name: 'text', title: t('boardSettings.viewTypeText') },
        { name: 'gadget', title: t('boardSettings.viewTypeGadget') },
    ],
}));
const gadgetTypeOptions = computed(() => ({
    type: 'fixed' as const,
    suggestions: [
        { name: 'gauge', title: t('boardSettings.gadgetGauge') },
        { name: 'bar', title: t('boardSettings.gadgetBar') },
        { name: 'trafficlight', title: t('boardSettings.gadgetTrafficlight') },
    ],
}));
const urlTargetOptions = computed(() => ({
    type: 'fixed' as const,
    suggestions: [
        { name: '_blank', title: t('boardSettings.targetNewTab') + ' (_blank)' },
        { name: '_self', title: t('boardSettings.targetSameTab') + ' (_self)' },
        { name: '_top', title: t('boardSettings.targetTopFrame') + ' (_top)' },
    ],
}));

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

// Autocomplete loads degrade to an empty list when the API errors; log the
// reason so an empty dropdown is diagnosable instead of looking like "no data".
function logLoadError(what: string): (e: unknown) => never[] {
    return (e) => {
        console.warn(`[OrbVis] Failed to load ${what}:`, e);
        return [];
    };
}

async function fetchMetrics(host: string, service?: string) {
    if (!props.connectionId || !host) return;
    fetchedMetrics.value = await connectionsApi
        .perfMetrics(props.connectionId, host, auth.accessToken!, service || undefined)
        .catch(logLoadError('metrics'));
}

async function fetchGraphTemplates(host: string, service?: string) {
    if (!props.connectionId || !host || props.object.type !== 'graph') return;
    graphTemplates.value = await connectionsApi
        .graphTemplates(props.connectionId, host, service ?? null, auth.accessToken!)
        .catch(logLoadError('graph templates'));
}

async function fetchBoardNames() {
    if (props.object.type !== 'map' || !auth.accessToken) return;
    const boards = await boardsApi.list(auth.accessToken).catch(logLoadError('board names'));
    boardNames.value = boards.map((b) => b.name);
    boardLabels.value = boards.map((b) => b.alias || b.name);
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
        form.connection_id = obj.connection_id ?? '';
        form.host_name = obj.host_name ?? '';
        form.service_description = obj.service_description ?? '';
        form.group_name = obj.group_name ?? '';
        form.map_name = obj.map_name ?? '';
        form.aggregation_id = obj.aggregation_id ?? '';
        form.object_types = obj.object_types ?? 'host';
        form.object_filter = obj.object_filter ?? '';
        form.expand_depth = obj.expand_depth ?? 0;
        form.line_style = obj.line_style ?? null;
        form.line_color = obj.line_color ?? null;
        form.line_color_border = obj.line_color_border ?? null;
        form.line_width = obj.line_width ?? null;
        form.line_perfdata_label = obj.line_perfdata_label ?? 'none';
        form.line_weather_color = obj.line_weather_color ?? false;
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
        form.weathermap_metric_out = obj.weathermap_metric_out ?? '';
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
        form.z = obj.z ?? props.boardDefaultZ ?? 1;
        form.x2 = obj.x2 ?? obj.x + 150;
        form.y2 = obj.y2 ?? obj.y;
        showLabelAdvanced.value = false;
        showTemplates.value = !!(obj.hover_template || obj.context_template || obj.hover_url);
        showFilter.value = !!(obj.exclude_members || obj.exclude_member_states);
    },
    { immediate: true },
);

// ---- Autocomplete ----

const availableConnections = ref<{ id: string; label: string }[]>([]);
const connectionDropdownOptions = computed(() => ({
    type: 'fixed' as const,
    suggestions: [
        { name: '', title: t('boardSettings.connectionInherit') },
        ...availableConnections.value.map((c) => ({ name: c.id, title: c.label })),
    ],
}));
async function loadConnections(): Promise<void> {
    if (!auth.accessToken) return;
    try {
        const all = await connectionsApi.list(auth.accessToken);
        availableConnections.value = all.map((c) => ({ id: c.id, label: c.label || c.id }));
    } catch {
        availableConnections.value = [];
    }
}
loadConnections();

// Refetch host/service suggestions whenever the operator switches the
// per-object connection — otherwise the dropdown stays bound to the board's
// default backend and the override is invisible until they save+reopen.
watch(
    () => form.connection_id,
    () => loadAutocomplete(),
);

const hosts = ref<string[]>([]);
const services = ref<string[]>([]);
const groups = ref<string[]>([]);
const aggregationIds = ref<string[]>([]);
const aggregationLabels = ref<string[]>([]);
const loadingHosts = ref(false);
const loadingServices = ref(false);
const loadingGroups = ref(false);
const loadingAggregations = ref(false);

async function loadAutocomplete() {
    // Per-object connection override wins; fall back to the board default.
    const cid = form.connection_id || props.connectionId;
    if (!cid) return;
    const type = props.object.type;
    if (type === 'host' || type === 'service' || type === 'line' || type === 'graph') {
        loadingHosts.value = true;
        hosts.value = await connectionsApi
            .objects(cid, 'host', auth.accessToken!)
            .catch(logLoadError('hosts'));
        loadingHosts.value = false;
        if ((type === 'service' || type === 'line' || type === 'graph') && form.host_name) {
            loadingServices.value = true;
            services.value = await connectionsApi
                .objects(cid, 'service', auth.accessToken!, form.host_name)
                .catch(logLoadError('services'));
            loadingServices.value = false;
        }
    } else if (type === 'hostgroup') {
        loadingGroups.value = true;
        groups.value = await connectionsApi
            .objects(cid, 'hostgroup', auth.accessToken!)
            .catch(logLoadError('host groups'));
        loadingGroups.value = false;
    } else if (type === 'servicegroup') {
        loadingGroups.value = true;
        groups.value = await connectionsApi
            .objects(cid, 'servicegroup', auth.accessToken!)
            .catch(logLoadError('service groups'));
        loadingGroups.value = false;
    } else if (type === 'aggregation') {
        loadingAggregations.value = true;
        const aggrs = await connectionsApi
            .aggregations(cid, auth.accessToken!)
            .catch(logLoadError('aggregations'));
        aggregationIds.value = aggrs.map((a) => a.id);
        aggregationLabels.value = aggrs.map((a) => a.title || a.id);
        loadingAggregations.value = false;
    }
}

loadAutocomplete();

// ── exclude_members suppression-count preview ─────────────────────────
// Cache the live tree once we know the aggregation id; the suppression
// count then re-computes locally as the operator types the regex without
// hitting the backend on every keystroke.
const excludeMembersTree = ref<AggregationNode | null>(null);

watch(
    () => [form.aggregation_id, props.connectionId] as const,
    async ([aggId, cid]) => {
        if (!aggId || !cid || !auth.accessToken) {
            excludeMembersTree.value = null;
            return;
        }
        try {
            // Fixed depth=10 = the API cap; "every leaf" guarantees the
            // count reflects the full aggregation, not just the
            // currently-displayed subtree.
            const result = await connectionsApi.aggregationTree(cid, aggId, 10, auth.accessToken);
            excludeMembersTree.value = result.tree;
        } catch {
            excludeMembersTree.value = null;
        }
    },
    { immediate: true },
);

const excludeMembersFeedback = computed<{ text: string; tone: string } | null>(() => {
    const tree = excludeMembersTree.value;
    if (!tree) return null;
    const memberRe = (form.exclude_members || '').trim();
    const stateList = (form.exclude_member_states || '')
        .split(',')
        .map((s) => s.trim().toUpperCase())
        .filter(Boolean);
    if (!memberRe && stateList.length === 0) return null;

    let regex: RegExp | null = null;
    if (memberRe) {
        try {
            // Pattern is operator-typed and only used to test against the
            // already-fetched leaves array — no server round-trip and no
            // unbounded input source. compileRegex centralises the eslint
            // tradeoff for security/detect-non-literal-regexp so we can
            // keep using the standard linter elsewhere.
            regex = compileRegex(memberRe);
        } catch {
            return {
                text: t('boardSettings.excludeRegexInvalid'),
                tone: 'orb-props__feedback--invalid',
            };
        }
    }

    const leaves = flattenAggregationLeaves(tree);
    const total = leaves.length;
    let suppressed = 0;
    for (const l of leaves) {
        const key = aggregationLeafId(l);
        const matchesMember = regex ? regex.test(key) : true;
        const matchesState = stateList.length
            ? stateList.includes(BI_STATE_LABEL[l.state] ?? '')
            : true;
        // exclude when BOTH (or only-defined) filters match the leaf.
        const memberApplies = !!regex;
        const stateApplies = stateList.length > 0;
        if (
            (memberApplies && stateApplies && matchesMember && matchesState) ||
            (memberApplies && !stateApplies && matchesMember) ||
            (!memberApplies && stateApplies && matchesState)
        ) {
            suppressed += 1;
        }
    }

    if (suppressed === 0) {
        return {
            text: t('boardSettings.excludeNoMatches', { total }),
            tone: 'orb-props__feedback--muted',
        };
    }
    if (suppressed >= total) {
        return {
            text: t('boardSettings.excludeAllMatched', { count: suppressed, total }),
            tone: 'orb-props__feedback--warn',
        };
    }
    return {
        text: t('boardSettings.excludeMatched', { count: suppressed, total }),
        tone: 'orb-props__feedback--matched',
    };
});

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
                .objects(props.connectionId, 'service', auth.accessToken!, host)
                .catch(logLoadError('services'));
            loadingServices.value = false;
        }
    },
);

const displayName = computed(() => getBoardObjectIdentifier(props.object));

// ---- Save ----

async function save() {
    saveError.value = '';
    if (props.object.type === 'line' && form.line_weather_color && !form.weathermap_metric.trim()) {
        saveError.value = t('boardSettings.metricRequiredWeathermap');
        return;
    }
    saving.value = true;
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
                          gadget_type:
                              form.display.mode === 'gadget' ? form.display.gadget_type : null,
                          gadget_metric:
                              form.display.mode === 'gadget'
                                  ? form.display.gadget_metric || null
                                  : null,
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
        if (props.object.type === 'aggregation') {
            updates.aggregation_id = form.aggregation_id || null;
            updates.expand_depth = form.expand_depth ?? 0;
        }
        if (props.object.type === 'dyngroup') {
            updates.object_types = form.object_types;
            updates.object_filter = form.object_filter || null;
        }

        if (props.object.type === 'line') {
            updates.host_name = form.host_name || null;
            updates.service_description = form.service_description || null;
            // Persist the metric whenever the line shows perfdata labels or
            // uses weather-coloring — both modes need it to look up perfdata.
            if (form.line_perfdata_label !== 'none' || form.line_weather_color) {
                updates.weathermap_metric = form.weathermap_metric || null;
                // Outbound only makes sense alongside an inbound metric (it's the
                // second direction); never persist it on its own.
                updates.weathermap_metric_out =
                    (form.weathermap_metric && form.weathermap_metric_out) || null;
            }
            if (props.mapType !== 'worldmap') {
                updates.x = form.x;
                updates.y = form.y;
                updates.x2 = form.x2;
                updates.y2 = form.y2;
            }
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
