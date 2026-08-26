import { useState } from 'react'
import ChatScreen from './ChatScreen'
import LoginScreen from './LoginScreen'
import { login } from './api'

export default function App() {
  const [session, setSession] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function handleStart(role, username, password) {
    setBusy(true)
    setError(null)
    try {
      setSession(await login(role, username, password))
    } catch (err) {
      setError(`Не удалось войти: ${err.message}. Backend запущен на порту 8000?`)
    } finally {
      setBusy(false)
    }
  }

  if (!session) {
    return <LoginScreen onStart={handleStart} error={error} busy={busy} />
  }
  return <ChatScreen session={session} onLogout={() => setSession(null)} />
}
