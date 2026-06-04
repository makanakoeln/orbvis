<template>
    <StatusSlideIn
        :open="!!object"
        :aria-label="displayName"
        :portal-to="portalTarget"
        @close="emit('close')"
    >
        <div
            v-if="object"
            class="detail-drawer"
            :class="`detail-drawer--${severityKind}`"
            :style="{
                '--detail-drawer-accent': state ? stateColor(state.state) : 'var(--border)',
            }"
            @click.stop
        >
            <div class="detail-drawer__severity-bar" />

            <header class="detail-drawer__header">
                <div class="detail-drawer__title">
                    <div class="detail-drawer__title-row">
                        <a
                            v-if="checkmkUrlFull"
                            :href="checkmkUrlFull"
                            target="_blank"
                            rel="noopener noreferrer"
                            class="detail-drawer__name detail-drawer__name--link"
                            :title="displayName"
                            :aria-label="t('board.detailDrawer.openInCheckmk')"
                            >{{ displayName }}</a
                        >
                        <span v-else class="detail-drawer__name" :title="displayName">{{
                            displayName
                        }}</span>
                        <span class="detail-drawer__type-pill">{{ typeLabel }}</span>
                    </div>
                    <div v-if="state" class="detail-drawer__state-line">
                        <span
                            class="detail-drawer__state-pill"
                            :style="{
                                color: stateColor(state.state),
                                borderColor: stateColor(state.state),
                                background: stateBgColor(state.state),
                            }"
                        >
                            {{ state.state }}
                        </span>
                        <span v-if="sinceText" class="detail-drawer__since-text">{{
                            sinceText
                        }}</span>
                    </div>
                </div>
                <a
                    v-if="checkmkUrlFull"
                    :href="checkmkUrlFull"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="detail-drawer__icon-btn"
                    :title="t('board.detailDrawer.openInCheckmk')"
                    :aria-label="t('board.detailDrawer.openInCheckmk')"
                >
                    <CmkIcon name="export-link" size="small" />
                </a>
                <!-- Aggregation-only: deep-link into Checkmk Setup → BI Packs.
                     Goes alongside the live-view "open in Checkmk" link so
                     the operator can jump straight to "edit the rules" when
                     the aggregation behaviour needs adjusting. -->
                <a
                    v-if="checkmkSetupUrlFull"
                    :href="checkmkSetupUrlFull"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="detail-drawer__icon-btn"
                    :title="t('board.detailDrawer.openInCheckmkSetup')"
                    :aria-label="t('board.detailDrawer.openInCheckmkSetup')"
                >
                    <CmkIcon name="main-setup" size="small" />
                </a>
                <button
                    type="button"
                    class="detail-drawer__close"
                    :title="t('board.detailDrawer.close')"
                    @click="emit('close')"
                >
                    ×
                </button>
            </header>

            <div v-if="state" class="detail-drawer__body">
                <CmkTabs v-model="activeTab" class="detail-drawer__tabs">
                    <template #tabs>
                        <CmkTab id="status">{{ t('board.detailDrawer.tabStatus') }}</CmkTab>
                        <CmkTab v-if="showPerformanceTab" id="performance">{{
                            t('board.detailDrawer.tabPerformance')
                        }}</CmkTab>
                        <CmkTab v-if="showContextTab" id="context">{{
                            t('board.detailDrawer.tabContext')
                        }}</CmkTab>
                        <CmkTab v-if="showMembersTab" id="members">
                            <span class="detail-drawer__tab-with-count">
                                {{ t('board.detailDrawer.tabMembers') }}
                                <span class="detail-drawer__tab-count">{{
                                    groupMembers.length
                                }}</span>
                            </span>
                        </CmkTab>
                        <CmkTab v-if="showActivityTab" id="activity">
                            <span class="detail-drawer__tab-with-count">
                                {{ t('board.detailDrawer.tabActivity') }}
                                <span class="detail-drawer__tab-count">{{
                                    commentList.length + downtimeList.length
                                }}</span>
                            </span>
                        </CmkTab>
                    </template>

                    <template #tab-contents>
                        <CmkTabContent id="status" spacing="none">
                            <div class="detail-drawer__pane">
                                <div v-if="modifiers.length" class="detail-drawer__badges">
                                    <span
                                        v-for="mod in modifiers"
                                        :key="mod.label"
                                        class="detail-drawer__badge"
                                        :class="`detail-drawer__badge--${mod.kind}`"
                                    >
                                        {{ mod.label }}
                                    </span>
                                </div>

                                <pre v-if="state.output" class="detail-drawer__output">{{
                                    state.output
                                }}</pre>

                                <div
                                    v-if="serviceChips.length"
                                    class="detail-drawer__chips"
                                    :style="{
                                        gridTemplateColumns: `repeat(${serviceChips.length}, 1fr)`,
                                    }"
                                >
                                    <component
                                        :is="chip.url ? 'a' : 'button'"
                                        v-for="chip in serviceChips"
                                        :key="chip.state"
                                        :type="chip.url ? undefined : 'button'"
                                        :href="chip.url || undefined"
                                        :target="chip.url ? '_blank' : undefined"
                                        :rel="chip.url ? 'noopener noreferrer' : undefined"
                                        class="detail-drawer__chip"
                                        :class="
                                            chip.count > 0
                                                ? `detail-drawer__chip--${chip.tone}`
                                                : 'detail-drawer__chip--zero'
                                        "
                                        :disabled="chip.count === 0 || !chip.url ? true : undefined"
                                    >
                                        <span class="detail-drawer__chip-count">{{
                                            chip.count
                                        }}</span>
                                        <span class="detail-drawer__chip-label">{{
                                            chip.label
                                        }}</span>
                                    </component>
                                </div>

                                <div
                                    v-if="hostChips.length"
                                    class="detail-drawer__chips"
                                    :style="{
                                        gridTemplateColumns: `repeat(${hostChips.length}, 1fr)`,
                                    }"
                                >
                                    <component
                                        :is="chip.url ? 'a' : 'button'"
                                        v-for="chip in hostChips"
                                        :key="chip.state"
                                        :type="chip.url ? undefined : 'button'"
                                        :href="chip.url || undefined"
                                        :target="chip.url ? '_blank' : undefined"
                                        :rel="chip.url ? 'noopener noreferrer' : undefined"
                                        class="detail-drawer__chip"
                                        :class="
                                            chip.count > 0
                                                ? `detail-drawer__chip--${chip.tone}`
                                                : 'detail-drawer__chip--zero'
                                        "
                                        :disabled="chip.count === 0 || !chip.url ? true : undefined"
                                    >
                                        <span class="detail-drawer__chip-count">{{
                                            chip.count
                                        }}</span>
                                        <span class="detail-drawer__chip-label">{{
                                            chip.label
                                        }}</span>
                                    </component>
                                </div>

                                <dl
                                    v-if="metaRows.length || checkInfoRows.length"
                                    class="detail-drawer__meta"
                                >
                                    <template v-for="row in metaRows" :key="row.label">
                                        <dt>{{ row.label }}</dt>
                                        <dd>
                                            <a
                                                v-if="row.href"
                                                :href="row.href"
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                class="detail-drawer__meta-link"
                                                >{{ row.value }}</a
                                            >
                                            <template v-else>{{ row.value }}</template>
                                        </dd>
                                    </template>
                                    <template v-for="row in checkInfoRows" :key="row.label">
                                        <dt>{{ row.label }}</dt>
                                        <dd
                                            :class="
                                                row.tone
                                                    ? `detail-drawer__meta-value--${row.tone}`
                                                    : ''
                                            "
                                        >
                                            {{ row.value }}
                                        </dd>
                                    </template>
                                </dl>
                                <!--
                                    BI aggregation summary: per-state leaf counts,
                                    the worst-leaf path, and a click-to-drill leaf
                                    list. Rendered only when this drawer is showing
                                    an aggregation object and the backend has
                                    materialised its tree (state.tree).
                                -->
                                <section
                                    v-if="aggregationSummary"
                                    class="detail-drawer__pane-section detail-drawer__section--aggregation"
                                >
                                    <div class="detail-drawer__section-head">
                                        <h3 class="detail-drawer__section-heading">
                                            {{ t('board.detailDrawer.aggregationSummary') }}
                                        </h3>
                                        <CmkToggleButtonGroup
                                            v-if="(object.expand_depth ?? 0) > 0"
                                            :model-value="aggregationView"
                                            :options="aggregationViewOptions"
                                            @update:model-value="setAggregationView"
                                        />
                                    </div>

                                    <div
                                        class="detail-drawer__chips"
                                        :style="{
                                            gridTemplateColumns: `repeat(${activeChips.length}, 1fr)`,
                                        }"
                                    >
                                        <button
                                            v-for="chip in activeChips"
                                            :key="chip.state"
                                            type="button"
                                            class="detail-drawer__chip"
                                            :class="
                                                chip.count > 0
                                                    ? `detail-drawer__chip--${chip.tone}`
                                                    : 'detail-drawer__chip--zero'
                                            "
                                            :disabled="chip.count === 0 ? true : undefined"
                                        >
                                            <span class="detail-drawer__chip-count">{{
                                                chip.count
                                            }}</span>
                                            <span class="detail-drawer__chip-label">{{
                                                chip.label
                                            }}</span>
                                        </button>
                                    </div>

                                    <!-- Worst-leaf path only fits the Details view; once the list
                                         is cut at a tree depth, naming a deeper leaf is misleading. -->
                                    <div
                                        v-if="
                                            aggregationView === 'details' &&
                                            aggregationSummary.worstPath
                                        "
                                        class="detail-drawer__list-text"
                                    >
                                        {{ t('board.detailDrawer.worstLeaf') }}:
                                        <span class="detail-drawer__list-strong">{{
                                            aggregationSummary.worstPath
                                        }}</span>
                                    </div>
                                    <div
                                        v-if="aggregationView === 'summary'"
                                        class="detail-drawer__list-text detail-drawer__tree-intro"
                                    >
                                        {{
                                            t('board.detailDrawer.aggregationTreeIntro', {
                                                count: aggregationSummary.treeRows.length,
                                                depth: aggregationSummary.treeDepth,
                                            })
                                        }}
                                    </div>
                                    <!--
                                        Stale-data hint: livestatus to a federated
                                        site went dead since the tree was fetched,
                                        so the per-leaf states the operator sees
                                        may not reflect reality. Surfacing this
                                        explicitly avoids misreading "1 CRIT"
                                        as fresh.
                                    -->
                                    <div
                                        v-if="state.stale"
                                        class="detail-drawer__list-text detail-drawer__stale-hint"
                                    >
                                        ⚠ {{ t('board.detailDrawer.aggregationStale') }}
                                    </div>
                                    <!-- Bulk-ack always targets real bi_leaf hosts/services —
                                         that's what Checkmk's command pipeline accepts. -->
                                    <button
                                        v-if="
                                            aggregationProblemLeaves.length &&
                                            canCommand('acknowledge')
                                        "
                                        type="button"
                                        class="detail-drawer__action-btn"
                                        @click="onBulkAcknowledgeClick"
                                    >
                                        {{
                                            t('board.detailDrawer.bulkAcknowledge', {
                                                count: aggregationProblemLeaves.length,
                                            })
                                        }}
                                    </button>
                                    <ul
                                        v-if="aggregationListRows.length"
                                        class="detail-drawer__list"
                                    >
                                        <li
                                            v-for="row in aggregationListRows"
                                            :key="row.id"
                                            class="detail-drawer__list-row"
                                            :class="{
                                                'detail-drawer__list-row--clickable':
                                                    !!row.hostName,
                                            }"
                                            @click="onAggregationLeafClick(row)"
                                        >
                                            <span
                                                class="detail-drawer__list-dot"
                                                :class="`detail-drawer__list-dot--${row.tone}`"
                                            />
                                            <span class="detail-drawer__list-text">
                                                {{ row.label }}
                                            </span>
                                            <span class="detail-drawer__list-state">{{
                                                row.stateLabel
                                            }}</span>
                                        </li>
                                    </ul>
                                </section>
                            </div>
                        </CmkTabContent>

                        <CmkTabContent v-if="showPerformanceTab" id="performance" spacing="none">
                            <div class="detail-drawer__pane">
                                <div v-if="mainHeadline" class="detail-drawer__main-metric">
                                    <div class="detail-drawer__main-metric-head">
                                        <span class="detail-drawer__main-metric-label">{{
                                            mainHeadline.label
                                        }}</span>
                                    </div>
                                    <div
                                        class="detail-drawer__perf-bar-wrap detail-drawer__perf-bar-wrap--lg"
                                    >
                                        <div
                                            class="detail-drawer__perf-bar"
                                            :style="{
                                                width: mainHeadline.pct + '%',
                                                background: mainHeadline.color,
                                            }"
                                        />
                                        <div
                                            v-if="mainPerfRow?.warnPct !== null && mainPerfRow"
                                            class="detail-drawer__perf-mark detail-drawer__perf-mark--warn"
                                            :style="{ left: mainPerfRow.warnPct + '%' }"
                                            :title="`warn: ${mainPerfRow.warnLabel}`"
                                        />
                                        <div
                                            v-if="mainPerfRow?.critPct !== null && mainPerfRow"
                                            class="detail-drawer__perf-mark detail-drawer__perf-mark--crit"
                                            :style="{ left: mainPerfRow.critPct + '%' }"
                                            :title="`crit: ${mainPerfRow.critLabel}`"
                                        />
                                    </div>
                                    <div
                                        v-if="mainHeadline.valueLabel"
                                        class="detail-drawer__main-metric-value"
                                    >
                                        {{ mainHeadline.valueLabel }}
                                    </div>
                                </div>

                                <div v-if="mainHistoryKey" class="detail-drawer__chart-wrap">
                                    <MetricChart
                                        :data="historyData"
                                        :metric-keys="[mainHistoryKey]"
                                        :window-secs="HISTORY_MINUTES * 60"
                                        :thresholds="mainThresholds"
                                        :unit="mainMetric?.unit"
                                        :dark="isDark"
                                    />
                                </div>

                                <div
                                    v-if="longOutputRows.length"
                                    class="detail-drawer__pane-section"
                                >
                                    <div class="detail-drawer__pane-heading">
                                        {{ t('board.detailDrawer.details') }}
                                    </div>
                                    <dl class="detail-drawer__output-rows">
                                        <template v-for="(row, i) in longOutputRows" :key="i">
                                            <dt v-if="row.label">{{ row.label }}</dt>
                                            <dd>{{ row.value }}</dd>
                                        </template>
                                    </dl>
                                </div>

                                <details
                                    v-if="otherPerfRows.length"
                                    class="detail-drawer__raw-metrics"
                                >
                                    <summary>
                                        {{
                                            t('board.detailDrawer.rawMetrics', {
                                                n: otherPerfRows.length,
                                            })
                                        }}
                                    </summary>
                                    <div class="detail-drawer__perf">
                                        <div
                                            v-for="row in otherPerfRows"
                                            :key="row.label"
                                            class="detail-drawer__perf-row"
                                        >
                                            <div
                                                class="detail-drawer__perf-label"
                                                :title="row.label"
                                            >
                                                {{ row.label }}
                                            </div>
                                            <div class="detail-drawer__perf-bar-wrap">
                                                <div
                                                    class="detail-drawer__perf-bar"
                                                    :style="{
                                                        width: row.pct + '%',
                                                        background: row.color,
                                                    }"
                                                />
                                                <div
                                                    v-if="row.warnPct !== null"
                                                    class="detail-drawer__perf-mark detail-drawer__perf-mark--warn"
                                                    :style="{ left: row.warnPct + '%' }"
                                                    :title="`warn: ${row.warnLabel}`"
                                                />
                                                <div
                                                    v-if="row.critPct !== null"
                                                    class="detail-drawer__perf-mark detail-drawer__perf-mark--crit"
                                                    :style="{ left: row.critPct + '%' }"
                                                    :title="`crit: ${row.critLabel}`"
                                                />
                                            </div>
                                            <div class="detail-drawer__perf-value">
                                                {{ row.valueLabel }}
                                            </div>
                                        </div>
                                    </div>
                                </details>
                            </div>
                        </CmkTabContent>

                        <CmkTabContent v-if="showContextTab" id="context" spacing="none">
                            <div class="detail-drawer__pane">
                                <dl
                                    v-if="contextMetaRowsWithoutCheckCmd.length"
                                    class="detail-drawer__meta"
                                >
                                    <template
                                        v-for="row in contextMetaRowsWithoutCheckCmd"
                                        :key="row.label"
                                    >
                                        <dt>{{ row.label }}</dt>
                                        <dd
                                            :class="
                                                row.tone
                                                    ? `detail-drawer__meta-value--${row.tone}`
                                                    : ''
                                            "
                                        >
                                            {{ row.value }}
                                        </dd>
                                    </template>
                                </dl>

                                <div v-if="checkCommandRow">
                                    <div class="detail-drawer__pane-heading">
                                        {{ checkCommandRow.label }}
                                    </div>
                                    <CmkCode :code-txt="checkCommandRow.value" width="fill" />
                                </div>

                                <dl
                                    v-if="topologyGroups.length"
                                    class="detail-drawer__meta detail-drawer__meta--stacked"
                                >
                                    <template v-for="group in topologyGroups" :key="group.label">
                                        <dt>{{ group.label }}</dt>
                                        <dd class="detail-drawer__chip-row">
                                            <CmkChip
                                                v-for="item in group.items"
                                                :key="item"
                                                size="small"
                                                :color="group.isHostList ? 'info' : 'others'"
                                                variant="outline"
                                                :as-div="!group.isHostList || !canSelectHost(item)"
                                                @click="
                                                    group.isHostList && canSelectHost(item)
                                                        ? emit('select-host', item)
                                                        : null
                                                "
                                            >
                                                {{ item }}
                                            </CmkChip>
                                        </dd>
                                    </template>
                                </dl>

                                <div v-if="labelEntries.length">
                                    <div class="detail-drawer__pane-heading">
                                        {{ t('board.detailDrawer.labels') }}
                                    </div>
                                    <div class="detail-drawer__chip-row">
                                        <CmkChip
                                            v-for="[key, value] in labelEntries"
                                            :key="key"
                                            size="small"
                                            color="others"
                                            variant="outline"
                                            as-div
                                            :title="`${key}: ${value}`"
                                        >
                                            <template #start>
                                                <span class="detail-drawer__label-key">{{
                                                    key
                                                }}</span>
                                            </template>
                                            {{ value }}
                                        </CmkChip>
                                    </div>
                                </div>
                            </div>
                        </CmkTabContent>

                        <CmkTabContent v-if="showMembersTab" id="members" spacing="none">
                            <div class="detail-drawer__pane">
                                <!-- Health summary chips: hide zero-counts to match
                                     the Status tab's hideZeros behaviour. The OK
                                     chip stays as an anchor for "all green". -->
                                <div
                                    v-if="groupMembers.length"
                                    class="detail-drawer__chips"
                                    :style="{
                                        gridTemplateColumns: `repeat(${memberChips.length}, 1fr)`,
                                    }"
                                >
                                    <button
                                        v-for="chip in memberChips"
                                        :key="chip.label"
                                        type="button"
                                        class="detail-drawer__chip"
                                        :class="`detail-drawer__chip--${chip.tone}`"
                                        @click="onlyProblems = chip.label !== 'OK'"
                                    >
                                        <span class="detail-drawer__chip-count">{{
                                            chip.count
                                        }}</span>
                                        <span class="detail-drawer__chip-label">{{
                                            chip.label
                                        }}</span>
                                    </button>
                                </div>

                                <div class="detail-drawer__member-controls">
                                    <input
                                        v-model="memberSearch"
                                        type="search"
                                        :placeholder="t('board.detailDrawer.memberSearch')"
                                        class="detail-drawer__member-search"
                                    />
                                    <CmkCheckbox
                                        v-model="onlyProblems"
                                        :label="t('board.detailDrawer.onlyProblems')"
                                    />
                                </div>

                                <p v-if="loadingMembers" class="detail-drawer__pane-empty">
                                    {{ t('common.loading') }}
                                </p>
                                <p
                                    v-else-if="filteredMembers.length === 0"
                                    class="detail-drawer__pane-empty"
                                >
                                    {{ t('board.detailDrawer.noMembers') }}
                                </p>
                                <ul v-else class="detail-drawer__member-list">
                                    <li
                                        v-for="m in visibleMembers"
                                        :key="m.host + ';' + m.service"
                                        class="detail-drawer__member-li"
                                    >
                                        <button
                                            type="button"
                                            class="detail-drawer__member-row"
                                            :title="
                                                t('board.detailDrawer.openMember', {
                                                    name: m.service
                                                        ? m.host + ' / ' + m.service
                                                        : m.host,
                                                })
                                            "
                                            @click="emit('select-host', m.host, m.service || null)"
                                        >
                                            <span
                                                class="detail-drawer__member-state"
                                                :class="`detail-drawer__member-state--${memberStateTone(m.state)}`"
                                                :title="m.state"
                                            >
                                                {{ memberStateBadge(m.state) }}
                                            </span>
                                            <div class="detail-drawer__member-body">
                                                <div class="detail-drawer__member-name">
                                                    <span>{{ m.host }}</span>
                                                    <span
                                                        v-if="m.service"
                                                        class="detail-drawer__member-svc"
                                                        >{{ m.service }}</span
                                                    >
                                                    <span
                                                        v-if="m.acknowledged"
                                                        class="detail-drawer__member-flag detail-drawer__member-flag--ack"
                                                        >ACK</span
                                                    >
                                                    <span
                                                        v-if="m.in_downtime"
                                                        class="detail-drawer__member-flag detail-drawer__member-flag--dt"
                                                        >DT</span
                                                    >
                                                    <span
                                                        v-if="m.notifications_enabled === false"
                                                        class="detail-drawer__member-flag detail-drawer__member-flag--mute"
                                                        >MUTED</span
                                                    >
                                                </div>
                                                <div
                                                    v-if="m.output"
                                                    class="detail-drawer__member-output"
                                                    :title="m.output"
                                                >
                                                    {{ m.output }}
                                                </div>
                                            </div>
                                            <span
                                                v-if="m.last_state_change"
                                                class="detail-drawer__member-since"
                                                :title="formatLocaleTime(m.last_state_change)"
                                            >
                                                {{ formatRelativeAge(m.last_state_change) }}
                                            </span>
                                        </button>
                                    </li>
                                </ul>
                                <p
                                    v-if="truncatedMemberCount > 0"
                                    class="detail-drawer__member-truncated"
                                >
                                    {{
                                        t('board.detailDrawer.moreMembers', {
                                            n: truncatedMemberCount,
                                        })
                                    }}
                                </p>
                            </div>
                        </CmkTabContent>

                        <CmkTabContent v-if="showActivityTab" id="activity" spacing="none">
                            <div class="detail-drawer__pane">
                                <div
                                    v-if="downtimeList.length"
                                    class="detail-drawer__pane-section detail-drawer__section--downtimes"
                                >
                                    <div class="detail-drawer__pane-heading">
                                        {{ t('board.detailDrawer.activeDowntimes') }}
                                    </div>
                                    <ul class="detail-drawer__list">
                                        <li
                                            v-for="dt in downtimeList"
                                            :key="dt.id"
                                            class="detail-drawer__list-row"
                                        >
                                            <div class="detail-drawer__list-meta">
                                                <span class="detail-drawer__list-author">{{
                                                    dt.author
                                                }}</span>
                                                <span
                                                    v-if="!dt.fixed"
                                                    class="detail-drawer__list-tag"
                                                    :title="
                                                        t('board.detailDrawer.flexibleDowntime')
                                                    "
                                                    >FLEX</span
                                                >
                                                <span class="detail-drawer__list-time">{{
                                                    dt.timeRange
                                                }}</span>
                                            </div>
                                            <div v-if="dt.comment" class="detail-drawer__list-text">
                                                {{ dt.comment }}
                                            </div>
                                        </li>
                                    </ul>
                                </div>

                                <div v-if="commentList.length" class="detail-drawer__pane-section">
                                    <div class="detail-drawer__pane-heading">
                                        {{ t('board.detailDrawer.comments') }}
                                    </div>
                                    <ul class="detail-drawer__list">
                                        <li
                                            v-for="c in commentList"
                                            :key="c.id"
                                            class="detail-drawer__list-row"
                                        >
                                            <div class="detail-drawer__list-meta">
                                                <span class="detail-drawer__list-author">{{
                                                    c.author
                                                }}</span>
                                                <span class="detail-drawer__list-time">{{
                                                    c.age
                                                }}</span>
                                                <span
                                                    v-if="c.expires"
                                                    class="detail-drawer__list-time"
                                                >
                                                    ·
                                                    {{ t('board.detailDrawer.expires') }}
                                                    {{ c.expires }}
                                                </span>
                                            </div>
                                            <div class="detail-drawer__list-text">
                                                {{ c.text }}
                                            </div>
                                        </li>
                                    </ul>
                                </div>
                            </div>
                        </CmkTabContent>
                    </template>
                </CmkTabs>
            </div>

            <footer v-if="!isSite" class="detail-drawer__actions">
                <h4 class="detail-drawer__actions-title">
                    {{ t('board.detailDrawer.sectionActions') }}
                </h4>
                <div class="detail-drawer__actions-grid">
                    <CmkButton
                        v-if="
                            !state?.acknowledged &&
                            (isProblematic || isGroup) &&
                            canCommand('acknowledge')
                        "
                        variant="success"
                        class="detail-drawer__action detail-drawer__action--primary"
                        :title="
                            isGroup
                                ? t('board.detailDrawer.ackGroupTooltip', {
                                      n: groupMembers.length,
                                  })
                                : ''
                        "
                        @click="emit('acknowledge')"
                    >
                        {{
                            isGroup
                                ? t('board.detailDrawer.ackGroupLabel', { n: groupMembers.length })
                                : t('board.detailDrawer.ackLabel')
                        }}
                    </CmkButton>
                    <CmkButton
                        v-if="state?.acknowledged && canCommand('remove_acknowledgement')"
                        variant="warning"
                        class="detail-drawer__action"
                        @click="emit('remove-ack')"
                    >
                        {{ t('board.detailDrawer.removeAckLabel') }}
                    </CmkButton>
                    <CmkButton
                        v-if="canCommand('force_check')"
                        variant="optional"
                        class="detail-drawer__action"
                        @click="emit('force-check')"
                    >
                        {{ t('board.detailDrawer.forceCheckLabel') }}
                    </CmkButton>
                    <CmkButton
                        v-if="!state?.in_downtime && canCommand('schedule_downtime')"
                        variant="optional"
                        class="detail-drawer__action"
                        :title="
                            isGroup
                                ? t('board.detailDrawer.dtGroupTooltip', {
                                      n: groupMembers.length,
                                  })
                                : ''
                        "
                        @click="emit('schedule-downtime')"
                    >
                        {{
                            isGroup
                                ? t('board.detailDrawer.dtGroupLabel', { n: groupMembers.length })
                                : t('board.detailDrawer.scheduleDowntimeLabel')
                        }}
                    </CmkButton>
                    <CmkButton
                        v-if="state?.in_downtime && canCommand('remove_downtime')"
                        variant="warning"
                        class="detail-drawer__action"
                        @click="emit('remove-downtime')"
                    >
                        {{ t('board.detailDrawer.removeDowntimeLabel') }}
                    </CmkButton>
                    <CmkButton
                        v-if="!isAggregation && canCommand('add_comment')"
                        variant="optional"
                        class="detail-drawer__action"
                        @click="emit('add-comment')"
                    >
                        {{ t('board.detailDrawer.addCommentLabel') }}
                    </CmkButton>
                    <CmkButton
                        v-if="
                            canCommand('disable_notifications') &&
                            state?.notifications_enabled !== false
                        "
                        variant="optional"
                        class="detail-drawer__action"
                        @click="emit('disable-notifications')"
                    >
                        {{ t('board.detailDrawer.disableNotificationsLabel') }}
                    </CmkButton>
                    <CmkButton
                        v-else-if="canCommand('enable_notifications')"
                        variant="optional"
                        class="detail-drawer__action"
                        @click="emit('enable-notifications')"
                    >
                        {{ t('board.detailDrawer.enableNotificationsLabel') }}
                    </CmkButton>
                </div>
            </footer>

            <footer v-else class="detail-drawer__actions detail-drawer__actions--site">
                <CmkButton
                    v-if="problemsUrlFull"
                    variant="success"
                    :href="problemsUrlFull"
                    target="_blank"
                    class="detail-drawer__action detail-drawer__action--primary"
                >
                    {{ t('board.detailDrawer.openProblems') }} ↗
                </CmkButton>
            </footer>
        </div>
    </StatusSlideIn>
