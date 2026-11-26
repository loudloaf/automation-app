/* ============================================================================
 * PAGE    : API helper
 * FILE    : src/api/http.js
 * ROUTE   : -
 * ORIGIN  : getHeader() di index.html lama
 * API     : -
 * STORE   : authStore
 * UPDATE  : paste THIS file only into an AI
 * ========================================================================== */
import { useAuthStore } from '../stores/authStore'

/** [HTTP-1] Header yang dikirim ke backend (sama seperti getHeader() lama) */
export function authHeader() {
  return { 'x-user-email': useAuthStore.getState().user?.email || '' }
}

/** [HTTP-2] fetch + header otomatis */
export function apiFetch(url, options = {}) {
  return fetch(url, { ...options, headers: { ...authHeader(), ...(options.headers || {}) } })
}
