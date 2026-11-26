/* ============================================================================
 * PAGE    : STORE: Toast global
 * FILE    : src/stores/toastStore.js
 * ROUTE   : -
 * ORIGIN  : showToast() di index.html lama
 * API     : -
 * STORE   : -
 * UPDATE  : paste THIS file only into an AI
 * NOTE    : Toast baru mengganti toast lama dan timer lama dibatalkan (di versi lama timer lama bisa menutup toast baru lebih cepat).
 * ========================================================================== */
import { create } from 'zustand'

let timer = null

export const useToastStore = create((set) => ({
  toast: null, // { msg, kind: 'ok' | 'warn' | 'error' }
  /** [TOAST-1] showToast(msg, kind)  (sama seperti showToast lama, tampil 5,5 detik) */
  showToast: (msg, kind = 'ok') => {
    clearTimeout(timer)
    set({ toast: { msg, kind } })
    timer = setTimeout(() => set({ toast: null }), 5500)
  },
}))