</template>

<script setup lang="ts">
import { useMutationObserver } from '@vueuse/core';
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';

import { connectionsApi, metricsApi } from '@/api/client';
import CmkCheckbox from '@/components/cmk/user-input/CmkCheckbox';
import { fmtValueWithUnit } from '@/composables/useMetricChart';
import { useAuthStore } from '@/stores/auth';
import type {
    AggregationNode,
    BoardObject,
    BulkAckTarget,
    GroupMember,
    MetricPoint,
    ObjectDetails,
    ObjectState,
    PerfometerResult,
} from '@/types/api';
import {
    BI_STATE_LABEL as BI_STATE_LABEL_MAP,
    BI_STATE_TONE,
    walkAggregationLeavesWithPath,
} from '@/utils/aggregationTree';
import { buildCheckmkSetupUrl, buildCheckmkUrl } from '@/utils/boardNavigation';
import { getBoardObjectName, getObjectTypeLabel } from '@/utils/naming';
import { parsePerfData, type PerfMetric, utilColor, utilPercent } from '@/utils/perf';
import { stateColor } from '@/utils/stateColors';
import { formatRelativeDuration, formatRelativeFuture } from '@/utils/time';
import CmkButton from '@/vendor/cmk/components/CmkButton.vue';
import { CmkChip } from '@/vendor/cmk/components/CmkChip';
import { CmkCode } from '@/vendor/cmk/components/CmkCode';
import CmkIcon from '@/vendor/cmk/components/CmkIcon';
import CmkTabs, { CmkTab, CmkTabContent } from '@/vendor/cmk/components/CmkTabs';
import CmkToggleButtonGroup from '@/vendor/cmk/components/CmkToggleButtonGroup.vue';

