<template>
  <div class="orb-board">
    <!-- Slim map-specific topbar -->
    <div v-if="!isKiosk && !isPreview" class="orb-board__topbar">
      <!-- Left: Checkmk-style breadcrumb -->
      <div class="orb-board__crumb">
        <CmkBreadcrumb :items="breadcrumbItems" />
      </div>

      <div
        class="orb-board__topbar-actions"
        :class="drawerObject ? 'orb-board__topbar-actions--dimmed' : ''"
      >
        <!-- Flow problems pill (informational; layout switch lives in
                     the dedicated bottom-right toggle, no need for a CTA here) -->
        <span
          v-if="isFlowmap && flowProblems.total > 0"
          class="orb-board__pill"
          :class="
            flowProblems.critical > 0 ? 'orb-board__pill--critical' : 'orb-board__pill--warning'
          "
          :title="
            _t(
              '%{total} service issues (%{critical} critical, %{warning} warning) across %{hostsWithProblems} hosts',
              flowProblems
            )
          "
        >
          <svg
            style="width: 10px; height: 10px"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2.5"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
            />
          </svg>
          {{ _t('%{critical} crit · %{warning} warn', flowProblems) }}
        </span>

        <!-- Connection status -->
        <div
          class="orb-board__pill"
          :class="statesStore.connected ? 'orb-board__pill--ok' : 'orb-board__pill--offline'"
        >
          <span
            class="orb-board__dot"
            :class="statesStore.connected ? 'orb-board__dot--ok' : 'orb-board__dot--offline'"
          />
          {{ statesStore.connected ? _t('Live') : _t('Offline') }}
        </div>

        <!-- Notification bell -->
        <button
          v-if="!auth.ssoActive && !auth.isCheckmkDeployment"
          class="orb-board__topbtn"
          :class="statesStore.notificationsEnabled ? 'orb-board__topbtn--alert' : ''"
          :title="
            statesStore.notificationsEnabled
              ? _t('Browser notifications enabled — click to disable')
              : _t('Enable browser notifications for state changes')
          "
          @click="statesStore.toggleNotifications()"
        >
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
              d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0"
            />
          </svg>
        </button>

        <!-- Read-only badge -->
        <span v-if="boardConfig?.readonly" class="orb-board__badge orb-board__badge--readonly">
          <svg
            style="width: 10px; height: 10px"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z"
            />
          </svg>
          {{ _t('Read-only') }}
        </span>

        <!-- Editing badge -->
        <span v-if="editor.editMode.value" class="orb-board__badge orb-board__badge--editing">
          <svg
            style="width: 10px; height: 10px"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2.5"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125"
            />
          </svg>
          {{ _t('Editing') }}
        </span>

        <!-- Rotation countdown -->
        <button
          v-if="boardConfig && boardConfig.rotation_interval > 0 && rotationCountdown > 0"
          :title="rotationPaused ? _t('Resume rotation') : _t('Pause rotation')"
          class="orb-board__pill orb-board__pill--rotation"
          :class="rotationPaused ? 'orb-board__pill--paused' : 'orb-board__pill--ok'"
          @click="toggleRotationPause"
        >
          <svg
            style="width: 10px; height: 10px"
            :class="rotationPaused ? '' : 'orb-board__spin'"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2.5"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"
            />
          </svg>
          {{ rotationCountdown }}{{ _t('s') }}
        </button>

        <!-- Fullscreen: browser fullscreen in standalone, new-tab kiosk in Checkmk -->
        <button
          v-if="auth.ssoActive || auth.isCheckmkDeployment"
          class="orb-board__topbtn"
          :title="_t('Open in new tab (full screen)')"
          @click="openKioskInNewTab"
        >
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
              d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"
            />
          </svg>
        </button>
        <button
          v-else
          class="orb-board__topbtn"
          :title="_t('Full screen')"
          @click="enterFullscreen"
        >
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
              d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15"
            />
          </svg>
        </button>

        <!-- Settings button (editors only, not for read-only boards) -->
        <button
          v-if="canEdit && !boardConfig?.readonly"
          data-tour="board-settings"
          class="orb-board__topbtn"
          :title="_t('Board settings')"
          @click="openSettings"
        >
          <svg
            style="width: 14px; height: 14px"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="1.5"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z"
            />
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
            />
          </svg>
        </button>
      </div>
    </div>

    <!-- Kiosk exit button (top-right, visible on hover) -->
    <button
      v-if="isKiosk"
      class="orb-board__kiosk-exit"
      :title="_t('Exit full screen')"
      @click="exitFullscreen"
    >
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
          d="M9 9V4.5M9 9H4.5M9 9L3.75 3.75M9 15v4.5M9 15H4.5M9 15l-5.25 5.25M15 9h4.5M15 9V4.5M15 9l5.25-5.25M15 15h4.5M15 15v4.5m0-4.5l5.25 5.25"
        />
      </svg>
    </button>

    <!-- Map area + optional edit panel. Acts as the portal target for the
             shared CmkSlideIn-based detail drawer so the slide-in stays under
             the topbar. -->
    <div id="orbvis-board-shell" class="orb-board__shell" data-tour="board-canvas">
      <!-- Loading overlay (covers all board types) -->
      <div v-if="isLoading" class="orb-board__loading">
        <CmkLoading />
        <span>{{ _t('Loading board…') }}</span>
      </div>
      <!-- Worldmap -->
      <div
        v-if="isWorldmap"
        class="orb-board__area orb-board__area--canvas"
        :class="{ 'worldmap-pick-active': worldmapPickActive }"
        @click="closeWorldmapMenus"
      >
        <div
          v-if="boardsStore.error"
          class="orb-board__msg orb-board__msg--overlay orb-board__msg--sm"
        >
          <span class="orb-board__error-text">{{ boardsStore.error }}</span>
          <router-link to="/" class="orb-board__backlink">
            {{ _t('← Back to overview') }}
          </router-link>
        </div>
        <WorldMapCanvas
          v-else-if="boardConfig"
          ref="worldmapCanvasRef"
          :config="boardConfig"
          :states="statesStore.states"
          :edit-mode="editor.editMode.value"
          :placing="editor.placing.value"
          :selected-object-id="editor.selectedObjectId.value"
          :filter-needle="boardFilterNeedle"
          :problems-only="problemsOnly"
          :preview="isPreview"
          @object-click="onObjectClick"
          @object-contextmenu="onObjectContextMenu"
          @object-contextmenu-view="onWorldmapContextMenuView"
          @object-hover="onWorldmapHover"
          @object-hover-leave="onWorldmapHoverLeave"
          @canvas-latlng-click="onCanvasLatLngClick"
          @canvas-contextmenu-view="onWorldmapCanvasContextMenu"
          @latlng-drag-end="onLatLngDragEnd"
          @latlng2-drag-end="onLatLng2DragEnd"
        />
        <BoardSearch
          v-if="
            boardConfig &&
            boardConfig.objects.length > 0 &&
            !editor.editMode.value &&
            !boardsStore.error &&
            !isPreview
          "
          v-model="boardFilterNeedle"
        >
          <template #trailing>
            <ProblemsOnlyToggle v-model="problemsOnly" />
          </template>
        </BoardSearch>
        <!-- Fit all button -->
        <button
          v-if="boardConfig && !isPreview && boardConfig.objects.some((o) => o.lat != null)"
          :title="_t('Fit all objects')"
          class="leaflet-control-fit-all orb-board__fit-all"
          @click.stop="worldmapCanvasRef?.fitAll()"
        >
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
              d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15"
            />
          </svg>
        </button>
        <div
          v-else-if="!boardConfig"
          class="orb-board__msg orb-board__msg--overlay orb-board__msg--muted"
        >
          <span>{{ _t('Board not found') }}</span>
          <router-link to="/" class="orb-board__backlink">
            {{ _t('← Back to overview') }}
          </router-link>
        </div>
        <div v-if="worldmapPickActive" class="orb-board__pick-banner" @click.stop>
          <span class="orb-board__pick-text">{{ _t('Pan/zoom the map, then apply.') }}</span>
          <CmkButton variant="primary" @click="applyWorldmapPick">
            {{ _t('Apply') }}
          </CmkButton>
          <CmkButton variant="secondary" @click="cancelWorldmapPick">
            {{ _t('Cancel') }}
          </CmkButton>
        </div>
      </div>

      <!-- Radar -->
      <div v-else-if="isRadar" class="orb-board__area">
        <RadarCanvas
          :states="statesStore.states"
          :checkmk-url="checkmkUrl"
          :readonly="isKiosk || isPreview || (boardConfig?.readonly ?? false)"
          :compact="isPreview"
          :loading="isRadarLoading"
          :filter-needle="boardFilterNeedle"
          :problems-only="problemsOnly"
          @object-click="onObjectClick"
        />
        <BoardSearch
          v-if="boardConfig && !editor.editMode.value && !isPreview"
          v-model="boardFilterNeedle"
        >
          <template #trailing>
            <ProblemsOnlyToggle v-model="problemsOnly" />
          </template>
        </BoardSearch>
      </div>

      <!-- Folder tree -->
      <div v-else-if="isFolderTree" class="orb-board__area">
        <FolderTreeBoard
          :view="
            boardConfig && boardConfig.view.type === 'foldertree'
              ? boardConfig.view
              : { type: 'foldertree' }
          "
          :preview="isPreview"
          :kiosk="isKiosk"
          v-bind="boardConfig ? { boardName: boardConfig.name } : {}"
          @select-host="onFolderHostSelect"
          @select-service="onFolderServiceSelect"
          @hover-host="onFolderHoverHost"
          @hover-service="onFolderHoverService"
          @hover-clear="onFolderHoverClear"
          @ctx-folder="onFolderCtx"
        />
      </div>

      <!-- Flowmap -->
      <div v-else-if="isFlowmap" class="orb-board__area">
        <FlowBoard
          v-if="boardConfig?.connection_id"
          ref="flowBoardRef"
          :connection-id="boardConfig.connection_id"
          :service-layout="serviceLayout"
          :readonly="isKiosk || isPreview || (boardConfig?.readonly ?? false)"
          :click-action="boardConfig.click_action"
          :checkmk-url="checkmkUrl"
          :flow-view="boardConfig.view.type === 'flow' ? boardConfig.view : null"
          :preview="isPreview"
          :problems-only="problemsOnly"
          :hover-template="boardConfig.hover_template ?? null"
          :context-template="boardConfig.context_template ?? null"
          @update:problems-only="problemsOnly = $event"
          @update:service-layout="onServiceLayoutChanged"
          @update:problems="flowProblems = $event"
          @drawer-object="flowDrawerObject = $event"
          @positions-changed="onFlowPositionsChanged"
        />
        <div v-else class="orb-board__noconn">
          {{ _t('No connection configured for this board.') }}
        </div>
      </div>

      <!-- Static map -->
      <div
        v-else
        class="orb-board__area orb-board__area--canvas orb-board__area--scroll"
        @click="onContainerClick"
      >
        <div
          v-if="boardsStore.error"
          class="orb-board__msg orb-board__msg--fill orb-board__msg--sm"
        >
          <span class="orb-board__error-text">{{ boardsStore.error }}</span>
          <router-link to="/" class="orb-board__backlink">
            {{ _t('← Back to overview') }}
          </router-link>
        </div>
        <template v-else-if="boardConfig">
          <BoardSearch
            v-if="boardConfig.objects.length > 0 && !editor.editMode.value && !isPreview"
            v-model="boardFilterNeedle"
          >
            <template #trailing>
              <ProblemsOnlyToggle v-model="problemsOnly" />
            </template>
          </BoardSearch>
          <!-- Empty board hint -->
          <div
            v-if="boardConfig.objects.length === 0 && !editor.editMode.value"
            class="orb-board__empty"
          >
            <svg
              class="orb-board__empty-icon"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="1.5"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M9 17.25v1.007a3 3 0 01-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0115 18.257V17.25m6-12V15a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 15V5.25m18 0A2.25 2.25 0 0018.75 3H5.25A2.25 2.25 0 003 5.25m18 0H3"
              />
            </svg>
            <p class="orb-board__empty-text">
              <template v-if="canEdit">{{
                _t('No objects yet — click the Edit button (bottom right) to add some')
              }}</template>
              <template v-else>{{ _t('This board has no objects yet') }}</template>
            </p>
          </div>
          <BoardCanvas
            ref="canvasRef"
            :config="boardConfig"
            :states="statesStore.states"
            :edit-mode="editor.editMode.value && !isPreview"
            :placing="editor.placing.value"
            :line-drag-positions="editor.lineDragPositions"
            :selected-object-id="editor.selectedObjectId.value"
            :checkmk-url="checkmkUrl"
            :is-admin="canEdit && !isKiosk && !isPreview"
            :snap-grid="editor.snapGrid.value"
            :filter-needle="boardFilterNeedle"
            :problems-only="problemsOnly"
            :preview="isPreview"
            @object-drag-start="isDragging = true"
            @object-drag-end="
              (id, x, y) => {
                isDragging = false
                onObjectDragEnd(id, x, y)
              }
            "
            @object-click="onObjectClick"
            @object-contextmenu="onObjectContextMenu"
            @object-dblclick="onObjectDblclick"
            @object-delete="onObjectDelete"
            @object-duplicate="onObjectDuplicate"
            @object-straighten="onObjectStraighten"
            @line-drag-start="onLineDragStart"
            @canvas-click="onCanvasClick"
            @graph-resize-end="onGraphResizeEnd"
          />
        </template>
        <div v-else class="orb-board__msg orb-board__msg--fill orb-board__msg--muted">
          <span>{{ _t('Board not found') }}</span>
          <router-link to="/" class="orb-board__backlink">
            {{ _t('← Back to overview') }}
          </router-link>
        </div>
      </div>

      <!-- Shared detail drawer for static / worldmap / radar boards -->
      <DetailDrawer
        v-if="!isFlowmap"
        :object="detailDrawerObject"
        :state="detailDrawerState"
        :checkmk-url="checkmkUrl"
        :connection-id="boardConfig?.connection_id ?? null"
        :selectable-hosts="selectableHostNames"
        :readonly="boardConfig?.readonly ?? false"
        portal-target="#orbvis-board-shell"
        @close="closeDetail"
        @acknowledge="onDetailAck"
        @remove-ack="onDetailRemoveAck"
        @schedule-downtime="onDetailDowntime"
        @remove-downtime="onDetailRemoveDowntime"
        @force-check="onDetailForceCheck"
        @add-comment="onDetailAddComment"
        @enable-notifications="onDetailToggleNotifications(true)"
        @disable-notifications="onDetailToggleNotifications(false)"
        @select-host="onSelectHost"
        @bulk-acknowledge="onDetailBulkAcknowledge"
      />
    </div>

    <!-- Shared drawer-action modals -->
    <AckModal
      v-if="detailActions.ackModalObject.value && checkmkUrl"
      :object="detailActions.ackModalObject.value"
      :checkmk-url="checkmkUrl"
      @close="closeDetailAckModal"
    />
    <DowntimeModal
      v-if="detailActions.downtimeModalObject.value && checkmkUrl"
      :object="detailActions.downtimeModalObject.value"
      :checkmk-url="checkmkUrl"
      @close="closeDetailDowntimeModal"
    />
    <CommentModal
      v-if="detailActions.commentModalObject.value && checkmkUrl"
      :object="detailActions.commentModalObject.value"
      :checkmk-url="checkmkUrl"
      @close="detailActions.commentModalObject.value = null"
    />
    <RemoveDowntimeModal
      v-if="detailActions.removeDowntimeModal.visible && checkmkUrl"
      :downtimes="detailActions.removeDowntimeModal.downtimes"
      :checkmk-url="checkmkUrl"
      :object-name="detailActions.removeDowntimeModal.objectName"
      @close="closeDetailRemoveDowntimeModal"
    />

    <BulkAckModal
      v-if="bulkAckModal && checkmkUrl"
      :aggregation-id="bulkAckModal.aggregationId"
      :targets="bulkAckModal.targets"
      :checkmk-url="checkmkUrl"
      @close="closeBulkAckModal"
    />

    <FolderBulkActionModal
      v-if="folderBulkModal && checkmkUrl && canBulkCommand"
      :folder="folderBulkModal"
      :checkmk-url="checkmkUrl"
      @close="closeFolderBulkModal"
    />

    <!-- FAB + Add Object panel + action bar (all bottom-right). Hidden
             while the detail drawer is open so it doesn't overlap triage. -->
    <Teleport to="body">
      <div
        v-if="
          canEdit &&
          !isKiosk &&
          !isPreview &&
          boardConfig &&
          !boardConfig.readonly &&
          !isFlowmap &&
          !isRadar &&
          !isFolderTree &&
          !drawerObject
        "
        class="orb-board__fab-stack"
      >
        <!-- Add Object panel — expands upward from FAB -->
        <Transition
          enter-from-class="orb-board__pop-enter-from"
          enter-active-class="orb-board__pop-enter-active"
          leave-to-class="orb-board__pop-leave-to"
          leave-active-class="orb-board__pop-leave-active"
          @after-leave="editor.resetDraft()"
        >
          <div
            v-if="editor.editMode.value && !!editor.draft.type"
            class="orb-board__edit-panel"
            data-tour="edit-panel"
          >
            <EditPanel
              :draft="editor.draft"
              :placing="editor.placing.value"
              :connection-id="boardConfig?.connection_id ?? ''"
              :snap-grid="editor.snapGrid.value"
              @start-placing="onStartPlacing()"
              @update:snap-grid="editor.snapGrid.value = $event"
              @cancel-add="editor.resetDraft()"
            />
          </div>
        </Transition>

        <!-- Action bar moved out — now anchored to selected object via separate Teleport -->

        <!-- FAB: Add object (with type picker popover) -->
        <Transition
          enter-from-class="orb-board__pop-enter-from"
          enter-active-class="orb-board__pop-enter-active"
          leave-to-class="orb-board__pop-leave-to"
          leave-active-class="orb-board__pop-leave-active"
        >
          <div
            v-if="editor.editMode.value && !editor.placing.value"
            v-click-outside="closeAddPicker"
            class="orb-board__fab-wrap"
          >
            <Transition
              enter-from-class="orb-board__menu-enter-from"
              enter-active-class="orb-board__menu-enter-active"
              leave-to-class="orb-board__menu-leave-to"
              leave-active-class="orb-board__menu-leave-active"
            >
              <div
                v-if="addPickerOpen"
                class="orb-board__addmenu"
                role="menu"
                :aria-label="_t('Select type…')"
              >
                <button
                  v-for="opt in placeableTypeOptions"
                  :key="opt.name"
                  role="menuitem"
                  class="orb-board__addmenu-item"
                  @click="chooseAddType(opt.name)"
                >
                  <svg
                    class="orb-board__addmenu-icon"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="2.5"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      d="M12 4.5v15m7.5-7.5h-15"
                    />
                  </svg>
                  <span>{{ opt.title }}</span>
                </button>
              </div>
            </Transition>
            <button
              data-tour="add-object-fab"
              class="orb-board__fab orb-board__fab--primary"
              :title="_t('Add Object')"
              :aria-expanded="addPickerOpen"
              aria-haspopup="menu"
              @click="onAddFabClick"
            >
              <svg
                style="width: 18px; height: 18px"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
              >
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
              </svg>
            </button>
          </div>
        </Transition>

        <!-- FAB: Edit toggle -->
        <button
          data-tour="edit-fab"
          class="orb-board__fab"
          :class="editor.editMode.value ? 'orb-board__fab--active' : 'orb-board__fab--idle'"
          :title="editor.editMode.value ? _t('Editing') : _t('Edit')"
          @click="onToggleEditMode"
        >
          <svg
            v-if="!editor.editMode.value"
            style="width: 18px; height: 18px"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="1.75"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z"
            />
          </svg>
          <svg
            v-else
            style="width: 18px; height: 18px"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="1.75"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M13.5 10.5V6.75a4.5 4.5 0 1 1 9 0v3.75M3.75 21.75h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H3.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z"
            />
          </svg>
        </button>
      </div>
    </Teleport>

    <!-- Action bar anchored to selected object (edit mode) -->
    <Teleport to="body">
      <Transition
        enter-from-class="orb-board__bar-enter-from"
        enter-active-class="orb-board__bar-enter-active"
        leave-to-class="orb-board__bar-leave-to"
        leave-active-class="orb-board__bar-leave-active"
      >
        <div
          v-if="
            editor.editMode.value &&
            editor.selectedObjectId.value &&
            selectedObject &&
            !isDragging &&
            !propsModalObject &&
            !editor.draft.type &&
            actionBarStyle
          "
          class="orb-board__actionbar"
          :style="actionBarStyle"
        >
          <span class="orb-board__actionbar-type">{{ selectedObject!.type }}</span>
          <div class="orb-board__actionbar-divider" />
          <button
            title="Edit properties"
            class="orb-board__actionbar-btn orb-board__actionbar-btn--edit"
            @click="openPropsModal(selectedObject!, selectedObjectAnchor)"
          >
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
                d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125"
              />
            </svg>
          </button>
          <button
            title="Duplicate"
            class="orb-board__actionbar-btn"
            @click="editor.duplicateSelected()"
          >
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
                d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 011.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 00-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 01-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 00-3.375-3.375h-1.5a1.125 1.125 0 01-1.125-1.125v-1.5a3.375 3.375 0 00-3.375-3.375H9.75"
              />
            </svg>
          </button>
          <button
            title="Delete"
            class="orb-board__actionbar-btn orb-board__actionbar-btn--danger"
            @click="deleteTargetObject = selectedObject"
          >
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
                d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"
              />
            </svg>
          </button>
        </div>
      </Transition>
    </Teleport>

    <!-- Services-layout toggle (Flow Board only). Hidden during triage. -->
    <Teleport to="body">
      <div v-if="isFlowmap && !drawerObject" class="orb-board__svc">
        <div class="orb-board__svc-wrap">
          <!-- Backdrop to close dropdown on outside click -->
          <div
            v-if="serviceLayoutOpen"
            class="orb-board__svc-backdrop"
            @click="serviceLayoutOpen = false"
          />

          <button
            class="orb-board__svc-btn"
            :class="serviceLayout !== 'off' ? 'orb-board__svc-btn--on' : 'orb-board__svc-btn--off'"
            @click="serviceLayoutOpen = !serviceLayoutOpen"
          >
            {{ _t('Services') }}
            <svg
              style="width: 10px; height: 10px"
              class="orb-board__svc-caret"
              :class="serviceLayoutOpen ? 'orb-board__svc-caret--open' : ''"
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

          <!-- Dropdown -->
          <Transition
            enter-from-class="orb-board__menu-enter-from"
            enter-active-class="orb-board__menu-enter-active"
            leave-to-class="orb-board__menu-leave-to"
            leave-active-class="orb-board__menu-leave-active"
          >
            <div v-if="serviceLayoutOpen" class="orb-board__svc-menu">
              <button
                v-for="opt in serviceLayoutOptions"
                :key="opt.value"
                class="orb-board__svc-item"
                :class="serviceLayout === opt.value ? 'orb-board__svc-item--active' : ''"
                @click="pickServiceLayout(opt.value)"
              >
                {{ opt.label }}
                <svg
                  v-if="serviceLayout === opt.value"
                  style="width: 12px; height: 12px"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="2.5"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
              </button>
            </div>
          </Transition>
        </div>
      </div>
    </Teleport>

    <!-- Delete confirmation -->
    <OrbConfirmDialog
      :open="!!deleteTargetObject"
      :title="deleteDialogTitle"
      :message="_t('This cannot be undone.')"
      :confirm-label="_t('Delete')"
      @confirm="confirmObjectDelete"
      @cancel="deleteTargetObject = null"
    />

    <!-- Worldmap HoverMenu -->
    <HoverMenu
      v-if="isWorldmap && worldmapHover.visible && worldmapHover.object"
      :object="worldmapHover.object"
      :state="statesStore.states[worldmapHover.object.id]"
      :x="worldmapHover.x"
      :y="worldmapHover.y"
      :connection-id="boardConfig?.connection_id ?? null"
      :template="
        resolveTemplate(
          worldmapHover.object.hover_template,
          boardConfig?.hover_template,
          settingsStore.settings.hover_template
        )
      "
    />

    <!-- Worldmap ContextMenu -->
    <ContextMenu
      v-if="isWorldmap && worldmapCtxMenu.visible && worldmapCtxMenu.object"
      :object="worldmapCtxMenu.object"
      v-bind="worldmapCtxState ? { state: worldmapCtxState } : {}"
      :x="worldmapCtxMenu.x"
      :y="worldmapCtxMenu.y"
      :checkmk-url="checkmkUrl"
      :show-edit="canEdit && !editor.editMode.value"
      :template="
        resolveTemplate(
          worldmapCtxMenu.object.context_template,
          boardConfig?.context_template,
          settingsStore.settings.context_template
        )
      "
      @close="closeWorldmapMenus"
      @edit="onWorldmapCtxEdit"
      @delete="onWorldmapCtxDelete"
      @duplicate="onWorldmapCtxDuplicate"
      @acknowledge="onWorldmapCtxAck"
      @remove-ack="onWorldmapCtxRemoveAck"
      @schedule-downtime="onWorldmapCtxDowntime"
      @remove-downtime="onWorldmapCtxRemoveDowntime"
      @force-check="onWorldmapCtxForceCheck"
      @add-comment="onWorldmapCtxAddComment"
      @enable-notifications="onWorldmapCtxToggleNotifications(true)"
      @disable-notifications="onWorldmapCtxToggleNotifications(false)"
    />

    <HoverMenu
      v-if="isFolderTree && folderHover"
      :object="folderHover.object"
      :state="folderHover.state"
      :x="folderHover.x"
      :y="folderHover.y"
    />

    <template v-if="isFolderTree && folderCtx">
      <div
        class="orb-board__ctx-backdrop"
        @click="closeFolderCtx"
        @contextmenu.prevent="closeFolderCtx"
      />
      <div
        class="orb-board__ctx"
        :style="{ left: `${folderCtx.x}px`, top: `${folderCtx.y}px` }"
        @click.stop
      >
        <div class="orb-board__ctx-header">
          <p class="orb-board__ctx-name">
            {{ folderCtx.node.title || 'Main' }}
          </p>
          <p class="orb-board__ctx-type">
            {{ _t('Folder') }}
          </p>
        </div>
        <button
          v-if="canBulkCommand && folderCtx.node.host_count > 0"
          type="button"
          class="orb-board__ctx-item"
          @click="onFolderCtxBulk"
        >
          <svg
            class="orb-board__ctx-icon"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span>{{ _t('Folder actions') }}</span>
        </button>
        <a
          v-if="folderSetupUrl"
          :href="folderSetupUrl"
          target="_blank"
          class="orb-board__ctx-item"
          @click="closeFolderCtx"
        >
          <svg
            class="orb-board__ctx-icon"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"
            />
          </svg>
          <span>{{ _t('Open in Checkmk Setup') }}</span>
        </a>
        <div
          v-if="!(canBulkCommand && folderCtx.node.host_count > 0) && !folderSetupUrl"
          class="orb-board__ctx-empty"
        >
          {{ _t('No Checkmk URL configured') }}
        </div>
      </div>
    </template>

    <div
      v-if="isWorldmap && worldmapCanvasCtxMenu.visible"
      class="orb-board__ctx"
      :style="{ left: `${worldmapCanvasCtxMenu.x}px`, top: `${worldmapCanvasCtxMenu.y}px` }"
      @click.stop
    >
      <button type="button" class="orb-board__ctx-item" @click="onWorldmapCanvasCtxSaveAsDefault">
        <svg
          class="orb-board__ctx-icon"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
        </svg>
        <span>{{ _t('Save current view as default') }}</span>
      </button>
    </div>
    <AckModal
      v-if="worldmapAckModal && checkmkUrl"
      :object="worldmapAckModal"
      :checkmk-url="checkmkUrl"
      @close="closeWorldmapAckModal"
    />
    <DowntimeModal
      v-if="worldmapDowntimeModal && checkmkUrl"
      :object="worldmapDowntimeModal"
      :checkmk-url="checkmkUrl"
      @close="closeWorldmapDowntimeModal"
    />
    <CommentModal
      v-if="worldmapCommentModal && checkmkUrl"
      :object="worldmapCommentModal"
      :checkmk-url="checkmkUrl"
      @close="worldmapCommentModal = null"
    />
    <RemoveDowntimeModal
      v-if="worldmapRemoveDowntimeModal.visible && checkmkUrl"
      :downtimes="worldmapRemoveDowntimeModal.downtimes"
      :checkmk-url="checkmkUrl"
      :object-name="worldmapRemoveDowntimeModal.objectName"
      @close="closeWorldmapRemoveDowntimeModal"
    />

    <!-- Object Properties Modal -->
    <Teleport to="body">
      <ObjectPropertiesModal
        v-if="propsModalObject"
        :object="propsModalObject"
        :state="statesStore.states[propsModalObject.id]"
        :connection-id="boardConfig?.connection_id ?? ''"
        :map-type="boardConfig?.view.type"
        :board-icon-size="boardConfig?.icon_size ?? settingsStore.settings.icon_size"
        :board-default-z="boardConfig?.default_z ?? 1"
        :checkmk-url="checkmkUrl"
        :anchor-rect="propsModalAnchor"
        @close="_closePropsModal()"
        @save="onPropsModalSave"
        @delete="onPropsModalDelete"
      />
    </Teleport>

    <!-- Map Settings Modal -->
    <BoardSettingsModal
      v-if="showSettings && boardConfigAsRead"
      :board="boardConfigAsRead"
      :worldmap-view="settingsWorldmapView"
      :parent-map-size="settingsParentMapSize"
      @close="showSettings = false"
      @updated="onSettingsUpdated"
      @pick-worldmap-view="onSettingsPickWorldmapView"
      @worldmap-view-change="onSettingsWorldmapViewChange"
    />

    <OnboardingTour
      v-if="showBoardTour && auth.user"
      :steps="boardTourSteps"
      :storage-key="`orbvis_board_toured_${auth.user.user_id}`"
      @close="showBoardTour = false"
      @step-click="onBoardTourStepClick"
      @step-back="onBoardTourStepBack"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch, watchEffect } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import OnboardingTour from '@/components/OnboardingTour.vue'
