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
  reachable: boolean;
}

export interface NodeState {
  info: NodeInfo;
  shareable: Device[];
  attached: AttachedDevice[];
}