import MetricChart from './MetricChart.vue';
import StatusSlideIn from './StatusSlideIn.vue';

function stateBgColor(state: string): string {
    const c = stateColor(state);
    if (c.startsWith('#') && c.length === 7) {
        const r = parseInt(c.slice(1, 3), 16);
        const g = parseInt(c.slice(3, 5), 16);
        const b = parseInt(c.slice(5, 7), 16);
        return `rgba(${r}, ${g}, ${b}, 0.12)`;
    }
    return c;
}

const props = defineProps<{
    object: BoardObject | null;
    state?: ObjectState;
    checkmkUrl?: string | null;
    /** Board's connection_id — used to fetch on-demand object details. */
    connectionId?: string | null;
    /** CSS selector for the StatusSlideIn portal target. Defaults to body. */
    portalTarget?: string;
    /** Hostnames currently on the board — topology entries to those hosts
     * become clickable buttons that emit `select-host` for the parent to act on. */
    selectableHosts?: string[];
    readonly?: boolean;
}>();

const portalTarget = computed(() => props.portalTarget);

const emit = defineEmits<{
    close: [];
    acknowledge: [];
    'remove-ack': [];
    'schedule-downtime': [];
    'remove-downtime': [];
    'force-check': [];
    'add-comment': [];
    'enable-notifications': [];
    'disable-notifications': [];
    /** Host name picked from the topology section — board may highlight + select it. */
    'select-host': [hostName: string, serviceDescription?: string | null];
    /** Bulk-acknowledge contributing leaves of a BI aggregation. */
    'bulk-acknowledge': [targets: BulkAckTarget[]];
}>();

const selectableHostSet = computed(() => new Set(props.selectableHosts ?? []));
function canSelectHost(host: string): boolean {
    return selectableHostSet.value.has(host);
}

// CMC reschedules checks sub-second, so `next_check` lags behind "now"
// between checks even when the host is healthy. Don't paint "overdue"
// until the LAST check is itself stale by this many seconds.
const OVERDUE_GRACE_SECONDS = 60;

// Drives age/overdue labels so they tick forward without a state push.
const nowMs = ref(Date.now());
let _tick: ReturnType<typeof setInterval> | null = null;
onMounted(() => {
    _tick = setInterval(() => {
        nowMs.value = Date.now();
    }, 1000);
});
onUnmounted(() => {
    if (_tick) clearInterval(_tick);
    _tick = null;
});

const auth = useAuthStore();

const canCommand = (verb: string): boolean => !props.readonly && auth.mayCommand(verb);

// On-demand details kept separate from the streamed ObjectState — long_output,
// comments, downtimes and topology rarely change but can be many KB each, so
// fetching them per Drawer-open keeps the WebSocket payload compact.
const details = ref<ObjectDetails | null>(null);
// CMK perf-o-meter result — same metric Checkmk shows in views, computed
// from the service's perfometer plugin definition (e.g. mem_used_percent for
// Linux Memory). Only populated for services.
const perfometer = ref<PerfometerResult | null>(null);

// Source the watch on primitive keys (not the reactive object) so it fires
// only when selection actually changes — state-stream updates that re-create
// the prop reference would otherwise cause refetches on every tick.
watch(
    [
        () => props.object?.type,
        () => props.object?.host_name,
        () => props.object?.service_description,
        () => props.connectionId,
    ],
    async ([objType, host, service, connId]) => {
        details.value = null;
        perfometer.value = null;
        if (!connId || !auth.accessToken || !host) return;
        if (objType !== 'host' && objType !== 'service') return;
        if (objType === 'service' && !service) return;
        const reqService = objType === 'service' ? (service ?? null) : null;
        try {
            const [detailsRes, perfRes] = await Promise.all([
                connectionsApi.objectDetails(connId, objType, host, reqService, auth.accessToken),
                objType === 'service' && reqService
                    ? metricsApi.getPerfometer(connId, host, reqService, auth.accessToken)
                    : Promise.resolve(null),
            ]);
            // Stale-response guard: between the await and now the user may have
            // clicked another object. Match all three identity fields so a host
            // response doesn't land on a same-named service or vice versa.
            // Note: service_description may be undefined on host BoardObjects
            // (Flow Board synthesises hosts without it) — normalise to null
            // before comparing so guard doesn't reject legitimate hosts.
            const currentService = props.object?.service_description ?? null;
            if (
                props.object?.type === objType &&
                props.object?.host_name === host &&
                currentService === reqService
            ) {
                details.value = detailsRes;
                perfometer.value = perfRes;
            }
        } catch {
            details.value = null;
            perfometer.value = null;
        }
    },
    { immediate: true },
);

