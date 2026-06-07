import axios from "axios";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export const api = axios.create({
  baseURL: API_BASE_URL,
});

export function setAuthToken(token?: string | null) {
  if (token) {
    api.defaults.headers.common.Authorization = `Bearer ${token}`;
    return;
  }
  delete api.defaults.headers.common.Authorization;
}

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

export type User = {
  user_id: string;
  email: string;
  nickname: string;
  email_verified: boolean;
  role: string;
  created_at?: string | null;
};

export type AuthTokenResponse = {
  accessToken: string;
  tokenType: string;
  user: User;
};

export type TmiLocation = {
  tmi_location_id: string;
  name: string;
  location_type: string;
  building_id?: string | null;
  room_id?: string | null;
  indoor_map_id?: string | null;
  floor_number?: number | null;
  latitude?: number | null;
  longitude?: number | null;
  map_x?: number | null;
  map_y?: number | null;
  representative_tags?: string | null;
  status: string;
  verified_count: number;
  created_by?: string | null;
  created_at?: string | null;
};

export type Report = {
  report_id: string;
  user_id?: string | null;
  report_type: string;
  target_type: string;
  target_id?: string | null;
  tmi_location_id?: string | null;
  building_id?: string | null;
  room_id?: string | null;
  title: string;
  content: string;
  tags?: string | null;
  status: string;
  verified_count: number;
  created_at?: string | null;
};

export type ReferenceData = {
  edgeTypes: Array<{
    edge_type: string;
    display_name: string;
    description?: string | null;
  }>;
  indoorNodeTypes: Array<{
    node_type: string;
    display_name: string;
    description?: string | null;
  }>;
  roomCategories: Array<{
    room_type: string;
    display_name: string;
    description?: string | null;
  }>;
  entrances: Array<{
    entrance_id: string;
    building_id: string;
    floor_number: number;
    entrance_name: string;
    entrance_type: string;
    description?: string | null;
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

export async function getReferenceData() {
  const response = await api.get<ReferenceData>("/api/reference-data");
  return response.data;
}

export async function register(email: string, password: string, nickname: string) {
  const response = await api.post<AuthTokenResponse>("/api/auth/register", {
    email,
    password,
    nickname,
  });
  setAuthToken(response.data.accessToken);
  return response.data;
}

export async function login(email: string, password: string) {
  const response = await api.post<AuthTokenResponse>("/api/auth/login", {
    email,
    password,
  });
  setAuthToken(response.data.accessToken);
  return response.data;
}

export async function requestEmailVerification(email: string) {
  const response = await api.post<{
    verificationId: string;
    email: string;
    expiresAt: string;
    deliveryMode: string;
    devCode?: string | null;
  }>("/api/auth/email/request", { email });
  return response.data;
}

export async function verifyEmail(email: string, code: string) {
  const response = await api.post<{ email: string; verified: boolean; user?: User | null }>(
    "/api/auth/email/verify",
    { email, code },
  );
  return response.data;
}

export async function getMe() {
  const response = await api.get<User>("/api/auth/me");
  return response.data;
}

export async function getTmiLocations(params?: {
  location_type?: string;
  building_id?: string;
  tag?: string;
}) {
  const response = await api.get<TmiLocation[]>("/api/tmi", { params });
  return response.data;
}

export async function createTmiLocation(payload: {
  name: string;
  locationType: string;
  buildingId?: string | null;
  roomId?: string | null;
  indoorMapId?: string | null;
  floorNumber?: number | null;
  latitude?: number | null;
  longitude?: number | null;
  mapX?: number | null;
  mapY?: number | null;
  representativeTags?: string | null;
}) {
  const response = await api.post<TmiLocation>("/api/tmi", payload);
  return response.data;
}

export async function createReport(payload: {
  reportType: string;
  targetType: string;
  targetId?: string | null;
  tmiLocationId?: string | null;
  buildingId?: string | null;
  roomId?: string | null;
  title: string;
  content: string;
  tags?: string | null;
}) {
  const response = await api.post<Report>("/api/reports", payload);
  return response.data;
}

export async function getApprovedReports(params?: {
  report_type?: string;
  building_id?: string;
  room_id?: string;
  tmi_location_id?: string;
}) {
  const response = await api.get<Report[]>("/api/reports/approved", { params });
  return response.data;
}

export async function updateTmiStatus(tmiLocationId: string, status: string) {
  const response = await api.patch<TmiLocation>(`/api/tmi/admin/${tmiLocationId}/status`, {
    status,
  });
  return response.data;
}

export async function updateReportStatus(reportId: string, status: string) {
  const response = await api.patch<Report>(`/api/reports/admin/${reportId}/status`, {
    status,
  });
  return response.data;
}
