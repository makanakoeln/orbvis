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

export interface MapObject {
  id: string
  type: ObjectType
  x: number
  y: number
  host_name?: string
  service_description?: string
  group_name?: string
  map_name?: string
  icon?: string
  line_type?: number
  view_type: string
  label_show: boolean
  label_text?: string
  extra: Record<string, unknown>
}

export interface MapGlobals {
  alias: string
  background_image?: string
  icon_size: number
  backend_id: string
  hover_template?: string
  context_template?: string
}

export interface MapConfig {
  name: string
  globals: MapGlobals
  objects: MapObject[]
}

export interface MapRead {
  name: string
  alias: string
  background_image?: string
  icon_size: number
  backend_id: string
  object_count: number
}

export interface ObjectState {
  object_id: string
  type: string
  state: MonitoringState
  output: string
  acknowledged: boolean
  in_downtime: boolean
  stale: boolean
}

export interface MapStates {
  map_name: string
  states: ObjectState[]
  generated_at: number
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface UserRead {
  user_id: number
  name: string
  is_active: boolean
  is_admin: boolean
  roles: RoleRef[]
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

export interface WebSocketStateUpdate {
  type: 'state_update'
  map: string
  states: MapStates
}