// Hostgroup / Servicegroup member-list — drives the Members tab. We fetch
// per-member state (not just the aggregate pill) so the operator can triage
// without leaving the drawer.
const groupMembers = ref<GroupMember[]>([]);
const loadingMembers = ref(false);
const memberSearch = ref('');
const onlyProblems = ref(false);

watch(
    [
        () => props.object?.type,
        () => props.object?.group_name,
        () => props.object?.object_filter,
        () => props.object?.object_types,
        () => props.connectionId,
    ],
    async ([objType, groupName, objFilter, objTypes, connId]) => {
        groupMembers.value = [];
        memberSearch.value = '';
        onlyProblems.value = false;
        if (!connId || !auth.accessToken) return;
        const isHostOrServiceGroup = objType === 'hostgroup' || objType === 'servicegroup';
        if (isHostOrServiceGroup && !groupName) return;
        if (objType === 'dyngroup' && !objFilter) return;
        if (!isHostOrServiceGroup && objType !== 'dyngroup') return;
        loadingMembers.value = true;
        try {
            const rows =
                objType === 'dyngroup'
                    ? await connectionsApi.dyngroupMembers(
                          connId,
                          objTypes ?? 'host',
                          objFilter ?? '',
                          auth.accessToken,
                      )
                    : await connectionsApi.groupMembers(
                          connId,
                          objType as 'hostgroup' | 'servicegroup',
                          groupName ?? '',
                          auth.accessToken,
                      );
            // Stale-response guard.
            if (
                props.object?.type === objType &&
                props.object?.group_name === groupName &&
                props.object?.object_filter === objFilter
            ) {
                groupMembers.value = rows;
            }
        } catch {
            groupMembers.value = [];
        } finally {
            loadingMembers.value = false;
        }
    },
    { immediate: true },
);

// Severity rank for sort: worst first. Matches the same intent as the radar
// view but inlined here so the member list and the donut counts agree.
const _MEMBER_SEVERITY: Record<string, number> = {
    DOWN: 5,
    CRITICAL: 5,
    UNREACHABLE: 4,
    WARNING: 3,
    UNKNOWN: 3,
    PENDING: 1,
    UP: 0,
    OK: 0,
};

const memberHealth = computed(() => {
    const counts = { ok: 0, warn: 0, crit: 0, unkn: 0, pending: 0 };
    for (const m of groupMembers.value) {
        if (m.state === 'OK' || m.state === 'UP') counts.ok += 1;
        else if (m.state === 'WARNING') counts.warn += 1;
        else if (m.state === 'CRITICAL' || m.state === 'DOWN') counts.crit += 1;
        else if (m.state === 'UNKNOWN' || m.state === 'UNREACHABLE') counts.unkn += 1;
        else counts.pending += 1;
    }
    return counts;
});

const filteredMembers = computed(() => {
    const needle = memberSearch.value.trim().toLowerCase();
    return groupMembers.value
        .filter((m) => {
            if (onlyProblems.value && (m.state === 'OK' || m.state === 'UP')) return false;
            if (!needle) return true;
            return (
                m.host.toLowerCase().includes(needle) ||
                m.service.toLowerCase().includes(needle) ||
                m.output.toLowerCase().includes(needle)
            );
        })
        .sort((a, b) => {
            const sa = _MEMBER_SEVERITY[a.state] ?? 0;
            const sb = _MEMBER_SEVERITY[b.state] ?? 0;
            if (sa !== sb) return sb - sa;
            return a.host.localeCompare(b.host) || a.service.localeCompare(b.service);
        });
});

const MEMBER_TRUNCATE = 50;
const visibleMembers = computed(() => filteredMembers.value.slice(0, MEMBER_TRUNCATE));
const truncatedMemberCount = computed(() =>
    Math.max(0, filteredMembers.value.length - MEMBER_TRUNCATE),
);

const isGroup = computed(
    () =>
        props.object?.type === 'hostgroup' ||
        props.object?.type === 'servicegroup' ||
        props.object?.type === 'dyngroup',
);
const isAggregation = computed(() => props.object?.type === 'aggregation');

interface MemberChip {
    label: string;
    count: number;
    tone: 'crit' | 'warn' | 'unknown' | 'ok';
}

const memberChips = computed<MemberChip[]>(() => {
    const h = memberHealth.value;
    const chips: MemberChip[] = [];
    if (h.crit > 0) chips.push({ label: 'CRIT', count: h.crit, tone: 'crit' });
    if (h.warn > 0) chips.push({ label: 'WARN', count: h.warn, tone: 'warn' });
    if (h.unkn > 0) chips.push({ label: 'UNKN', count: h.unkn, tone: 'unknown' });
    chips.push({ label: 'OK', count: h.ok, tone: 'ok' });
    return chips;
});

function memberStateTone(state: string): string {
    if (state === 'CRITICAL' || state === 'DOWN') return 'crit';
    if (state === 'WARNING') return 'warn';
    if (state === 'UNKNOWN' || state === 'UNREACHABLE') return 'unknown';
    if (state === 'PENDING') return 'pending';
    return 'ok';
}

function memberStateBadge(state: string): string {
    switch (state) {
        case 'CRITICAL':
        case 'DOWN':
            return state === 'DOWN' ? 'D' : 'C';
        case 'WARNING':
            return 'W';
        case 'UNKNOWN':
            return '?';
        case 'UNREACHABLE':
            return 'U';
        case 'PENDING':
            return '·';
        case 'OK':
        case 'UP':
            return '✓';
        default:
            return '·';
    }
}

function formatRelativeAge(ts: number | null | undefined): string {
    return formatRelativeDuration(ts, nowMs.value);
}

function formatLocaleTime(ts: number | null | undefined): string {
    if (!ts) return '';
    return new Date(ts * 1000).toLocaleString();
}

const PROBLEM_STATES = new Set(['CRITICAL', 'WARNING', 'UNKNOWN', 'DOWN', 'UNREACHABLE']);
const isProblematic = computed(() => (props.state ? PROBLEM_STATES.has(props.state.state) : false));
const isSite = computed(() => props.object?.type === 'site');
const severityKind = computed(() => {
    const s = props.state?.state;
    if (!s) return 'pending';
    if (s === 'CRITICAL' || s === 'DOWN') return 'critical';
    if (s === 'UNREACHABLE') return 'unreachable';
    if (s === 'WARNING' || s === 'UNKNOWN') return 'warn';
    if (s === 'OK' || s === 'UP') return 'ok';
    return 'pending';
});

const { t } = useI18n();

const displayName = computed(() => (props.object ? getBoardObjectName(props.object) : ''));
const typeLabel = computed(() => (props.object ? getObjectTypeLabel(props.object) : ''));

const checkmkUrlFull = computed(() =>
    props.object
        ? buildCheckmkUrl(props.object, props.checkmkUrl ?? null, props.state?.site_id)
        : null,
);
// Lookup of aggregation_id → pack_id, populated lazily when this drawer
// shows a BI aggregation. Lets buildCheckmkSetupUrl deep-link into the
// owning pack's rules editor instead of the bi_packs overview.
//
// Map values: string = pack id; null = looked up but not surfaced by
// cmk.bi (cache the negative so subsequent drawer opens don't re-fetch
// the whole aggregation catalog).
const aggregationPackIds = ref<Record<string, string | null>>({});
watch(
    () => [props.object?.type, props.object?.aggregation_id, props.connectionId] as const,
    async ([type, aggId, connId]) => {
        if (type !== 'aggregation' || !aggId || !connId) return;
        if (aggId in aggregationPackIds.value) return;
        const auth = useAuthStore();
        if (!auth.accessToken) return;
        try {
            const aggrs = await connectionsApi.aggregations(connId, auth.accessToken);
            const next: Record<string, string | null> = { ...aggregationPackIds.value };
            for (const a of aggrs) {
                next[a.id] = a.pack_id || null;
            }
            if (!(aggId in next)) next[aggId] = null;
            aggregationPackIds.value = next;
        } catch {
            // Pack-id lookup failure means we fall back to the bi_packs
            // overview link, which is fine; nothing to do here.
        }
    },
    { immediate: true },
);

const checkmkSetupUrlFull = computed(() => {
    if (!props.object) return null;
    const aggId = props.object.aggregation_id ?? null;
    const packId = aggId ? aggregationPackIds.value[aggId] : null;
    return buildCheckmkSetupUrl(
        props.object,
        props.checkmkUrl ?? null,
        packId ?? null,
        props.state?.site_id,
    );
});

const problemsUrlFull = computed(() => {
    if (!props.object || props.object.type !== 'site' || !props.checkmkUrl) return null;
    const base = props.checkmkUrl.replace(/\/check_mk\/?$/, '').replace(/\/$/, '');
    const siteId = props.object.host_name ?? props.state?.site_id;
    if (!siteId) return null;
    // svcproblems' built-in defaults (CRIT/WARN/UNKN active) are exactly what
    // the operator wants here — no filled_in, just the site scope.
    const params = new URLSearchParams({
        view_name: 'svcproblems',
        site: siteId,
    });
    return `${base}/check_mk/view.py?${params}`;
});

const sinceText = computed(() => {
    const duration = formatRelativeDuration(props.state?.last_state_change, nowMs.value);
    return duration ? t('board.detailDrawer.since', { duration }) : null;
});

interface SummaryChip {
    state: string;
    count: number;
    label: string;
    tone: 'crit' | 'warn' | 'unknown' | 'ok';
    url: string | null;
}

interface AggregationLeafRow {
    id: string;
    label: string;
    stateLabel: string;
    tone: 'ok' | 'warn' | 'crit' | 'unknown';
    /** Walked path back to root, used for "worstPath" display. */
    path: string[];
    hostName: string | null;
    serviceDescription: string | null;
    state: number;
}

interface AggregationSummary {
    chips: SummaryChip[];
    worstPath: string | null;
    leaves: AggregationLeafRow[];
    /** Nodes at depth=`expand_depth` (or shallower terminal bi_leaves). */
    treeRows: AggregationLeafRow[];
    treeChips: SummaryChip[];
    treeDepth: number;
}

type AggregationView = 'summary' | 'details';

// Operator-facing labels for the BI severity ordering: CRIT > WARN > UNKN > OK.
// Used for chip layout, "worst leaf" sort, and tree-node count breakdown.
const BI_CHIP_ORDER: readonly number[] = [2, 1, 3, 0];

function _aggregationRow(node: AggregationNode, path: string[]): AggregationLeafRow {
    const fullPath = [...path, node.name];
    return {
        id: fullPath.join('::'),
        label: node.name,
        stateLabel: BI_STATE_LABEL_MAP[node.state] ?? String(node.state),
        tone: BI_STATE_TONE[node.state] ?? 'unknown',
        path: fullPath,
        hostName: node.host_name ?? null,
        serviceDescription: node.service_description ?? null,
        state: node.state,
    };
}

function _walkAggregationLeaves(node: AggregationNode): AggregationLeafRow[] {
    return walkAggregationLeavesWithPath(node).map(({ leaf, path }) =>
        _aggregationRow(leaf, path.slice(0, -1)),
    );
}

