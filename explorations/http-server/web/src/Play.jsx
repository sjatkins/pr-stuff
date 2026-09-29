import { useState } from 'react'
import GameTerminal from './GameTerminal.jsx'
import RoomPicture from './RoomPicture.jsx'

// The game page: picture widget above, terminal widget below. The only
// link between them is the room the terminal reports from the game's
// OSC marker; the picture widget fetches its image from the API.
export default function Play() {
  const [room, setRoom] = useState(null)   // { zone, vnum } or null
  return (
    <main className="play">
      <RoomPicture room={room} />
      <GameTerminal onRoom={setRoom} />
    </main>
  )
}
