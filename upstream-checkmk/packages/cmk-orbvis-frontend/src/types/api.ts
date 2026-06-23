/**
 * TypeScript types mirroring the backend Pydantic schemas.
 * In production, generate these from the OpenAPI spec:
 *   npx openapi-typescript http://localhost:8000/api/openapi.json -o src/types/api.ts
 */

export type ObjectType =
  | 'host'
  | 'service'
  | 'hostgroup'
  | 'servicegroup'
  | 'dyngroup'
  | 'map'
  | 'image'
  | 'line'
  | 'textbox'
  | 'cmk_label'
  | 'graph'
  | 'aggregation'
  | 'site'

export interface AggregationInfo {
  id: string
  title: string
  pack_id: string
  /** Aggregation function (worst / best / count_ok / state_of_host / …)
   * used by the EditPanel as a read-only chip. May be null when the
   * cmk.bi compiler couldn't extract it (e.g. very old CMK versions). */
  function?: string | null
}

export interface AggregationNode {
  name: string
  node_type: 'bi_aggregator' | 'bi_leaf'
  state: number
  in_downtime?: boolean
  acknowledged?: boolean
  host_name?: string | null
  service_description?: string | null
  /** Plugin output of the node's compute result (leaf check output). */
  output?: string
  children: AggregationNode[]
}

export interface LabelConfig {
  show: boolean
  text?: string | null
  x: number
  y: number
  size: number
  color: string
  background: string
  // Fixed pixel width that wraps long labels (NagVis label_width).
  width?: number | null
  weight?: 'normal' | 'bold' | null
  align?: 'left' | 'right' | 'center' | 'justify' | null
}

export interface DisplayConfig {
  mode: 'icon' | 'text' | 'gadget'
  image?: string | null
  image_size?: number | null
  gadget_type?: 'gauge' | 'bar' | 'trafficlight' | 'value' | null
  gadget_metric?: string | null
}

export type LineStyle =
  | 'plain'
  | 'arrow_end'
  | 'arrow_start'
  | 'arrow_both'
  | 'arrow_inward'
  | 'dashed'

export type LinePerfdataLabel = 'none' | 'percent' | 'bandwidth' | 'both'

export type ServiceLayout = 'off' | 'fan' | 'row' | 'orbit' | 'donut'

export interface StaticView {
  type: 'static'
  problems_only?: boolean
}
export interface WorldmapView {
  type: 'worldmap'
  lat: number
  lng: number
  zoom: number
  tile_url?: string | null
  tile_saturate?: number | null
  auto_source?: 'all_hosts' | 'hostgroup' | 'servicegroup' | null
  auto_filter_value?: string
  problems_only?: boolean
}
export interface RadarView {
  type: 'radar'
  filter: string
  filter_value: string
  problems_only?: boolean
}
export interface FlowNodePosition {
  x: number
  y: number
}
export interface FlowView {
  type: 'flow'
  root?: string | null
  child_layers?: number | null
  parent_layers?: number | null
  top_affected_hosts?: number | null
  max_services_per_host?: number | null
  positions?: Record<string, FlowNodePosition>
  service_layout?: ServiceLayout | null
  problems_only?: boolean
}
export interface FolderTreeView {
  type: 'foldertree'
  root_folder?: string
  default_view?: 'list' | 'map'
  default_expand_depth?: number
  show_services?: boolean
  show_empty_folders?: boolean
  problems_only?: boolean
  /** What counts as a "problem" for problems_only ('any' default). */
  problems_severity?: 'any' | 'critical'
  only_hard_states?: boolean
  sites?: string[]
}
export type PresentationTheme = 'midnight' | 'paper' | 'ops' | 'aurora'

// Monitoring object types a presentation element can bind to. Absent/null
// keeps the legacy host/service derivation.
export type PresentationObjectType =
  | 'host'
  | 'service'
  | 'hostgroup'
  | 'servicegroup'
  | 'aggregation'

export interface ElementLabel {
  show: boolean
  text?: string | null
  size: number
  // null = inherit the slide theme.
  color?: string | null
  background?: string | null
  weight?: 'normal' | 'bold' | null
  align?: 'left' | 'right' | 'center' | null
}

// Absolute slide pixels — deliberately not the static map's percentages.
interface PresentationElementBase {
  id: string
  x: number
  y: number
  w: number
  h: number
  rotation: number
  z: number
  opacity: number
  locked: boolean
  hidden: boolean
  name?: string | null
}

