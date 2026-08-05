// Mirrors the FastAPI/pydantic models in node/usbip_node/core/models.py.
// Phase 4 can auto-generate these from the node's OpenAPI schema.

export interface Device {
  busid: string;
  description: string;
  shared: boolean;
}

export interface AttachedDevice {
  port: string;
  busid: string;
  description: string;
  remote_host: string | null;
  auto: boolean;
}

export interface NodeInfo {
  node_id: string;
  display_name: string;
  os_name: string;
  version: string;
  host: string;
  port: number;
  reachable: boolean;
  paired: boolean;
}

export interface CommandResponse {
  ok: boolean;
  message: string;
}

export interface PairedRef {
  node_id: string;
  name: string;
}

export interface SecurityState {
  mode: "open" | "locked";
  this_node: PairedRef;
  trusted: PairedRef[];
  pending: PairedRef[];
}

export interface AuthStatus {
  enabled: boolean;
  authed: boolean;
  totp_enabled: boolean;
  username: string;
}

export interface SetAuthResponse {
  ok: boolean;
  message: string;
  totp_secret: string | null;
  otpauth_uri: string | null;
}

export interface UpdateState {
  node_id: string;
  current_version: string;
  installed_commit: string;
  installed_commit_time: string | null;
  remote_commit: string | null;
  remote_commit_time: string | null;
  branch: string;
  update_available: boolean;
  update_running: boolean;
  update_stage: string;
  update_message: string;
  last_check: string | null;
  can_update: boolean;
  rollback_tag: string | null;
}

export interface NodeState {
  info: NodeInfo;
  shareable: Device[];
  attached: AttachedDevice[];
  update?: UpdateState;
}
