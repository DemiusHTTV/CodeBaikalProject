import { useState } from 'react'
import AnalyticsScreen from './AnalyticsScreen'
import ChatScreen from './ChatScreen'
import LoginScreen from './LoginScreen'
import { login } from './api'

export default function App() {
  const [session, setSession] = useState(null)
  const [screen, setScreen] = useState('chat')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function handleStart(role, studentId) {
    setBusy(true)
    setError(null)
    try {
      setSession(await login(role, studentId))
      setScreen('chat')
    } catch (err) {
      setError(`Не удалось войти: ${err.message}. Backend запущен на порту 8000?`)
    } finally {
      setBusy(false)
    }
  }

  if (!session) {
    return <LoginScreen onStart={handleStart} error={error} busy={busy} />
  }

  if (screen === 'analytics') {
    return <AnalyticsScreen session={session} onBack={() => setScreen('chat')} />
  }

  return (
    <ChatScreen
      session={session}
      onLogout={() => setSession(null)}
      onOpenAnalytics={() => setScreen('analytics')}
    />
  )
}