// Collect nodes at exactly `targetDepth` below root. A branch shorter than
// targetDepth terminates at its real bi_leaf — no synthetic placeholders.
// Root itself is never returned (caller starts with empty path).
function _nodesAtDepth(
    node: AggregationNode,
    targetDepth: number,
    path: string[] = [],
): AggregationLeafRow[] {
    if (targetDepth === 0) {
        return path.length > 0 ? [_aggregationRow(node, path)] : [];
    }
    if (node.children.length === 0) {
        return path.length > 0 ? [_aggregationRow(node, path)] : [];
    }
    const next = [...path, node.name];
    return node.children.flatMap((c) => _nodesAtDepth(c, targetDepth - 1, next));
}

function _chipsFromCounts(counts: Record<number, number>): SummaryChip[] {
    return BI_CHIP_ORDER.map((s) => ({
        state: BI_STATE_LABEL_MAP[s],
        count: counts[s] ?? 0,
        label: BI_STATE_LABEL_MAP[s],
        tone: BI_STATE_TONE[s] ?? 'unknown',
        url: null,
    }));
}

function _countByState(rows: ReadonlyArray<{ state: number }>): Record<number, number> {
    const out: Record<number, number> = { 0: 0, 1: 0, 2: 0, 3: 0 };
    for (const r of rows) out[r.state] = (out[r.state] ?? 0) + 1;
    return out;
}

// Checkmk's filter machinery takes a single "svc_state" / "host_state" filter
// whose individual st*/hst* checkboxes are interpreted as a bitmask. A box
// only counts as ON when its parameter is present and equals "on" — sending
// "off" or omitting it both mean "exclude this state". The whole filter is
// only honored when "_active" lists svcstate/hoststate alongside the host /
// site filter; without it the Setup-defined view defaults win.
function svcStateOn(state: string): string {
    if (state === 'CRITICAL') return 'st2';
    if (state === 'WARNING') return 'st1';
    if (state === 'UNKNOWN') return 'st3';
    return 'st0'; // OK
}

function hostStateOn(state: string): string {
    if (state === 'DOWN') return 'hst1';
    if (state === 'UNREACHABLE') return 'hst2';
    return 'hst0'; // UP
}

function buildServiceChipUrl(state: string, count: number): string | null {
    if (count <= 0 || !props.checkmkUrl || !props.object) return null;
    const base = props.checkmkUrl.replace(/\/check_mk\/?$/, '').replace(/\/$/, '');
    const params: Record<string, string> = {
        view_name: 'allservices',
        filled_in: 'filter',
        _active: 'svcstate;host',
        [svcStateOn(state)]: 'on',
    };
    if (props.object.type === 'site' && props.object.host_name) {
        params.site = props.object.host_name;
        params._active = 'svcstate;site';
    } else if (props.object.host_name) {
        params.host = props.object.host_name;
    } else {
        return null;
    }
    return `${base}/check_mk/view.py?${new URLSearchParams(params)}`;
}

function buildHostChipUrl(state: string, count: number): string | null {
    if (count <= 0 || !props.checkmkUrl || !props.object) return null;
    if (props.object.type !== 'site' || !props.object.host_name) return null;
    const base = props.checkmkUrl.replace(/\/check_mk\/?$/, '').replace(/\/$/, '');
    const params: Record<string, string> = {
        view_name: 'allhosts',
        filled_in: 'filter',
        _active: 'hoststate;site',
        site: props.object.host_name,
        [hostStateOn(state)]: 'on',
    };
    return `${base}/check_mk/view.py?${new URLSearchParams(params)}`;
}

const aggregationSummary = computed<AggregationSummary | null>(() => {
    const obj = props.object;
    const tree = props.state?.tree;
    if (!obj || obj.type !== 'aggregation' || !tree) return null;

    const leaves = _walkAggregationLeaves(tree);
    if (!leaves.length) return null;

    const chips = _chipsFromCounts(_countByState(leaves));

    // Worst-leaf sort follows BI_CHIP_ORDER so ties resolve deterministically
    // to the highest-severity slot (CRIT > WARN > UNKN > OK).
    const sorted = [...leaves].sort(
        (a, b) => BI_CHIP_ORDER.indexOf(a.state) - BI_CHIP_ORDER.indexOf(b.state),
    );
    const worst = sorted.find((l) => l.state > 0) ?? null;
    const worstPath = worst ? worst.path.join(' › ') : null;

    const expandDepth = obj.expand_depth ?? 0;
    if (expandDepth === 0) {
        return {
            chips,
            worstPath,
            leaves: sorted,
            treeRows: [],
            treeChips: [],
            treeDepth: 0,
        };
    }

    const treeRows = _nodesAtDepth(tree, expandDepth);
    const treeChips = _chipsFromCounts(_countByState(treeRows));

    return {
        chips,
        worstPath,
        leaves: sorted,
        treeRows,
        treeChips,
        treeDepth: expandDepth,
    };
});

const aggregationView = ref<AggregationView>('summary');
// Re-pick the default view only when the operator switches to a different
// object — otherwise an edit to expand_depth would clobber a manual tab
// choice in the open drawer.
watch(
    () => props.object?.id,
    () => {
        aggregationView.value = (props.object?.expand_depth ?? 0) > 0 ? 'summary' : 'details';
    },
    { immediate: true },
);

const aggregationViewOptions = computed(() => {
    const d = aggregationSummary.value?.treeDepth ?? 1;
    return [
        {
            label: t('board.detailDrawer.aggregationViewSummary', { depth: d }),
            value: 'summary',
        },
        { label: t('board.detailDrawer.aggregationViewDetails'), value: 'details' },
    ];
});

function setAggregationView(v: string): void {
    if (v === 'summary' || v === 'details') aggregationView.value = v;
}

const aggregationListRows = computed<AggregationLeafRow[]>(() => {
    const s = aggregationSummary.value;
    if (!s) return [];
    return aggregationView.value === 'summary' ? s.treeRows : s.leaves;
});

const activeChips = computed<SummaryChip[]>(() => {
    const s = aggregationSummary.value;
    if (!s) return [];
    return aggregationView.value === 'summary' ? s.treeChips : s.chips;
});

function onAggregationLeafClick(leaf: AggregationLeafRow): void {
    if (!leaf.hostName) return;
    emit('select-host', leaf.hostName, leaf.serviceDescription ?? null);
}

const aggregationProblemLeaves = computed<AggregationLeafRow[]>(() => {
    const summary = aggregationSummary.value;
    if (!summary) return [];
    // state>0 = WARN/CRIT/UNKN; OK leaves don't need ack.
    return summary.leaves.filter((l) => l.state > 0 && !!l.hostName);
});

function onBulkAcknowledgeClick(): void {
    if (!aggregationProblemLeaves.value.length) return;
    emit(
        'bulk-acknowledge',
        aggregationProblemLeaves.value.map((l) => ({
            host: l.hostName as string,
            service: l.serviceDescription ?? null,
        })),
    );
}

const serviceChips = computed<SummaryChip[]>(() => {
    const s = props.state?.services_summary;
    if (!s) return [];
    const make = (
        state: string,
        count: number,
        label: string,
        tone: SummaryChip['tone'],
    ): SummaryChip => ({
        state,
        count,
        label,
        tone,
        url: buildServiceChipUrl(state, count),
    });
    // Hide problem chips at zero (visual noise); always keep the OK anchor so
    // the operator sees an "all green" cue when nothing is wrong.
    return [
        make('CRITICAL', s.critical ?? 0, 'CRIT', 'crit'),
        make('WARNING', s.warning ?? 0, 'WARN', 'warn'),
        make('UNKNOWN', s.unknown ?? 0, 'UNKN', 'unknown'),
        make('OK', s.ok ?? 0, 'OK', 'ok'),
    ].filter((chip) => chip.state === 'OK' || chip.count > 0);
});

// Site state output looks like "504 hosts (504 up, 0 down, 0 unreachable)";
// extract the host counts so we can render the same kind of chip row as services.
const hostsSummary = computed<{ up: number; down: number; unreachable: number } | null>(() => {
    if (!isSite.value) return null;
    const out = props.state?.output;
    if (!out) return null;
    const m = out.match(/(\d+)\s+up,\s*(\d+)\s+down,\s*(\d+)\s+unreachable/);
    if (!m) return null;
    return { up: parseInt(m[1], 10), down: parseInt(m[2], 10), unreachable: parseInt(m[3], 10) };
});

const hostChips = computed<SummaryChip[]>(() => {
    const h = hostsSummary.value;
    if (!h) return [];
    const make = (
        state: string,
        count: number,
        label: string,
        tone: SummaryChip['tone'],
    ): SummaryChip => ({
        state,
        count,
        label,
        tone,
        url: buildHostChipUrl(state, count),
    });
    return [
        make('DOWN', h.down, 'DOWN', 'crit'),
        make('UNREACHABLE', h.unreachable, 'UNRCH', 'warn'),
        make('UP', h.up, 'UP', 'ok'),
    ].filter((chip) => chip.state === 'UP' || chip.count > 0);
});

interface Modifier {
    label: string;
    kind: 'ack' | 'downtime' | 'stale' | 'muted' | 'flapping';
}
const modifiers = computed<Modifier[]>(() => {
    const s = props.state;
    if (!s) return [];
    const list: Modifier[] = [];
    if (s.acknowledged) list.push({ label: 'ACK', kind: 'ack' });
    if (s.in_downtime) list.push({ label: 'DOWNTIME', kind: 'downtime' });
    if (s.stale) list.push({ label: 'STALE', kind: 'stale' });
    if (s.notifications_enabled === false) list.push({ label: 'MUTED', kind: 'muted' });
    if (details.value?.is_flapping) list.push({ label: 'FLAPPING', kind: 'flapping' });
    return list;
});

const longOutputText = computed(() => details.value?.long_output ?? '');

interface MetaRow {
    label: string;
    value: string;
    tone?: 'warn';
    href?: string | null;
}

// Service drawers list the parent host as a metadata row; link it to the
// host's "Status of host" view (Nagios-familiar: both the title and the host
// name are clickable). Reuses buildCheckmkUrl by switching the object to a
// host so the same site/base-URL resolution applies.
const hostStatusUrl = computed(() => {
    const o = props.object;
    if (o?.type !== 'service' || !o.host_name) return null;
    return buildCheckmkUrl(
        { ...o, type: 'host', service_description: null },
        props.checkmkUrl ?? null,
        props.state?.site_id,
    );
});

const metaRows = computed<MetaRow[]>(() => {
    const s = props.state;
    const o = props.object;
    if (!s) return [];
    const rows: MetaRow[] = [];
    if (s.alias && s.alias !== displayName.value) {
        rows.push({ label: 'Alias', value: s.alias });
    }
    if (s.address) rows.push({ label: 'Address', value: s.address });
    if (o?.type === 'service' && o.host_name) {
        rows.push({
            label: t('board.detailDrawer.host'),
            value: o.host_name,
            href: hostStatusUrl.value,
        });
    }
    // For site drawers, the site name is already the title — no point repeating it.
    if (s.site_id && o?.type !== 'site') {
        rows.push({ label: t('board.detailDrawer.site'), value: s.site_id });
    }
    return rows;
});

