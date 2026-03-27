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
  | 'map'
  | 'image'
  | 'line'
  | 'textbox'
  | 'cmk_label'
  | 'graph';

export interface LabelConfig {
  show: boolean;
  text?: string | null;
  x: number;
  y: number;
  size: number;
  color: string;
  background: string;
}

export interface DisplayConfig {
  mode: 'icon' | 'text' | 'gadget';
  image?: string | null;
  image_size?: number | null;
  gadget_type?: 'gauge' | 'bar' | 'trafficlight' | null;
  gadget_metric?: string | null;
}

export type LineStyle =
  | 'plain'
  | 'arrow_end'
  | 'arrow_start'
  | 'arrow_both'
  | 'dashed'
  | 'weathermap';

export interface StaticView {
  type: 'static';
}
export interface WorldmapView {
  type: 'worldmap';
  lat: number;
  lng: number;
  zoom: number;
  tile_url?: string | null;
  tile_saturate?: number | null;
}
export interface RadarView {
  type: 'radar';
  filter: string;
  filter_value: string;
}
export interface AutomapView {
  type: 'automap';
}
export type BoardView = StaticView | WorldmapView | RadarView | AutomapView;

export type HostState = 'UP' | 'DOWN' | 'UNREACHABLE' | 'PENDING';
export type ServiceState = 'OK' | 'WARNING' | 'CRITICAL' | 'UNKNOWN' | 'PENDING';
export type MonitoringState = HostState | ServiceState;

export interface BoardObject {
  id: string;
  type: ObjectType;
  x: number;
  y: number;
  lat?: number | null;
  lng?: number | null;
  z: number;
  host_name?: string | null;
  service_description?: string | null;
  group_name?: string | null;
  map_name?: string | null;
  image_src?: string | null;
  x2?: number | null;
  y2?: number | null;
  line_style?: LineStyle | null;
  weathermap_metric?: string | null;
  cmk_label_name?: string | null;
  cmk_label_value?: string | null;
  cmk_label_target?: 'hosts' | 'services' | null;
  only_hard_states?: boolean;
  recognize_services?: boolean;
  exclude_members?: string | null;
  exclude_member_states?: string | null;
  label?: LabelConfig | null;
  display?: DisplayConfig | null;
  label_border?: string | null;
  label_maxlen?: number | null;
  textbox_background?: string | null;
  textbox_border?: string | null;
  textbox_width?: number | null;
  textbox_height?: number | null;
  graph_url?: string | null;
  graph_embed_type?: 'img' | 'iframe';
  graph_width?: number | null;
  graph_height?: number | null;
  graph_refresh_interval?: number | null;
  graph_metric?: string[] | null;
  graph_id?: string | null;
  graph_time_window?: number | null;
  line_color?: string | null;
  line_color_border?: string | null;
  url?: string | null;
  url_target: string;
  hover_url?: string | null;
  hover_template?: string | null;
  context_template?: string | null;
}

export interface BoardConfig {
  name: string;
  alias: string;
  readonly?: boolean;
  backend_id: string;
  icon_size: number;
  rotation_interval: number;
  hover_template?: string | null;
  context_template?: string | null;
  background_image?: string | null;
  view: BoardView;
  objects: BoardObject[];
}

export interface BoardRead {
  name: string;
  alias: string;
  background_image?: string | null;
  icon_size: number;
  backend_id: string;
  view_type: string;
  view: BoardView;
  object_count: number;
  rotation_interval: number;
  readonly?: boolean;
  show_in_lists?: boolean;
  hover_template?: string | null;
  context_template?: string | null;
}

export interface ObjectState {
  object_id: string;
  type: string;
  state: MonitoringState;
  output: string;
  perf_data: string;
  acknowledged: boolean;
  in_downtime: boolean;
  stale: boolean;
  address?: string;
  last_check?: number | null;
  state_type?: string;
  current_attempt?: number;
  max_attempts?: number;
  last_state_change?: number | null;
}

export interface ServiceNode {
  name: string;
  state: string;
  output: string;
}

export interface TopologyNode {
  name: string;
  parents: string[];
  state: string;
  output: string;
  services?: ServiceNode[];
}

export interface MapStates {
  map_name: string;
  states: ObjectState[];
  generated_at: number;
  backend_ok: boolean;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface PermissionRef {
  perm_id: number;
  mod: string;
  act: string;
  obj: string;
}

export interface UserRead {
  user_id: number;
  name: string;
  is_active: boolean;
  is_admin: boolean;
  must_change_password: boolean;
  theme: string;
  language: string;
  cmk_theme: string | null;
  cmk_language: string | null;
  roles: RoleRef[];
  permissions: PermissionRef[];
}

export interface RoleRef {
  role_id: number;
  name: string;
}

export interface RoleRead {
  role_id: number;
  name: string;
  permissions: PermissionRead[];
}

export interface PermissionRead {
  perm_id: number;
  mod: string;
  act: string;
  obj: string;
}

export interface BackendConfig {
  id: string;
  type: 'livestatus' | 'icinga2' | 'test';
  label: string;
  socket_path?: string | null;
  host?: string | null;
  port: number;
  timeout: number;
  checkmk_url?: string | null;
  automation_user?: string | null;
  automation_secret?: string | null;
  icinga2_url?: string | null;
  icinga2_username?: string | null;
  icinga2_password?: string | null;
  icinga2_verify_ssl?: boolean;
}

export interface BackendContext {
  monitoring_core: 'cmc' | 'nagios' | null;
  omd_site: string | null;
}

export interface GlobalSettings {
  icon_size: number;
  view_type: string;
  label_show: boolean;
  label_size: number;
  label_color: string;
  label_background: string;
  label_x: number;
  label_y: number;
  url_target: string;
  z: number;
  line_style?: LineStyle | null;
  default_backend_id: string;
  default_map_type: string;
  hover_template?: string | null;
  context_template?: string | null;
  checkmk_url?: string | null;
}

export interface WebSocketStateUpdate {
  type: 'state_update';
  map: string;
  states: MapStates;
}

export interface ImageEntry {
  name: string;
  url: string;
}

export interface BoardPermissions {
  view: string[];
  edit: string[];
}

export interface MetricPoint {
  ts: number;
  value: number;
  unit: string;
}

export interface MetricGraphGroup {
  id: string;
  title: string;
  metrics: string[];
}

export interface MetricHistoryResponse {
  series: Record<string, MetricPoint[]>;
  titles: Record<string, string>;
  graphs: MetricGraphGroup[];
}
