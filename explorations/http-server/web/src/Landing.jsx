import { Link } from 'react-router-dom'

// Placeholder landing page; decorate freely. Anything dynamic (who is
// online, news, motd) comes from /api/* routes added to api_server.py.
export default function Landing() {
  return (
    <main className="landing">
      <h1>Perilous Realms</h1>
      <p>A text world, running since the 1990s.</p>
      <p>
        <Link to="/play" className="button">Enter the realms</Link>
      </p>
      <p className="small">
        Or telnet to perilousrealms.com port 2150.
      </p>
    </main>
  )
}
