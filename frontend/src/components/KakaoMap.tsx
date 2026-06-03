import { useEffect, useRef } from "react";

function KakaoMap() {
  const mapRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const kakaoMapKey = import.meta.env.VITE_KAKAO_MAP_KEY;

    if (!kakaoMapKey) {
      console.error(".env.local에 VITE_KAKAO_MAP_KEY가 없습니다.");
      return;
    }

    const scriptId = "kakao-map-script";

    const drawMap = () => {
      if (!window.kakao || !window.kakao.maps) {
        console.error("window.kakao.maps를 찾을 수 없습니다.");
        return;
      }

      window.kakao.maps.load(() => {
        if (!mapRef.current) return;

        const dkuCenter = new window.kakao.maps.LatLng(37.3216, 127.1268);

        const map = new window.kakao.maps.Map(mapRef.current, {
          center: dkuCenter,
          level: 4,
        });

        const marker = new window.kakao.maps.Marker({
          position: dkuCenter,
        });

        marker.setMap(map);
      });
    };

    const existingScript = document.getElementById(scriptId);

    if (existingScript) {
      drawMap();
      return;
    }

    const script = document.createElement("script");
    script.id = scriptId;
    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${kakaoMapKey}&autoload=false`;
    script.async = true;
    script.onload = drawMap;
    script.onerror = () => {
      console.error("카카오맵 스크립트 로딩에 실패했습니다.");
    };

    document.head.appendChild(script);
  }, []);

  return (
    <div className="h-[500px] w-full overflow-hidden rounded-2xl border border-slate-200 bg-white shadow">
      <div ref={mapRef} className="h-full w-full" />
    </div>
  );
}

export default KakaoMap;