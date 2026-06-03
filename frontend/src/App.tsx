import { BrowserRouter, Route, Routes } from "react-router-dom";
import IndoorMapPage from "./pages/IndoorMapPage";
import MainMapPage from "./pages/MainMapPage";
import RoomSearchPage from "./pages/RoomSearchPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainMapPage />} />
        <Route path="/rooms" element={<RoomSearchPage />} />
        <Route path="/indoor/:buildingId/:floor" element={<IndoorMapPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
