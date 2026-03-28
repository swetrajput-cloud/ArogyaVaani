import { useEffect, useRef, useState } from 'react'

export default function useWebSocket() {
  const [messages, setMessages] = useState([])
  const [connected, setConnected] = useState(false)
  const ws = useRef(null)
  const pingRef = useRef(null)

  useEffect(() => {
    const connect = () => {
      ws.current = new WebSocket('ws://localhost:8000/ws/dashboard')

      ws.current.onopen = () => {
        setConnected(true)
        console.log('[WS] Connected')
        pingRef.current = setInterval(() => {
          if (ws.current?.readyState === WebSocket.OPEN) ws.current.send('ping')
        }, 20000)
      }

      ws.current.onmessage = (event) => {
        if (event.data === 'pong') return
        try {
          const data = JSON.parse(event.data)
          setMessages((prev) => [data, ...prev].slice(0, 50))
        } catch (e) { console.error('[WS] Parse error', e) }
      }

      ws.current.onclose = () => {
        setConnected(false)
        clearInterval(pingRef.current)
        setTimeout(connect, 3000)
      }

      ws.current.onerror = (err) => {
        console.error('[WS] Error', err)
        ws.current.close()
      }
    }

    connect()
    return () => { clearInterval(pingRef.current); ws.current?.close() }
  }, [])

  return { messages, connected }
}