import OrbConfirmDialog from '@/components/OrbConfirmDialog.vue'
import AckModal from '@/components/board/AckModal.vue'
import BoardCanvas from '@/components/board/BoardCanvas.vue'
import BoardSearch from '@/components/board/BoardSearch.vue'
import BoardSettingsModal from '@/components/board/BoardSettingsModal.vue'
import BulkAckModal from '@/components/board/BulkAckModal.vue'
import CommentModal from '@/components/board/CommentModal.vue'
import ContextMenu from '@/components/board/ContextMenu.vue'
import DetailDrawer from '@/components/board/DetailDrawer.vue'
import DowntimeModal from '@/components/board/DowntimeModal.vue'
import EditPanel from '@/components/board/EditPanel.vue'
import FlowBoard from '@/components/board/FlowBoard.vue'
import FolderBulkActionModal from '@/components/board/FolderBulkActionModal.vue'
import FolderTreeBoard from '@/components/board/FolderTreeBoard.vue'
import HoverMenu from '@/components/board/HoverMenu.vue'
import ObjectPropertiesModal from '@/components/board/ObjectPropertiesModal.vue'
import ProblemsOnlyToggle from '@/components/board/ProblemsOnlyToggle.vue'
import RadarCanvas from '@/components/board/RadarCanvas.vue'
import RemoveDowntimeModal from '@/components/board/RemoveDowntimeModal.vue'
import WorldMapCanvas from '@/components/board/WorldMapCanvas.vue'
import type { BreadcrumbItem } from '@/components/cmk/CmkBreadcrumb.vue'
import CmkBreadcrumb from '@/components/cmk/CmkBreadcrumb.vue'
import CmkButton from '@/components/cmk/CmkButton'

