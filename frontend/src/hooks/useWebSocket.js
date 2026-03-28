import { useEffect, useRef, useState } from 'react'

export default function useWebSocket() {
  const [messages, setMessages] = useState([])
  const [connected, setConnected] = useState(false)
  const ws = useRef(null)
  const pingRef = useRef(null)
  const reconnectRef = useRef(null)

  useEffect(() => {
    const connect = () => {
      if (ws.current?.readyState === WebSocket.OPEN) return

      const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'
      ws.current = new WebSocket(`${WS_URL}/ws/dashboard`)

      ws.current.onopen = () => {
        setConnected(true)
        console.log('[WS] Connected')
        clearInterval(pingRef.current)
        // Ping every 10s to keep connection alive through Vercel/Railway proxies
        pingRef.current = setInterval(() => {
          if (ws.current?.readyState === WebSocket.OPEN) {
            ws.current.send('ping')
          }
        }, 10000)
      }

      ws.current.onmessage = (event) => {
        if (event.data === 'pong') return
        try {
          const data = JSON.parse(event.data)
          console.log('[WS] Message received:', data)
          setMessages((prev) => [data, ...prev].slice(0, 50))
        } catch (e) {
          console.error('[WS] Parse error', e)
        }
      }

      ws.current.onclose = () => {
        setConnected(false)
        clearInterval(pingRef.current)
        console.log('[WS] Disconnected, reconnecting in 2s...')
        reconnectRef.current = setTimeout(connect, 2000)
      }

      ws.current.onerror = () => {
        ws.current?.close()
      }
    }

    connect()

    return () => {
      clearInterval(pingRef.current)
      clearTimeout(reconnectRef.current)
      ws.current?.close()
    }
  }, [])

  return { messages, connected }
}