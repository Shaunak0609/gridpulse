import { Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import Navbar from './components/Navbar'
import ProtectedRoute from './components/ProtectedRoute'
import Home from './pages/Home'
import Drivers from './pages/Drivers'
import DriverDetail from './pages/DriverDetail'
import Teams from './pages/Teams'
import Calendar from './pages/Calendar'
import Standings from './pages/Standings'
import Login from './pages/Login'
import Signup from './pages/Signup'
import Profile from './pages/Profile'
import Reminders from './pages/Reminders'
import Notifications from './pages/Notifications'
import Settings from './pages/Settings'
import GoogleCallback from './pages/GoogleCallback'

function App() {
  return (
    <AuthProvider>
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
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/auth/google/callback" element={<GoogleCallback />} />
            <Route
              path="/profile"
              element={
                <ProtectedRoute>
                  <Profile />
                </ProtectedRoute>
              }
            />
            <Route
              path="/reminders"
              element={
                <ProtectedRoute>
                  <Reminders />
                </ProtectedRoute>
              }
            />
            <Route
              path="/notifications"
              element={
                <ProtectedRoute>
                  <Notifications />
                </ProtectedRoute>
              }
            />
            <Route
              path="/settings"
              element={
                <ProtectedRoute>
                  <Settings />
                </ProtectedRoute>
              }
            />
          </Routes>
        </main>
      </div>
    </AuthProvider>
  )
}

export default App
