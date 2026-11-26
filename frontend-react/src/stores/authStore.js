/* ============================================================================
 * PAGE    : STORE: Login & sesi Google
 * FILE    : src/stores/authStore.js
 * ROUTE   : (semua; dipakai LoginPage + AppShell)
 * ORIGIN  : onUserSwitch(), startGoogleLogin(), logoutGoogle() di index.html lama
 * API     : GET /api/auth/me · GET /api/auth/google/login · POST /api/auth/logout
 * STORE   : authStore
 * UPDATE  : paste THIS file only into an AI
 * NOTE    : Alur sama persis: cek sesi -> (redirect Google -> /auth/callback -> kembali ke /) -> sesi cookie.
 * ========================================================================== */
import { create } from 'zustand'
import { ENDPOINTS } from '../config/endpoints'
import { useToastStore } from './toastStore'

export const useAuthStore = create((set, get) => ({
  /* ───── [AUTH-0] STATE ───── */
  status: 'loading', // 'loading' | 'anon' | 'authed'
  user: null,        // { email, name, picture, is_admin, is_owner, gsheets_ready, ... }
  authError: '',
  signingIn: false,

  /* ───── [AUTH-1] loadSession  (lama: onUserSwitch) ───── */
  loadSession: async () => {
    const urlError = new URLSearchParams(window.location.search).get('auth_error')
    if (urlError) {
      let msg = urlError
      try { msg = decodeURIComponent(urlError) } catch { /* pakai apa adanya */ }
      set({ authError: msg })
      window.history.replaceState({}, document.title, '/')
    }
    try {
      const auth = await (await fetch(ENDPOINTS.auth.me)).json()
      if (!auth.authenticated || !auth.user) return set({ status: 'anon', user: null })
      set({ status: 'authed', user: auth.user })
    } catch {
      set({ status: 'anon', user: null })
    }
  },

  /* ───── [AUTH-2] startGoogleLogin  (lama: startGoogleLogin) ───── */
  startGoogleLogin: async () => {
    set({ authError: '', signingIn: true })
    try {
      const res = await fetch(ENDPOINTS.auth.googleLogin)
      const data = await res.json()
      if (!res.ok) return set({ authError: data.detail || 'Gagal memulai login Google.' })
      if (data.mode === 'redirect' && data.auth_url) { window.location.href = data.auth_url; return }
      await get().loadSession()
    } catch {
      set({ authError: 'Gagal terhubung ke server. Pastikan server backend sedang berjalan.' })
    } finally {
      set({ signingIn: false })
    }
  },

  /* ───── [AUTH-3] logout  (lama: logoutGoogle) ───── */
  logout: async () => {
    await fetch(ENDPOINTS.auth.logout, { method: 'POST' })
    set({ status: 'anon', user: null })
    useToastStore.getState().showToast('Berhasil keluar dari sesi akun Google.', 'ok')
  },
}))
