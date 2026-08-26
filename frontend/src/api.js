// Единственное место, которое знает про адрес бэкенда.
const BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

async function request(path, { method = 'POST', body, token, signal } = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
    signal,
  })

  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(payload.detail || `Ошибка ${response.status}`)
  }
  return payload
}

// Роль уходит на сервер один раз — в обмен на подписанный токен. Дальше клиент
// роль не передаёт: она внутри токена, подменить её на "staff" не получится.
export function login(role, studentId) {
  return request('/api/login', {
    body: { role, student_id: role === 'student' ? studentId : null },
  })
}

export function ask(question, token, signal) {
  return request('/api/ask', { body: { question }, token, signal })
}

// Доступно только роли staff — на сервере стоит проверка, здесь просто запрос.
export function fetchAnalytics(token) {
  return request('/api/analytics', { method: 'GET', token })
}
