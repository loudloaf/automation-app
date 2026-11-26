/* ============================================================================
 * PAGE    : STORE: judul halaman di topbar
 * FILE    : src/stores/uiStore.js
 * ROUTE   : -
 * ORIGIN  : document.getElementById("page-title") di index.html lama
 * API     : -
 * STORE   : -
 * UPDATE  : paste THIS file only into an AI
 * ========================================================================== */
import { create } from 'zustand'

export const useUiStore = create((set) => ({
  pageTitle: 'Overview',
  setPageTitle: (pageTitle) => set({ pageTitle }),
}))
