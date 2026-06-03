import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getIndoorMap, mapAssetUrl, type IndoorMap } from "../api/backend";

function IndoorMapPage() {
  const { buildingId = "", floor = "" } = useParams();
  const [map, setMap] = useState<IndoorMap | null>(null);
  const [error, setError] = useState("");
  const [showGraph, setShowGraph] = useState(true);

  useEffect(() => {
    let ignore = false;
    setError("");
    getIndoorMap(buildingId, floor)
      .then((data) => {
        if (!ignore) setMap(data);
      })
      .catch(() => {
        if (!ignore) setError("실내 지도 데이터를 불러오지 못했습니다.");
      });
    return () => {
      ignore = true;
    };
  }, [buildingId, floor]);

  const nodeById = useMemo(() => {
    return new Map(map?.indoor_nodes.map((node) => [node.indoor_node_id, node]) ?? []);
  }, [map]);

  if (error) {
    return <main className="p-4 text-red-700">{error}</main>;
  }

  if (!map) {
    return <main className="p-4 text-slate-600">지도 로딩 중...</main>;
  }

  return (
    <main className="min-h-screen bg-slate-100 p-4">
      <section className="mx-auto max-w-6xl space-y-4">
        <header className="rounded-2xl bg-white p-4 text-left shadow">
          <Link to="/rooms" className="text-sm font-semibold text-blue-600">
            강의실 검색으로
          </Link>
          <h1 className="mt-2 text-2xl font-bold text-slate-900">
            {map.building_id} {map.floor_label} 실내 지도
          </h1>
          <p className="text-sm text-slate-500">
            강의실 {map.room_positions.length}개, 노드 {map.indoor_nodes.length}개, 간선{" "}
            {map.indoor_edges.length}개
          </p>
          <label className="mt-3 inline-flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={showGraph}
              onChange={(event) => setShowGraph(event.target.checked)}
            />
            실내 그래프 표시
          </label>
        </header>

        <div
          className="relative overflow-hidden rounded-2xl bg-white shadow"
          style={{ aspectRatio: `${map.canvas_width} / ${map.canvas_height}` }}
        >
          <img
            src={mapAssetUrl(map.map_file_url)}
            alt={`${map.building_id} ${map.floor_label}`}
            className="h-full w-full object-contain"
          />

          {map.room_positions.map((position) => (
            <div
              key={position.position_id}
              className="absolute border border-blue-500 bg-blue-500/10"
              title={position.room_id}
              style={{
                left: `${(position.x / map.canvas_width) * 100}%`,
                top: `${(position.y / map.canvas_height) * 100}%`,
                width: `${(position.width / map.canvas_width) * 100}%`,
                height: `${(position.height / map.canvas_height) * 100}%`,
              }}
            />
          ))}

          {showGraph && (
            <svg className="pointer-events-none absolute inset-0 h-full w-full" viewBox={`0 0 ${map.canvas_width} ${map.canvas_height}`}>
              {map.indoor_edges.map((edge) => {
                const from = nodeById.get(edge.from_node_id);
                const to = nodeById.get(edge.to_node_id);
                if (!from || !to) return null;
                return (
                  <line
                    key={edge.indoor_edge_id}
                    x1={from.x}
                    y1={from.y}
                    x2={to.x}
                    y2={to.y}
                    stroke={edge.edge_type === "stair" ? "#ef4444" : edge.edge_type === "elevator" ? "#22c55e" : "#f97316"}
                    strokeWidth={3}
                    strokeLinecap="round"
                    opacity={0.75}
                  />
                );
              })}
              {map.indoor_nodes.map((node) => (
                <circle
                  key={node.indoor_node_id}
                  cx={node.x}
                  cy={node.y}
                  r={5}
                  fill={node.node_type === "elevator" ? "#22c55e" : node.node_type === "stair" ? "#ef4444" : "#0f172a"}
                />
              ))}
            </svg>
          )}
        </div>
      </section>
    </main>
  );
}

export default IndoorMapPage;
