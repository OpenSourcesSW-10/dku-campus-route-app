import { Link } from "react-router-dom";

function MainMapPage() {
  return (
    <main className="min-h-screen bg-slate-100">
      <header className="p-4 bg-white shadow-sm">
        <h1 className="text-xl font-bold">단국맵 DKU MAP</h1>
      </header>

      <section className="p-4 space-y-3">
        <Link
          to="/rooms"
          className="block rounded-xl bg-blue-600 px-4 py-3 text-white text-center font-semibold"
        >
          강의실 검색하기
        </Link>

        <div className="h-[500px] rounded-2xl bg-white shadow flex items-center justify-center text-slate-500">
          Kakao Map 영역
        </div>
      </section>
    </main>
  );
}

export default MainMapPage;