import { boardsApi, cmkApi, connectionsApi } from '@/api/client'
import { useBoardEditor } from '@/composables/useBoardEditor'
import { useElementRect } from '@/composables/useElementRect'
import { useObjectActions } from '@/composables/useObjectActions'
import { useToast } from '@/composables/useToast'
import { useAuthStore } from '@/stores/auth'
import { useBoardsStore } from '@/stores/boards'
import { useConnectionsStore } from '@/stores/connections'
import { useSettingsStore } from '@/stores/settings'
import { useStatesStore } from '@/stores/states'
import type {
  BoardObject,
  BulkAckTarget,
  DowntimeEntry,
  FolderTreeNode,
  MonitoringState,
  ObjectState,
  ObjectType,
  ServiceLayout
} from '@/types/api'
import type { TourStep } from '@/types/tour'
import { buildCheckmkUrl, openUrl } from '@/utils/boardNavigation'
import { placeableObjectTypes } from '@/utils/dropdownOptions'
import { getBoardObjectIdentifier, getBoardObjectName, getObjectTypeLabel } from '@/utils/naming'
import { PREVIEW_EDIT, PREVIEW_READY } from '@/utils/previewBridge'
import { resolveTemplate } from '@/utils/template'
import CmkLoading from '@/vendor/cmk/components/CmkLoading.vue'
import usei18n from '@/vendor/cmk/lib/i18n'
import useClickOutside from '@/vendor/cmk/lib/useClickOutside'

type LineDragMode = 'move' | 'start' | 'end' | 'mid'

const { _t } = usei18n()
const toast = useToast()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const canBulkCommand = computed(
  () => auth.mayCommand('acknowledge') || auth.mayCommand('schedule_downtime')
)
const boardsStore = useBoardsStore()
const statesStore = useStatesStore()
const connectionsStore = useConnectionsStore()
const settingsStore = useSettingsStore()

const boardName = computed(() => route.params.name as string)
const isKiosk = computed(() => !!route.meta.kiosk)
const isPreview = computed(() => route.query.preview === '1')

