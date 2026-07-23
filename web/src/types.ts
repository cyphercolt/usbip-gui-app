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

export interface NodeState {
  info: NodeInfo;
  shareable: Device[];
  attached: AttachedDevice[];
}