export interface ShapeElement extends PresentationElementBase {
  kind: 'shape'
  shape: 'rect' | 'ellipse' | 'line' | 'arrow'
  fill?: string | null
  stroke?: string | null
  stroke_width: number
  corner_radius: number
  dash: 'solid' | 'dashed' | 'dotted'
  // Optional monitoring binding: when bound, the shape colours by state and can
  // show a state label.
  connection_id?: string | null
  object_type?: PresentationObjectType | null
  host_name?: string | null
  service_description?: string | null
  group_name?: string | null
  aggregation_id?: string | null
  only_hard_states?: boolean
  label?: ElementLabel | null
  // Endpoint docking (line/arrow): start/end follows a referenced element's centre.
  start_ref?: string | null
  end_ref?: string | null
  // Weathermap flow: animate + drive colour/width/speed from a utilisation
  // metric; a back metric splits the connector into a two-way link.
  flow?: boolean
  flow_metric?: string | null
  flow_metric_back?: string | null
  // Intended data slot (template placeholder): counted by the connect-data
  // walkthrough until bound; plain decorative shapes never are.
  data_slot?: boolean
}

export interface TextElement extends PresentationElementBase {
  kind: 'text'
  text: string
  font_family?: string | null
  font_size: number
  font_weight: 'normal' | 'bold'
  font_style: 'normal' | 'italic'
  text_align: 'left' | 'center' | 'right' | 'justify'
  line_height: number
  // null = inherit the slide theme.
  color?: string | null
  background?: string | null
  letter_spacing: number
}

export interface ImageElement extends PresentationElementBase {
  kind: 'image'
  src?: string | null
  fit: 'cover' | 'contain' | 'fill'
  alt?: string | null
}

export interface DataElement extends PresentationElementBase {
  kind: 'data'
  connection_id?: string | null
  object_type?: PresentationObjectType | null
  host_name?: string | null
  service_description?: string | null
  group_name?: string | null
  aggregation_id?: string | null
  only_hard_states: boolean
  display: DisplayConfig
  label?: ElementLabel | null
  fill?: string | null
  stroke?: string | null
}

export interface GroupElement extends PresentationElementBase {
  kind: 'group'
  children: string[]
}

export type PresentationElement =
  | ShapeElement
  | TextElement
  | ImageElement
  | DataElement
  | GroupElement

export interface PresentationView {
  type: 'presentation'
  width: number
  height: number
  theme: PresentationTheme
  background?: string | null
  background_image?: string | null
  elements: PresentationElement[]
  problems_only?: boolean
}

export type MapView =
  | StaticView
  | WorldmapView
  | RadarView
  | FlowView
  | FolderTreeView
  | PresentationView

// Unsaved server-side foldertree view fields the Settings preview sends so the
// server rebuilds the tree without persisting. Client-side fields (problems_only,
// default_view, expand depth) are mirrored in the map and stay out of this.
export interface FolderTreeOverride {
  rootFolder: string
  showEmptyFolders: boolean
  onlyHardStates: boolean
  sites: string[]
}

export interface FolderTreeNode {
  path: string
  title: string
  kind: 'folder' | 'host' | 'service'
  state: string
  is_empty: boolean
  folder_id: string
  host_count: number
  problem_count: number
  severity_counts: Record<string, number>
  output: string
  acknowledged: boolean
  in_downtime: boolean
  /** Distributed: the node's site went dead — last known state, render greyed. */
  stale?: boolean
  site_id: string | null
  services_summary?: ServicesSummary | null
  children: FolderTreeNode[]
  // Only set on service leaves built client-side from a lazy folder-host-services
  // fetch (never emitted by the backend tree).
  last_state_change?: number | null
  is_flapping?: boolean
  // Synthetic node (map only): groups a folder's healthy hosts into one
  // "✓ N OK" container so problems dominate the treemap. Never from the backend.
  ok_group?: boolean
}

// Live-field update for one foldertree node, keyed by path. Sent over SSE instead
// of the whole tree once a snapshot exists. `children_order` is set only when the
// node's child order changed (severity-sorted siblings reorder on a state flip).
export interface FolderTreeNodePatch {
  path: string
  title: string
  site_id?: string | null
  state: string
  is_empty: boolean
  host_count: number
  problem_count: number
  severity_counts: Record<string, number>
  output: string
  acknowledged: boolean
  in_downtime: boolean
  is_flapping: boolean
  stale?: boolean
  last_state_change?: number | null
  services_summary?: ServicesSummary | null
  children_order?: string[] | null
}

// SSE folder-tree update: `full` carries the whole tree (first tick / structural
// change), else `changed` carries only the nodes whose fields or child order moved.
export interface FolderTreeDelta {
  full: boolean
  tree?: FolderTreeNode | null
  changed: FolderTreeNodePatch[]
}