function openKioskInNewTab() {
  const url = router.resolve({ name: 'board-kiosk', params: { name: boardName.value } }).href
  const a = document.createElement('a')
  a.href = url
  a.target = '_blank'
  a.rel = 'noreferrer'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

function enterFullscreen() {
  router.push({ name: 'board-kiosk', params: { name: boardName.value } })
  document.documentElement.requestFullscreen().catch(() => {})
}

function exitFullscreen() {
  router.push({ name: 'board', params: { name: boardName.value } })
  if (document.fullscreenElement) document.exitFullscreen().catch(() => {})
}

// ─── Board tour ───────────────────────────────────────────────────────────────

const showBoardTour = ref(false)

const boardTourSteps = computed<TourStep[]>(() => {
  const base: TourStep[] = [
    {
      selector: null,
      title: _t('Welcome to your board'),
      body: _t(
        'This is where your monitoring landscape comes to life. Objects update in real time.'
      )
    },
    {
      selector: '[data-tour="board-canvas"]',
      title: _t('The canvas'),
      body: _t(
        'Each object represents a monitored host, service, or group and shows its current state.'
      )
    }
  ]
  if (!auth.isAdmin) return base
  return [
    ...base,
    {
      selector: '[data-tour="board-settings"]',
      title: _t('Board settings'),
      body: _t(
        'Use the gear icon to open board settings — upload a background image, set a name, and configure auto-rotation.'
      )
    },
    {
      selector: '[data-tour="edit-fab"]',
      title: _t('Edit mode'),
      body: _t(
        'Click the pencil to enter edit mode and start placing monitoring objects on the board.'
      )
    },
    {
      selector: '[data-tour="edit-panel"]',
      title: _t('Add objects'),
      body: _t(
        'Choose an object type, configure it, and click "Place on board" to position it on the canvas.'
      )
    }
  ]
})

function onBoardTourStepClick(step: number) {
  // Step 4 = FAB — ensure edit mode is ON so EditPanel renders for step 5
  if (auth.isAdmin && step === 4 && !editor.editMode.value) {
    editor.toggleEditMode()
  }
}
function onBoardTourStepBack(step: number) {
  // Leaving step 5 backwards — ensure edit mode is OFF
  if (auth.isAdmin && step === 5 && editor.editMode.value) {
    editor.toggleEditMode()
  }
}
const boardConfig = computed(() => boardsStore.currentBoard)
// Whether the current user may edit *this* board: admins always, otherwise the
// per-board capability the backend stamps on the board-list entry.
const canEdit = computed(
  () =>
    auth.isAdmin || boardsStore.boards.find((b) => b.name === boardName.value)?.can_edit === true
)
const boardConfigAsRead = computed<import('@/types/api').BoardRead | null>(() => {
  const cfg = boardsStore.currentBoard
  if (!cfg) return null
  const { objects, ...rest } = cfg
  return {
    ...rest,
    view_type: cfg.view.type,
    object_count: objects.length
  }
})
const canvasRef = ref<InstanceType<typeof BoardCanvas> | null>(null)
const worldmapCanvasRef = ref<InstanceType<typeof WorldMapCanvas> | null>(null)

const isWorldmap = computed(() => boardConfig.value?.view.type === 'worldmap')
const isFlowmap = computed(() => boardConfig.value?.view.type === 'flow')
const isRadar = computed(() => boardConfig.value?.view.type === 'radar')
const isFolderTree = computed(() => boardConfig.value?.view.type === 'foldertree')

// Top-right search bar shared by static / worldmap / radar boards.
// FlowBoard ships its own search because it filters d3 nodes directly.
const boardFilterNeedle = ref('')
watch(boardName, () => {
  boardFilterNeedle.value = ''
})
const isLoading = computed(
  () => boardsStore.loading || (statesStore.initialLoad && !boardsStore.error)
)

const isRadarLoading = computed(
  () =>
    statesStore.initialLoad ||
    (!statesStore.connected && Object.keys(statesStore.states).length === 0)
)

const checkmkUrl = computed(() => {
  const bid = boardConfig.value?.connection_id
  const connUrl = bid
    ? (connectionsStore.connections.find((b) => b.id === bid)?.checkmk_url ?? null)
    : null
  return connUrl ?? settingsStore.system.checkmk_url ?? null
})

async function reloadBoard() {
  await boardsStore.fetchBoard(boardName.value)
}

const editor = useBoardEditor(boardName, reloadBoard)

// ---- Add-object type picker (anchored above the "+" FAB) ----

const vClickOutside = useClickOutside()
const addPickerOpen = ref(false)
const isDragging = ref(false)

// ---- Action bar position anchored to selected object ----
const selectedObjectEl = ref<HTMLElement | null>(null)
const selectedRect = useElementRect(selectedObjectEl)

watch(
  () => editor.selectedObjectId.value,
  async (id) => {
    await nextTick()
    selectedObjectEl.value = id
      ? (document.querySelector(`[data-object-id="${CSS.escape(id)}"]`) as HTMLElement | null)
      : null
  },
  { immediate: true }
)

const actionBarStyle = computed(() => {
  const { top, left, width, bottom } = selectedRect
  if (!selectedObjectEl.value || width === 0) return null
  const barHeightApprox = 36
  const gap = 8
  const aboveTop = top - barHeightApprox - gap
  const useAbove = aboveTop >= 8
  return {
    top: `${useAbove ? aboveTop : bottom + gap}px`,
    left: `${left + width / 2}px`,
    transform: 'translateX(-50%)'
  }
})

const selectedObjectAnchor = computed<AnchorRect | null>(() => {
  if (!selectedObjectEl.value || selectedRect.width === 0) return null
  return {
    left: selectedRect.left,
    top: selectedRect.top,
    right: selectedRect.right,
    bottom: selectedRect.bottom
  }
})

const placeableTypeOptions = computed(() =>
  placeableObjectTypes(_t, settingsStore.system.enable_graph_objects)
)

function chooseAddType(type: ObjectType) {
  editor.draft.type = type
  addPickerOpen.value = false
}

function onAddFabClick() {
  if (editor.draft.type) {
    editor.resetDraft()
    addPickerOpen.value = true
  } else {
    addPickerOpen.value = !addPickerOpen.value
  }
}

function closeAddPicker() {
  addPickerOpen.value = false
}

watch(
  () => editor.editMode.value,
  (on) => {
    if (!on) addPickerOpen.value = false
  }
)

// ---- Object properties modal (right-click in view mode) ----

type AnchorRect = { left: number; top: number; right: number; bottom: number }

const propsModalObject = ref<BoardObject | null>(null)
const propsModalAnchor = ref<AnchorRect | null>(null)
const deleteTargetObject = ref<BoardObject | null>(null)

const deleteDialogTitle = computed(() => {
  const obj = deleteTargetObject.value
  if (!obj) return _t('Delete object')
  const type = getObjectTypeLabel(obj)
  const name = obj.label?.text || getBoardObjectIdentifier(obj)
  if (!name || name === obj.id) return _t('Delete %{type}?', { type })
  return _t('Delete %{type} "%{name}"?', { type, name })
})

function openPropsModal(obj: BoardObject, anchor?: AnchorRect | null) {
  editor.selectObject(obj.id)
  propsModalAnchor.value = anchor ?? null
  propsModalObject.value = obj
}

function onObjectContextMenu(obj: BoardObject, anchor?: AnchorRect | null) {
  openPropsModal(obj, anchor)
}

function onObjectDblclick(obj: BoardObject) {
  if (!editor.editMode.value) return
  const el = document.querySelector(
    `[data-object-id="${CSS.escape(obj.id)}"]`
  ) as HTMLElement | null
  const r = el?.getBoundingClientRect()
  const anchor =
    r && (r.width > 0 || r.height > 0)
      ? { left: r.left, top: r.top, right: r.right, bottom: r.bottom }
      : null
  openPropsModal(obj, anchor)
}

function onObjectDuplicate(obj: BoardObject) {
  editor.selectObject(obj.id)
  editor.duplicateSelected()
}

function onObjectStraighten(obj: BoardObject) {
  void editor.updateObjectProperties(obj.id, { mid_x: null, mid_y: null })
}

// ---- Worldmap hover & context menu ----

const worldmapHover = reactive({ visible: false, object: null as BoardObject | null, x: 0, y: 0 })
const worldmapCtxMenu = reactive({
  visible: false,
  object: null as BoardObject | null,
  x: 0,
  y: 0
})
const worldmapCtxState = computed(() =>
  worldmapCtxMenu.object ? statesStore.states[worldmapCtxMenu.object.id] : undefined
)
const worldmapCanvasCtxMenu = reactive({
  visible: false,
  x: 0,
  y: 0,
  view: null as { lat: number; lng: number; zoom: number } | null
})

function onWorldmapHover(obj: BoardObject, event: MouseEvent) {
  worldmapHover.object = obj
  worldmapHover.x = event.pageX + 12
  worldmapHover.y = event.pageY + 12
  worldmapHover.visible = true
}

function onWorldmapHoverLeave() {
  worldmapHover.visible = false
}

function onWorldmapContextMenuView(obj: BoardObject, x: number, y: number) {
  editor.selectObject(obj.id)
  worldmapCtxMenu.object = obj
  worldmapCtxMenu.x = x
  worldmapCtxMenu.y = y
  worldmapCtxMenu.visible = true
}

function onWorldmapCtxEdit() {
  const obj = worldmapCtxMenu.object
  const x = worldmapCtxMenu.x
  const y = worldmapCtxMenu.y
  worldmapCtxMenu.visible = false
  if (obj) openPropsModal(obj, { left: x, top: y, right: x, bottom: y })
}

function onWorldmapCtxDelete() {
  if (boardConfig.value?.readonly) return
  const obj = worldmapCtxMenu.object
  worldmapCtxMenu.visible = false
  if (obj) {
    editor.selectObject(obj.id)
    editor.deleteSelected()
  }
}

function onWorldmapCtxDuplicate() {
  const obj = worldmapCtxMenu.object
  worldmapCtxMenu.visible = false
  if (obj) {
    editor.selectObject(obj.id)
    editor.duplicateSelected()
  }
}

const worldmapAckModal = ref<BoardObject | null>(null)
const worldmapDowntimeModal = ref<BoardObject | null>(null)
const worldmapCommentModal = ref<BoardObject | null>(null)
const worldmapRemoveDowntimeModal = reactive<{
  visible: boolean
  downtimes: DowntimeEntry[]
  objectName: string
}>({
  visible: false,
  downtimes: [],
  objectName: ''
})

function onWorldmapCtxDowntime() {
  const obj = worldmapCtxMenu.object
  worldmapCtxMenu.visible = false
  if (obj) worldmapDowntimeModal.value = obj
}

async function onWorldmapCtxRemoveDowntime() {
  const obj = worldmapCtxMenu.object
  worldmapCtxMenu.visible = false
  if (!obj || !checkmkUrl.value) return
  let downtimes: DowntimeEntry[]
  try {
    if (obj.type === 'service' && obj.host_name && obj.service_description) {
      downtimes = await cmkApi.listDowntimesService(
        checkmkUrl.value,
        obj.host_name,
        obj.service_description
      )
    } else if (obj.host_name) {
      downtimes = await cmkApi.listDowntimesHost(checkmkUrl.value, obj.host_name)
    } else {
      return
    }
  } catch {
    toast.error(_t('Failed to remove downtime'))
    return
  }
  if (downtimes.length === 0) {
    toast.error(_t('No active downtimes found'))
    return
  }
  if (downtimes.length === 1 && downtimes[0]) {
    await doWorldmapRemoveDowntime(downtimes[0])
    return
  }
  worldmapRemoveDowntimeModal.downtimes = downtimes
  worldmapRemoveDowntimeModal.objectName = obj.host_name ?? ''
  worldmapRemoveDowntimeModal.visible = true
}

async function doWorldmapRemoveDowntime(dt: DowntimeEntry) {
  if (!checkmkUrl.value) return
  try {
    await cmkApi.removeDowntimeById(checkmkUrl.value, dt.id, dt.site_id)
    toast.success(_t('Downtime removed'))
    statesStore.refreshAfterCommand()
  } catch {
    toast.error(_t('Failed to remove downtime'))
  }
}

function onWorldmapCtxAck() {
  const obj = worldmapCtxMenu.object
  worldmapCtxMenu.visible = false
  if (obj) worldmapAckModal.value = obj
}

function onWorldmapCtxAddComment() {
  const obj = worldmapCtxMenu.object
  worldmapCtxMenu.visible = false
  if (obj) worldmapCommentModal.value = obj
}

async function onWorldmapCtxRemoveAck() {
  const obj = worldmapCtxMenu.object
  worldmapCtxMenu.visible = false
  if (!obj || !checkmkUrl.value) return
  const siteId = statesStore.getState(obj.id)?.site_id ?? null
  try {
    if (obj.type === 'service' && obj.host_name && obj.service_description) {
      await cmkApi.removeAcknowledgementService(
        checkmkUrl.value,
        obj.host_name,
        obj.service_description,
        siteId
      )
    } else if (obj.host_name) {
      await cmkApi.removeAcknowledgementHost(checkmkUrl.value, obj.host_name, siteId)
    }
  } catch (err) {
    const detail = err instanceof Error ? err.message : ''
    toast.error(
      detail
        ? `${_t('Failed to remove acknowledgement')}: ${detail}`
        : _t('Failed to remove acknowledgement')
    )
  }
}

async function onWorldmapCtxToggleNotifications(enable: boolean) {
  const obj = worldmapCtxMenu.object
  worldmapCtxMenu.visible = false
  if (!obj || !checkmkUrl.value) return
  const siteId = statesStore.getState(obj.id)?.site_id ?? null
  try {
    if (obj.type === 'service' && obj.host_name && obj.service_description) {
      await (enable ? cmkApi.enableNotificationsService : cmkApi.disableNotificationsService)(
        checkmkUrl.value,
        obj.host_name,
        obj.service_description,
        siteId
      )
    } else if (obj.host_name) {
      await (enable ? cmkApi.enableNotificationsHost : cmkApi.disableNotificationsHost)(
        checkmkUrl.value,
        obj.host_name,
        siteId
      )
    }
  } catch {
    toast.error(_t('Failed to toggle notifications'))
  }
}

async function onWorldmapCtxForceCheck() {
  const obj = worldmapCtxMenu.object
  worldmapCtxMenu.visible = false
  if (!obj || !checkmkUrl.value) return
  const siteId = statesStore.getState(obj.id)?.site_id ?? null
  try {
    if (obj.type === 'service' && obj.host_name && obj.service_description) {
      await cmkApi.forceCheckService(
        checkmkUrl.value,
        obj.host_name,
        obj.service_description,
        siteId
      )
    } else if (obj.host_name) {
      await cmkApi.forceCheckHost(checkmkUrl.value, obj.host_name, siteId)
    }
  } catch {
    toast.error(_t('Force check failed'))
  }
}

function closeWorldmapMenus() {
  worldmapHover.visible = false
  worldmapCtxMenu.visible = false
  worldmapCanvasCtxMenu.visible = false
}

function onWorldmapCanvasContextMenu(
  view: { lat: number; lng: number; zoom: number },
  screen: { x: number; y: number }
) {
  worldmapCanvasCtxMenu.view = view
  worldmapCanvasCtxMenu.x = screen.x
  worldmapCanvasCtxMenu.y = screen.y
  worldmapCanvasCtxMenu.visible = true
}

function onWorldmapCanvasCtxSaveAsDefault() {
  if (!worldmapCanvasCtxMenu.view) return
  settingsWorldmapView.value = { ...worldmapCanvasCtxMenu.view }
  settingsParentMapSize.value = worldmapCanvasRef.value?.getContainerSize() ?? null
  worldmapCanvasCtxMenu.visible = false
  showSettings.value = true
}

function _closePropsModal() {
  propsModalObject.value = null
  propsModalAnchor.value = null
}

async function onPropsModalSave(updates: Record<string, unknown>) {
  if (!propsModalObject.value) {
    _closePropsModal()
    return
  }
  try {
    await editor.updateObjectProperties(propsModalObject.value.id, updates)
  } catch (e) {
    toast.error(e instanceof Error ? e.message : _t('Save failed'))
  } finally {
    // Always close the modal so its local "saving" state resets even if
    // the backend rejected the update — otherwise the Save button stays
    // stuck on "Saving…" with no feedback.
    _closePropsModal()
  }
}

async function onPropsModalDelete() {
  const obj = propsModalObject.value
  _closePropsModal()
  if (obj) {
    editor.selectObject(obj.id)
    await editor.deleteSelected()
  }
}

function onToggleEditMode() {
  editor.toggleEditMode()
}

function onObjectDelete(obj: BoardObject) {
  deleteTargetObject.value = obj
}

async function confirmObjectDelete() {
  const obj = deleteTargetObject.value
  deleteTargetObject.value = null
  if (obj) {
    editor.selectObject(obj.id)
    await editor.deleteSelected()
  }
}

const selectedObject = computed<BoardObject | null>(() => {
  if (!editor.selectedObjectId.value || !boardConfig.value) return null
  return boardConfig.value.objects.find((o) => o.id === editor.selectedObjectId.value) ?? null
})

// ---- Detail drawer (shared across static / worldmap / radar boards) ----

const detailDrawerObject = ref<BoardObject | null>(null)
// Foldertree host/service leaves never enter the SSE states store (services are
// lazy; the flat host states list is empty by design), so the drawer has no live
// state to key off its synthesized id. Capture the clicked node's state here so
// the drawer still shows status/output/age.
const folderLeafState = ref<ObjectState | null>(null)
const detailDrawerState = computed(() => {
  const obj = detailDrawerObject.value
  if (!obj) return undefined
  const live = statesStore.states[obj.id]
  if (live) return live
  if (folderLeafState.value?.object_id === obj.id) return folderLeafState.value
  return undefined
})
const detailActions = useObjectActions(
  () => checkmkUrl.value,
  () => {}
)

function openDetail(obj: BoardObject) {
  // A line is a visual relation between two endpoints, but in monitoring
  // terms it represents either the host or the host's service (whichever
  // is configured). Drawer logic keys off `type` to fetch state and
  // render the right tabs, so expose the line as its underlying
  // host/service for the drawer's purposes.
  if (obj.type === 'line' && obj.host_name) {
    detailDrawerObject.value = {
      ...obj,
      type: obj.service_description ? 'service' : 'host'
    }
  } else {
    detailDrawerObject.value = obj
  }
  worldmapHover.visible = false
  worldmapCtxMenu.visible = false
}

// All host BoardObjects on this board, keyed by hostname so the Drawer's
// topology section can decide whether a parent/child entry can highlight on
// the board (vs. just linking to Checkmk).
const selectableHostNames = computed(() =>
  (boardConfig.value?.objects ?? [])
    .filter((o) => o.type === 'host' && o.host_name)
    .map((o) => o.host_name as string)
)

function onSelectHost(hostName: string, serviceDescription?: string | null) {
  // Prefer a real board-object so toolbar actions (ack/downtime) bind to the
  // operator's curated entry. Fall back to a synthesised object so members
  // discovered via the hostgroup drawer (often not placed on the board)
  // still open in the same slidein — the parent state cycle lifts onto the
  // standard host/service-detail-fetch watch automatically.
  const objs = boardConfig.value?.objects ?? []
  const real = objs.find((o) => {
    if (o.type === 'service') {
      return (
        o.host_name === hostName &&
        (serviceDescription ? o.service_description === serviceDescription : true)
      )
    }
    return o.type === 'host' && o.host_name === hostName
  })
  if (real) {
    detailDrawerObject.value = real
    return
  }
  detailDrawerObject.value = {
    id: serviceDescription
      ? `transient:${hostName};${serviceDescription}`
      : `transient:${hostName}`,
    type: serviceDescription ? 'service' : 'host',
    host_name: hostName,
    ...(serviceDescription ? { service_description: serviceDescription } : {}),
    x: 0,
    y: 0,
    z: 0,
    url_target: '_blank'
  }
}

function closeDetail() {
  detailDrawerObject.value = null
  folderLeafState.value = null
}

// Foldertree leaves never enter the SSE states map (services are lazy; the flat
// host states list is empty by design), so synthesise an ObjectState from the
// tree node for the hover/drawer. Pass `host` for a service leaf, omit for a host.
function folderNodeToState(node: FolderTreeNode, host?: string): ObjectState {
  const isService = host !== undefined
  return {
    object_id: isService ? `${host};${node.title}` : node.title,
    type: isService ? 'service' : 'host',
    state: node.state as MonitoringState,
    output: node.output,
    perf_data: '',
    acknowledged: node.acknowledged,
    in_downtime: node.in_downtime,
    stale: false,
    site_id: node.site_id,
    last_state_change: node.last_state_change ?? null,
    services_summary: node.services_summary ?? null
  }
}

function onFolderHostSelect(node: FolderTreeNode) {
  if (isPreview.value) return
  if (node.kind !== 'host') return
  folderLeafState.value = folderNodeToState(node)
  onObjectClick({
    id: node.title,
    type: 'host',
    host_name: node.title,
    x: 0,
    y: 0,
    z: 0,
    url_target: '_blank'
  })
}

function onFolderServiceSelect(host: string, node: FolderTreeNode) {
  if (isPreview.value) return
  // The drawer self-fetches the richer detail (long output, comments,
  // downtimes) by host + service on top of this node-derived state.
  const id = `${host};${node.title}`
  folderLeafState.value = folderNodeToState(node, host)
  onObjectClick({
    id,
    type: 'service',
    host_name: host,
    service_description: node.title,
    x: 0,
    y: 0,
    z: 0,
    url_target: '_blank'
  })
}

const folderBulkModal = ref<FolderTreeNode | null>(null)
function onFolderAction(node: FolderTreeNode) {
  if (!canBulkCommand.value) return
  folderBulkModal.value = node
}

// Same node-derived state as the folder click→drawer path (see folderNodeToState).
interface FolderHover {
  object: BoardObject
  state: ObjectState | undefined
  x: number
  y: number
}
const folderHover = ref<FolderHover | null>(null)

function onFolderHoverHost(node: FolderTreeNode, x: number, y: number) {
  folderHover.value = {
    object: {
      id: node.title,
      type: 'host',
      host_name: node.title,
      x: 0,
      y: 0,
      z: 0,
      url_target: '_blank'
    },
    state: folderNodeToState(node),
    x: x + 12,
    y: y + 12
  }
}

function onFolderHoverService(host: string, node: FolderTreeNode, x: number, y: number) {
  const id = `${host};${node.title}`
  folderHover.value = {
    object: {
      id,
      type: 'service',
      host_name: host,
      service_description: node.title,
      x: 0,
      y: 0,
      z: 0,
      url_target: '_blank'
    },
    state: folderNodeToState(node, host),
    x: x + 12,
    y: y + 12
  }
}

function onFolderHoverClear() {
  folderHover.value = null
}

interface FolderCtx {
  node: FolderTreeNode
  x: number
  y: number
}
const folderCtx = ref<FolderCtx | null>(null)

function onFolderCtx(node: FolderTreeNode, x: number, y: number) {
  // The settings preview is non-interactive; read-only displays (click_action
  // 'none') get no context menu, mirroring onObjectClick's click gating.
  if (isPreview.value || boardConfig.value?.click_action === 'none') return
  folderHover.value = null
  folderCtx.value = { node, x, y }
}

function closeFolderCtx() {
  folderCtx.value = null
}

function onFolderCtxBulk() {
  if (folderCtx.value) onFolderAction(folderCtx.value.node)
  closeFolderCtx()
}

// wato.py addresses folders by their relative path (Main = ""), which is the
// tree node's path.
const folderSetupUrl = computed(() => {
  const node = folderCtx.value?.node
  if (!node) return null
  const raw = checkmkUrl.value
  if (!raw) return null
  const base = raw.replace(/\/check_mk\/?$/, '').replace(/\/$/, '')
  const p = new URLSearchParams({ mode: 'folder', folder: node.path })
  return `${base}/check_mk/wato.py?${p.toString()}`
})

function onDetailAck() {
  detailActions.handlers.acknowledge(detailDrawerObject.value)
}
function onDetailRemoveAck() {
  void detailActions.handlers.removeAck(detailDrawerObject.value)
}
function onDetailDowntime() {
  detailActions.handlers.scheduleDowntime(detailDrawerObject.value)
}
function onDetailRemoveDowntime() {
  void detailActions.handlers.removeDowntime(detailDrawerObject.value)
}
function onDetailForceCheck() {
  void detailActions.handlers.forceCheck(detailDrawerObject.value)
}
function onDetailAddComment() {
  detailActions.handlers.addComment(detailDrawerObject.value)
}
function onDetailToggleNotifications(enable: boolean) {
  void detailActions.handlers.toggleNotifications(detailDrawerObject.value, enable)
}

/**
 * Bulk-acknowledge contributing leaves of a BI aggregation. Opens the
 * BulkAckModal — that previews the targets, lets the operator review/edit
 * the comment (pre-filled with "Bulk-ack: <aggregation_id>" so audit logs
 * trace back to the originating aggregation), and runs the per-leaf ack
 * loop with progress feedback. The previous "fire immediately on click"
 * version was risky for misclicks since N acks have no atomic undo.
 */
function onDetailBulkAcknowledge(targets: BulkAckTarget[]) {
  if (!checkmkUrl.value || !targets.length) return
  const obj = detailDrawerObject.value
  const aggregationId = obj?.aggregation_id ?? obj?.id ?? 'unknown'
  bulkAckModal.value = { aggregationId, targets }
}

const bulkAckModal = ref<{
  aggregationId: string
  targets: BulkAckTarget[]
} | null>(null)

// ---- Static map event handlers ----

async function onObjectDragEnd(id: string, x: number, y: number) {
  await editor.saveObjectPosition(id, x, y)
}

function onObjectClick(obj: BoardObject, event?: MouseEvent) {
  if (editor.editMode.value) {
    editor.selectObject(obj.id)
    return
  }
  if (boardConfig.value?.click_action === 'none') return
  if (obj.url) {
    openUrl(obj.url, obj.url_target || '_blank')
    return
  }
  if (obj.type === 'map' && obj.map_name) {
    void router.push({ name: 'board', params: { name: obj.map_name } })
    return
  }
  if (event && (event.ctrlKey || event.metaKey)) {
    const cmkUrl = buildCheckmkUrl(obj, checkmkUrl.value, statesStore.getState(obj.id)?.site_id)
    if (cmkUrl) openUrl(cmkUrl, '_blank')
    return
  }
  // Decorative objects without a monitored target have nothing to show in
  // the slide-in. Click is a no-op rather than an empty drawer.
  if (!objectHasMonitoringTarget(obj)) return
  openDetail(obj)
}

function objectHasMonitoringTarget(obj: BoardObject): boolean {
  switch (obj.type) {
    case 'host':
    case 'service':
    case 'line':
      return Boolean(obj.host_name)
    case 'hostgroup':
    case 'servicegroup':
      return Boolean(obj.group_name)
    case 'dyngroup':
      return Boolean(obj.object_filter)
    case 'aggregation':
      return Boolean(obj.aggregation_id)
    default:
      return false
  }
}

async function onCanvasClick(event: MouseEvent) {
  if (!editor.editMode.value) return
  if (!editor.placing.value) {
    editor.selectObject(null)
    return
  }
  const pos = canvasRef.value?.getMapPosition(event)
  if (pos) {
    await editor.placeAt(pos.x, pos.y)
    if (selectedObject.value) openPropsModal(selectedObject.value)
  }
}

// Clicks on the scroll container outside the canvas bounds also trigger placing.
async function onContainerClick(event: MouseEvent) {
  if (!editor.editMode.value || !editor.placing.value) return
  const pos = canvasRef.value?.getMapPosition(event)
  if (pos) {
    await editor.placeAt(pos.x, pos.y)
    if (selectedObject.value) openPropsModal(selectedObject.value)
  }
}

function onLineDragStart(event: MouseEvent, obj: BoardObject, mode: LineDragMode) {
  const canvas = canvasRef.value?.getCanvasEl()
  if (canvas) editor.startLineDrag(event, obj, mode, canvas)
}

async function onGraphResizeEnd(id: string, width: number, height: number) {
  const obj = boardConfig.value?.objects.find((o) => o.id === id)
  if (!obj) return
  if (obj.type === 'textbox') {
    obj.textbox_width = width
    obj.textbox_height = height
    await editor.updateObjectProperties(id, { textbox_width: width, textbox_height: height })
    return
  }
  obj.graph_width = width
  obj.graph_height = height
  await editor.updateObjectProperties(id, { graph_width: width, graph_height: height })
}

// ---- Worldmap event handlers ----

async function onStartPlacing() {
  const d = editor.draft
  const connectionId = boardConfig.value?.connection_id
  if (boardConfig.value?.view.type === 'worldmap' && connectionId && d.host_name) {
    try {
      const geo = await connectionsApi.hostGeo(connectionId, d.host_name, auth.accessToken!)
      if (geo) {
        editor.startPlacing()
        await editor.placeAtLatLng(geo.lat, geo.lng)
        if (selectedObject.value) openPropsModal(selectedObject.value)
        return
      }
    } catch {}
  }
  editor.startPlacing()
}

async function onCanvasLatLngClick(lat: number, lng: number) {
  if (!editor.editMode.value || !editor.placing.value) return
  await editor.placeAtLatLng(lat, lng)
  if (selectedObject.value) openPropsModal(selectedObject.value)
}

function onLatLngDragEnd(id: string, lat: number, lng: number) {
  editor.moveObjectToLatLng(id, lat, lng)
}

function onLatLng2DragEnd(id: string, lat: number, lng: number) {
  editor.moveObjectToLatLng2(id, lat, lng)
}

// ---- Map Settings ----

const SERVICE_LAYOUT_DEFAULT: ServiceLayout = 'off'
const serviceLayout = ref<ServiceLayout>(SERVICE_LAYOUT_DEFAULT)
const serviceLayoutOpen = ref(false)

type FlowProblems = {
  critical: number
  warning: number
  hostsWithProblems: number
  total: number
}
const FLOW_PROBLEMS_DEFAULT: FlowProblems = {
  critical: 0,
  warning: 0,
  hostsWithProblems: 0,
  total: 0
}
const flowProblems = ref<FlowProblems>({ ...FLOW_PROBLEMS_DEFAULT })
const flowDrawerObject = ref<BoardObject | null>(null)
const flowBoardRef = ref<{ closeDetail: () => void } | null>(null)
const drawerObject = computed<BoardObject | null>(
  () => detailDrawerObject.value ?? flowDrawerObject.value
)
function closeAnyDrawer(): void {
  if (detailDrawerObject.value) closeDetail()
  if (flowDrawerObject.value) flowBoardRef.value?.closeDetail()
}

const breadcrumbItems = computed<BreadcrumbItem[]>(() => {
  const boardTitle = boardConfig.value?.alias || String(route.params.name ?? '')
  const items: BreadcrumbItem[] = [{ title: _t('Boards'), to: '/' }]
  if (drawerObject.value) {
    items.push({ title: boardTitle, onClick: closeAnyDrawer })
    items.push({ title: getBoardObjectName(drawerObject.value) })
  } else {
    items.push({ title: boardTitle })
  }
  return items
})

async function persistView(patch: Record<string, unknown>): Promise<void> {
  const cfg = boardConfig.value
  if (!cfg || cfg.readonly) return
  const token = auth.accessToken
  if (!token) return
  const newView = { ...cfg.view, ...patch }
  cfg.view = newView
  try {
    const updated = await boardsApi.update(cfg.name, { view: newView }, token)
    // Without this, the next If-Match-gated save (settings modal) sees a
    // stale version and 409s on top of our own background layout write.
    if (updated.version != null && (cfg.version == null || updated.version > cfg.version)) {
      cfg.version = updated.version
    }
  } catch (err) {
    // View prefs are low-stakes — log and let the next change retry.
    console.warn('Failed to persist board view:', err)
  }
}

function onFlowPositionsChanged(positions: Record<string, { x: number; y: number }>): void {
  void persistView({ positions })
}

// FolderTree manages its own problems-only copy; this drives the other types.
const problemsOnly = computed<boolean>({
  get: () => {
    const view = boardConfig.value?.view as { problems_only?: boolean } | undefined
    return view?.problems_only ?? false
  },
  set: (value) => {
    void persistView({ problems_only: value })
  }
})

function onServiceLayoutChanged(layout: ServiceLayout): void {
  serviceLayout.value = layout
  void persistView({ service_layout: layout })
}

// Hydrate the local serviceLayout ref from the persisted view whenever the
// board config swaps. The watch on boardName below clears the ref before the
// new board arrives, so this fires once the new boardConfig is in place.
watch(
  () => boardConfig.value?.view,
  (view) => {
    if (view?.type === 'flow' && view.service_layout) {
      serviceLayout.value = view.service_layout
    }
  },
  { immediate: true }
)

watch(boardName, () => {
  serviceLayout.value = SERVICE_LAYOUT_DEFAULT
  serviceLayoutOpen.value = false
  flowProblems.value = { ...FLOW_PROBLEMS_DEFAULT }
})
const serviceLayoutOptions = computed(() => [
  { value: 'off' as ServiceLayout, label: _t('Off') },
  { value: 'donut' as ServiceLayout, label: _t('Donut') },
  { value: 'fan' as ServiceLayout, label: _t('Fan') },
  { value: 'orbit' as ServiceLayout, label: _t('Orbit') },
  { value: 'row' as ServiceLayout, label: _t('Row') }
])
const showSettings = ref(false)
const settingsWorldmapView = ref<{ lat: number; lng: number; zoom: number } | null>(null)
const settingsParentMapSize = ref<{ width: number; height: number } | null>(null)

const worldmapPickActive = ref(false)
let worldmapPickResolver:
  | ((view: { lat: number; lng: number; zoom: number } | null) => void)
  | null = null

function onSettingsPickWorldmapView(
  done: (view: { lat: number; lng: number; zoom: number } | null) => void
) {
  worldmapPickResolver = done
  worldmapPickActive.value = true
}

function applyWorldmapPick() {
  const view = worldmapCanvasRef.value?.getView() ?? null
  const resolver = worldmapPickResolver
  worldmapPickResolver = null
  worldmapPickActive.value = false
  resolver?.(view)
}

function cancelWorldmapPick() {
  const resolver = worldmapPickResolver
  worldmapPickResolver = null
  worldmapPickActive.value = false
  resolver?.(null)
}

function onSettingsWorldmapViewChange(view: { lat: number; lng: number; zoom: number }) {
  worldmapCanvasRef.value?.setView(view.lat, view.lng, view.zoom)
}

function openSettings() {
  if (!boardConfig.value) return
  settingsWorldmapView.value = null
  settingsParentMapSize.value =
    boardConfig.value.view.type === 'worldmap'
      ? (worldmapCanvasRef.value?.getContainerSize() ?? null)
      : null
  showSettings.value = true
}

async function onSettingsUpdated() {
  // Settings save may have changed the connection or filter; refresh
  // monitoring states so the canvas reflects the new scope. Flipping
  // ``initialLoad`` gives radar / flow boards a spinner in the gap.
  stopRotation()
  scheduleRotation(boardsStore.currentBoard?.rotation_interval ?? 0)
  await statesStore.refreshWithIndicator()
}

// ---- Rotation ----

let rotationTimer: ReturnType<typeof setInterval> | null = null
const rotationCountdown = ref(0)
const rotationPaused = ref(false)

function stopRotation() {
  if (rotationTimer !== null) {
    clearInterval(rotationTimer)
    rotationTimer = null
  }
  rotationCountdown.value = 0
}

async function goToNextBoard() {
  if (boardsStore.boards.length === 0) await boardsStore.fetchBoards()
  const pool = boardsStore.boards.filter((b) => (b.rotation_interval ?? 0) > 0)
  if (pool.length < 2) return
  const idx = pool.findIndex((b) => b.name === boardName.value)
  const next = pool[(idx + 1) % pool.length]
  if (!next) return
  router.push({ name: 'board', params: { name: next.name } })
}

function scheduleRotation(intervalSeconds: number) {
  stopRotation()
  rotationPaused.value = false
  if (intervalSeconds <= 0 || editor.editMode.value) return
  rotationCountdown.value = intervalSeconds
  rotationTimer = setInterval(() => {
    if (rotationPaused.value || editor.editMode.value) return
    rotationCountdown.value--
    if (rotationCountdown.value <= 0) {
      stopRotation()
      goToNextBoard()
    }
  }, 1000)
}

function toggleRotationPause() {
  rotationPaused.value = !rotationPaused.value
}

// Re-run whenever the map name changes (component is reused by Vue Router between maps).
// Reset all edit state so edit mode, selection, and unsaved changes from Map A
// don't carry over when navigating to Map B.
watchEffect(async () => {
  const name = boardName.value
  stopRotation()
  editor.resetForNewMap()

  await boardsStore.fetchBoard(name)
  statesStore.connectToMap(name, auth.accessToken ?? undefined)
  scheduleRotation(boardsStore.currentBoard?.rotation_interval ?? 0)

  const cfg = boardsStore.currentBoard
  if (
    auth.user &&
    cfg &&
    !cfg.readonly &&
    !localStorage.getItem(`orbvis_board_toured_${auth.user.user_id}`)
  ) {
    showBoardTour.value = true
  }
})

function onKeyDown(e: KeyboardEvent) {
  if (!editor.editMode.value) return
  const target = e.target as HTMLElement
  if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT')
    return
  if (e.key === 'Escape') {
    e.preventDefault()
    if (addPickerOpen.value) addPickerOpen.value = false
    else if (editor.placing.value) editor.cancelPlacing()
    else editor.selectObject(null)
  } else if ((e.key === 'Delete' || e.key === 'Backspace') && editor.selectedObjectId.value) {
    e.preventDefault()
    editor.deleteSelected()
  } else if (e.key === 'd' && (e.ctrlKey || e.metaKey)) {
    e.preventDefault()
    editor.duplicateSelected()
  }
}

function onFullscreenChange() {
  if (!document.fullscreenElement && isKiosk.value) {
    router.push({ name: 'board', params: { name: boardName.value } })
  }
}

function onPreviewMessage(ev: MessageEvent) {
  if (ev.origin !== window.location.origin) return
  const data = ev.data as { source?: string; patch?: Record<string, unknown> } | null
  if (!data || data.source !== PREVIEW_EDIT || !data.patch) return
  const cur = boardsStore.currentBoard
  if (!cur) return
  Object.assign(cur, data.patch)
  // Radar and foldertree resolve their view server-side, so the disk-cfg
  // state stream can't reflect live-edited fields. Push the unsaved values
  // into the next states fetch as an override.
  const view = (
    data.patch as {
      view?: {
        type?: string
        filter?: string
        filter_value?: string
        root_folder?: string
        show_empty_folders?: boolean
        only_hard_states?: boolean
        sites?: string[]
      }
    }
  ).view
  if (view?.type === 'radar') {
    statesStore.setRadarOverride(view.filter ?? null, view.filter_value ?? '')
    statesStore.setFolderTreeOverride(null)
  } else if (view?.type === 'foldertree') {
    statesStore.setRadarOverride(null)
    statesStore.setFolderTreeOverride({
      rootFolder: view.root_folder ?? '',
      showEmptyFolders: view.show_empty_folders ?? true,
      onlyHardStates: view.only_hard_states ?? false,
      sites: view.sites ?? []
    })
  } else if (view) {
    statesStore.setRadarOverride(null)
    statesStore.setFolderTreeOverride(null)
  }
}

onMounted(() => {
  if (auth.canConfigure || auth.canCreateBoards) connectionsStore.fetchConnections()
  // The board list carries per-board can_edit; ensure it's loaded even on a
  // direct deep-link so non-admin editors get their edit affordances.
  if (boardsStore.boards.length === 0) void boardsStore.fetchBoards()
  document.addEventListener('keydown', onKeyDown)
  document.addEventListener('fullscreenchange', onFullscreenChange)
  window.addEventListener('message', onPreviewMessage)
})

watch(
  () => boardsStore.currentBoard?.name,
  (name) => {
    if (!name || !isPreview.value || window.parent === window) return
    window.parent.postMessage({ source: PREVIEW_READY }, window.location.origin)
  },
  { immediate: true }
)

onUnmounted(() => {
  statesStore.disconnect()
  stopRotation()
  document.removeEventListener('keydown', onKeyDown)
  document.removeEventListener('fullscreenchange', onFullscreenChange)
  window.removeEventListener('message', onPreviewMessage)
})

function closeDetailAckModal(): void {
  detailActions.ackModalObject.value = null
  statesStore.refreshAfterCommand()
}

function closeDetailDowntimeModal(): void {
  detailActions.downtimeModalObject.value = null
  statesStore.refreshAfterCommand()
}

function closeDetailRemoveDowntimeModal(): void {
  detailActions.removeDowntimeModal.visible = false
  statesStore.refreshAfterCommand()
}

function closeBulkAckModal(): void {
  bulkAckModal.value = null
  statesStore.refreshAfterCommand()
}

function closeFolderBulkModal(): void {
  folderBulkModal.value = null
  statesStore.refreshAfterCommand()
}

function pickServiceLayout(v: Parameters<typeof onServiceLayoutChanged>[0]): void {
  onServiceLayoutChanged(v)
  serviceLayoutOpen.value = false
}

function closeWorldmapAckModal(): void {
  worldmapAckModal.value = null
  statesStore.refreshAfterCommand()
}

function closeWorldmapDowntimeModal(): void {
  worldmapDowntimeModal.value = null
  statesStore.refreshAfterCommand()
}

function closeWorldmapRemoveDowntimeModal(): void {
  worldmapRemoveDowntimeModal.visible = false
  statesStore.refreshAfterCommand()
}
</script>

<style>
/* Fadenkreuz, solange das Settings-Slide-In den View-Picker aktiviert hat —
   überschreibt Leaflets eigene grab/grabbing-Cursor (unscoped, da Leaflet sich
   nicht an Vues data-v-… hängt). */
.worldmap-pick-active .leaflet-grab,
.worldmap-pick-active .leaflet-dragging .leaflet-grab,
.worldmap-pick-active .leaflet-container {
  cursor: crosshair !important;
}
</style>

<style scoped>
.orb-board {
  display: flex;
  flex: 1 1 0%;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg);
}

