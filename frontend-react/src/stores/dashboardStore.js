/* ============================================================================
 * PAGE    : STORE: State & Antrean Upload Dashboard (Penjualan & DOI)
 * FILE    : src/stores/dashboardStore.js
 * ROUTE   : /analytics/penjualan · /analytics/doi
 * ORIGIN  : dashboardUploadQueue, dashboardPayloads, dashboardCanRestore,
 *           downloadDashboardHtml() di index.html lama
 * API     : GET/POST/DELETE /api/dashboard/...
 * STORE   : dashboardStore
 * UPDATE  : paste THIS file only into an AI
 * ========================================================================== */
import { create } from 'zustand'
import { authHeader } from '../api/http'
import { ENDPOINTS } from '../config/endpoints'
import { useToastStore } from './toastStore'

export const useDashboardStore = create((set, get) => ({
  /* ───── [DASH-STORE-1] STATE ───── */
  queues: { sales: [], doi: [] },
  payloads: { sales: null, doi: null },
  canRestore: { sales: false, doi: false },
  busy: false,
  status: { visible: false, determinate: false, percent: 0, msg: 'Menyiapkan upload file...' },

  // Opsi Upload Mandiri di Analytics
  salesUseMasterSupplier: true,
  doiUseMasterDaftar: true,
  doiUploadParams: {
    cabang: '',
    hari_kerja: '26',
    standar_doi_default: '30',
    ambang_ams_min: '0',
    bulan_stok_masuk_ams: 'auto',
    maks_bulan_ams: '0',
  },

  setSalesUseMasterSupplier: (val) => set({ salesUseMasterSupplier: val }),
  setDoiUseMasterDaftar: (val) => set({ doiUseMasterDaftar: val }),
  setDoiUploadParam: (key, val) =>
    set((s) => ({ doiUploadParams: { ...s.doiUploadParams, [key]: val } })),

  /* ───── [DASH-STORE-2] QUEUE ACTIONS ───── */
  addFiles: (kind, fileList) => {
    const s = get()
    if (s.busy) return
    const validFile = /\.(xlsx|xls|xlsm|csv)$/i
    const rejected = []
    const nextQueue = [...s.queues[kind]]
    for (const file of fileList || []) {
      if (!validFile.test(file.name)) {
        rejected.push(file.name)
        continue
      }
      const exists = nextQueue.some(
        (item) => item.name === file.name && item.size === file.size && item.lastModified === file.lastModified
      )
      if (!exists) nextQueue.push(file)
    }
    set({ queues: { ...s.queues, [kind]: nextQueue } })
    if (rejected.length) {
      useToastStore.getState().showToast(`Format file tidak sesuai: ${rejected.join(', ')}`, 'warn')
    }
  },

  removeFile: (kind, index) => {
    const s = get()
    if (s.busy) return
    const nextQueue = [...s.queues[kind]]
    nextQueue.splice(index, 1)
    set({ queues: { ...s.queues, [kind]: nextQueue } })
  },

  clearQueue: (kind) => {
    const s = get()
    if (s.busy) return
    set({ queues: { ...s.queues, [kind]: [] } })
  },

  /* ───── [DASH-STORE-3] XHR UPLOAD FORM WITH PROGRESS ───── */
  uploadForm: (url, formData, kind, count) => {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      xhr.open('POST', url)
      for (const [name, value] of Object.entries(authHeader())) {
        xhr.setRequestHeader(name, value)
      }
      xhr.upload.addEventListener('progress', (event) => {
        if (!event.lengthComputable || event.total <= 0) return
        const percent = Math.min(100, Math.round((event.loaded / event.total) * 100))
        const label = kind === 'doi' ? 'laporan DOI' : 'file Penjualan'
        set({
          status: {
            visible: true,
            determinate: true,
            percent,
            msg: `Mengunggah ${count} ${label} ke server: ${percent}%`,
          },
        })
      })
      xhr.upload.addEventListener('load', () => {
        const label = kind === 'doi' ? 'laporan DOI' : 'file Penjualan'
        set({
          status: {
            visible: true,
            determinate: false,
            percent: 0,
            msg: `${count} ${label} terkirim. Server sedang membaca dan memproses data...`,
          },
        })
      })
      xhr.addEventListener('load', () => {
        let data = {}
        try {
          data = JSON.parse(xhr.responseText || '{}')
        } catch {
          data = {}
        }
        if (xhr.status < 200 || xhr.status >= 300) {
          reject(new Error(data.detail || `Server gagal memproses file (HTTP ${xhr.status}).`))
          return
        }
        resolve(data)
      })
      xhr.addEventListener('error', () => reject(new Error('Koneksi terputus saat mengunggah file.')))
      xhr.addEventListener('abort', () => reject(new Error('Upload dibatalkan.')))
      xhr.send(formData)
    })
  },

  /* ───── [DASH-STORE-4] FETCH / UPLOAD / CLEAR / RESTORE ACTIONS ───── */
  loadSalesData: async (query = '') => {
    try {
      const res = await fetch(`${ENDPOINTS.dashboard.salesData}${query ? `?${query}` : ''}`)
      const data = await res.json()
      set((s) => ({ payloads: { ...s.payloads, sales: data } }))
      return data
    } catch {
      return { ready: false }
    }
  },

  uploadSales: async () => {
    const s = get()
    const files = s.queues.sales
    if (!files.length) {
      useToastStore.getState().showToast('Pilih atau seret file Penjualan ke antrean terlebih dahulu.', 'warn')
      return
    }
    set({
      busy: true,
      status: { visible: true, determinate: false, percent: 0, msg: `Menyiapkan upload ${files.length} file Penjualan...` },
    })
    const fd = new FormData()
    for (const f of files) fd.append('files', f)
    fd.append('use_master_supplier', s.salesUseMasterSupplier)
    try {
      const data = await s.uploadForm(ENDPOINTS.dashboard.salesUpload, fd, 'sales', files.length)
      set((st) => ({
        queues: { ...st.queues, sales: [] },
        payloads: { ...st.payloads, sales: data },
      }))
      useToastStore.getState().showToast(
        data.master_sync_warning ? 'Dashboard siap, tetapi sinkronisasi Master Data gagal.' : 'Dashboard Penjualan berhasil diperbarui!',
        data.master_sync_warning ? 'warn' : 'ok'
      )
    } catch (err) {
      useToastStore.getState().showToast(err.message || 'Gagal membaca data penjualan', 'error')
    } finally {
      set({ busy: false, status: { visible: false, determinate: false, percent: 0, msg: '' } })
    }
  },

  clearSales: async () => {
    try {
      const res = await fetch(ENDPOINTS.dashboard.salesData, { method: 'DELETE', headers: authHeader() })
      const data = await res.json()
      set((s) => ({
        queues: { ...s.queues, sales: [] },
        payloads: { ...s.payloads, sales: { ready: false } },
        canRestore: { ...s.canRestore, sales: Boolean(data.can_restore) },
      }))
      useToastStore.getState().showToast('Data dashboard dibersihkan.', 'ok')
    } catch {
      /* ignore */
    }
  },

  restoreSales: async () => {
    try {
      const res = await fetch(`${ENDPOINTS.dashboard.salesData.replace('/data', '')}/restore`, { method: 'POST', headers: authHeader() })
      const data = await res.json()
      set((s) => ({
        payloads: { ...s.payloads, sales: data },
        canRestore: { ...s.canRestore, sales: false },
      }))
      useToastStore.getState().showToast(data.ready ? 'Data automation dipulihkan.' : 'Belum ada hasil automation untuk dipulihkan.', data.ready ? 'ok' : 'warn')
    } catch {
      /* ignore */
    }
  },

  loadDoiData: async (query = '') => {
    try {
      const res = await fetch(`${ENDPOINTS.dashboard.doiData}${query ? `?${query}` : ''}`)
      const data = await res.json()
      set((s) => ({ payloads: { ...s.payloads, doi: data } }))
      return data
    } catch {
      return { ready: false }
    }
  },

  uploadDoi: async () => {
    const s = get()
    const files = s.queues.doi
    if (!files.length) {
      useToastStore.getState().showToast('Pilih atau seret laporan DOI ke antrean terlebih dahulu.', 'warn')
      return
    }
    set({
      busy: true,
      status: { visible: true, determinate: false, percent: 0, msg: `Menyiapkan upload ${files.length} laporan DOI...` },
    })
    const fd = new FormData()
    for (const f of files) fd.append('files', f)
    fd.append('use_master_daftar_barang', s.doiUseMasterDaftar)
    fd.append('cabang', s.doiUploadParams.cabang)
    fd.append('hari_kerja', s.doiUploadParams.hari_kerja)
    fd.append('standar_doi_default', s.doiUploadParams.standar_doi_default)
    fd.append('ambang_ams_min', s.doiUploadParams.ambang_ams_min)
    fd.append('bulan_stok_masuk_ams', s.doiUploadParams.bulan_stok_masuk_ams)
    fd.append('maks_bulan_ams', s.doiUploadParams.maks_bulan_ams)

    try {
      const data = await s.uploadForm(ENDPOINTS.dashboard.doiUpload, fd, 'doi', files.length)
      set((st) => ({
        queues: { ...st.queues, doi: [] },
        payloads: { ...st.payloads, doi: data },
      }))
      useToastStore.getState().showToast('Dashboard DOI berhasil diperbarui!', 'ok')
    } catch (err) {
      useToastStore.getState().showToast(err.message || 'Gagal membaca file DOI', 'error')
    } finally {
      set({ busy: false, status: { visible: false, determinate: false, percent: 0, msg: '' } })
    }
  },

  clearDoi: async () => {
    try {
      const res = await fetch(ENDPOINTS.dashboard.doiData, { method: 'DELETE', headers: authHeader() })
      const data = await res.json()
      set((s) => ({
        queues: { ...s.queues, doi: [] },
        payloads: { ...s.payloads, doi: { ready: false } },
        canRestore: { ...s.canRestore, doi: Boolean(data.can_restore) },
      }))
      useToastStore.getState().showToast('Data dashboard dibersihkan.', 'ok')
    } catch {
      /* ignore */
    }
  },

  restoreDoi: async () => {
    try {
      const res = await fetch(`${ENDPOINTS.dashboard.doiData.replace('/data', '')}/restore`, { method: 'POST', headers: authHeader() })
      const data = await res.json()
      set((s) => ({
        payloads: { ...s.payloads, doi: data },
        canRestore: { ...s.canRestore, doi: false },
      }))
      useToastStore.getState().showToast(data.ready ? 'Data automation dipulihkan.' : 'Belum ada hasil automation untuk dipulihkan.', data.ready ? 'ok' : 'warn')
    } catch {
      /* ignore */
    }
  },

  /* ───── [DASH-STORE-5] DOWNLOAD DASHBOARD HTML (lama: downloadDashboardHtml) ───── */
  downloadDashboardHtml: (kind) => {
    const payload = get().payloads[kind]
    if (!payload || !payload.charts) {
      useToastStore.getState().showToast('Data visualisasi belum tersedia.', 'warn')
      return
    }
    const escapeHtml = (value) =>
      String(value ?? '').replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]))

    const chartNames =
      kind === 'sales'
        ? [
            ['tren', 'Tren omset & forecast'],
            ['retur', 'Rasio retur'],
            ['cabang', 'Omset per cabang'],
            ['principal', 'Top principal'],
            ['hari', 'Pola hari kerja'],
            ['customer', 'Top customer'],
            ['pareto', 'Konsentrasi outlet'],
          ]
        : [
            ['doi_std', 'DOI vs standar'],
            ['lebih_kurang', 'Kelebihan / kekurangan stok'],
            ['porsi', 'Porsi omset vs stok'],
            ['bucket', 'Sebaran rentang DOI'],
            ['scatter', 'Peta SKU'],
            ['top_lebih', 'SKU kelebihan stok'],
            ['top_kritis', 'SKU kritis / kosong'],
            ['tren', 'Tren omset bulanan'],
            ['gudang', 'Nilai stok per gudang'],
          ]
    const charts = chartNames
      .filter(([key]) => payload.charts[key])
      .map(([key, title], index) => ({ id: `chart-${index}`, title, figure: payload.charts[key] }))
    const kpiLabels =
      kind === 'sales'
        ? [
            ['omset', 'Omset bersih'],
            ['faktur', 'Faktur'],
            ['outlet', 'Outlet aktif'],
            ['forecast_30d', 'Forecast 30 hari'],
          ]
        : [
            ['saldo', 'Nilai stok'],
            ['ams', 'AMS / bulan'],
            ['doi', 'DOI total'],
            ['n_sku', 'SKU aktif'],
            ['kelebihan', 'Kelebihan stok'],
            ['kekurangan', 'Kekurangan stok'],
          ]
    const kpis = kpiLabels.map(([key, label]) => `<div class="kpi"><small>${label}</small><b>${escapeHtml(payload.kpi[key] ?? '-')}</b></div>`).join('')
    const insights = (payload.insights || []).map((text) => `<li>${escapeHtml(String(text).replace(/<[^>]*>/g, ''))}</li>`).join('')
    const chartMarkup = charts.map((chart) => `<section><h2>${chart.title}</h2><div id="${chart.id}" class="chart"></div></section>`).join('')
    const chartData = JSON.stringify(charts).replace(/</g, '\\u003c')
    const title = kind === 'doi' ? 'Dashboard DOI (Stok vs Omset)' : 'Dashboard Penjualan & Forecast'
    const html = `<!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${title}</title><script src="https://cdn.plot.ly/plotly-2.32.0.min.js"><\/script><style>body{margin:0;background:#f4f6f8;color:#0f172a;font:15px Arial,sans-serif;padding:24px}.wrap{max-width:1280px;margin:auto}h1{font-size:24px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}.kpi,section{background:white;border:1px solid #e2e8f0;border-radius:10px;padding:18px;margin:12px 0}.kpi small,.kpi b{display:block}.kpi small{color:#64748b}.kpi b{font-size:21px;margin-top:8px}.chart{min-height:320px}li{margin:7px 0}@media(max-width:640px){body{padding:12px}.chart{min-height:260px}}</style></head><body><main class="wrap"><h1>${title}</h1><div class="grid">${kpis}</div><section><h2>Insight</h2><ul>${insights}</ul></section>${chartMarkup}</main><script>const charts=${chartData};for(const item of charts){Plotly.newPlot(document.getElementById(item.id),item.figure.data,item.figure.layout,{responsive:true,displaylogo:false});}<\/script></body></html>`
    const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `${kind === 'doi' ? 'Dashboard_DOI' : 'Dashboard_Penjualan'}_${new Date().toISOString().slice(0, 10)}.html`
    link.click()
    URL.revokeObjectURL(link.href)
  },
}))