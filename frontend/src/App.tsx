import KakaoMap from "./components/KakaoMap";

function App() {
  return (
    <main className="min-h-screen bg-slate-100 p-4">
      <section className="mx-auto max-w-md space-y-4">
        <div className="rounded-2xl bg-white p-4 shadow">
          <h1 className="text-2xl font-bold text-slate-900">DKU MAP</h1>
          <p className="mt-1 text-sm text-slate-500">
            단국대 죽전캠퍼스 길찾기 앱
          </p>
        </div>

        <KakaoMap />
      </section>
    </main>
  );
}

export default App;