.orb-board__topbar {
  z-index: 30;
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: space-between;
  height: 36px;
  padding: 0 var(--dimension-6);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border);
}

.orb-board__crumb {
  min-width: 0;
}

.orb-board__topbar-actions {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 5px;
  transition: opacity 0.15s;
}

.orb-board__topbar-actions--dimmed {
  opacity: 0.4;
}

.orb-board__topbar-actions--dimmed:hover {
  opacity: 1;
}

.orb-board__pill {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  padding: var(--dimension-2) 7px;
  font-size: var(--font-size-normal);
  line-height: 16px;
  font-weight: 500;
  border-radius: 9999px;
  transition: all 0.15s;
}

.orb-board__pill--critical {
  color: var(--color-light-red-40);
  background: color-mix(in srgb, var(--color-light-red-50) 10%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-light-red-50) 30%, transparent);
}

.orb-board__pill--warning {
  color: var(--color-yellow-50);
  background: color-mix(in srgb, var(--color-warning) 10%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-warning) 30%, transparent);
}

.orb-board__pill--ok {
  color: var(--color-corporate-green-50);
  background: color-mix(in srgb, var(--color-corporate-green-50) 8%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-corporate-green-50) 20%, transparent);
}

.orb-board__pill--offline {
  color: var(--color-light-red-40);
  background: color-mix(in srgb, var(--color-light-red-50) 8%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-light-red-50) 20%, transparent);
}

