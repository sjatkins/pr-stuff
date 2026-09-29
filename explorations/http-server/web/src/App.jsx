import { Routes, Route, Link } from 'react-router-dom'
import Landing from './Landing.jsx'
import Play from './Play.jsx'

// Two pages. Caddy's try_files fallback means /play works on reload.
export default function App() {
  return (
    <>
      <nav className="nav">
        <Link to="/">Perilous Realms</Link>
        <Link to="/play">Play</Link>
      </nav>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/play" element={<Play />} />
      </Routes>
    </>
  )
}