// One service of a foldertree host, fetched lazily when the host is expanded.
export interface FolderHostService {
  name: string
  state: string
  output: string
  acknowledged: boolean
  in_downtime: boolean
  is_flapping: boolean
  last_state_change: number | null
}

// One host + its services that matched a server-side folder-map service
// search (grouped by host so the frontend injects them into the loaded tree).
export interface FolderServiceMatch {
  host: string
  site_id: string | null
  services: FolderHostService[]
}

// Result of a server-side (Livestatus) folder-map service search.
export interface FolderServiceSearchResult {
  matches: FolderServiceMatch[]
  truncated: boolean
  limit: number
}

// Bulk-ack target shape shared by DetailDrawer (emits) → MapView
// (handler) → BulkAckModal (props). One declaration so a future field
// (e.g. site_id for federated targets) lands in one place.
export interface BulkAckTarget {
  host: string
  service: string | null
}

export type HostState = 'UP' | 'DOWN' | 'UNREACHABLE' | 'PENDING'
export type ServiceState = 'OK' | 'WARNING' | 'CRITICAL' | 'UNKNOWN' | 'PENDING'
export type MonitoringState = HostState | ServiceState | 'NO_PERMISSION' | 'NOT_FOUND'

export interface MapObject {
  id: string
  type: ObjectType
  connection_id?: string | null
  x: number
  y: number
  lat?: number | null
  lng?: number | null
  // null/undefined ⇒ inherit the map's default_z (NagVis-style global default).
  z?: number | null
  host_name?: string | null
  service_description?: string | null
  // Runtime-only hint (not persisted): the host's monitoring site, so commands
  // route to the right site on maps whose objects aren't in the state map
  // (e.g. the Flow Map, which is topology-driven). Optional everywhere else.
  site_id?: string | null
  group_name?: string | null
  map_name?: string | null
  image_src?: string | null
  x2?: number | null
  y2?: number | null
  lat2?: number | null
  lng2?: number | null
  // Optional line bend; null ⇒ geometric midpoint of the two endpoints.
  mid_x?: number | null
  mid_y?: number | null
  // Sticky connectors: a bound endpoint follows the referenced object's position.
  start_ref?: string | null
  end_ref?: string | null
  line_style?: LineStyle | null
  line_width?: number | null
  line_perfdata_label?: LinePerfdataLabel | null
  line_weather_color?: boolean | null
  weathermap_metric?: string | null
  weathermap_metric_out?: string | null
  cmk_label_name?: string | null
  cmk_label_value?: string | null
  cmk_label_target?: 'hosts' | 'services' | null
  aggregation_id?: string | null
  object_types?: 'host' | 'service' | null
  object_filter?: string | null
  bundle_kind?: 'static' | 'location' | null
  bundle_hosts?: string[] | null
  bundle_precision?: number | null
  expand_depth?: number
  only_hard_states?: boolean
  recognize_services?: boolean
  exclude_members?: string | null
  exclude_member_states?: string | null
  label?: LabelConfig | null
  display?: DisplayConfig | null
  label_border?: string | null
  label_maxlen?: number | null
  textbox_background?: string | null
  textbox_border?: string | null
  textbox_width?: number | null
  textbox_height?: number | null
  graph_url?: string | null
  graph_embed_type?: 'img' | 'iframe'
  graph_width?: number | null
  graph_height?: number | null
  graph_refresh_interval?: number | null
  graph_metric?: string[] | null
  graph_id?: string | null
  graph_time_window?: number | null
  line_color?: string | null
  line_color_border?: string | null
  url?: string | null
  url_target: string
  hover_url?: string | null
  hover_template?: string | null
  context_template?: string | null
}

export type ClickAction = 'link' | 'none'

export type RenderMode = 'default' | 'nagvis_classic'

export interface MapConfig {
  name: string
  alias: string
  readonly?: boolean
  connection_id: string
  icon_size: number | null
  rotation_interval: number
  sort_order: number
  click_action: ClickAction
  hover_template?: string | null
  context_template?: string | null
  background_image?: string | null
  background_color?: string | null
  render_mode?: RenderMode
  // Map-wide fallback z for objects without an explicit z. Default 1.
  default_z?: number
  show_in_lists?: boolean
  version?: number
  // Persisted percent-positioning divisor; see MapConfig.canvas_width (backend).
  canvas_width?: number | null
  canvas_height?: number | null
  view: MapView
  objects: MapObject[]
}