const checkInfoRows = computed<MetaRow[]>(() => {
    const s = props.state;
    if (!s) return [];
    const rows: MetaRow[] = [];
    const now = Math.floor(Date.now() / 1000);

    // Aggregators have no check attempts of their own — 0/0 would confuse.
    const objType = props.object?.type;
    const isAggregator =
        objType === 'aggregation' ||
        objType === 'hostgroup' ||
        objType === 'servicegroup' ||
        objType === 'dyngroup';
    if (
        !isAggregator &&
        typeof s.current_attempt === 'number' &&
        typeof s.max_attempts === 'number'
    ) {
        const isSoft = s.state_type === 'SOFT' || s.state_type === 'soft';
        rows.push({
            label: t('board.detailDrawer.attemptLabel'),
            value: t('board.detailDrawer.attemptValue', {
                current: s.current_attempt,
                max: s.max_attempts,
                type: isSoft
                    ? t('board.detailDrawer.stateTypeSoft')
                    : t('board.detailDrawer.stateTypeHard'),
            }),
            tone: isSoft ? 'warn' : undefined,
        });
    }

    if (s.last_check && s.last_check > 0) {
        rows.push({
            label: t('board.detailDrawer.lastCheck'),
            value: t('board.detailDrawer.timeAgo', {
                duration: formatRelativeDuration(s.last_check, nowMs.value),
            }),
        });
    } else if (s.last_check === 0) {
        rows.push({
            label: t('board.detailDrawer.lastCheck'),
            value: t('board.detailDrawer.never'),
        });
    }

    if (s.next_check && s.next_check > 0) {
        if (s.next_check < now) {
            // CMC keeps `next_check` slightly behind "now" between checks
            // because it reschedules sub-second. Suppress "overdue" while
            // the LAST check is recent — only flag it if the check chain
            // really has stalled.
            const sinceLastCheck = s.last_check && s.last_check > 0 ? now - s.last_check : Infinity;
            if (sinceLastCheck >= OVERDUE_GRACE_SECONDS) {
                rows.push({
                    label: t('board.detailDrawer.nextCheck'),
                    value: `${t('board.detailDrawer.overdue')} (${formatRelativeDuration(s.next_check, nowMs.value)})`,
                    tone: 'warn',
                });
            }
        } else {
            rows.push({
                label: t('board.detailDrawer.nextCheck'),
                value: t('board.detailDrawer.timeIn', {
                    // An imminent check (sub-second away) formats to '' — show
                    // '<1s' so the row never reads a dangling "in ".
                    duration: formatRelativeFuture(s.next_check, nowMs.value) || '<1s',
                }),
            });
        }
    }

    const d = details.value;
    // Service-only: when did this check last go OK? Lets the operator see
    // "broken for 2 days" vs. "just flipped" without leaving the drawer.
    if (d?.last_time_ok && d.last_time_ok > 0 && s.state !== 'OK') {
        rows.push({
            label: t('board.detailDrawer.lastOk'),
            value: t('board.detailDrawer.timeAgo', {
                duration: formatRelativeDuration(d.last_time_ok, nowMs.value),
            }),
        });
    }

    return rows;
});

// Topology / membership / labels — from on-demand details. Empty groups are
// hidden so the drawer stays compact when nothing useful is set.
interface TopologyGroup {
    label: string;
    items: string[];
    /** Optional Checkmk-style hostname links (parents, children) */
    isHostList?: boolean;
}
const topologyGroups = computed<TopologyGroup[]>(() => {
    const d = details.value;
    if (!d) return [];
    const out: TopologyGroup[] = [];
    if (d.parents.length)
        out.push({ label: t('board.detailDrawer.parents'), items: d.parents, isHostList: true });
    if (d.children.length)
        out.push({ label: t('board.detailDrawer.children'), items: d.children, isHostList: true });
    if (d.host_groups.length)
        out.push({ label: t('board.detailDrawer.hostGroups'), items: d.host_groups });
    if (d.service_groups.length)
        out.push({ label: t('board.detailDrawer.serviceGroups'), items: d.service_groups });
    if (d.contact_groups.length)
        out.push({ label: t('board.detailDrawer.contactGroups'), items: d.contact_groups });
    return out;
});

const labelEntries = computed(() => Object.entries(details.value?.labels ?? {}));

interface Comment {
    id: number;
    author: string;
    text: string;
    age: string;
    expires: string | null;
}
const commentList = computed<Comment[]>(() => {
    const list = details.value?.comments ?? [];
    return list.map((c) => ({
        id: c.id,
        author: c.author || '?',
        text: c.comment,
        age: t('board.detailDrawer.timeAgo', {
            duration: formatRelativeDuration(c.entry_time, nowMs.value),
        }),
        expires:
            c.expire_time && c.expire_time > 0
                ? t('board.detailDrawer.timeIn', {
                      duration: formatRelativeFuture(c.expire_time, nowMs.value),
                  })
                : null,
    }));
});

interface Downtime {
    id: number;
    author: string;
    comment: string;
    timeRange: string;
    fixed: boolean;
}
function fmtDateTime(ts: number): string {
    return new Date(ts * 1000).toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}
const downtimeList = computed<Downtime[]>(() => {
    const list = details.value?.downtimes ?? [];
    return list.map((d) => ({
        id: d.id,
        author: d.author || '?',
        comment: d.comment,
        timeRange: `${fmtDateTime(d.start_time)} → ${fmtDateTime(d.end_time)}`,
        fixed: d.fixed,
    }));
});

interface PerfRow {
    label: string;
    pct: number;
    color: string;
    warnPct: number | null;
    critPct: number | null;
    warnLabel: string;
    critLabel: string;
    valueLabel: string;
}

function fmtNum(n: number, unit: string): string {
    return fmtValueWithUnit(n, unit);
}

// Tab visibility — only show tabs that actually have content. The Status tab
// always renders (output + state badges + chips); others appear conditionally.
const showPerformanceTab = computed(() => perfRows.value.length > 0 || !!longOutputText.value);
const showContextTab = computed(
    () =>
        topologyGroups.value.length > 0 ||
        labelEntries.value.length > 0 ||
        contextMetaRows.value.length > 0,
);
const showActivityTab = computed(
    () => commentList.value.length > 0 || downtimeList.value.length > 0,
);
const showMembersTab = computed(() => isGroup.value);

const activeTab = ref('status');

watch([() => props.object?.host_name, () => props.object?.service_description], () => {
    // Reset to overview whenever the user picks a different object so they
    // don't land on an empty tab from the previous selection.
    activeTab.value = 'status';
});

interface MetaRow2 {
    label: string;
    value: string;
    tone?: 'warn';
}

const contextMetaRows = computed<MetaRow2[]>(() => {
    const d = details.value;
    const rows: MetaRow2[] = [];
    if (!d) return rows;
    if (d.check_command)
        rows.push({ label: t('board.detailDrawer.checkCommand'), value: d.check_command });
    if (typeof d.latency === 'number' && d.latency >= 0) {
        rows.push({
            label: t('board.detailDrawer.latency'),
            value: `${(d.latency * 1000).toFixed(0)} ms`,
        });
    }
    if (d.notification_period && d.notification_period !== '24X7') {
        rows.push({
            label: t('board.detailDrawer.notificationPeriod'),
            value: d.notification_period,
            tone: d.in_notification_period ? undefined : 'warn',
        });
    }
    return rows;
});

// Check command gets its own CmkCode block — it's typically long and benefits
// from monospace + horizontal scroll, while latency / notif. period stay in
// the regular dt/dd grid.
const checkCommandRow = computed<MetaRow2 | null>(
    () =>
        contextMetaRows.value.find((r) => r.label === t('board.detailDrawer.checkCommand')) ?? null,
);
const contextMetaRowsWithoutCheckCmd = computed<MetaRow2[]>(() =>
    contextMetaRows.value.filter((r) => r.label !== t('board.detailDrawer.checkCommand')),
);

const parsedMetrics = computed<PerfMetric[]>(() => {
    const raw = props.state?.perf_data;
    return raw ? parsePerfData(raw) : [];
});

function _displayLabel(metricId: string): string {
    return details.value?.metric_titles[metricId] || metricId;
}

function _toPerfRow(m: PerfMetric): PerfRow {
    const pct = utilPercent(m);
    const refMax = m.max ?? m.crit ?? null;
    const warnPct =
        m.warn !== null && refMax !== null && refMax > 0
            ? Math.min(100, (m.warn / refMax) * 100)
            : null;
    const critPct =
        m.crit !== null && refMax !== null && refMax > 0
            ? Math.min(100, (m.crit / refMax) * 100)
            : null;
    return {
        label: _displayLabel(m.label),
        pct,
        color: utilColor(pct),
        warnPct,
        critPct,
        warnLabel: m.warn !== null ? fmtNum(m.warn, m.unit) : '',
        critLabel: m.crit !== null ? fmtNum(m.crit, m.unit) : '',
        valueLabel: fmtNum(m.value, m.unit),
    };
}

const perfRows = computed<PerfRow[]>(() => parsedMetrics.value.map(_toPerfRow));

// Pick the metric that best summarizes the service: prefer one with thresholds
// set (those drive the actual state), then fall back to the highest utilization.
// Anchors the Performance tab so the operator sees the headline value first.
const mainMetric = computed<PerfMetric | null>(() => {
    const metrics = parsedMetrics.value;
    if (!metrics.length) return null;
    const withThresholds = metrics.filter((m) => m.warn !== null || m.crit !== null);
    const candidates = withThresholds.length ? withThresholds : metrics;
    return [...candidates].sort((a, b) => utilPercent(b) - utilPercent(a))[0] ?? null;
});

const mainPerfRow = computed<PerfRow | null>(() =>
    mainMetric.value ? _toPerfRow(mainMetric.value) : null,
);

const otherPerfRows = computed<PerfRow[]>(() => {
    const main = mainMetric.value?.label;
    return perfRows.value.filter((r) => r.label !== main);
});

// Headline label/value above the bar — match what Checkmk's own Perf-O-Meter
// would show (e.g. "RAM usage" for Linux Memory). Falls back to the highest
// long-output percent line, then to the raw perf_data metric.
interface MainHeadline {
    label: string;
    valueLabel: string;
    pct: number;
    color: string;
}
const mainHeadline = computed<MainHeadline | null>(() => {
    const pf = perfometer.value;
    if (pf && pf.pcts.length > 0) {
        const pct = Math.min(100, pf.pcts[0]);
        // pf.label already encodes both name and value ("RAM 53.88%"), so we
        // don't repeat it as a separate detail line under the bar.
        return { label: pf.label, valueLabel: '', pct, color: utilColor(pct) };
    }
    const longRow = [...longOutputRows.value]
        .map((r) => {
            const pctMatch = r.value.match(/(\d+(?:\.\d+)?)\s*%/);
            return pctMatch && r.label ? { ...r, pct: parseFloat(pctMatch[1]) } : null;
        })
        .filter((r): r is NonNullable<typeof r> => r !== null)
        .sort((a, b) => b.pct - a.pct)[0];
    if (longRow) {
        const pct = Math.min(100, longRow.pct);
        return { label: longRow.label, valueLabel: longRow.value, pct, color: utilColor(pct) };
    }
    const row = mainPerfRow.value;
    if (!row) return null;
    return { label: row.label, valueLabel: row.valueLabel, pct: row.pct, color: row.color };
});

// Long output is a multi-line agent summary; each line tends to be
// "Label: <value>" — render as a structured two-column list instead of <pre>
// so it scans like a real summary table.
interface LongOutputRow {
    label: string;
    value: string;
}
const longOutputRows = computed<LongOutputRow[]>(() => {
    const raw = longOutputText.value;
    if (!raw) return [];
    return raw
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean)
        .map((line) => {
            const idx = line.indexOf(':');
            if (idx <= 0) return { label: '', value: line };
            return { label: line.slice(0, idx).trim(), value: line.slice(idx + 1).trim() };
        });
});

