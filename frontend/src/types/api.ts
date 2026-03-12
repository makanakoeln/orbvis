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
  | 'shape'
  | 'line'
  | 'textbox'

export type HostState = 'UP' | 'DOWN' | 'UNREACHABLE' | 'PENDING'
export type ServiceState = 'OK' | 'WARNING' | 'CRITICAL' | 'UNKNOWN' | 'PENDING'
export type MonitoringState = HostState | ServiceState

export interface BoardObject {
  id: string
  type: ObjectType
  x: number
  y: number
  lat?: number
  lng?: number
  host_name?: string
  service_description?: string
  group_name?: string
  map_name?: string
  icon?: string
  line_type?: number
  view_type: string
  gadget_type?: string
  gadget_metric?: string
  icon_size?: number
  label_show: boolean
  label_text?: string
  label_x: number
  label_y: number
  label_size: number
  label_color: string
  label_background: string
  url?: string
  url_target: string
  z: number
  hover_template?: string | null
  context_template?: string | null
  extra: Record<string, unknown>
}

export interface BoardGlobals {
  alias: string
  background_image?: string
  icon_size: number
  backend_id: string
  hover_template?: string
  context_template?: string
  map_type: string
  worldmap_lat: number
  worldmap_lng: number
  worldmap_zoom: number
  radar_type: string
  radar_value: string
  rotation_interval: number
}

export interface BoardConfig {
  name: string
  globals: BoardGlobals
  objects: BoardObject[]
  readonly?: boolean
}

export interface BoardRead {
  name: string
  alias: string
  background_image?: string | null
  icon_size: number
  backend_id: string
  map_type: string
  object_count: number
  rotation_interval: number
  readonly?: boolean
  worldmap_lat?: number
  worldmap_lng?: number
  worldmap_zoom?: number
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
}

export interface ServiceNode {
  name: string
  state: string
  output: string
}

export interface TopologyNode {
  name: string
  parents: string[]
  state: string
  output: string
  services?: ServiceNode[]
}

export interface MapStates {
  map_name: string
  states: ObjectState[]
  generated_at: number
  backend_ok: boolean
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
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

export interface BackendConfig {
  id: string
  type: 'livestatus' | 'icinga2' | 'test'
  label: string
  socket_path?: string | null
  host?: string | null
  port: number
  timeout: number
  checkmk_url?: string | null
  icinga2_url?: string | null
  icinga2_username?: string | null
  icinga2_password?: string | null
  icinga2_verify_ssl?: boolean
}

export interface GlobalSettings {
  icon_size: number
  view_type: string
  label_show: boolean
  label_size: number
  label_color: string
  label_background: string
  label_x: number
  label_y: number
  url_target: string
  z: number
  line_type?: number | null
  default_backend_id: string
  default_map_type: string
  hover_template?: string | null
  context_template?: string | null
}

export interface WebSocketStateUpdate {
  type: 'state_update'
  map: string
  states: MapStates
}


export interface IconEntry {
  name: string
  url: string
}

export interface BoardPermissions {
  view: string[]
  edit: string[]
}
