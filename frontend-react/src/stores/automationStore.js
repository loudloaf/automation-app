/* ============================================================================
 * PAGE    : STORE: Antrean Upload, Parameter & Hasil Automation Scripts
 * FILE    : src/stores/automationStore.js
 * ROUTE   : /automation/rangkuman · /automation/doi
 * ORIGIN  : automationQueue, automationUpload(), runRangkumanPenjualan(),
 *           runRangkumanGSheets(), runDoiPipeline() di index.html lama
 * API     : POST /api/automate/rangkuman-penjualan · /rangkuman-gsheets · /doi-cabang
 * STORE   : automationStore
 * UPDATE  : paste THIS file only into an AI
 * ========================================================================== */
import { create } from 'zustand'
import { authHeader, apiFetch } from '../api/http'
import { ENDPOINTS } from '../config/endpoints'
import { useToastStore } from './toastStore'

const AUTO_VALID = /\.(xlsx|xls|xlsm|csv)$/i

export const useAutomationStore = create((set, get) => ({
  /* ───── [AUTO-1] STATE ───── */
  queues: { rkMain: [], rkBl: [], rkTl: [], doi: [] },
  busy: { rk: false, doi: false, gs: false },
  status: {
    rk: { visible: false, msg: 'Menyiapkan upload file...', determinate: false, percent: 0 },
    doi: { visible: false, msg: 'Menyiapkan upload file...', determinate: false, percent: 0 },
  },
  errors: { rk: '', doi: '' },

  // Rangkuman Options & Output State
  rkUseMasterSupplier: false,
  rkPaksaSummary: false,
  rkResult: null,   // { message, supplier_source, zip_files, per_file_reports, logs }
  rkGsResult: null, // { summary_excel_name, logs }

  // DOI Options & Output State
  doiUseMasterDaftar: false,
  doiParams: {
    cabang: '',
    hari_kerja: '26',
    standar_doi_default: '30',
    ambang_ams_min: '0',
    bulan_stok_masuk_ams: 'auto',
    maks_bulan_ams: '0',
  },
  doiResult: null,  // { out_name, cabang, ams_months, sku_count, oms_mode, peringatan, summary_rows, logs }

  /* ───── [AUTO-2] QUEUE & PARAMETER ACTIONS ───── */
  setRkUseMasterSupplier: (val) => set({ rkUseMasterSupplier: val }),
  setRkPaksaSummary: (val) => set({ rkPaksaSummary: val }),
  setDoiUseMasterDaftar: (val) => set({ doiUseMasterDaftar: val }),
  setDoiParam: (key, val) => set((s) => ({ doiParams: { ...s.doiParams, [key]: val } })),

  autoAddFiles: (slot, fileList) => {
    const s = get()
    if (s.busy.rk || s.busy.doi) return
    const rejected = []
    const nextQueue = [...s.queues[slot]]
    for (const file of fileList || []) {
      if (!AUTO_VALID.test(file.name)) {
        rejected.push(file.name)
        continue
      }
      const exists = nextQueue.some(
        (f) => f.name === file.name && f.size === file.size && f.lastModified === file.lastModified
      )
      if (!exists) nextQueue.push(file)
    }
    set({ queues: { ...s.queues, [slot]: nextQueue } })
    if (rejected.length) {
      useToastStore.getState().showToast(`Format file tidak sesuai: ${rejected.join(', ')}`, 'warn')
    }
  },

  autoRemove: (slot, index) => {
    const s = get()
    if (s.busy.rk || s.busy.doi) return
    const nextQueue = [...s.queues[slot]]
    nextQueue.splice(index, 1)
    set({ queues: { ...s.queues, [slot]: nextQueue } })
  },

  autoClear: (slot) => {
    const s = get()
    if (s.busy.rk || s.busy.doi) return
    set({ queues: { ...s.queues, [slot]: [] } })
  },

  resetRkWorkspace: () => {
    const s = get()
    if (s.busy.rk || s.busy.doi) return
    set({
      queues: { ...s.queues, rkMain: [], rkBl: [], rkTl: [] },
      rkResult: null,
      rkGsResult: null,
      errors: { ...s.errors, rk: '' },
    })
  },

  resetDoiWorkspace: () => {
    const s = get()
    if (s.busy.rk || s.busy.doi) return
    set({
      queues: { ...s.queues, doi: [] },
      doiResult: null,
      errors: { ...s.errors, doi: '' },
    })
  },

  /* ───── [AUTO-3] XHR UPLOAD WITH PROGRESS & TIMER (lama: automationUpload) ───── */
  automationUpload: (url, formData, ws, count) => {
    return new Promise((resolve) => {
      let timer = null
      const stop = () => {
        if (timer) {
          clearInterval(timer)
          timer = null
        }
      }
      const fail = (detail) => {
        stop()
        resolve({ ok: false, data: { detail } })
      }
      const xhr = new XMLHttpRequest()
      xhr.open('POST', url)
      for (const [name, value] of Object.entries(authHeader())) {
        xhr.setRequestHeader(name, value)
      }
      xhr.upload.addEventListener('progress', (event) => {
        if (!event.lengthComputable || event.total <= 0) return
        const percent = Math.min(100, Math.round((event.loaded / event.total) * 100))
        set((s) => ({
          status: {
            ...s.status,
            [ws]: {
              visible: true,
              determinate: true,
              percent,
              msg: `Mengunggah ${count} file ke server: ${percent}%`,
            },
          },
        }))
      })
      xhr.upload.addEventListener('load', () => {
        const t0 = Date.now()
        const tick = () => {
          const sec = Math.floor((Date.now() - t0) / 1000)
          const mm = String(Math.floor(sec / 60)).padStart(2, '0')
          const ss = String(sec % 60).padStart(2, '0')
          set((s) => ({
            status: {
              ...s.status,
              [ws]: {
                visible: true,
                determinate: false,
                percent: 0,
                msg: `${count} file terkirim. Server sedang memproses data (file besar bisa beberapa menit)... ${mm}:${ss}`,
              },
            },
          }))
        }
        tick()
        timer = setInterval(tick, 1000)
      })
      xhr.addEventListener('load', () => {
        stop()
        let data = {}
        try {
          data = JSON.parse(xhr.responseText || '{}')
        } catch {
          data = {}
        }
        if (xhr.status < 200 || xhr.status >= 300) {
          return fail(
            data.detail ||
              `Server gagal memproses file (HTTP ${xhr.status}). Lihat pesan error di terminal server.`
          )
        }
        resolve({ ok: true, data })
      })
      xhr.addEventListener('error', () =>
        fail('Koneksi ke server terputus. Pastikan server masih berjalan (cek terminal).')
      )
      xhr.addEventListener('abort', () => fail('Upload dibatalkan.'))
      xhr.send(formData)
    })
  },

  /* ───── [AUTO-4] RUN RANGKUMAN PENJUALAN (lama: runRangkumanPenjualan) ───── */
  runRangkumanPenjualan: async () => {
    const s = get()
    const mainFiles = s.queues.rkMain
    if (!mainFiles.length) {
      useToastStore.getState().showToast('Pilih file penjualan Orlan/Zeta terlebih dahulu!', 'warn')
      return false
    }
    const totalRk = mainFiles.length + s.queues.rkBl.length + s.queues.rkTl.length
    set({
      busy: { ...s.busy, rk: true },
      errors: { ...s.errors, rk: '' },
      status: {
        ...s.status,
        rk: { visible: true, determinate: false, percent: 0, msg: `Menyiapkan upload ${totalRk} file...` },
      },
    })

    const fd = new FormData()
    for (const f of mainFiles) fd.append('files', f)
    for (const f of s.queues.rkBl) fd.append('files_bulan_lalu', f)
    for (const f of s.queues.rkTl) fd.append('files_tahun_lalu', f)
    fd.append('use_master_supplier', s.rkUseMasterSupplier)

    try {
      const { ok, data } = await get().automationUpload(ENDPOINTS.automate.rangkuman, fd, 'rk', totalRk)
      if (!ok) {
        const errMsg = data.detail || 'Gagal memproses Rangkuman Penjualan'
        set((st) => ({ errors: { ...st.errors, rk: errMsg } }))
        useToastStore.getState().showToast(errMsg, 'error')
        return false
      }
      useToastStore.getState().showToast(data.message, 'ok')
      set({ rkResult: data, rkGsResult: null })
      return true
    } finally {
      set((st) => ({
        busy: { ...st.busy, rk: false },
        status: { ...st.status, rk: { ...st.status.rk, visible: false, determinate: false, percent: 0 } },
      }))
    }
  },

  /* ───── [AUTO-5] RUN RANGKUMAN GSHEETS (lama: runRangkumanGSheets) ───── */
  runRangkumanGSheets: async () => {
    const s = get()
    set({ busy: { ...s.busy, gs: true } })
    const fd = new FormData()
    fd.append('paksa_summary_bulan_lama', s.rkPaksaSummary)
    try {
      const res = await apiFetch(ENDPOINTS.automate.rangkumanGsheets, { method: 'POST', body: fd })
      const data = await res.json()
      if (!res.ok) {
        useToastStore.getState().showToast(data.detail || 'Gagal sinkronisasi GSheets', 'error')
        return false
      }
      useToastStore.getState().showToast(data.message, 'ok')
      set({ rkGsResult: data })
      return true
    } finally {
      set((st) => ({ busy: { ...st.busy, gs: false } }))
    }
  },

  /* ───── [AUTO-6] RUN DOI PIPELINE (lama: runDoiPipeline) ───── */
  runDoiPipeline: async () => {
    const s = get()
    const files = s.queues.doi
    if (!files.length) {
      useToastStore.getState().showToast('Pilih file Mutasi Stok & Penjualan terlebih dahulu!', 'warn')
      return false
    }
    set({
      busy: { ...s.busy, doi: true },
      errors: { ...s.errors, doi: '' },
      status: {
        ...s.status,
        doi: { visible: true, determinate: false, percent: 0, msg: `Menyiapkan upload ${files.length} file...` },
      },
    })

    const fd = new FormData()
    for (const f of files) fd.append('files', f)
    fd.append('use_master_daftar_barang', s.doiUseMasterDaftar)
    fd.append('cabang', s.doiParams.cabang)
    fd.append('hari_kerja', s.doiParams.hari_kerja)
    fd.append('standar_doi_default', s.doiParams.standar_doi_default)
    fd.append('ambang_ams_min', s.doiParams.ambang_ams_min)
    fd.append('bulan_stok_masuk_ams', s.doiParams.bulan_stok_masuk_ams)
    fd.append('maks_bulan_ams', s.doiParams.maks_bulan_ams)

    try {
      const { ok, data } = await get().automationUpload(ENDPOINTS.automate.doi, fd, 'doi', files.length)
      if (!ok) {
        const errMsg = data.detail || 'Gagal membuat Laporan DOI'
        set((st) => ({ errors: { ...st.errors, doi: errMsg } }))
        useToastStore.getState().showToast(errMsg, 'error')
        return false
      }
      useToastStore.getState().showToast(data.message, 'ok')
      set({ doiResult: data })
      return true
    } finally {
      set((st) => ({
        busy: { ...st.busy, doi: false },
        status: { ...st.status, doi: { ...st.status.doi, visible: false, determinate: false, percent: 0 } },
      }))
    }
  },
}))