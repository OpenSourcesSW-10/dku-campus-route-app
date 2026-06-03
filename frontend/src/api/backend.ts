import axios from "axios";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export const api = axios.create({
  baseURL: API_BASE_URL,
});

export type RoomPosition = {
  position_id: string;
  room_id: string;
  indoor_map_id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  polygon_points?: string | null;
  center_x?: number | null;
  center_y?: number | null;
};

export type RoomSearchResult = {
  type: "ROOM";
  roomId: string;
  roomCode: string;
  buildingId: string;
  buildingName: string;
  floorNumber: number;
  floorLabel: string;
  roomNumber: string;
  indoorMap: {
    indoorMapId: string;
    mapFileUrl: string;
    canvasWidth: number;
    canvasHeight: number;
  };
  position?: RoomPosition | null;
  nearestIndoorNodeId?: string | null;
};

export type IndoorMap = {
  indoor_map_id: string;
  building_id: string;
  floor_number: number;
  floor_label: string;
  map_file_url: string;
  canvas_width: number;
  canvas_height: number;
  rooms: Array<{
    room_id: string;
    room_number: string;
    description?: string | null;
    nearest_indoor_node_id?: string | null;
  }>;
  room_positions: RoomPosition[];
  indoor_nodes: Array<{
    indoor_node_id: string;
    floor_number: number;
    node_type: string;
    x: number;
    y: number;
  }>;
  indoor_edges: Array<{
    indoor_edge_id: string;
    from_node_id: string;
    to_node_id: string;
    is_bidirectional: boolean;
    edge_type: string;
  }>;
};

export type RouteDetail = {
  routeType: string;
  title: string;
  totalCost: number;
  totalDistance: number;
  totalEstimatedTime: number;
  reason?: string | null;
  segments: Array<{
    type: string;
    buildingId?: string | null;
    floorNumber?: number | null;
    indoorMapId?: string | null;
    nodeIds: string[];
    edgeIds: string[];
    pathPoints: Array<{
      nodeId: string;
      x?: number | null;
      y?: number | null;
      floorNumber?: number | null;
      indoorMapId?: string | null;
      latitude?: number | null;
      longitude?: number | null;
      label?: string | null;
    }>;
  }>;
};

export type OutdoorMap = {
  map_file_url: string;
  canvas_width?: number | null;
  canvas_height?: number | null;
  nodes: Array<{
    outdoor_node_id: string;
    node_type: string;
    building_id?: string | null;
    latitude?: number | null;
    longitude?: number | null;
    map_x?: number | null;
    map_y?: number | null;
    outdoor_level?: string | null;
    altitude_m?: number | null;
    label?: string | null;
    description?: string | null;
  }>;
  edges: Array<{
    outdoor_edge_id: string;
    from_node_id: string;
    to_node_id: string;
    is_bidirectional: boolean;
    distance: number;
    estimated_time: number;
    edge_type: string;
    is_covered: boolean;
    is_indoor: boolean;
    has_stairs: boolean;
    has_slope: boolean;
    slope_level: number;
    altitude_gain?: number | null;
    complexity_level: number;
    accessibility_level: number;
    is_shortcut: boolean;
    cost_fast: number;
    cost_comfortable: number;
    cost_indoor: number;
    description?: string | null;
  }>;
  entrance_links: Array<{
    link_id: string;
    building_id: string;
    outdoor_node_id: string;
    indoor_node_id: string;
    entrance_name: string;
    floor_number?: number | null;
    is_main: boolean;
  }>;
};

export function mapAssetUrl(mapFileUrl: string) {
  if (mapFileUrl.startsWith("http")) return mapFileUrl;
  return `${API_BASE_URL}${mapFileUrl}`;
}

export async function searchRoom(keyword: string) {
  const response = await api.get<RoomSearchResult>("/api/rooms/search", {
    params: { keyword },
  });
  return response.data;
}

export async function getIndoorMap(buildingId: string, floor: string | number) {
  const response = await api.get<IndoorMap>(
    `/api/buildings/${buildingId}/floors/${floor}/indoor-map`,
  );
  return response.data;
}

export async function getIntegratedRoutes(start: string, destination: string) {
  const response = await api.post<RouteDetail[]>("/api/routes", {
    start,
    destination,
    routeTypes: ["DEFAULT", "COMFORTABLE", "RAINY"],
    preferences: {},
  });
  return response.data;
}

export async function getOutdoorMap() {
  const response = await api.get<OutdoorMap>("/api/outdoor/map");
  return response.data;
}
