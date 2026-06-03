import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { mapAssetUrl, searchRoom, type RoomSearchResult } from "../api/backend";

function RoomSearchPage() {
  const [keyword, setKeyword] = useState("소프트305");
  const [result, setResult] = useState<RoomSearchResult | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const data = await searchRoom(keyword);
      setResult(data);
    } catch {
      setResult(null);
      setError("강의실을 찾지 못했습니다. 검색어와 백엔드 실행 상태를 확인해 주세요.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-100 p-4">
      <section className="mx-auto max-w-4xl space-y-4">
        <div className="rounded-2xl bg-white p-4 shadow">
          <Link to="/" className="text-sm font-semibold text-blue-600">
            메인으로
          </Link>
          <h1 className="mt-2 text-2xl font-bold text-slate-900">강의실 검색</h1>
          <p className="mt-1 text-sm text-slate-500">
            예: 소프트305, ICT401, 도서관301
          </p>
        </div>

        <form onSubmit={handleSubmit} className="flex gap-2 rounded-2xl bg-white p-4 shadow">
          <input
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            className="min-w-0 flex-1 rounded-xl border border-slate-300 px-4 py-3 text-slate-900"
            placeholder="강의실 검색어"
          />
          <button
            type="submit"
            disabled={loading}
            className="rounded-xl bg-blue-600 px-5 py-3 font-semibold text-white disabled:opacity-50"
          >
            {loading ? "검색 중" : "검색"}
          </button>
        </form>

        {error && <div className="rounded-xl bg-red-50 p-4 text-red-700">{error}</div>}

        {result && (
          <section className="grid gap-4 lg:grid-cols-[320px_1fr]">
            <article className="rounded-2xl bg-white p-4 text-left shadow">
              <h2 className="text-xl font-bold text-slate-900">
                {result.buildingName} {result.roomNumber}호
              </h2>
              <dl className="mt-3 space-y-2 text-sm text-slate-600">
                <div>건물 ID: {result.buildingId}</div>
                <div>층: {result.floorLabel}</div>
                <div>roomId: {result.roomId}</div>
                <div>nearest node: {result.nearestIndoorNodeId ?? "미연결"}</div>
              </dl>
              <Link
                to={`/indoor/${result.buildingId}/${result.floorNumber}`}
                className="mt-4 block rounded-xl bg-slate-900 px-4 py-3 text-center font-semibold text-white"
              >
                층별 지도 보기
              </Link>
            </article>

            <div
              className="relative overflow-hidden rounded-2xl bg-white shadow"
              style={{
                aspectRatio: `${result.indoorMap.canvasWidth} / ${result.indoorMap.canvasHeight}`,
              }}
            >
              <img
                src={mapAssetUrl(result.indoorMap.mapFileUrl)}
                alt="실내 지도"
                className="h-full w-full object-contain"
              />
              {result.position && (
                <div
                  className="absolute border-4 border-red-500 bg-red-500/20"
                  style={{
                    left: `${(result.position.x / result.indoorMap.canvasWidth) * 100}%`,
                    top: `${(result.position.y / result.indoorMap.canvasHeight) * 100}%`,
                    width: `${(result.position.width / result.indoorMap.canvasWidth) * 100}%`,
                    height: `${(result.position.height / result.indoorMap.canvasHeight) * 100}%`,
                  }}
                />
              )}
            </div>
          </section>
        )}
      </section>
    </main>
  );
}

export default RoomSearchPage;
