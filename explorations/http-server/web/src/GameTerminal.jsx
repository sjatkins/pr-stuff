import { useEffect, useRef } from 'react'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'

// OSC number the game uses for out-of-band markers on the web port:
//   ESC ] 9001 ; room=<zone>:<vnum> BEL
// xterm.js hands the handler the text after "9001;" and shows nothing.
const PR_OSC = 9001

export default function GameTerminal({ onRoom }) {
  const hostRef = useRef(null)

  useEffect(() => {
    const term = new Terminal({
      cursorBlink: true,
      convertEol: false,          // game sends \r\n already
      fontFamily: 'monospace',
      scrollback: 5000,
      theme: { background: '#000000' },
    })
    const fit = new FitAddon()
    term.loadAddon(fit)
    term.open(hostRef.current)
    fit.fit()

    term.parser.registerOscHandler(PR_OSC, (data) => {
      const m = /^room=([A-Za-z0-9_-]+):(\d+)$/.exec(data)
      if (m) onRoom({ zone: m[1], vnum: Number(m[2]) })
      return true               // handled; do not display
    })

    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${location.host}/ws`)
    ws.binaryType = 'arraybuffer'
    ws.onopen = () => term.focus()
    ws.onmessage = (ev) => term.write(new Uint8Array(ev.data))
    ws.onclose = () => term.write('\r\n\x1b[31m[connection closed]\x1b[0m\r\n')
    ws.onerror = () => term.write('\r\n\x1b[31m[connection error]\x1b[0m\r\n')

    // Keystrokes go straight to the game; it does its own echo and line
    // editing exactly as it would for telnet.
    const sub = term.onData((d) => {
      if (ws.readyState === WebSocket.OPEN) ws.send(d)
    })

    const onResize = () => fit.fit()
    window.addEventListener('resize', onResize)

    return () => {
      window.removeEventListener('resize', onResize)
      sub.dispose()
      ws.close()
      term.dispose()
    }
  }, [onRoom])

  return <div className="terminal" ref={hostRef} />
}