.orb-board__pill--paused {
  color: var(--text-muted);
  background: var(--bg-hover);
  box-shadow: 0 0 0 1px var(--default-border-color);
}

.orb-board__pill--rotation {
  gap: 3px;
}

.orb-board__dot {
  display: inline-block;
  width: 5px;
  height: 5px;
  border-radius: 9999px;
}

.orb-board__dot--ok {
  background: var(--color-corporate-green-50);
  animation: orb-board-pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

.orb-board__dot--offline {
  background: var(--color-light-red-40);
}

@keyframes orb-board-pulse {
  50% {
    opacity: 0.5;
  }
}

.orb-board__spin {
  animation: orb-board-spin 3s linear infinite;
}

@keyframes orb-board-spin {
  to {
    transform: rotate(360deg);
  }
}

.orb-board__topbtn {
  padding: 5px;
  color: var(--text-muted);
  border-radius: 8px;
  transition: all 0.15s;
}

.orb-board__topbtn:hover {
  color: var(--text);
  background: var(--bg-hover);
}

.orb-board__topbtn--alert,
.orb-board__topbtn--alert:hover {
  color: var(--color-yellow-50);
}

.orb-board__topbtn--alert:hover {
  background: color-mix(in srgb, var(--color-warning) 10%, transparent);
}

.orb-board__badge {
  display: flex;
  align-items: center;
  gap: 3px;
  padding: var(--dimension-2) 6px;
  font-size: var(--font-size-normal);
  line-height: 16px;
  font-weight: 600;
  border-radius: 8px;
}

.orb-board__badge--readonly {
  color: var(--text-muted);
  background: var(--bg-hover);
  box-shadow: 0 0 0 1px var(--default-border-color);
}

.orb-board__badge--editing {
  color: var(--color-yellow-50);
  background: color-mix(in srgb, var(--color-warning) 10%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-warning) 20%, transparent);
}

