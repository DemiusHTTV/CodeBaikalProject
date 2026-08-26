import { useState } from 'react'
import birdIllustration from './assets/login-bird.svg'

const ROLES = [
  { id: 'applicant', label: 'Абитуриент' },
  { id: 'student', label: 'Студент' },
  { id: 'teacher', label: 'Преподаватель' },
  { id: 'staff', label: 'Сотрудник' },
]

export default function LoginScreen({ onStart, error, busy }) {
  const [role, setRole] = useState('student')
  const [studentId, setStudentId] = useState('1')

  return (
    <div className="login-page">
      <div className="login-card">
        <img className="login-illustration" src={birdIllustration} alt="" />

        <div className="login-form">
          <h1 className="login-title">Здравствуйте!</h1>
          <h2 className="login-subtitle">Кто вы?</h2>
          <p className="login-hint">
            Роль определяет, какие данные и отчёты будут доступны в чате.
          </p>

          <div className="role-list" role="radiogroup" aria-label="Выбор роли">
            {ROLES.map((item) => (
              <button
                key={item.id}
                type="button"
                role="radio"
                aria-checked={role === item.id}
                className={`role-option ${role === item.id ? 'is-selected' : ''}`}
                onClick={() => setRole(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>

          {role === 'student' && (
            <label className="student-id-field">
              Ваш student_id
              <input
                type="number"
                min="1"
                value={studentId}
                onChange={(event) => setStudentId(event.target.value)}
              />
              <span className="student-id-note">
                Определяет, чьи оценки вы увидите. Чужие — запрещены.
              </span>
            </label>
          )}

          {error && <p className="login-error">{error}</p>}

          <button
            type="button"
            className="primary-button login-submit"
            disabled={busy}
            onClick={() => onStart(role, Number(studentId) || 1)}
          >
            {busy ? 'Входим…' : 'Начать'}
          </button>
        </div>
      </div>
    </div>
  )
}
