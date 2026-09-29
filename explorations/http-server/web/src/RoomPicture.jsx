import { useEffect, useState } from 'react'

// Shows the room picture if there is one, else the zone picture, else
// nothing. Both come from the API; a 404 just means "no picture yet".
export default function RoomPicture({ room }) {
  const [src, setSrc] = useState(null)

  useEffect(() => {
    if (!room) { setSrc(null); return }
    let cancelled = false
    const tryUrl = async (url) => {
      const r = await fetch(url, { method: 'HEAD' })
      return r.ok ? url : null
    }
    ;(async () => {
      const url =
        (await tryUrl(`/api/room-image/${room.vnum}`)) ||
        (await tryUrl(`/api/zone-image/${room.zone}`))
      if (!cancelled) setSrc(url)
    })()
    return () => { cancelled = true }
  }, [room?.zone, room?.vnum])

  if (!src) return <div className="picture empty" />
  return (
    <div className="picture">
      <img src={src} alt={room ? `${room.zone} ${room.vnum}` : ''} />
    </div>
  )
}
