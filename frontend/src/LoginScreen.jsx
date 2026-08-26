import { useState } from 'react'
import birdIllustration from './assets/login-bird.svg'

// Абитуриент входит без аккаунта: он ещё не в университете, а доступны ему
// только справочные данные о наборе.
const ROLES = [
  { id: 'applicant', label: 'Абитуриент', note: 'без входа в аккаунт' },
  { id: 'student', label: 'Студент' },
  { id: 'teacher', label: 'Преподаватель' },
  { id: 'staff', label: 'Сотрудник' },
]

export default function LoginScreen({ onStart, error, busy }) {
  const [role, setRole] = useState(null)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  function handleRoleClick(id) {
    if (id === 'applicant') {
      onStart(id)
      return
    }
    setRole(id)
  }

  function handleSubmit(event) {
    event.preventDefault()
    if (!username || !password) return
    onStart(role, username, password)
  }

  const roleLabel = ROLES.find((item) => item.id === role)?.label

  return (
    <div className="login-page">
      <div className="login-card">
        <img className="login-illustration" src={birdIllustration} alt="" />

        {role === null ? (
          <div className="login-form">
            <h1 className="login-title">Здравствуйте!</h1>
            <h2 className="login-subtitle">Кто вы?</h2>
            <p className="login-hint">
              Роль определяет, какие данные и отчёты будут доступны в чате.
            </p>

            <div className="role-list" role="group" aria-label="Выбор роли">
              {ROLES.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className="role-option"
                  disabled={busy}
                  onClick={() => handleRoleClick(item.id)}
                >
                  {item.label}
                  {item.note && <span className="role-note">{item.note}</span>}
                </button>
              ))}
            </div>

            {error && <p className="login-error">{error}</p>}
          </div>
        ) : (
          <form className="login-form" onSubmit={handleSubmit}>
            <h1 className="login-title">{roleLabel}</h1>
            <h2 className="login-subtitle">Войдите в свой аккаунт</h2>
            <p className="login-hint">
              Введите логин и пароль, выданные университетом.
            </p>

            <label className="login-field">
              Логин
              <input
                type="text"
                autoComplete="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
              />
            </label>

            <label className="login-field">
              Пароль
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>

            {error && <p className="login-error">{error}</p>}

            <button
              type="submit"
              className="primary-button login-submit"
              disabled={busy || !username || !password}
            >
              {busy ? 'Входим…' : 'Войти'}
            </button>

            <button
              type="button"
              className="login-back"
              disabled={busy}
              onClick={() => setRole(null)}
            >
              ← Выбрать другую роль
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