// Mini-graph data — fetched lazily when the Performance tab is visible.
// 4 hours window matches Checkmk's default Perf-O-Meter graph; it's enough to
// see "trending toward warn" without being noisy.
const HISTORY_MINUTES = 240;
const historyData = ref<Record<string, MetricPoint[]>>({});
let _historyReqId = 0;

async function _loadHistory(): Promise<void> {
    historyData.value = {};
    const obj = props.object;
    const connId = props.connectionId;
    if (
        !connId ||
        !auth.accessToken ||
        !obj?.host_name ||
        (obj.type !== 'host' && obj.type !== 'service')
    )
        return;
    const reqId = ++_historyReqId;
    try {
        const res = await connectionsApi.metricHistory(
            connId,
            obj.host_name,
            obj.type === 'service' ? (obj.service_description ?? null) : null,
            HISTORY_MINUTES,
            auth.accessToken,
        );
        if (reqId === _historyReqId) historyData.value = res.series ?? {};
    } catch {
        if (reqId === _historyReqId) historyData.value = {};
    }
}

// Refetch on selection change, but only when the Performance tab actually has
// content to show — otherwise we'd hit metric-history for hosts that don't
// expose perf_data at all.
watch(
    [
        () => props.object?.type,
        () => props.object?.host_name,
        () => props.object?.service_description,
        () => props.connectionId,
        showPerformanceTab,
    ],
    ([, , , , show]) => {
        if (show) void _loadHistory();
        else historyData.value = {};
    },
);

const mainHistoryKey = computed(() => {
    const main = mainMetric.value?.label;
    if (!main) return null;
    // metric-history keys come straight from Checkmk's metric IDs (perf_data
    // labels), so a direct match works for normal services.
    return main in historyData.value ? main : null;
});

const mainThresholds = computed(() => {
    const m = mainMetric.value;
    if (!m) return null;
    return { warn: m.warn, crit: m.crit };
});

const isDark = ref(document.documentElement.classList.contains('dark'));
useMutationObserver(
    document.documentElement,
    () => {
        isDark.value = document.documentElement.classList.contains('dark');
    },
    { attributes: true, attributeFilter: ['class'] },
);
</script>

<style scoped>
.detail-drawer {
    /* Mounted inside StatusSlideIn — the shell handles size, position and
       animation; this block only owns the inner column layout. */
    display: flex;
    flex-direction: column;
    flex: 1 1 auto;
    min-height: 0;
    border-left: 4px solid var(--detail-drawer-accent, var(--border));
}

.detail-drawer__severity-bar {
    height: 3px;
    flex-shrink: 0;
    background: var(--detail-drawer-accent, var(--border));
}

.detail-drawer__header {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
}