export interface MapRead {
  name: string
  alias: string
  background_image?: string | null
  background_color?: string | null
  icon_size: number | null
  connection_id: string
  view_type: string
  view: MapView
  object_count: number
  rotation_interval: number
  version?: number
  sort_order: number
  click_action: ClickAction
  readonly?: boolean
  show_in_lists?: boolean
  hover_template?: string | null
  context_template?: string | null
  render_mode?: RenderMode
  default_z?: number
  can_edit?: boolean
}

export interface MapBulkDeleteFailure {
  name: string
  reason: string
}

export interface MapBulkDeleteResult {
  deleted: string[]
  failed: MapBulkDeleteFailure[]
}

export interface MapBulkEditFailure {
  name: string
  reason: string
}

export interface MapBulkEditResult {
  updated: string[]
  failed: MapBulkEditFailure[]
}

export interface ServicesSummary {
  ok: number
  warning: number
  critical: number
  unknown: number
  pending: number
}

export interface ObjectState {
  object_id: string
  type: string
  state: MonitoringState
  output: string
  perf_data: string
  acknowledged: boolean
  in_downtime: boolean
  stale: boolean
  notifications_enabled?: boolean
  active_checks_enabled?: boolean
  address?: string
  alias?: string
  site_id?: string | null
  last_check?: number | null
  next_check?: number | null
  state_type?: string
  current_attempt?: number
  max_attempts?: number
  last_state_change?: number | null
  tree?: AggregationNode | null
  services_summary?: ServicesSummary | null
  hosts_summary?: ServicesSummary | null
}

export interface PerfometerSegment {
  pct: number
  color: string
}

export interface PerfometerResult {
  label: string
  rows: PerfometerSegment[][]
  pcts: number[]
}

// cmk-shared-typing UnitFormat plus the perfdata→registry scale factor —
// what GET /metrics/units returns per raw perfdata label.
export interface MetricUnitSpec {
  notation: 'decimal' | 'si' | 'iec' | 'standard_scientific' | 'engineering_scientific' | 'time'
  symbol: string
  precision: { type: 'auto' | 'strict'; digits: number }
  scale: number
}

export type MetricUnitMap = Record<string, MetricUnitSpec>

export interface DowntimeEntry {
  id: string
  site_id: string
  host_name: string
  service_description?: string
  author: string
  comment: string
  start_time: string
  end_time: string
  type: 'host' | 'service'
}

export interface ServiceNode {
  name: string
  state: string
  output: string
  acknowledged?: boolean
  in_downtime?: boolean
  notifications_enabled?: boolean
  last_state_change?: number | null
  last_check?: number | null
  next_check?: number | null
}

export interface TopologyNode {
  name: string
  parents: string[]
  state: string
  output: string
  site_id?: string | null
  services?: ServiceNode[]
  services_truncated_count?: number
  services_omitted?: boolean
  alias?: string
  address?: string
  acknowledged?: boolean
  in_downtime?: boolean
  notifications_enabled?: boolean
  active_checks_enabled?: boolean
  last_check?: number | null
  next_check?: number | null
  last_state_change?: number | null
  state_type?: string
  current_attempt?: number
  max_attempts?: number
  services_summary?: ServicesSummary | null
}

