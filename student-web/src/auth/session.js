const TOKEN_KEY = 'student_access_token'
const USER_KEY = 'student_current_user'

export const getToken = () => sessionStorage.getItem(TOKEN_KEY)

export function getCurrentUser() {
  const value = sessionStorage.getItem(USER_KEY)
  try { return value ? JSON.parse(value) : null } catch { return null }
}

export function saveSession(accessToken, user) {
  sessionStorage.setItem(TOKEN_KEY, accessToken)
  sessionStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function clearSession() {
  sessionStorage.removeItem(TOKEN_KEY)
  sessionStorage.removeItem(USER_KEY)
}

export const isAuthenticated = () => Boolean(getToken())