.orb-board__kiosk-exit {
  position: fixed;
  top: var(--dimension-5);
  right: var(--dimension-5);
  z-index: 50;
  padding: 5px;
  color: var(--color-white-60);
  background: rgb(0 0 0 / 40%);
  border-radius: 8px;
  transition:
    color 0.15s,
    background-color 0.15s;
}

.orb-board__kiosk-exit:hover {
  color: var(--color-white-100);
  background: rgb(0 0 0 / 60%);
}

.orb-board__shell {
  position: relative;
  display: flex;
  flex: 1 1 0%;
  overflow: hidden;
}

.orb-board__loading {
  position: absolute;
  inset: 0;
  z-index: 30;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--dimension-5);
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
  background: var(--bg);
}

.orb-board__area {
  position: relative;
  flex: 1 1 0%;
  overflow: hidden;
}

.orb-board__area--canvas {
  background: var(--bg);
}

.orb-board__area--scroll {
  overflow: auto;
}

.orb-board__msg {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--dimension-5);
}

.orb-board__msg--overlay {
  position: absolute;
  inset: 0;
  z-index: 10;
}

.orb-board__msg--fill {
  height: 100%;
}

.orb-board__msg--sm {
  font-size: var(--font-size-large);
  line-height: 20px;
}

.orb-board__msg--muted {
  color: var(--text-muted);
}

