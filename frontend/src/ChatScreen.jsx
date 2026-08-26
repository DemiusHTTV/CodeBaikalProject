import { useEffect, useRef, useState } from 'react'
import { ask } from './api'
import { AnswerMessage, ErrorMessage, LoadingMessage, UserMessage } from './Message'

// Подсказки под роль — то, что этой роли реально разрешено спросить.
const SUGGESTIONS = {
  applicant: [
    'Сколько бюджетных мест на направлении «Программная инженерия»?',
    'Какой средний балл ЕГЭ у зачисленных в 2025 году?',
    'Какие есть направления подготовки?',
    'Сколько заявлений подали на «Экономику» в 2025 году?',
  ],
  student: [
    'Какие у меня оценки?',
    'Есть ли у меня задолженности?',
    'Сколько студентов на факультете информационных технологий?',
    'Какие дисциплины идут в первом семестре?',
  ],
  teacher: [
    'Сколько студентов в группах по моим дисциплинам?',
    'Какой средний балл по дисциплине «Базы данных»?',
    'Сколько студентов имеют академическую задолженность?',
    'Какая кафедра имеет наибольшую учебную нагрузку?',
  ],
  staff: [
    'Сколько студентов на каждом факультете?',
    'Покажи динамику набора студентов по годам',
    'Какая кафедра имеет наибольшую учебную нагрузку?',
    'Какова средняя заполняемость аудиторий?',
  ],
}

const ROLE_LABELS = {
  applicant: 'Абитуриент',
  student: 'Студент',
  teacher: 'Преподаватель',
  staff: 'Сотрудник',
}

export default function ChatScreen({ session, onLogout }) {
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const abortRef = useRef(null)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, busy])

  async function send(question) {
    const text = question.trim()
    if (!text || busy) return

    setMessages((prev) => [...prev, { kind: 'user', text }])
    setDraft('')
    setBusy(true)

    const controller = new AbortController()
    abortRef.current = controller

    try {
      const result = await ask(text, session.token, controller.signal)
      if (result.error) {
        setMessages((prev) => [
          ...prev,
          {
            kind: 'error',
            title: result.error_kind === 'forbidden' ? 'Запрос отклонён защитой' : 'Не могу ответить',
            text: result.error,
            question: text,
          },
        ])
      } else {
        setMessages((prev) => [...prev, { kind: 'answer', result }])
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        setMessages((prev) => [
          ...prev,
          { kind: 'error', title: 'Запрос остановлен', text: 'Вы прервали генерацию ответа.', question: text },
        ])
      } else {
        setMessages((prev) => [
          ...prev,
          { kind: 'error', title: 'Модель не ответила', text: err.message, question: text },
        ])
      }
    } finally {
      setBusy(false)
      abortRef.current = null
    }
  }

  const suggestions = SUGGESTIONS[session.role] || []
  const isEmpty = messages.length === 0

  return (
    <div className="chat-page">
      <header className="chat-header">
        <span className="chat-title">Ассистент университета</span>
        <div className="chat-header-right">
          <span className="role-badge">{ROLE_LABELS[session.role]}</span>
          {session.allow_raw_pii ? (
            <span className="pii-badge pii-open">ФИО доступны</span>
          ) : (
            <span className="pii-badge">ФИО только агрегатно</span>
          )}
          <button type="button" className="link-button" onClick={onLogout}>
            Сменить роль
          </button>
        </div>
      </header>

      <main className="chat-body">
        <div className="chat-content">
          {isEmpty && (
            <div className="empty-state">
              <h1 className="empty-title">Рады вам, {ROLE_LABELS[session.role].toLowerCase()}</h1>
              <p className="empty-subtitle">
                Спросите про факультеты, нагрузку, успеваемость или приёмную кампанию.
                Отвечу и покажу SQL-запрос, которым получен ответ.
              </p>
              <div className="suggestions">
                {suggestions.map((item) => (
                  <button key={item} type="button" className="suggestion" onClick={() => send(item)}>
                    {item}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((message, index) => {
            if (message.kind === 'user') return <UserMessage key={index} text={message.text} />
            if (message.kind === 'answer') return <AnswerMessage key={index} result={message.result} />
            return (
              <ErrorMessage
                key={index}
                title={message.title}
                text={message.text}
                onRetry={message.question ? () => send(message.question) : undefined}
              />
            )
          })}

          {busy && <LoadingMessage onStop={() => abortRef.current?.abort()} />}
          <div ref={bottomRef} />
        </div>
      </main>

      <footer className="composer">
        <form
          className="composer-inner"
          onSubmit={(event) => {
            event.preventDefault()
            send(draft)
          }}
        >
          <input
            className="composer-input"
            placeholder="Спросите про факультеты, нагрузку или успеваемость…"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            disabled={busy}
          />
          <button type="submit" className="send-button" disabled={busy || !draft.trim()} aria-label="Отправить">
            <span className="send-glyph" />
          </button>
        </form>
      </footer>
    </div>
  )
}
