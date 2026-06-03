import { Link } from "react-router-dom";
import KakaoMap from "../components/KakaoMap";

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

        <KakaoMap />
      </section>
    </main>
  );
}

export default MainMapPage;