.orb-board__error-text {
  color: var(--color-light-red-40);
}

.orb-board__backlink {
  font-size: var(--font-size-normal);
  line-height: 16px;
  color: var(--text-muted);
  transition: color 0.15s;
}

.orb-board__backlink:hover {
  color: var(--text);
}

.orb-board__fit-all {
  position: absolute;
  top: 80px;
  left: 10px;
  z-index: 1000;
  padding: var(--dimension-2) var(--dimension-3);
  font-size: var(--font-size-normal);
  line-height: 16px;
  font-weight: 500;
  color: var(--color-mist-grey-90);
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 4px;
  box-shadow:
    0 1px 3px 0 rgb(0 0 0 / 10%),
    0 1px 2px -1px rgb(0 0 0 / 10%);
  transition:
    color 0.15s,
    background-color 0.15s;
}

.orb-board__fit-all:hover {
  background: var(--color-mist-grey-0);
}

.orb-board__pick-banner {
  position: absolute;
  top: var(--dimension-6);
  left: 50%;
  z-index: 2000;
  display: flex;
  align-items: center;
  gap: var(--dimension-5);
  padding: var(--dimension-4) var(--dimension-6);
  background: var(--bg-glass);
  backdrop-filter: blur(12px);
  border-radius: 8px;
  box-shadow:
    0 0 0 1px var(--border),
    0 25px 50px -12px rgb(0 0 0 / 25%);
  transform: translateX(-50%);
}

.orb-board__pick-text {
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text);
}

.orb-board__noconn {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
}

.orb-board__empty {
  position: absolute;
  inset: 0;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--dimension-4);
  pointer-events: none;
  user-select: none;
}

.orb-board__empty-icon {
  width: 32px;
  height: 32px;
  color: var(--text-muted);
}

.orb-board__empty-text {
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
}

.orb-board__fab-stack {
  position: fixed;
  right: var(--dimension-8);
  bottom: var(--dimension-8);
  z-index: 40;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
}

.orb-board__pop-enter-from,
.orb-board__pop-leave-to {
  opacity: 0;
  transform: translateY(16px) scaleX(0.95) scaleY(0.75);
}

.orb-board__pop-enter-active {
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  transform-origin: bottom right;
}

.orb-board__pop-leave-active {
  transition: all 0.2s cubic-bezier(0.4, 0, 1, 1);
  transform-origin: bottom right;
}

.orb-board__menu-enter-from,
.orb-board__menu-leave-to {
  opacity: 0;
  transform: translateY(4px) scale(0.95);
}

.orb-board__menu-enter-active {
  transition: all 0.15s cubic-bezier(0, 0, 0.2, 1);
  transform-origin: bottom right;
}

.orb-board__menu-leave-active {
  transition: all 0.1s cubic-bezier(0.4, 0, 1, 1);
  transform-origin: bottom right;
}

.orb-board__bar-enter-from,
.orb-board__bar-leave-to {
  opacity: 0;
  transform: translateY(4px) scale(0.95);
}

.orb-board__bar-enter-active {
  transition: all 0.15s cubic-bezier(0, 0, 0.2, 1);
}

.orb-board__bar-leave-active {
  transition: all 0.1s cubic-bezier(0.4, 0, 1, 1);
}

.orb-board__edit-panel {
  display: flex;
  flex-direction: column;
  width: 256px;
  max-height: calc(100vh - 160px);
  background: var(--bg-surface);
  backdrop-filter: blur(24px);
  border-radius: 16px;
  box-shadow:
    0 0 0 1px rgb(255 255 255 / 8%),
    0 25px 50px -12px rgb(0 0 0 / 60%);
}

.orb-board__fab-wrap {
  position: relative;
}

.orb-board__addmenu {
  position: absolute;
  right: 0;
  bottom: 100%;
  width: 224px;
  margin-bottom: var(--dimension-4);
  overflow: hidden;
  background: var(--bg-surface);
  backdrop-filter: blur(24px);
  border-radius: 12px;
  box-shadow:
    0 0 0 1px rgb(255 255 255 / 8%),
    0 25px 50px -12px rgb(0 0 0 / 60%);
}

.orb-board__addmenu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: var(--dimension-4) var(--dimension-5);
  font-size: 13px;
  color: var(--text);
  text-align: left;
  transition:
    color 0.15s,
    background-color 0.15s;
}

.orb-board__addmenu-item:hover {
  background: var(--bg-hover);
}

.orb-board__addmenu-icon {
  flex-shrink: 0;
  width: 12px;
  height: 12px;
  color: var(--text-muted);
}

.orb-board__fab {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  transition: all 0.2s;
}

.orb-board__fab:active {
  transform: scale(0.95);
}

.orb-board__fab--primary {
  color: var(--color-white-100);
  background: color-mix(in srgb, var(--color-corporate-green-50) 90%, transparent);
  box-shadow:
    0 0 0 1px color-mix(in srgb, var(--color-corporate-green-50) 60%, transparent),
    0 10px 15px -3px rgb(0 0 0 / 30%),
    0 4px 6px -4px rgb(0 0 0 / 30%);
}

.orb-board__fab--primary:hover {
  background: var(--color-corporate-green-50);
}

.orb-board__fab--active {
  color: var(--text);
  background: var(--bg-input);
  box-shadow:
    0 0 0 1px var(--default-border-color),
    0 10px 15px -3px rgb(0 0 0 / 30%),
    0 4px 6px -4px rgb(0 0 0 / 30%);
}

.orb-board__fab--active:hover {
  background: var(--bg-hover);
}

.orb-board__fab--idle {
  color: var(--text-muted);
  background: color-mix(in srgb, var(--bg-surface) 80%, transparent);
  box-shadow:
    0 0 0 1px var(--border),
    0 10px 15px -3px rgb(0 0 0 / 30%),
    0 4px 6px -4px rgb(0 0 0 / 30%);
}

.orb-board__fab--idle:hover {
  color: var(--text);
  background: var(--bg-surface);
}

.orb-board__actionbar {
  position: fixed;
  z-index: 40;
  display: flex;
  align-items: center;
  gap: 3px;
  padding: var(--dimension-3) 6px;
  background: var(--bg-surface);
  backdrop-filter: blur(12px);
  border-radius: 12px;
  box-shadow:
    0 0 0 1px var(--border),
    0 25px 50px -12px rgb(0 0 0 / 40%);
}

.orb-board__actionbar-type {
  padding: 0 var(--dimension-3);
  font-size: 10px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: capitalize;
}

.orb-board__actionbar-divider {
  width: 1px;
  height: 14px;
  margin: 0 1px;
  background: var(--border);
}

.orb-board__actionbar-btn {
  padding: 7px;
  color: var(--text-muted);
  border-radius: 8px;
  transition: all 0.15s;
}

.orb-board__actionbar-btn:hover {
  color: var(--text);
  background: var(--bg-hover);
}

.orb-board__actionbar-btn--edit:hover {
  color: var(--color-corporate-green-40);
  background: color-mix(in srgb, var(--color-corporate-green-50) 10%, transparent);
}

.orb-board__actionbar-btn--danger:hover {
  color: var(--color-light-red-40);
  background: color-mix(in srgb, var(--color-light-red-50) 10%, transparent);
}

.orb-board__svc {
  position: fixed;
  right: var(--dimension-8);
  bottom: var(--dimension-8);
  z-index: 40;
}

.orb-board__svc-wrap {
  position: relative;
}

.orb-board__svc-backdrop {
  position: fixed;
  inset: 0;
  z-index: 0;
}

.orb-board__svc-btn {
  position: relative;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 10px;
  font-size: var(--font-size-normal);
  line-height: 16px;
  font-weight: 500;
  border-radius: 12px;
  transition: all 0.2s;
}

.orb-board__svc-btn--on {
  color: var(--color-corporate-green-40);
  background: color-mix(in srgb, var(--color-corporate-green-50) 15%, transparent);
  box-shadow:
    0 0 0 1px color-mix(in srgb, var(--color-corporate-green-50) 40%, transparent),
    0 10px 15px -3px rgb(0 0 0 / 30%),
    0 4px 6px -4px rgb(0 0 0 / 30%);
}

.orb-board__svc-btn--off {
  color: var(--text-muted);
  background: color-mix(in srgb, var(--bg-surface) 80%, transparent);
  box-shadow:
    0 0 0 1px var(--border),
    0 10px 15px -3px rgb(0 0 0 / 30%),
    0 4px 6px -4px rgb(0 0 0 / 30%);
}

.orb-board__svc-btn--off:hover {
  color: var(--text);
  background: var(--bg-surface);
}

.orb-board__svc-caret {
  transition: transform 0.15s;
}

.orb-board__svc-caret--open {
  transform: rotate(180deg);
}

.orb-board__svc-menu {
  position: absolute;
  right: 0;
  bottom: 100%;
  z-index: 10;
  width: 120px;
  margin-bottom: 6px;
  overflow: hidden;
  background: var(--bg-surface);
  border-radius: 12px;
  box-shadow:
    0 0 0 1px var(--border),
    0 25px 50px -12px rgb(0 0 0 / 50%);
}

.orb-board__svc-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 5px 10px;
  font-size: var(--font-size-normal);
  line-height: 16px;
  color: var(--text-muted);
  transition:
    color 0.15s,
    background-color 0.15s;
}

.orb-board__svc-item:hover {
  color: var(--text);
  background: var(--bg-hover);
}

.orb-board__svc-item--active,
.orb-board__svc-item--active:hover {
  color: var(--color-corporate-green-40);
  background: color-mix(in srgb, var(--color-corporate-green-50) 10%, transparent);
}

.orb-board__ctx-backdrop {
  position: fixed;
  inset: 0;
  z-index: 40;
}

.orb-board__ctx {
  position: fixed;
  z-index: 50;
  min-width: 224px;
  padding: 6px 0;
  background: var(--bg-glass);
  backdrop-filter: blur(12px);
  border-radius: 12px;
  box-shadow:
    0 0 0 1px var(--border),
    0 25px 50px -12px rgb(0 0 0 / 60%);
}

.orb-board__ctx-header {
  margin-bottom: var(--dimension-3);
  padding: var(--dimension-4) 14px;
  border-bottom: 1px solid var(--border);
}

.orb-board__ctx-name {
  overflow: hidden;
  max-width: 208px;
  font-size: var(--font-size-normal);
  line-height: 16px;
  font-weight: 600;
  color: var(--text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.orb-board__ctx-type {
  margin-top: var(--dimension-2);
  font-size: 10px;
  color: var(--text-muted);
}

.orb-board__ctx-item {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  width: 100%;
  padding: var(--dimension-4) 14px;
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
  text-align: left;
  transition:
    color 0.15s,
    background-color 0.15s;
}

.orb-board__ctx-item:hover {
  color: var(--text);
  background: var(--bg-hover);
}

.orb-board__ctx-icon {
  flex-shrink: 0;
  width: 14px;
  height: 14px;
}

.orb-board__ctx-empty {
  padding: var(--dimension-4) 14px;
  font-size: var(--font-size-normal);
  line-height: 16px;
  font-style: italic;
  color: var(--text-muted);
}
</style>
