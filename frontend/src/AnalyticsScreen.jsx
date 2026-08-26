import { useEffect, useState } from 'react'
import { fetchAnalytics } from './api'

const ROLE_LABELS = {
  applicant: 'Абитуриент',
  student: 'Студент',
  teacher: 'Преподаватель',
  staff: 'Сотрудник',
}

const OUTCOME_LABELS = {
  ok: 'Успешно',
  forbidden: 'Отклонено защитой',
  refused: 'Не по теме',
  db_error: 'Ошибка базы',
}

function StatCard({ label, value, hint }) {
  return (
    <div className="stat-card">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
      {hint && <div className="stat-hint">{hint}</div>}
    </div>
  )
}

function Distribution({ title, data, labels }) {
  const total = Object.values(data).reduce((sum, n) => sum + n, 0)
  if (!total) return null

  return (
    <section className="panel">
      <h2 className="panel-title">{title}</h2>
      <div className="bars">
        {Object.entries(data).map(([key, count]) => (
          <div key={key} className="bar-row">
            <span className="bar-label">{labels?.[key] || key}</span>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${(count / total) * 100}%` }} />
            </div>
            <span className="bar-value">
              {count} <span className="bar-share">({Math.round((count / total) * 100)}%)</span>
            </span>
          </div>
        ))}
      </div>
    </section>
  )
}

function QuestionList({ title, items, note, emptyText }) {
  return (
    <section className="panel">
      <h2 className="panel-title">{title}</h2>
      {note && <p className="panel-note">{note}</p>}
      {items.length === 0 ? (
        <p className="panel-empty">{emptyText}</p>
      ) : (
        <ul className="question-list">
          {items.map((item, index) => (
            <li key={index}>
              <span className="question-role">{ROLE_LABELS[item.role] || item.role}</span>
              <span className="question-text">{item.question}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export default function AnalyticsScreen({ session, onBack }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    fetchAnalytics(session.token)
      .then((result) => !cancelled && setData(result))
      .catch((err) => !cancelled && setError(err.message))
    return () => {
      cancelled = true
    }
  }, [session.token])

  if (error) {
    return (
      <div className="analytics-page">
        <header className="chat-header">
          <span className="chat-title">Аналитика обращений</span>
          <button type="button" className="link-button" onClick={onBack}>
            Вернуться в чат
          </button>
        </header>
        <main className="analytics-body">
          <div className="error-card">
            <div className="error-title">
              <span className="error-marker" aria-hidden="true" />
              Не удалось загрузить аналитику
            </div>
            <p className="error-text">{error}</p>
          </div>
        </main>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="analytics-page">
        <header className="chat-header">
          <span className="chat-title">Аналитика обращений</span>
          <button type="button" className="link-button" onClick={onBack}>
            Вернуться в чат
          </button>
        </header>
        <main className="analytics-body">
          <div className="skeleton" style={{ width: '60%' }} />
          <div className="skeleton" style={{ width: '85%' }} />
          <div className="skeleton" style={{ width: '40%' }} />
        </main>
      </div>
    )
  }

  const okCount = data.by_outcome.ok || 0
  const successShare = data.total ? Math.round((okCount / data.total) * 100) : 0

  return (
    <div className="analytics-page">
      <header className="chat-header">
        <span className="chat-title">Аналитика обращений</span>
        <div className="chat-header-right">
          <span className="role-badge">Сотрудник</span>
          <button type="button" className="link-button" onClick={onBack}>
            Вернуться в чат
          </button>
        </div>
      </header>

      <main className="analytics-body">
        {data.total === 0 ? (
          <div className="empty-state">
            <h1 className="empty-title">Обращений пока нет</h1>
            <p className="empty-subtitle">
              Статистика появится, как только пользователи начнут задавать вопросы.
            </p>
          </div>
        ) : (
          <div className="analytics-content">
            <div className="stat-row">
              <StatCard label="Всего обращений" value={data.total} />
              <StatCard label="Успешных" value={`${successShare}%`} hint={`${okCount} из ${data.total}`} />
              <StatCard
                label="Медиана ответа"
                value={`${(data.timing.median_ms / 1000).toFixed(1)} с`}
                hint={`95-й процентиль — ${(data.timing.p95_ms / 1000).toFixed(1)} с`}
              />
              <StatCard label="Отклонено защитой" value={data.by_outcome.forbidden || 0} />
            </div>

            <div className="panel-grid">
              <Distribution title="Кто спрашивает" data={data.by_role} labels={ROLE_LABELS} />
              <Distribution title="Чем закончилось" data={data.by_outcome} labels={OUTCOME_LABELS} />
            </div>

            <div className="panel-grid">
              <QuestionList
                title="Отработали, но вернули пусто"
                note="Формально успех, но пользователю не помогли — чинить в первую очередь."
                items={data.empty_results}
                emptyText="Таких обращений нет."
              />
              <QuestionList
                title="Отклонено"
                note="Сработала защита персональных данных или вопрос был не по теме."
                items={data.blocked}
                emptyText="Отклонённых обращений нет."
              />
            </div>

            {data.top_questions.length > 0 && (
              <section className="panel">
                <h2 className="panel-title">Самые частые вопросы</h2>
                <ul className="question-list">
                  {data.top_questions.map((item, index) => (
                    <li key={index}>
                      <span className="question-count">{item.count}×</span>
                      <span className="question-text">{item.question}</span>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            <section className="panel">
              <h2 className="panel-title">Последние обращения</h2>
              <p className="panel-note">
                Показаны роль и вопрос. Идентификаторы пользователей не выводятся.
              </p>
              <div className="result-table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>Время</th>
                      <th>Роль</th>
                      <th>Вопрос</th>
                      <th>Итог</th>
                      <th>Строк</th>
                      <th>мс</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.recent.map((item, index) => (
                      <tr key={index}>
                        <td className="cell-muted">{item.time?.slice(11) || '—'}</td>
                        <td>{ROLE_LABELS[item.role] || item.role}</td>
                        <td className="cell-question" title={item.sql || ''}>
                          {item.question}
                        </td>
                        <td>{OUTCOME_LABELS[item.outcome] || item.outcome}</td>
                        <td>{item.row_count}</td>
                        <td className="cell-muted">{item.elapsed_ms}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        )}
      </main>
    </div>
  )
}
