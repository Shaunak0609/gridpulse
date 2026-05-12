import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Home from './pages/Home'
import Drivers from './pages/Drivers'
import DriverDetail from './pages/DriverDetail'
import Teams from './pages/Teams'
import Calendar from './pages/Calendar'
import Standings from './pages/Standings'

function App() {
  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <Navbar />
      <main className="max-w-6xl mx-auto px-4 py-8">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/drivers" element={<Drivers />} />
          <Route path="/drivers/:id" element={<DriverDetail />} />
          <Route path="/teams" element={<Teams />} />
          <Route path="/calendar" element={<Calendar />} />
          <Route path="/standings" element={<Standings />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
