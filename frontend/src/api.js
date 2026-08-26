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

// Логин/пароль уходят на сервер один раз — в обмен на подписанный токен.
// Роль сервер сверяет с той, что записана у пользователя в БД, и в токен
// кладёт именно её — прислать "staff" и получить чужие права не выйдет.
export function login(role, username, password) {
  return request('/api/login', {
    body: { role, username, password },
  })
}

export function ask(question, token, signal) {
  return request('/api/ask', { body: { question }, token, signal })
}

// Доступно только роли staff — на сервере стоит проверка, здесь просто запрос.
export function fetchAnalytics(token) {
  return request('/api/analytics', { method: 'GET', token })
}