.detail-drawer__title {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.detail-drawer__title-row {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
}

.detail-drawer__name {
    font-weight: var(--font-weight-semibold);
    color: var(--text);
    font-size: 14px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    min-width: 0;
}

.detail-drawer__name--link {
    cursor: pointer;
    text-decoration: none;
}

.detail-drawer__name--link:hover,
.detail-drawer__name--link:focus-visible {
    color: var(--color-corporate-green-50, rgb(34 197 94));
    text-decoration: underline;
}

.detail-drawer__meta-link {
    color: inherit;
    text-decoration: none;
}

.detail-drawer__meta-link:hover,
.detail-drawer__meta-link:focus-visible {
    color: var(--color-corporate-green-50, rgb(34 197 94));
    text-decoration: underline;
}

.detail-drawer__type-pill {
    color: var(--text-muted);
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    background: var(--bg-hover);
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 1px 6px;
    flex-shrink: 0;
    font-weight: var(--font-weight-semibold);
}

.detail-drawer__state-line {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}

.detail-drawer__since-text {
    font-size: 12px;
    font-weight: var(--font-weight-semibold);
    color: var(--text);
}

.detail-drawer--critical .detail-drawer__since-text,
.detail-drawer--unreachable .detail-drawer__since-text,
.detail-drawer--warn .detail-drawer__since-text {
    color: var(--text);
}

.detail-drawer__close,
.detail-drawer__icon-btn {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: var(--bg-hover);
    color: var(--text-muted);
    border: none;
    cursor: pointer;
    font-size: 18px;
    line-height: 22px;
    text-align: center;
    padding: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    text-decoration: none;
    flex-shrink: 0;
}

.detail-drawer__icon-btn {
    color: var(--text);
}

.detail-drawer__close:hover,
.detail-drawer__icon-btn:hover {
    color: var(--color-corporate-green-50, rgb(34 197 94));
    background: var(--bg);
}

.detail-drawer__body {
    flex: 1 1 auto;
    overflow-y: auto;
    padding: 0;
    display: flex;
    flex-direction: column;
    min-height: 0;
}

.detail-drawer__tabs {
    flex: 1 1 auto;
    min-height: 0;
}

/* Override the vendor CmkTabs styling to fit the narrow Drawer: thin tab pills
   instead of the default boxy tab bar, no content-area border. */
/* stylelint-disable selector-pseudo-class-no-unknown */
.detail-drawer__tabs :deep(.cmk-tabs__list) {
    padding: 0 12px;
    background: var(--bg-surface);
    border-bottom: 1px solid var(--border);
}

.detail-drawer__tabs :deep(.cmk-tab__li) {
    padding: 6px 10px !important;
    font-size: 11px;
    line-height: 1;
    border-radius: 0;
    border-color: transparent;
    background: transparent;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    font-weight: var(--font-weight-semibold);
}

.detail-drawer__tabs :deep(.cmk-tab__li[data-state='active']) {
    color: var(--text);
    background: transparent;
    border-bottom: 2px solid var(--color-corporate-green-50, rgb(34 197 94));
}

.detail-drawer__tabs :deep(.cmk-tab-content) {
    border: none;
    padding: 0;
}
/* stylelint-enable selector-pseudo-class-no-unknown */

.detail-drawer__pane {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 12px 16px;
}

.detail-drawer__pane-section + .detail-drawer__pane-section {
    margin-top: 4px;
}

.detail-drawer__pane-heading {
    font-size: 10px;
    text-transform: uppercase;
    color: var(--text-muted);
    letter-spacing: 0.04em;
    font-weight: var(--font-weight-semibold);
    margin: 4px 0 6px;
}

.detail-drawer__tab-with-count {
    display: inline-flex;
    align-items: center;
    gap: 4px;
}

.detail-drawer__tab-count {
    background: color-mix(in srgb, var(--color-state-warning) 20%, transparent);
    color: var(--text);
    font-size: 9px;
    line-height: 14px;
    min-width: 16px;
    padding: 0 4px;
    border-radius: 999px;
    text-align: center;
    font-weight: var(--font-weight-bold);
}

.detail-drawer__row {
    display: flex;
    align-items: baseline;
    gap: 10px;
}

.detail-drawer__state-pill {
    font-weight: var(--font-weight-bold);
    font-size: 11px;
    letter-spacing: 0.04em;
    padding: 2px 10px;
    border-radius: 999px;
    border: 1px solid currentcolor;
}

.detail-drawer__badges {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}

.detail-drawer__badge {
    font-size: 10px;
    font-weight: var(--font-weight-semibold);
    padding: 2px 8px;
    border-radius: 999px;
}

.detail-drawer__badge--ack {
    background: rgb(251 191 36 / 15%);
    color: var(--color-yellow-50);
    border: 1px solid rgb(251 191 36 / 40%);
}

.detail-drawer__badge--downtime {
    background: rgb(59 130 246 / 15%);
    color: var(--color-blue-50, var(--text));
    border: 1px solid rgb(59 130 246 / 40%);
}

.detail-drawer__badge--stale,
.detail-drawer__badge--muted {
    background: rgb(113 113 122 / 15%);
    color: var(--text-muted);
    border: 1px solid rgb(113 113 122 / 40%);
}

.detail-drawer__badge--flapping {
    background: rgb(168 85 247 / 15%);
    color: var(--color-purple-50, #c084fc);
    border: 1px solid rgb(168 85 247 / 40%);
}

.detail-drawer__output {
    font-family: var(--font-mono, monospace);
    font-size: 11px;
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: var(--border-radius);
    padding: 8px 10px;
    margin: 4px 0 0;
    overflow: auto;
    white-space: pre-wrap;
    max-height: 180px;
}

/* Long agent output is dimmer than the summary so the eye lands on the
   short status line first. */
.detail-drawer__output--long {
    color: var(--text-muted);
    max-height: 240px;
}

.detail-drawer__section h4 {
    font-size: 10px;
    text-transform: uppercase;
    color: var(--text-muted);
    letter-spacing: 0.04em;
    margin: 6px 0 4px;
    font-weight: var(--font-weight-semibold);
}

.detail-drawer__meta {
    display: grid;
    grid-template-columns: 90px 1fr;
    gap: 4px 12px;
    margin: 0;
    font-size: 11px;
}

.detail-drawer__meta dt {
    color: var(--text-muted);
    text-transform: uppercase;
    font-size: 10px;
    letter-spacing: 0.04em;
    align-self: center;
}

.detail-drawer__meta dd {
    color: var(--text);
    margin: 0;
    overflow-wrap: anywhere;
}

/* Topology rows have variable-length labels ("Contact groups") and many chips
   that wouldn't fit in the 90px first column — stack vertically instead so
   each label gets its own line above the chips. */
.detail-drawer__meta--stacked {
    grid-template-columns: 1fr;
    gap: 6px;
}

.detail-drawer__meta--stacked dt {
    margin-top: 4px;
}

.detail-drawer__meta-value--warn {
    color: var(--color-yellow-50);
}

.detail-drawer__perf {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.detail-drawer__perf-row {
    display: grid;
    grid-template-columns: 80px 1fr 90px;
    gap: 8px;
    align-items: center;
    font-size: 11px;
}

.detail-drawer__perf-label {
    color: var(--text-muted);
    text-transform: uppercase;
    font-size: 9px;
    letter-spacing: 0.04em;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.detail-drawer__perf-bar-wrap {
    position: relative;
    height: 8px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 4px;
    overflow: hidden;
}

.detail-drawer__perf-bar-wrap--lg {
    height: 14px;
    border-radius: 6px;
}

/* Headline metric block — visually anchored at the top of the Performance
   tab so the operator sees the status-driving value without scanning. */
.detail-drawer__main-metric {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 4px 0 6px;
}

.detail-drawer__main-metric-head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 8px;
}

.detail-drawer__main-metric-label {
    color: var(--text-muted);
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: var(--font-weight-semibold);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.detail-drawer__main-metric-value {
    color: var(--text);
    font-size: 18px;
    font-weight: var(--font-weight-bold);
    font-variant-numeric: tabular-nums;
}

.detail-drawer__chart-wrap {
    height: 120px;
    margin: 4px 0;
}

/* Long output rendered as a label/value table — the human-readable summary
   that Checkmk already produces, so we treat it as the primary breakdown
   and skip duplicating the same data as bars below. */
.detail-drawer__output-rows {
    display: grid;
    grid-template-columns: minmax(80px, max-content) 1fr;
    gap: 3px 12px;
    margin: 0;
    font-size: 11px;
}

.detail-drawer__output-rows dt {
    color: var(--text-muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.detail-drawer__output-rows dd {
    color: var(--text);
    margin: 0;
    font-variant-numeric: tabular-nums;
    overflow-wrap: anywhere;
}

.detail-drawer__raw-metrics {
    border-top: 1px solid var(--border);
    padding-top: 6px;
}

.detail-drawer__raw-metrics > summary {
    cursor: pointer;
    color: var(--text-muted);
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: var(--font-weight-semibold);
    padding: 4px 0;
    user-select: none;
}

/* stylelint-disable-next-line no-descending-specificity */
.detail-drawer__raw-metrics[open] > summary {
    color: var(--text);
}

.detail-drawer__raw-metrics > .detail-drawer__perf {
    margin-top: 6px;
}

.detail-drawer__perf-bar {
    height: 100%;
    transition: width 0.2s ease;
}

.detail-drawer__perf-mark {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 1px;
}

.detail-drawer__perf-mark--warn {
    background: rgb(255 208 0 / 80%);
}

.detail-drawer__perf-mark--crit {
    background: rgb(248 113 113 / 80%);
}

.detail-drawer__perf-value {
    color: var(--text);
    text-align: right;
    font-variant-numeric: tabular-nums;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.detail-drawer__chips {
    /* Column count is set inline based on the chip count (zero-state chips are
       filtered out before render). */
    display: grid;
    gap: 6px;
}

.detail-drawer__chip {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1px;
    padding: 6px 4px;
    border-radius: var(--border-radius);
    border: 1px solid var(--border);
    background: var(--bg);
    color: var(--text);
    font: inherit;
    cursor: pointer;
    text-decoration: none;
    transition:
        transform 0.1s ease,
        border-color 0.1s ease;
}

.detail-drawer__chip:disabled {
    cursor: default;
}

.detail-drawer__chip:not(:disabled):hover {
    transform: translateY(-1px);
}

.detail-drawer__chip-count {
    font-size: 16px;
    font-weight: var(--font-weight-bold);
    line-height: 1;
}

.detail-drawer__chip-label {
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-muted);
    font-weight: var(--font-weight-semibold);
}

/* Chips track the global Checkmk state-color tokens (style.css) so they stay
   in sync with the rest of OrbVis/CMK. Background/border are tinted variants
   produced via color-mix; text uses the full state color. */
.detail-drawer__chip--crit {
    background: color-mix(in srgb, var(--color-state-critical) 12%, transparent);
    border-color: color-mix(in srgb, var(--color-state-critical) 35%, transparent);
}

.detail-drawer__chip--crit .detail-drawer__chip-count,
.detail-drawer__chip--crit .detail-drawer__chip-label {
    color: var(--color-state-critical);
}

.detail-drawer__chip--warn {
    background: color-mix(in srgb, var(--color-state-warning) 12%, transparent);
    border-color: color-mix(in srgb, var(--color-state-warning) 35%, transparent);
}

.detail-drawer__chip--warn .detail-drawer__chip-count,
.detail-drawer__chip--warn .detail-drawer__chip-label {
    color: var(--color-state-warning);
}

.detail-drawer__chip--unknown {
    background: color-mix(in srgb, var(--color-state-unknown) 12%, transparent);
    border-color: color-mix(in srgb, var(--color-state-unknown) 35%, transparent);
}

.detail-drawer__chip--unknown .detail-drawer__chip-count,
.detail-drawer__chip--unknown .detail-drawer__chip-label {
    color: var(--color-state-unknown);
}

.detail-drawer__chip--ok {
    background: color-mix(in srgb, var(--color-state-ok) 8%, transparent);
    border-color: color-mix(in srgb, var(--color-state-ok) 25%, transparent);
}

.detail-drawer__chip--ok .detail-drawer__chip-count,
.detail-drawer__chip--ok .detail-drawer__chip-label {
    color: var(--color-state-ok);
}

.detail-drawer__chip--zero {
    opacity: 0.45;
}

/* Inline chip rows for topology + labels sections — wraps the vendored
   CmkChip components with consistent spacing. */
.detail-drawer__chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin: 0;
}

.detail-drawer__label-key {
    color: var(--text-muted);
    margin-right: 4px;
}

/* Comments + downtimes lists share the row layout. */
.detail-drawer__list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.detail-drawer__list-row {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--border-radius);
    padding: 6px 8px;
    font-size: 11px;
}

.detail-drawer__list-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    color: var(--text-muted);
    font-size: 10px;
    margin-bottom: 2px;
    align-items: center;
}

.detail-drawer__list-author {
    color: var(--text);
    font-weight: var(--font-weight-semibold);
}

.detail-drawer__list-tag {
    background: rgb(59 130 246 / 18%);
    color: var(--color-blue-50, var(--text));
    border: 1px solid rgb(59 130 246 / 40%);
    border-radius: 999px;
    padding: 0 6px;
    font-weight: var(--font-weight-semibold);
    letter-spacing: 0.04em;
}

.detail-drawer__list-text {
    color: var(--text);
    overflow-wrap: anywhere;
    white-space: pre-wrap;
}

.detail-drawer__section--downtimes .detail-drawer__list-row {
    border: 1px solid rgb(59 130 246 / 35%);
    background: rgb(59 130 246 / 6%);
}

/* BI aggregation summary pane: per-leaf clickable rows. */
.detail-drawer__section--aggregation {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.detail-drawer__section-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    flex-wrap: wrap;
}

.detail-drawer__section-head .detail-drawer__section-heading {
    margin: 0;
}

.detail-drawer__tree-intro {
    color: var(--text-muted);
    font-size: 11px;
}

.detail-drawer__section--aggregation .detail-drawer__list {
    display: flex;
    flex-direction: column;
    gap: 4px;
    list-style: none;
    padding: 0;
    margin: 0;
}

.detail-drawer__section--aggregation .detail-drawer__list-row {
    display: grid;
    grid-template-columns: 8px 1fr auto;
    align-items: center;
    gap: 8px;
}

.detail-drawer__list-row--clickable {
    cursor: pointer;
}

.detail-drawer__list-row--clickable:hover {
    background: var(--bg-hover);
}

.detail-drawer__list-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--text-muted);
}

.detail-drawer__list-dot--ok {
    background: var(--color-green, #22c55e);
}

.detail-drawer__list-dot--warn {
    background: var(--color-yellow, #ffd000);
}

.detail-drawer__list-dot--crit {
    background: var(--color-red, #ef4444);
}

.detail-drawer__list-dot--unknown {
    background: var(--color-orange, #f97316);
}

.detail-drawer__list-state {
    font-family: var(--font-mono, monospace);
    font-size: 10px;
    color: var(--text-muted);
}

.detail-drawer__list-strong {
    font-weight: var(--font-weight-semibold);
    color: var(--text);
}

/* Stale-data hint inside the aggregation pane — same visual language as
 * the connection-down banner elsewhere in the SPA, dialed down for an
 * inline warning. */
.detail-drawer__stale-hint {
    color: var(--color-yellow, #f59e0b);
    font-style: italic;
    margin-top: 4px;
}

.detail-drawer__actions {
    border-top: 1px solid var(--border);
    padding: 12px 16px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    flex-shrink: 0;
    background: var(--bg-surface);
}

.detail-drawer__actions--site {
    gap: 6px;
}

.detail-drawer__actions-title {
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-muted);
    margin: 0;
    font-weight: var(--font-weight-semibold);
}

.detail-drawer__actions-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 6px;
    align-items: stretch;
}

/* CmkButton is inline-flex; stretch it across the grid cell so the actions
   line up. The --primary variant spans both columns for emphasis. */
.detail-drawer__action {
    width: 100%;
}

/* Override CmkButton's fixed height so wrapped long labels are not clipped;
   compound selector beats the scoped .cmk-button specificity. */
.detail-drawer__actions-grid .detail-drawer__action {
    height: auto;
    min-height: var(--dimension-10, 32px);
    padding-top: 4px;
    padding-bottom: 4px;
    line-height: 1.25;
}

.detail-drawer__action--primary {
    grid-column: span 2;
}

/* Summary acts as the More-actions toggle and styled to match a sibling
   CmkButton (optional variant). */
.detail-drawer__btn {
    display: inline-flex;
    height: var(--dimension-10, 32px);
    padding: 0 8px;
    align-items: center;
    justify-content: center;
    background-color: var(--default-button-optional-color, var(--bg));
    border: 1px solid var(--button-optional-border-color, var(--border));
    color: var(--button-optional-text-color, var(--text));
    border-radius: var(--dimension-3, var(--border-radius));
    font-size: 12px;
    font-weight: bold;
    cursor: pointer;
    text-align: center;
    text-decoration: none;
}

.detail-drawer__btn:hover {
    background: var(--bg-hover);
}

/* ── Group members tab ──────────────────────────────────────────────────── */

.detail-drawer__pane-empty {
    color: var(--text-muted);
    font-size: 12px;
    padding: 16px;
    text-align: center;
}

.detail-drawer__member-controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    margin-top: 12px;
    margin-bottom: 8px;
}

.detail-drawer__member-search {
    flex: 1;
    min-width: 0;
    background: var(--default-form-element-bg-color);
    border: 1px solid var(--default-form-element-border-color);
    color: var(--text);
    padding: 4px 8px;
    border-radius: var(--border-radius);
    font-size: 12px;
}

.detail-drawer__member-search:focus {
    outline: none;
    border-color: var(--color-corporate-green-50);
}

.detail-drawer__member-toggle {
    display: flex;
    align-items: center;
    gap: 4px;
    color: var(--text-muted);
    font-size: 11px;
    cursor: pointer;
    user-select: none;
    white-space: nowrap;
}

.detail-drawer__member-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
}

.detail-drawer__member-li {
    list-style: none;
}

.detail-drawer__member-row {
    display: grid;
    grid-template-columns: 24px 1fr auto;
    gap: 8px;
    align-items: start;
    padding: 6px 8px;
    border-radius: var(--border-radius);
    background: rgb(255 255 255 / 2%);
    border: none;
    width: 100%;
    text-align: left;
    color: inherit;
    font: inherit;
    cursor: pointer;
    transition: background 100ms ease;
}

.detail-drawer__member-row:hover {
    background: var(--bg-hover);
}

.detail-drawer__member-row:focus-visible {
    outline: 2px solid var(--color-corporate-green-50);
    outline-offset: -2px;
}

.detail-drawer__member-state {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    font-size: 11px;
    font-weight: 700;
    color: white;
}

.detail-drawer__member-state--ok {
    background: #22c55e;
}

.detail-drawer__member-state--warn {
    background: #ffd000;
    color: var(--button-primary-text-color, black);
}

.detail-drawer__member-state--crit {
    background: #ef4444;
}

.detail-drawer__member-state--unknown {
    background: #f97316;
}

.detail-drawer__member-state--pending {
    background: var(--text-muted);
}

.detail-drawer__member-body {
    min-width: 0;
}

.detail-drawer__member-name {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: var(--text);
}

.detail-drawer__member-svc {
    color: var(--text-muted);
    font-style: italic;
}

.detail-drawer__member-flag {
    font-size: 9px;
    font-weight: 700;
    padding: 1px 5px;
    border-radius: 3px;
    text-transform: uppercase;
}

.detail-drawer__member-flag--ack {
    background: rgb(245 158 11 / 20%);
    color: var(--color-mod-acknowledged);
}

.detail-drawer__member-flag--dt {
    background: rgb(59 130 246 / 20%);
    color: var(--color-mod-downtime);
}

.detail-drawer__member-flag--mute {
    background: rgb(113 113 122 / 30%);
    color: var(--color-mod-muted);
}

.detail-drawer__member-output {
    color: var(--text-muted);
    font-size: 11px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    margin-top: 1px;
}

.detail-drawer__member-since {
    color: var(--text-muted);
    font-size: 10px;
    white-space: nowrap;
    align-self: center;
    font-variant-numeric: tabular-nums;
}

.detail-drawer__member-truncated {
    color: var(--text-muted);
    font-size: 11px;
    text-align: center;
    margin-top: 8px;
    font-style: italic;
}
</style>
