/* ============================================================================
 * PAGE    : STORE: Cache Global untuk Overview, Master Data, dan Izin Akses
 * FILE    : src/stores/appDataStore.js
 * ROUTE   : / · /master · /access
 * ORIGIN  : loadOverview(), loadMasterData(), loadUsers() di index.html lama
 * API     : GET /api/overview · GET /api/master/:entity · GET /api/users
 * STORE   : appDataStore
 * ========================================================================== */
import { create } from 'zustand'
import { apiFetch } from '../api/http'
import { ENDPOINTS } from '../config/endpoints'

export const useAppDataStore = create((set, get) => ({
  /* ───── [CACHE-1] OVERVIEW STATE ───── */
  overview: {
    output_count: 0,
    output_files: [],
    master_counts: {},
    loaded: false,
  },
  loadOverview: async () => {
    try {
      const res = await fetch(ENDPOINTS.overview)
      if (res.ok) {
        const d = await res.json()
        set({ overview: { ...d, loaded: true } })
      }
    } catch {
      /* ignore network error */
    }
  },

  /* ───── [CACHE-2] MASTER DATA STATE (Per Entity Cache) ───── */
  currentEntity: 'supplier_rekap',
  masterSchemas: {}, // { supplier_rekap: { title, pk, fields, rows, counts }, ... }
  masterCounts: {},
  setCurrentEntity: (ent) => set({ currentEntity: ent }),

  loadMasterData: async (ent) => {
    const target = ent || get().currentEntity
    try {
      const res = await apiFetch(ENDPOINTS.master.get(target))
      if (!res.ok) return
      const data = await res.json()
      set((s) => ({
        masterSchemas: { ...s.masterSchemas, [target]: data },
        masterCounts: data.counts || s.masterCounts,
      }))
    } catch {
      /* ignore network error */
    }
  },

  /* ───── [CACHE-3] ACCESS / USERS STATE ───── */
  users: [],
  usersLoaded: false,
  loadUsers: async () => {
    try {
      const res = await apiFetch(ENDPOINTS.users)
      if (!res.ok) return
      const data = await res.json()
      set({ users: data.users || [], usersLoaded: true })
    } catch {
      /* ignore network error */
    }
  },
}))