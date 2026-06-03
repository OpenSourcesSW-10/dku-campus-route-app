import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Splash from './pages/Splash'
import Landing from './pages/Landing'
import SignUp from './pages/SignUp'
import Login from './pages/Login'
import MapHome from './pages/MapHome'
import RouteFind from './pages/RouteFind'
import PlaceSearch from './pages/PlaceSearch'
import IndoorMapPage from './pages/IndoorMapPage'
import Tmi from './pages/Tmi'
import Report from './pages/Report'

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <Routes>
          <Route path="/" element={<Splash />} />
          <Route path="/landing" element={<Landing />} />
          <Route path="/signup" element={<SignUp />} />
          <Route path="/login" element={<Login />} />
          <Route path="/home" element={<MapHome />} />
          <Route path="/route" element={<RouteFind />} />
          <Route path="/search" element={<PlaceSearch />} />
          <Route path="/indoor" element={<IndoorMapPage />} />
          <Route path="/indoor/:buildingId/:floor" element={<IndoorMapPage />} />
          <Route path="/tmi" element={<Tmi />} />
          <Route path="/report" element={<Report />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
