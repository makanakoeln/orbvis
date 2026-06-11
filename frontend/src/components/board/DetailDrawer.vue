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
        '--detail-drawer-accent': state ? stateColor(state.state) : 'var(--border)'
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
              :aria-label="_t('Open in Checkmk')"
              >{{ displayName }}</a
            >
            <span v-else class="detail-drawer__name" :title="displayName">{{ displayName }}</span>
            <span class="detail-drawer__type-pill">{{ typeLabel }}</span>
          </div>
          <div v-if="state" class="detail-drawer__state-line">
            <span
              class="detail-drawer__state-pill"
              :style="{
                color: stateColor(state.state),
                borderColor: stateColor(state.state),
                background: stateBgColor(state.state)
              }"
            >
              {{ state.state }}
            </span>
            <span v-if="sinceText" class="detail-drawer__since-text">{{ sinceText }}</span>
          </div>
        </div>
        <a
          v-if="checkmkUrlFull"
          :href="checkmkUrlFull"
          target="_blank"
          rel="noopener noreferrer"
          class="detail-drawer__icon-btn"
          :title="_t('Open in Checkmk')"
          :aria-label="_t('Open in Checkmk')"
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
          :title="_t('Edit in Checkmk Setup')"
          :aria-label="_t('Edit in Checkmk Setup')"
        >
          <CmkIcon name="main-setup" size="small" />
        </a>
        <button
          type="button"
          class="detail-drawer__close"
          :title="_t('Close')"
          @click="emit('close')"
        >
          ×
        </button>
      </header>

      <div v-if="state" class="detail-drawer__body">
        <CmkTabs v-model="activeTab" class="detail-drawer__tabs">
          <template #tabs>
            <CmkTab id="status">{{ _t('Status') }}</CmkTab>
            <CmkTab v-if="showPerformanceTab" id="performance">{{ _t('Performance') }}</CmkTab>
            <CmkTab v-if="showContextTab" id="context">{{ _t('Context') }}</CmkTab>
            <CmkTab v-if="showMembersTab" id="members">
              <span class="detail-drawer__tab-with-count">
                {{ _t('Members') }}
                <span class="detail-drawer__tab-count">{{ groupMembers.length }}</span>
              </span>
            </CmkTab>
            <CmkTab v-if="showActivityTab" id="activity">
              <span class="detail-drawer__tab-with-count">
                {{ _t('Activity') }}
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

                <pre v-if="state.output" class="detail-drawer__output">{{ state.output }}</pre>

                <div
                  v-if="serviceChips.length"
                  class="detail-drawer__chips"
                  :style="{
                    gridTemplateColumns: `repeat(${serviceChips.length}, 1fr)`
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
                    <span class="detail-drawer__chip-count">{{ chip.count }}</span>
                    <span class="detail-drawer__chip-label">{{ chip.label }}</span>
                  </component>
                </div>

                <div
                  v-if="hostChips.length"
                  class="detail-drawer__chips"
                  :style="{
                    gridTemplateColumns: `repeat(${hostChips.length}, 1fr)`
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
                    <span class="detail-drawer__chip-count">{{ chip.count }}</span>
                    <span class="detail-drawer__chip-label">{{ chip.label }}</span>
                  </component>
                </div>

                <dl v-if="metaRows.length || checkInfoRows.length" class="detail-drawer__meta">
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
                    <dd :class="row.tone ? `detail-drawer__meta-value--${row.tone}` : ''">
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
                      {{ _t('Aggregation') }}
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
                      gridTemplateColumns: `repeat(${activeChips.length}, 1fr)`
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
                      <span class="detail-drawer__chip-count">{{ chip.count }}</span>
                      <span class="detail-drawer__chip-label">{{ chip.label }}</span>
                    </button>
                  </div>

                  <!-- Worst-leaf path only fits the Details view; once the list
                                         is cut at a tree depth, naming a deeper leaf is misleading. -->
                  <div
                    v-if="aggregationView === 'details' && aggregationSummary.worstPath"
                    class="detail-drawer__list-text"
                  >
                    {{ _t('Worst leaf') }}:
                    <span class="detail-drawer__list-strong">{{
                      aggregationSummary.worstPath
                    }}</span>
                    <div v-if="aggregationSummary.worstOutput" class="detail-drawer__worst-output">
                      {{ aggregationSummary.worstOutput }}
                    </div>
                  </div>
                  <div
                    v-if="aggregationView === 'summary'"
                    class="detail-drawer__list-text detail-drawer__tree-intro"
                  >
                    {{
                      _t('%{count} nodes at depth %{depth} below the root.', {
                        count: aggregationSummary.treeRows.length,
                        depth: aggregationSummary.treeDepth
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
                    ⚠
                    {{
                      _t(
                        'Connection to at least one federation site is unhealthy — leaf states shown may be out of date.'
                      )
                    }}
                  </div>
                  <!-- Bulk-ack always targets real bi_leaf hosts/services —
                                         that's what Checkmk's command pipeline accepts. -->
                  <button
                    v-if="aggregationProblemLeaves.length && canCommand('acknowledge')"
                    type="button"
                    class="detail-drawer__action-btn"
                    @click="onBulkAcknowledgeClick"
                  >
                    {{
                      _t('Acknowledge %{count} contributing leaves', {
                        count: aggregationProblemLeaves.length
                      })
                    }}
                  </button>
                  <ul v-if="aggregationListRows.length" class="detail-drawer__list">
                    <li
                      v-for="row in aggregationListRows"
                      :key="row.id"
                      class="detail-drawer__list-row"
                      :class="{
                        'detail-drawer__list-row--clickable': !!row.hostName
                      }"
                      :title="row.output || undefined"
                      @click="onAggregationLeafClick(row)"
                    >
                      <span
                        class="detail-drawer__list-dot"
                        :class="`detail-drawer__list-dot--${row.tone}`"
                      />
                      <span class="detail-drawer__list-text">
                        <span
                          v-if="aggregationListMultiHost && row.hostName && row.serviceDescription"
                          class="detail-drawer__list-host"
                          >{{ row.hostName }} ·
                        </span>
                        {{ row.label }}
                      </span>
                      <span class="detail-drawer__list-state">{{ row.stateLabel }}</span>
                    </li>
                  </ul>
                </section>
              </div>
            </CmkTabContent>

            <CmkTabContent v-if="showPerformanceTab" id="performance" spacing="none">
              <div class="detail-drawer__pane">
                <div v-if="mainHeadline" class="detail-drawer__main-metric">
                  <div class="detail-drawer__main-metric-head">
                    <span class="detail-drawer__main-metric-label">{{ mainHeadline.label }}</span>
                  </div>
                  <div class="detail-drawer__perf-bar-wrap detail-drawer__perf-bar-wrap--lg">
                    <div
                      class="detail-drawer__perf-bar"
                      :style="{
                        width: mainHeadline.pct + '%',
                        background: mainHeadline.color
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
                  <div v-if="mainHeadline.valueLabel" class="detail-drawer__main-metric-value">
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

                <div v-if="longOutputRows.length" class="detail-drawer__pane-section">
                  <div class="detail-drawer__pane-heading">
                    {{ _t('Details') }}
                  </div>
                  <dl class="detail-drawer__output-rows">
                    <template v-for="(row, i) in longOutputRows" :key="i">
                      <dt v-if="row.label">{{ row.label }}</dt>
                      <dd>{{ row.value }}</dd>
                    </template>
                  </dl>
                </div>

                <details v-if="otherPerfRows.length" class="detail-drawer__raw-metrics">
                  <summary>
                    {{
                      _t('Raw metrics (%{n})', {
                        n: otherPerfRows.length
                      })
                    }}
                  </summary>
                  <div class="detail-drawer__perf">
                    <div
                      v-for="row in otherPerfRows"
                      :key="row.label"
                      class="detail-drawer__perf-row"
                    >
                      <div class="detail-drawer__perf-label" :title="row.label">
                        {{ row.label }}
                      </div>
                      <div class="detail-drawer__perf-bar-wrap">
                        <div
                          class="detail-drawer__perf-bar"
                          :style="{
                            width: row.pct + '%',
                            background: row.color
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
                <dl v-if="contextMetaRowsWithoutCheckCmd.length" class="detail-drawer__meta">
                  <template v-for="row in contextMetaRowsWithoutCheckCmd" :key="row.label">
                    <dt>{{ row.label }}</dt>
                    <dd :class="row.tone ? `detail-drawer__meta-value--${row.tone}` : ''">
                      {{ row.value }}
                    </dd>
                  </template>
                </dl>

                <div v-if="checkCommandRow">
                  <div class="detail-drawer__pane-heading">
                    {{ checkCommandRow.label }}
                  </div>
                  <CmkCode :code-text="checkCommandRow.value" width="fill" />
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
                          group.isHostList && canSelectHost(item) ? emit('select-host', item) : null
                        "
                      >
                        {{ item }}
                      </CmkChip>
                    </dd>
                  </template>
                </dl>

                <div v-if="labelEntries.length">
                  <div class="detail-drawer__pane-heading">
                    {{ _t('Labels') }}
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
                        <span class="detail-drawer__label-key">{{ key }}</span>
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
                    gridTemplateColumns: `repeat(${memberChips.length}, 1fr)`
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
                    <span class="detail-drawer__chip-count">{{ chip.count }}</span>
                    <span class="detail-drawer__chip-label">{{ chip.label }}</span>
                  </button>
                </div>

                <div class="detail-drawer__member-controls">
                  <input
                    v-model="memberSearch"
                    type="search"
                    :placeholder="_t('Search members…')"
                    class="detail-drawer__member-search"
                  />
                  <CmkCheckbox v-model="onlyProblems" :label="_t('Only problems')" />
                </div>

                <p v-if="loadingMembers" class="detail-drawer__pane-empty">
                  {{ _t('Loading…') }}
                </p>
                <p v-else-if="filteredMembers.length === 0" class="detail-drawer__pane-empty">
                  {{ _t('No members match the current filter') }}
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
                        _t('Open %{name} in the drawer', {
                          name: m.service ? m.host + ' / ' + m.service : m.host
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
                          <span v-if="m.service" class="detail-drawer__member-svc">{{
                            m.service
                          }}</span>
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
                        <div v-if="m.output" class="detail-drawer__member-output" :title="m.output">
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
                <p v-if="truncatedMemberCount > 0" class="detail-drawer__member-truncated">
                  {{
                    _t('+%{n} more — refine the filter to see them', {
                      n: truncatedMemberCount
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
                    {{ _t('Active downtimes') }}
                  </div>
                  <ul class="detail-drawer__list">
                    <li v-for="dt in downtimeList" :key="dt.id" class="detail-drawer__list-row">
                      <div class="detail-drawer__list-meta">
                        <span class="detail-drawer__list-author">{{ dt.author }}</span>
                        <span
                          v-if="!dt.fixed"
                          class="detail-drawer__list-tag"
                          :title="_t('Flexible (triggered) downtime')"
                          >FLEX</span
                        >
                        <span class="detail-drawer__list-time">{{ dt.timeRange }}</span>
                      </div>
                      <div v-if="dt.comment" class="detail-drawer__list-text">
                        {{ dt.comment }}
                      </div>
                    </li>
                  </ul>
                </div>

                <div v-if="commentList.length" class="detail-drawer__pane-section">
                  <div class="detail-drawer__pane-heading">
                    {{ _t('Comments') }}
                  </div>
                  <ul class="detail-drawer__list">
                    <li v-for="c in commentList" :key="c.id" class="detail-drawer__list-row">
                      <div class="detail-drawer__list-meta">
                        <span class="detail-drawer__list-author">{{ c.author }}</span>
                        <span class="detail-drawer__list-time">{{ c.age }}</span>
                        <span v-if="c.expires" class="detail-drawer__list-time">
                          ·
                          {{ _t('expires') }}
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

      <!-- Aggregations get no host/service command footer: the commands
           dispatch via host_name/service_description, which BI aggregation
           objects don't carry — every button would be a silent no-op. The
           aggregation pane's "Acknowledge N contributing leaves" bulk action
           targets the real bi_leaf hosts/services instead. -->
      <footer v-if="!isSite && !isAggregation" class="detail-drawer__actions">
        <h4 class="detail-drawer__actions-title">
          {{ _t('Actions') }}
        </h4>
        <div class="detail-drawer__actions-grid">
          <CmkButton
            v-if="!state?.acknowledged && (isProblematic || isGroup) && canCommand('acknowledge')"
            variant="success"
            class="detail-drawer__action detail-drawer__action--primary"
            :title="
              isGroup
                ? _t('Acknowledge problems on all %{n} members of this group', {
                    n: groupMembers.length
                  })
                : ''
            "
            @click="emit('acknowledge')"
          >
            {{ isGroup ? _t('Acknowledge (%{n})', { n: groupMembers.length }) : _t('Acknowledge') }}
          </CmkButton>
          <CmkButton
            v-if="state?.acknowledged && canCommand('remove_acknowledgement')"
            variant="warning"
            class="detail-drawer__action"
            @click="emit('remove-ack')"
          >
            {{ _t('Remove ACK') }}
          </CmkButton>
          <CmkButton
            v-if="canCommand('force_check')"
            variant="optional"
            class="detail-drawer__action"
            @click="emit('force-check')"
          >
            {{ _t('Force check') }}
          </CmkButton>
          <CmkButton
            v-if="!state?.in_downtime && canCommand('schedule_downtime')"
            variant="optional"
            class="detail-drawer__action"
            :title="
              isGroup
                ? _t('Schedule downtime on all %{n} members of this group', {
                    n: groupMembers.length
                  })
                : ''
            "
            @click="emit('schedule-downtime')"
          >
            {{
              isGroup ? _t('Downtime (%{n})', { n: groupMembers.length }) : _t('Schedule downtime')
            }}
          </CmkButton>
          <CmkButton
            v-if="state?.in_downtime && canCommand('remove_downtime')"
            variant="warning"
            class="detail-drawer__action"
            @click="emit('remove-downtime')"
          >
            {{ _t('Remove downtime') }}
          </CmkButton>
          <CmkButton
            v-if="!isAggregation && canCommand('add_comment')"
            variant="optional"
            class="detail-drawer__action"
            @click="emit('add-comment')"
          >
            {{ _t('Add comment') }}
          </CmkButton>
          <CmkButton
            v-if="canCommand('disable_notifications') && state?.notifications_enabled !== false"
            variant="optional"
            class="detail-drawer__action"
            @click="emit('disable-notifications')"
          >
            {{ _t('Disable notifications') }}
          </CmkButton>
          <CmkButton
            v-else-if="canCommand('enable_notifications')"
            variant="optional"
            class="detail-drawer__action"
            @click="emit('enable-notifications')"
          >
            {{ _t('Enable notifications') }}
          </CmkButton>
        </div>
      </footer>

      <footer v-else-if="isSite" class="detail-drawer__actions detail-drawer__actions--site">
        <CmkButton
          v-if="problemsUrlFull"
          variant="success"
          :href="problemsUrlFull"
          target="_blank"
          rel="noopener noreferrer"
          class="detail-drawer__action detail-drawer__action--primary"
        >
          {{ _t('Show problems') }} ↗
        </CmkButton>
      </footer>
    </div>
  </StatusSlideIn>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'

import CmkCheckbox from '@/components/cmk/user-input/CmkCheckbox'

import { useAggregationDetail } from '@/composables/useAggregationDetail'
import { useGroupMembers } from '@/composables/useGroupMembers'
import { useMetricUnits } from '@/composables/useMetricUnits'
import { useObjectDetailsFetch } from '@/composables/useObjectDetailsFetch'
import { usePerformanceHistory } from '@/composables/usePerformanceHistory'
import { usePerformanceMetrics } from '@/composables/usePerformanceMetrics'
import { useSummaryChips } from '@/composables/useSummaryChips'
import { useIsDark } from '@/composables/useTheme'
import { useAuthStore } from '@/stores/auth'
import type { BoardObject, BulkAckTarget, ObjectState } from '@/types/api'
import { buildCheckmkUrl, stripCheckmkBase } from '@/utils/boardNavigation'
import { getBoardObjectName, getObjectTypeLabel } from '@/utils/naming'
import { stateColor } from '@/utils/stateColors'
import { formatRelativeDuration, formatRelativeFuture } from '@/utils/time'
import CmkButton from '@/vendor/cmk/components/CmkButton'
import CmkChip from '@/vendor/cmk/components/CmkChip.vue'
import CmkCode from '@/vendor/cmk/components/CmkCode.vue'
import CmkIcon from '@/vendor/cmk/components/CmkIcon'
import CmkTabs, { CmkTab, CmkTabContent } from '@/vendor/cmk/components/CmkTabs'
import CmkToggleButtonGroup from '@/vendor/cmk/components/CmkToggleButtonGroup.vue'
import usei18n from '@/vendor/cmk/lib/i18n'

import MetricChart from './MetricChart.vue'
import StatusSlideIn from './StatusSlideIn.vue'

function stateBgColor(state: string): string {
  const c = stateColor(state)
  if (c.startsWith('#') && c.length === 7) {
    const r = parseInt(c.slice(1, 3), 16)
    const g = parseInt(c.slice(3, 5), 16)
    const b = parseInt(c.slice(5, 7), 16)
    return `rgba(${r}, ${g}, ${b}, 0.12)`
  }
  return c
}

const props = defineProps<{
  object: BoardObject | null
  state?: ObjectState | undefined
  checkmkUrl?: string | null
  /** Board's connection_id — used to fetch on-demand object details. */
  connectionId?: string | null
  /** CSS selector for the StatusSlideIn portal target. Defaults to body. */
  portalTarget?: string
  /** Hostnames currently on the board — topology entries to those hosts
   * become clickable buttons that emit `select-host` for the parent to act on. */
  selectableHosts?: string[]
  readonly?: boolean
}>()

const portalTarget = computed(() => props.portalTarget ?? 'body')

const emit = defineEmits<{
  close: []
  acknowledge: []
  'remove-ack': []
  'schedule-downtime': []
  'remove-downtime': []
  'force-check': []
  'add-comment': []
  'enable-notifications': []
  'disable-notifications': []
  /** Host name picked from the topology section — board may highlight + select it.
   *  ``seed`` carries a node-derived ObjectState (sans object_id) so drilldowns
   *  into objects without a board state entry still render a status pane. */
  'select-host': [
    hostName: string,
    serviceDescription?: string | null,
    seed?: Omit<ObjectState, 'object_id'> | null
  ]
  /** Bulk-acknowledge contributing leaves of a BI aggregation. */
  'bulk-acknowledge': [targets: BulkAckTarget[]]
}>()

const selectableHostSet = computed(() => new Set(props.selectableHosts ?? []))
function canSelectHost(host: string): boolean {
  return selectableHostSet.value.has(host)
}

// CMC reschedules checks sub-second, so `next_check` lags behind "now"
// between checks even when the host is healthy. Don't paint "overdue"
// until the LAST check is itself stale by this many seconds.
const OVERDUE_GRACE_SECONDS = 60

// Drives age/overdue labels so they tick forward without a state push.
const nowMs = ref(Date.now())
let _tick: ReturnType<typeof setInterval> | null = null
onMounted(() => {
  _tick = setInterval(() => {
    nowMs.value = Date.now()
  }, 1000)
})
onUnmounted(() => {
  if (_tick) clearInterval(_tick)
  _tick = null
})

const auth = useAuthStore()

const canCommand = (verb: string): boolean => !props.readonly && auth.mayCommand(verb)

// On-demand details (long_output, comments, downtimes, topology, metric
// titles) + CMK perfometer, kept off the streamed ObjectState because they're
// large and rarely change.
const { details, perfometer } = useObjectDetailsFetch({
  object: () => props.object,
  connectionId: () => props.connectionId,
  accessToken: () => auth.accessToken
})

// Registered display units so the Performance tab's value labels match the
// Checkmk GUI (IEC for memory, auto-scaled time, …).
const drawerMetricUnits = useMetricUnits({
  connectionId: () => props.object?.connection_id ?? props.connectionId,
  hostName: () => props.object?.host_name,
  serviceDescription: () => props.object?.service_description,
  perfData: () => props.state?.perf_data,
  enabled: () => !!props.object?.host_name && !!props.object?.service_description
})

// Hostgroup / Servicegroup / dyngroup member-list — drives the Members tab.
const {
  groupMembers,
  loadingMembers,
  memberSearch,
  onlyProblems,
  filteredMembers,
  visibleMembers,
  truncatedMemberCount,
  memberChips,
  memberStateTone,
  memberStateBadge,
  isGroup
} = useGroupMembers({
  object: () => props.object,
  connectionId: () => props.connectionId,
  accessToken: () => auth.accessToken
})

const isAggregation = computed(() => props.object?.type === 'aggregation')

function formatRelativeAge(ts: number | null | undefined): string {
  return formatRelativeDuration(ts, nowMs.value)
}

function formatLocaleTime(ts: number | null | undefined): string {
  if (!ts) return ''
  return new Date(ts * 1000).toLocaleString()
}

const PROBLEM_STATES = new Set(['CRITICAL', 'WARNING', 'UNKNOWN', 'DOWN', 'UNREACHABLE'])
const isProblematic = computed(() => (props.state ? PROBLEM_STATES.has(props.state.state) : false))
const isSite = computed(() => props.object?.type === 'site')
const severityKind = computed(() => {
  const s = props.state?.state
  if (!s) return 'pending'
  if (s === 'CRITICAL' || s === 'DOWN') return 'critical'
  if (s === 'UNREACHABLE') return 'unreachable'
  if (s === 'WARNING' || s === 'UNKNOWN') return 'warn'
  if (s === 'OK' || s === 'UP') return 'ok'
  return 'pending'
})

const { _t } = usei18n()

const displayName = computed(() => (props.object ? getBoardObjectName(props.object) : ''))
const typeLabel = computed(() => (props.object ? getObjectTypeLabel(props.object) : ''))

const checkmkUrlFull = computed(() =>
  props.object
    ? buildCheckmkUrl(props.object, props.checkmkUrl ?? null, props.state?.site_id)
    : null
)
const {
  checkmkSetupUrlFull,
  aggregationSummary,
  aggregationView,
  aggregationViewOptions,
  setAggregationView,
  aggregationListRows,
  aggregationListMultiHost,
  activeChips,
  onAggregationLeafClick,
  aggregationProblemLeaves,
  onBulkAcknowledgeClick
} = useAggregationDetail({
  object: () => props.object,
  state: () => props.state,
  checkmkUrl: () => props.checkmkUrl,
  connectionId: () => props.connectionId,
  accessToken: () => auth.accessToken,
  onSelectHost: (host, service, seed) => emit('select-host', host, service, seed),
  onBulkAcknowledge: (targets) => emit('bulk-acknowledge', targets)
})

const problemsUrlFull = computed(() => {
  if (!props.object || props.object.type !== 'site' || !props.checkmkUrl) return null
  const base = stripCheckmkBase(props.checkmkUrl)
  const siteId = props.object.host_name ?? props.state?.site_id
  if (!siteId) return null
  // svcproblems' built-in defaults (CRIT/WARN/UNKN active) are exactly what
  // the operator wants here — no filled_in, just the site scope.
  const params = new URLSearchParams({
    view_name: 'svcproblems',
    site: siteId
  })
  return `${base}/check_mk/view.py?${params}`
})

const sinceText = computed(() => {
  const duration = formatRelativeDuration(props.state?.last_state_change, nowMs.value)
  return duration ? _t('since %{duration}', { duration }) : null
})

const { serviceChips, hostChips } = useSummaryChips({
  object: () => props.object,
  state: () => props.state,
  checkmkUrl: () => props.checkmkUrl,
  isSite: () => isSite.value
})

interface Modifier {
  label: string
  kind: 'ack' | 'downtime' | 'stale' | 'muted' | 'flapping'
}
const modifiers = computed<Modifier[]>(() => {
  const s = props.state
  if (!s) return []
  const list: Modifier[] = []
  if (s.acknowledged) list.push({ label: 'ACK', kind: 'ack' })
  if (s.in_downtime) list.push({ label: 'DOWNTIME', kind: 'downtime' })
  if (s.stale) list.push({ label: 'STALE', kind: 'stale' })
  if (s.notifications_enabled === false) list.push({ label: 'MUTED', kind: 'muted' })
  if (details.value?.is_flapping) list.push({ label: 'FLAPPING', kind: 'flapping' })
  return list
})

const {
  perfRows,
  mainMetric,
  mainPerfRow,
  otherPerfRows,
  mainHeadline,
  longOutputRows,
  longOutputText
} = usePerformanceMetrics({
  state: () => props.state,
  details,
  perfometer,
  metricUnits: drawerMetricUnits
})

interface MetaRow {
  label: string
  value: string
  tone?: 'warn' | undefined
  href?: string | null
}

// Service drawers list the parent host as a metadata row; link it to the
// host's "Status of host" view (Nagios-familiar: both the title and the host
// name are clickable). Reuses buildCheckmkUrl by switching the object to a
// host so the same site/base-URL resolution applies.
const hostStatusUrl = computed(() => {
  const o = props.object
  if (o?.type !== 'service' || !o.host_name) return null
  return buildCheckmkUrl(
    { ...o, type: 'host', service_description: null },
    props.checkmkUrl ?? null,
    props.state?.site_id
  )
})

const metaRows = computed<MetaRow[]>(() => {
  const s = props.state
  const o = props.object
  if (!s) return []
  const rows: MetaRow[] = []
  if (s.alias && s.alias !== displayName.value) {
    rows.push({ label: 'Alias', value: s.alias })
  }
  if (s.address) rows.push({ label: 'Address', value: s.address })
  if (o?.type === 'service' && o.host_name) {
    rows.push({
      label: _t('Host'),
      value: o.host_name,
      href: hostStatusUrl.value
    })
  }
  // For site drawers, the site name is already the title — no point repeating it.
  if (s.site_id && o?.type !== 'site') {
    rows.push({ label: _t('Site'), value: s.site_id })
  }
  return rows
})

const checkInfoRows = computed<MetaRow[]>(() => {
  const s = props.state
  if (!s) return []
  const rows: MetaRow[] = []
  const now = Math.floor(Date.now() / 1000)

  // Aggregators have no check attempts of their own — 0/0 would confuse.
  const objType = props.object?.type
  const isAggregator =
    objType === 'aggregation' ||
    objType === 'hostgroup' ||
    objType === 'servicegroup' ||
    objType === 'dyngroup'
  if (
    !isAggregator &&
    typeof s.current_attempt === 'number' &&
    typeof s.max_attempts === 'number'
  ) {
    const isSoft = s.state_type === 'SOFT' || s.state_type === 'soft'
    rows.push({
      label: _t('Attempt'),
      value: _t('%{current}/%{max} (%{type})', {
        current: s.current_attempt,
        max: s.max_attempts,
        type: isSoft ? _t('soft') : _t('hard')
      }),
      tone: isSoft ? 'warn' : undefined
    })
  }

  if (s.last_check && s.last_check > 0) {
    rows.push({
      label: _t('Last check'),
      value: _t('%{duration} ago', {
        duration: formatRelativeDuration(s.last_check, nowMs.value)
      })
    })
  } else if (s.last_check === 0) {
    rows.push({
      label: _t('Last check'),
      value: _t('never')
    })
  }

  if (s.next_check && s.next_check > 0) {
    if (s.next_check < now) {
      // CMC keeps `next_check` slightly behind "now" between checks
      // because it reschedules sub-second. Suppress "overdue" while
      // the LAST check is recent — only flag it if the check chain
      // really has stalled.
      const sinceLastCheck = s.last_check && s.last_check > 0 ? now - s.last_check : Infinity
      if (sinceLastCheck >= OVERDUE_GRACE_SECONDS) {
        rows.push({
          label: _t('Next check'),
          value: `${_t('overdue')} (${formatRelativeDuration(s.next_check, nowMs.value)})`,
          tone: 'warn'
        })
      }
    } else {
      rows.push({
        label: _t('Next check'),
        value: _t('in %{duration}', {
          // An imminent check (sub-second away) formats to '' — show
          // '<1s' so the row never reads a dangling "in ".
          duration: formatRelativeFuture(s.next_check, nowMs.value) || '<1s'
        })
      })
    }
  }

  const d = details.value
  // Service-only: when did this check last go OK? Lets the operator see
  // "broken for 2 days" vs. "just flipped" without leaving the drawer.
  if (d?.last_time_ok && d.last_time_ok > 0 && s.state !== 'OK') {
    rows.push({
      label: _t('Last OK'),
      value: _t('%{duration} ago', {
        duration: formatRelativeDuration(d.last_time_ok, nowMs.value)
      })
    })
  }

  return rows
})

// Topology / membership / labels — from on-demand details. Empty groups are
// hidden so the drawer stays compact when nothing useful is set.
interface TopologyGroup {
  label: string
  items: string[]
  /** Optional Checkmk-style hostname links (parents, children) */
  isHostList?: boolean
}
const topologyGroups = computed<TopologyGroup[]>(() => {
  const d = details.value
  if (!d) return []
  const out: TopologyGroup[] = []
  if (d.parents.length) out.push({ label: _t('Parents'), items: d.parents, isHostList: true })
  if (d.children.length) out.push({ label: _t('Children'), items: d.children, isHostList: true })
  if (d.host_groups.length) out.push({ label: _t('Host groups'), items: d.host_groups })
  if (d.service_groups.length) out.push({ label: _t('Service groups'), items: d.service_groups })
  if (d.contact_groups.length) out.push({ label: _t('Contact groups'), items: d.contact_groups })
  return out
})

const labelEntries = computed(() => Object.entries(details.value?.labels ?? {}))

interface Comment {
  id: number
  author: string
  text: string
  age: string
  expires: string | null
}
const commentList = computed<Comment[]>(() => {
  const list = details.value?.comments ?? []
  return list.map((c) => ({
    id: c.id,
    author: c.author || '?',
    text: c.comment,
    age: _t('%{duration} ago', {
      duration: formatRelativeDuration(c.entry_time, nowMs.value)
    }),
    expires:
      c.expire_time && c.expire_time > 0
        ? _t('in %{duration}', {
            duration: formatRelativeFuture(c.expire_time, nowMs.value)
          })
        : null
  }))
})

interface Downtime {
  id: number
  author: string
  comment: string
  timeRange: string
  fixed: boolean
}
function fmtDateTime(ts: number): string {
  return new Date(ts * 1000).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}
const downtimeList = computed<Downtime[]>(() => {
  const list = details.value?.downtimes ?? []
  return list.map((d) => ({
    id: d.id,
    author: d.author || '?',
    comment: d.comment,
    timeRange: `${fmtDateTime(d.start_time)} → ${fmtDateTime(d.end_time)}`,
    fixed: d.fixed
  }))
})

// Tab visibility — only show tabs that actually have content. The Status tab
// always renders (output + state badges + chips); others appear conditionally.
const showPerformanceTab = computed(() => perfRows.value.length > 0 || !!longOutputText.value)
const showContextTab = computed(
  () =>
    topologyGroups.value.length > 0 ||
    labelEntries.value.length > 0 ||
    contextMetaRows.value.length > 0
)
const showActivityTab = computed(
  () => commentList.value.length > 0 || downtimeList.value.length > 0
)
const showMembersTab = computed(() => isGroup.value)

const activeTab = ref('status')

watch([() => props.object?.host_name, () => props.object?.service_description], () => {
  // Reset to overview whenever the user picks a different object so they
  // don't land on an empty tab from the previous selection.
  activeTab.value = 'status'
})

interface MetaRow2 {
  label: string
  value: string
  tone?: 'warn' | undefined
}

const contextMetaRows = computed<MetaRow2[]>(() => {
  const d = details.value
  const rows: MetaRow2[] = []
  if (!d) return rows
  if (d.check_command) rows.push({ label: _t('Check command'), value: d.check_command })
  if (typeof d.latency === 'number' && d.latency >= 0) {
    rows.push({
      label: _t('Latency'),
      value: `${(d.latency * 1000).toFixed(0)} ms`
    })
  }
  if (d.notification_period && d.notification_period !== '24X7') {
    rows.push({
      label: _t('Notif. period'),
      value: d.notification_period,
      tone: d.in_notification_period ? undefined : 'warn'
    })
  }
  return rows
})

// Check command gets its own CmkCode block — it's typically long and benefits
// from monospace + horizontal scroll, while latency / notif. period stay in
// the regular dt/dd grid.
const checkCommandRow = computed<MetaRow2 | null>(
  () => contextMetaRows.value.find((r) => r.label === _t('Check command')) ?? null
)
const contextMetaRowsWithoutCheckCmd = computed<MetaRow2[]>(() =>
  contextMetaRows.value.filter((r) => r.label !== _t('Check command'))
)

const { historyData, mainHistoryKey, mainThresholds, HISTORY_MINUTES } = usePerformanceHistory({
  object: () => props.object,
  connectionId: () => props.connectionId,
  accessToken: () => auth.accessToken,
  mainMetric,
  showPerformanceTab: () => showPerformanceTab.value
})

const isDark = useIsDark()
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

/* Worst-leaf plugin output — secondary line under the path so the operator
 * sees the failure reason without drilling into the leaf. */
.detail-drawer__worst-output {
  margin-top: 2px;
  color: var(--text-muted);
  font-size: var(--font-size-small);
  overflow-wrap: anywhere;
}

/* Host prefix on service-leaf rows of multi-host aggregations. */
.detail-drawer__list-host {
  color: var(--text-muted);
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