export interface MapStates {
  map_name: string
  states: ObjectState[]
  generated_at: number
  connection_ok: boolean
  /** Distributed: federation sites that stopped answering (their tree leaves
   *  freeze on the last known state, marked stale). */
  dead_sites?: string[]
  folder_tree?: FolderTreeNode | null
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface StreamTicketResponse {
  ticket: string
  expires_in: number
}

export interface PermissionRef {
  perm_id: number
  mod: string
  act: string
  obj: string
}

export interface UserRead {
  user_id: number
  name: string
  is_active: boolean
  is_admin: boolean
  must_change_password: boolean
  theme: string
  language: string
  cmk_theme: string | null
  cmk_language: string | null
  cmk_inline_help: boolean
  can_configure: boolean
  can_create_maps: boolean
  command_permissions: string[]
  roles: RoleRef[]
  permissions: PermissionRef[]
}

export interface RoleRef {
  role_id: number
  name: string
}

export interface RoleRead {
  role_id: number
  name: string
  permissions: PermissionRead[]
}

export interface PermissionRead {
  perm_id: number
  mod: string
  act: string
  obj: string
}

export interface GroupMember {
  host: string
  service: string
  state: string
  output: string
  acknowledged?: boolean
  in_downtime?: boolean
  notifications_enabled?: boolean
  last_state_change?: number | null
}

export interface ConnectionConfig {
  id: string
  type: 'livestatus' | 'icinga2' | 'test'
  label: string
  socket_path?: string | null
  host?: string | null
  port?: number | null
  timeout: number
  checkmk_url?: string | null
  automation_user?: string | null
  automation_secret?: string | null
  icinga2_url?: string | null
  icinga2_username?: string | null
  icinga2_password?: string | null
  icinga2_verify_ssl?: boolean
}

export interface ConnectionContext {
  monitoring_core: 'cmc' | 'nagios' | null
  omd_site: string | null
}

export interface GlobalSettings {
  icon_size: number
  view_type: string
  label_show: boolean
  label_size: number
  label_color: string
  label_background: string
  url_target: string
  z: number
  line_style?: LineStyle | null
  default_backend_id: string
  default_map_type: string
  default_render_mode?: RenderMode
  hover_template?: string | null
  context_template?: string | null
  map_list_view?: MapListView
}

export type MapListView = 'cards' | 'table'

export type LogLevel = 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL'

export interface SystemSettings {
  log_level?: LogLevel | null
  checkmk_url?: string | null
  enable_folder_maps?: boolean
  enable_graph_objects?: boolean
  enable_presentation_maps?: boolean
}

// Slim timing patch for fields excluded from the state change-hash; see backend ObjectTiming.
export interface ObjectTiming {
  object_id: string
  last_check?: number | null
  next_check?: number | null
  current_attempt?: number
}

// The `states` payload of an SSE state_update: like MapStates, but the foldertree
// arrives as a delta (folder_tree_delta) rather than the full tree each tick.
export interface StateUpdatePayload {
  map_name: string
  states: ObjectState[]
  generated_at: number
  connection_ok: boolean
  dead_sites?: string[]
  folder_tree_delta?: FolderTreeDelta | null
}

export interface WebSocketStateUpdate {
  type: 'state_update'
  map: string
  // When `full` is true (or absent, for old servers), `states.states` holds
  // every object on the map and replaces the local map. When false, it
  // contains only added/changed entries and `removed_ids` lists object_ids
  // that disappeared since the previous tick — frontend merges in place.
  states: StateUpdatePayload
  full?: boolean
  removed_ids?: string[]
  // Timing-only patches for objects not in `states.states`.
  timing?: ObjectTiming[]
}

// Slim check-timing patch for a flow topology host (+ its services), parallel
// to ObjectTiming on the state channel. Carries the last/next-check fields the
// topology change-hash omits, so the Flow Map's next-check stays live.
export interface ServiceTiming {
  name: string
  last_check?: number | null
  next_check?: number | null
}

export interface TopologyTiming {
  name: string
  last_check?: number | null
  next_check?: number | null
  current_attempt?: number
  services?: ServiceTiming[]
}

export interface TopologyDelta {
  full: boolean
  generated_at: number
  added: TopologyNode[]
  changed: TopologyNode[]
  removed: string[]
  timing?: TopologyTiming[]
}

export interface WebSocketTopologyUpdate {
  type: 'topology_update'
  map: string
  delta: TopologyDelta
}

export interface ImageEntry {
  name: string
  url: string
  builtin: boolean
}

export interface ImageUsageEntry {
  map: string
  alias: string | null
  object_ids: string[]
  is_background: boolean
}

export interface MapPermissions {
  view: string[]
  edit: string[]
}

export interface MetricPoint {
  ts: number
  value: number
  unit: string
}

export interface MetricGraphGroup {
  id: string
  title: string
  metrics: string[]
  // Metrics CMK draws mirrored below the x-axis (a Bidirectional graph's lower half).
  mirrored?: string[]
}

export interface MetricChoice {
  name: string
  title: string
}

export interface MetricHistoryResponse {
  series: Record<string, MetricPoint[]>
  titles: Record<string, string>
  graphs: MetricGraphGroup[]
  error?: string | null
}

export interface CommentInfo {
  id: number
  author: string
  comment: string
  entry_time: number
  expire_time: number | null
}

export interface DowntimeInfo {
  id: number
  author: string
  comment: string
  start_time: number
  end_time: number
  fixed: boolean
}

export interface ObjectDetails {
  type: 'host' | 'service'
  host_name: string
  service_description: string | null
  long_output: string
  check_command: string
  latency: number | null
  execution_time: number | null
  is_flapping: boolean
  in_notification_period: boolean
  last_time_ok: number | null
  notification_period: string
  check_interval: number | null
  parents: string[]
  children: string[]
  host_groups: string[]
  service_groups: string[]
  contact_groups: string[]
  labels: Record<string, string>
  metric_titles: Record<string, string>
  comments: CommentInfo[]
  downtimes: DowntimeInfo[]
}
