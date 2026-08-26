import { useState } from 'react'
import avatar from './assets/avatar.svg'
import ResultTable from './ResultTable'

function AssistantHeader({ meta }) {
  return (
    <div className="assistant-header">
      <img className="assistant-avatar" src={avatar} alt="" />
      <span className="assistant-name">Ассистент</span>
      {meta && <span className="assistant-meta">{meta}</span>}
    </div>
  )
}

export function UserMessage({ text }) {
  return (
    <div className="row row-user">
      <div className="bubble-user">{text}</div>
    </div>
  )
}

export function LoadingMessage({ onStop }) {
  return (
    <div className="row">
      <AssistantHeader meta="готовлю ответ — перевожу вопрос в SQL" />
      <div className="assistant-body">
        <div className="skeleton" style={{ width: '96%' }} />
        <div className="skeleton" style={{ width: '68%' }} />
        <div className="skeleton" style={{ width: '42%' }} />
        <button type="button" className="secondary-button" onClick={onStop}>
          Остановить
        </button>
      </div>
    </div>
  )
}

export function ErrorMessage({ title, text, onRetry }) {
  return (
    <div className="row">
      <AssistantHeader />
      <div className="assistant-body">
        <div className="error-card">
          <div className="error-title">
            <span className="error-marker" aria-hidden="true" />
            {title}
          </div>
          <p className="error-text">{text}</p>
          {onRetry && (
            <button type="button" className="primary-button error-retry" onClick={onRetry}>
              Повторить
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export function AnswerMessage({ result }) {
  const [sqlOpen, setSqlOpen] = useState(false)
  const { sql, columns, rows, row_count: rowCount, answer, elapsed_ms: elapsedMs } = result

  // answer — пересказ от модели. Если она не ответила, показываем таблицу
  // с короткой служебной подписью, а не пустое место.
  const summary =
    answer ||
    (rowCount === 0
      ? 'Запрос отработал, но подходящих записей в базе не нашлось.'
      : `Нашёл записей: ${rowCount}.`)

  return (
    <div className="row">
      <AssistantHeader meta={`SQL выполнен за ${elapsedMs} мс`} />
      <div className="assistant-body">
        <p className="answer-text">{summary}</p>

        <ResultTable columns={columns} rows={rows} />

        <div className="sources">
          <button
            type="button"
            className="sql-toggle"
            onClick={() => setSqlOpen((open) => !open)}
            aria-expanded={sqlOpen}
          >
            {sqlOpen ? 'Скрыть SQL-запрос' : 'Показать SQL-запрос'}
          </button>
          {sqlOpen && <pre className="sql-block">{sql}</pre>}
        </div>
      </div>
    </div>
  )
}
