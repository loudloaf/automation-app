/* ============================================================================
 * PAGE    : Master Data Hub (6 Kategori + Modal Tambah/Edit + Self-Learning Mapper)
 * FILE    : src/pages/MasterDataPage.jsx
 * ROUTE   : /master
 * ORIGIN  : #view-master + #rowModal + #mapModal + loadMasterData(), renderTable(),
 *           uploadMasterFile(), openMapModal(), confirmColumnMapping(),
 *           openRowModal(), submitRowModal(), deleteRow(), clearCurrentTable()
 * API     : GET/POST/DELETE /api/master/:entity...
 * STORE   : authStore, toastStore, uiStore
 * UPDATE  : paste THIS file only into an AI
 * ========================================================================== */
import { useEffect, useState, useCallback, useRef } from 'react'
import {
  Building2,
  Map,
  Store,
  Package,
  Factory,
  MapPin,
  Upload,
  Search,
  Trash2,
  Lock,
  AlertTriangle,
  Zap,
} from 'lucide-react'
import usePageTitle from '../shared/usePageTitle'
import { apiFetch } from '../api/http'
import { ENDPOINTS } from '../config/endpoints'
import { useAuthStore } from '../stores/authStore'
import { useToastStore } from '../stores/toastStore'
import { useAppDataStore } from '../stores/appDataStore'

/* ───── [MASTER-1] DAFTAR ENTITAS MASTER DATA ───── */
const ENTITIES = [
  { id: 'supplier_rekap', label: 'Supplier · Rekap', Icon: Building2 },
  { id: 'supplier_cabang', label: 'Supplier · Per Cabang (Zeta)', Icon: Map },
  { id: 'customer', label: 'Customer / Outlet', Icon: Store },
  { id: 'product', label: 'Daftar Barang / SKU', Icon: Package },
  { id: 'warehouse', label: 'Gudang (DOI)', Icon: Factory },
  { id: 'branch', label: 'Cabang', Icon: MapPin },
]

export default function MasterDataPage() {
  usePageTitle('Master Data Hub')
  const fileInputRef = useRef(null)

  const user = useAuthStore((s) => s.user)
  const currentIsAdmin = Boolean(user?.is_admin)
  const showToast = useToastStore((s) => s.showToast)

/* ───── [MASTER-2] STATE ───── */
  const currentEntity = useAppDataStore((s) => s.currentEntity)
  const setCurrentEntity = useAppDataStore((s) => s.setCurrentEntity)
  const masterSchemas = useAppDataStore((s) => s.masterSchemas)
  const masterCounts = useAppDataStore((s) => s.masterCounts)
  const loadMasterData = useAppDataStore((s) => s.loadMasterData)

  const currentSchema = masterSchemas[currentEntity] || {
    title: '',
    pk: '',
    fields: [],
    rows: [],
    counts: masterCounts,
  }
  
  const [searchQuery, setSearchQuery] = useState('')
  const [pendingUploadFile, setPendingUploadFile] = useState(null)

  // Modal 1: Add / Edit Row State
  const [rowModalOpen, setRowModalOpen] = useState(false)
  const [modalMode, setModalMode] = useState('add')
  const [rowModalPkVal, setRowModalPkVal] = useState('')
  const [rowFormValues, setRowFormValues] = useState({})

  // Modal 2: Dynamic Column Mapper State
  const [mapModalOpen, setMapModalOpen] = useState(false)
  const [mapModalInfo, setMapModalInfo] = useState(null)
  const [columnMapSelection, setColumnMapSelection] = useState({})

  useEffect(() => {
    loadMasterData(currentEntity)
  }, [currentEntity, loadMasterData])

  /* ───── [MASTER-4] UPLOAD EXCEL / CSV & SELF-LEARNING MAPPER (lama: uploadMasterFile) ───── */
  const uploadMasterFile = async (fileObj, customMap = null) => {
    const file = customMap ? pendingUploadFile : fileObj
    if (!file) return
    setPendingUploadFile(file)

    const fd = new FormData()
    fd.append('file', file)
    if (customMap) fd.append('custom_mapping_json', JSON.stringify(customMap))

    try {
      const res = await apiFetch(ENDPOINTS.master.upload(currentEntity), {
        method: 'POST',
        body: fd,
      })
      const data = await res.json()
      if (fileInputRef.current) fileInputRef.current.value = ''

      if (!res.ok) {
        showToast(data.detail || 'Gagal memproses file', 'error')
        return
      }
      if (data.status === 'NEEDS_MAPPING') {
        const initMap = {}
        ;(data.all_fields || []).forEach((f) => {
          initMap[f.field] = data.matched?.[f.field] || ''
        })
        setColumnMapSelection(initMap)
        setMapModalInfo(data)
        setMapModalOpen(true)
        return
      }
      setMapModalOpen(false)
      showToast(data.message, 'ok')
      await loadMasterData(currentEntity)
    } catch {
      showToast('Gagal mengunggah file Master Data', 'error')
    }
  }

  const confirmColumnMapping = async () => {
    const mapping = {}
    Object.entries(columnMapSelection).forEach(([k, v]) => {
      if (v) mapping[k] = v
    })
    await uploadMasterFile(null, mapping)
  }

  /* ───── [MASTER-5] ADD / EDIT / DELETE / CLEAR HANDLERS ───── */
  const openRowModal = (mode, rowData = {}) => {
    setModalMode(mode)
    setRowModalPkVal(rowData[currentSchema.pk] ?? '')
    const initialVals = {}
    ;(currentSchema.fields || []).forEach((f) => {
      initialVals[f.field] = rowData[f.field] ?? ''
    })
    setRowFormValues(initialVals)
    setRowModalOpen(true)
  }

  const submitRowModal = async () => {
    const payload = { ...rowFormValues }
    if (rowModalPkVal) payload[currentSchema.pk] = rowModalPkVal

    const res = await apiFetch(ENDPOINTS.master.row(currentEntity, modalMode), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    const data = await res.json()
    if (!res.ok) {
      showToast(data.detail || 'Gagal menyimpan', 'error')
      return
    }
    setRowModalOpen(false)
    showToast(data.message, 'ok')
    await loadMasterData(currentEntity)
  }

  const deleteRow = async (pkVal) => {
    if (!window.confirm('Hapus baris ini dari Master Data?')) return
    const res = await apiFetch(ENDPOINTS.master.deleteRow(currentEntity, pkVal), {
      method: 'DELETE',
    })
    const data = await res.json()
    if (!res.ok) {
      showToast(data.detail || 'Akses ditolak', 'error')
      return
    }
    showToast(data.message, 'ok')
    await loadMasterData(currentEntity)
  }

  const clearCurrentTable = async () => {
    if (!window.confirm(`Kosongkan seluruh isi tabel "${currentSchema.title}"?`)) return
    const res = await apiFetch(ENDPOINTS.master.clear(currentEntity), {
      method: 'DELETE',
    })
    const data = await res.json()
    if (!res.ok) {
      showToast(data.detail || 'Akses ditolak', 'error')
      return
    }
    showToast(data.message, 'ok')
    await loadMasterData(currentEntity)
  }

  /* ───── [MASTER-6] FILTER BARIS TABEL (lama: renderTable) ───── */
  const q = searchQuery.toLowerCase().trim()
  const rows = currentSchema.rows || []
  const fields = currentSchema.fields || []
  const filteredRows = rows.filter(
    (r) => !q || Object.values(r).some((v) => String(v || '').toLowerCase().includes(q))
  )

  return (
    <section id="view-master" className="space-y-6">
      {/* Top Cards: Entity Selector & File Upload */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="lg:col-span-8 panel rounded-xl p-7 flex flex-col justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Master Data</h1>
            <p className="text-sm text-slate-500 mt-1 leading-relaxed">
              Pusat referensi data lengkap perusahaan. Saat pengguna menjalankan script dengan file mereka sendiri, data baru otomatis ditambahkan ke sini tanpa menimpa editan Admin.
            </p>
          </div>

          <div className="flex flex-wrap gap-2 mt-5" id="entity-Selector">
            {ENTITIES.map(({ id, label, Icon }) => {
              const active = currentEntity === id
              const cnt = currentSchema.counts?.[id] ?? 0
              return (
                <button
                  key={id}
                  onClick={() => setCurrentEntity(id)}
                  data-ent={id}
                  className={
                    active
                      ? 'ent-btn px-4 py-2.5 rounded-lg text-sm font-semibold transition-all bg-blue-600 text-white flex items-center gap-2'
                      : 'ent-btn px-4 py-2.5 rounded-lg text-sm font-semibold transition-all bg-slate-100 text-slate-600 hover:bg-slate-200 flex items-center gap-2'
                  }
                >
                  <span>
                    <Icon className="lucide" /> {label}
                  </span>
                  <span className="text-xs font-mono px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-800">
                    {cnt}
                  </span>
                </button>
              )
            })}
          </div>
        </div>

        <div className="lg:col-span-4 panel rounded-xl p-7 flex flex-col justify-between transition-all">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-blue-700 font-mono">Sinkronisasi file</span>
              <span id="total-count-badge" className="text-sm font-mono px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-900">
                {rows.length} baris
              </span>
            </div>
            <h3 className="text-base font-bold text-slate-900 mt-2">Upload Excel / CSV Master</h3>
            <p className="text-sm text-slate-500 mt-1">
              Otomatis membaca 2 sheet <code className="text-slate-700">Supplier.xlsx</code> sekaligus atau mendeteksi struktur kolom baru.
            </p>
          </div>

          <label className="mt-4 border-2 border-dashed border-slate-200 hover:border-blue-400 rounded-lg p-5 text-center cursor-pointer transition-all bg-slate-50 hover:bg-slate-50">
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.xls,.csv"
              className="hidden"
              onChange={(e) => {
                if (e.target.files?.[0]) uploadMasterFile(e.target.files[0])
              }}
            />
            <div className="text-2xl mb-1">
              <Upload className="lucide" />
            </div>
            <span className="text-sm font-semibold text-slate-900 block">Klik untuk pilih file Excel / CSV</span>
            <span className="text-xs text-slate-500 block mt-0.5">Incremental Sync (Data lama aman)</span>
          </label>
        </div>
      </div>

      {/* Master Data Table Card */}
      <div className="panel rounded-xl p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-5 mb-5">
          <div className="flex flex-wrap items-center gap-4 flex-1">
            <div className="relative flex-1 max-w-md min-w-[220px]">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Cari kode, nama, grup barang, atau cabang..."
                className="w-full bg-white border border-slate-200 rounded-lg pl-10 pr-4 py-2.5 text-sm text-slate-900 placeholder-slate-500 focus:outline-none focus:border-blue-600"
              />
              <span className="absolute left-3.5 top-2.5 text-slate-500 text-sm">
                <Search className="lucide" />
              </span>
            </div>
            <span id="active-table-title" className="text-sm font-mono text-slate-500">
              {currentSchema.title} ({rows.length} data)
            </span>
          </div>

          <div className="flex items-center gap-2.5">
            {currentIsAdmin && rows.length > 0 && (
              <button
                onClick={clearCurrentTable}
                className="px-3.5 py-2.5 rounded-lg bg-rose-50 hover:bg-rose-100 border border-rose-200 text-rose-700 text-sm font-semibold transition-all"
              >
                <Trash2 className="lucide" /> Kosongkan Tabel
              </button>
            )}
            <button
              onClick={() => openRowModal('add')}
              className="px-4 py-2.5 rounded-lg text-white text-sm font-semibold transition-all bg-blue-600 hover:bg-blue-700"
            >
              + Tambah Data Baru
            </button>
          </div>
        </div>

        <div className="overflow-x-auto rounded-lg border border-slate-200">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-xs font-mono text-slate-500">
                {fields.map((f) => (
                  <th key={f.field} className="py-3.5 px-4">
                    {f.label}
                  </th>
                ))}
                <th className="py-3.5 px-4 text-right">
                  Aksi {currentIsAdmin ? '(Admin)' : <Lock className="lucide" />}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-sm">
              {!filteredRows.length ? (
                <tr>
                  <td colSpan={fields.length + 1} className="py-12 text-center text-slate-500">
                    Database kategori <b>{currentSchema.title}</b> masih kosong (0 data). Upload file Excel/CSV di kanan atas atau klik <b>+ Tambah Data Baru</b>.
                  </td>
                </tr>
              ) : (
                filteredRows.slice(0, 400).map((row, rIdx) => {
                  const pkVal = row[currentSchema.pk] ?? rIdx
                  return (
                    <tr key={pkVal} className="hover:bg-slate-100 transition-colors">
                      {fields.map((f, idx) => (
                        <td
                          key={f.field}
                          className={`py-3.5 px-4 ${
                            idx === 0 ? 'font-mono font-semibold text-blue-700' : 'text-slate-700'
                          }`}
                        >
                          {row[f.field] ?? ''}
                        </td>
                      ))}
                      <td className="py-3.5 px-4 text-right whitespace-nowrap">
                        {currentIsAdmin ? (
                          <>
                            <button
                              onClick={() => openRowModal('edit', row)}
                              className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-50 text-blue-700 mr-1"
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => deleteRow(row[currentSchema.pk])}
                              className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-rose-100 text-rose-600"
                            >
                              Hapus
                            </button>
                          </>
                        ) : (
                          <span className="text-xs font-mono text-slate-500">Hanya Admin</span>
                        )}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* MODAL 1: ADD / EDIT MASTER ROW */}
      {rowModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 flex items-center justify-center p-5">
          <div className="panel rounded-xl p-7 w-full max-w-md border border-slate-200 bg-white">
            <h3 className="text-base font-bold text-slate-900 mb-4">
              {modalMode === 'add' ? `Tambah ${currentSchema.title}` : `Edit ${currentSchema.title} (Admin)`}
            </h3>
            <div className="space-y-4">
              {fields.map((f) => (
                <div key={f.field}>
                  <label className="text-sm text-slate-500 block mb-1">
                    {f.label} {f.required ? '*' : ''}
                  </label>
                  <input
                    type="text"
                    value={rowFormValues[f.field] ?? ''}
                    onChange={(e) =>
                      setRowFormValues((prev) => ({ ...prev, [f.field]: e.target.value }))
                    }
                    className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-900"
                  />
                </div>
              ))}
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setRowModalOpen(false)}
                className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-sm text-slate-600"
              >
                Batal
              </button>
              <button
                onClick={submitRowModal}
                className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-sm font-semibold text-white"
              >
                Simpan
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: DYNAMIC COLUMN MAPPER */}
      {mapModalOpen && mapModalInfo && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 flex items-center justify-center p-5">
          <div className="panel rounded-xl p-7 w-full max-w-lg border border-amber-300 bg-white">
            <div className="flex items-center gap-2 text-amber-700 text-sm font-mono mb-1">
              <span>
                <AlertTriangle className="lucide" /> Struktur File Berbeda Terdeteksi
              </span>
            </div>
            <h3 className="text-base font-bold text-slate-900">Pencocokan Kolom Pintar (Self-Learning)</h3>
            <p className="text-sm text-slate-600 mt-1 leading-relaxed">
              {mapModalInfo.message}
              <br />
              <span className="text-amber-700">
                Kolom wajib belum dikenali:{' '}
                <b>{(mapModalInfo.missing_required || []).map((m) => m.label).join(', ')}</b>
              </span>
              .
            </p>
            <div className="space-y-4 mt-4 max-h-72 overflow-y-auto pr-1">
              {(mapModalInfo.all_fields || []).map((f) => (
                <div key={f.field} className="flex flex-col gap-1">
                  <label className="text-sm font-semibold text-slate-700">
                    {f.label} {f.required && <span className="text-rose-600">*Wajib</span>}
                  </label>
                  <select
                    value={columnMapSelection[f.field] || ''}
                    onChange={(e) =>
                      setColumnMapSelection((prev) => ({ ...prev, [f.field]: e.target.value }))
                    }
                    className="bg-white border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-900"
                  >
                    <option value="">-- Tidak Dipakai / Kosong --</option>
                    {(mapModalInfo.available_columns || []).map((c) => (
                      <option key={c} value={c}>
                        Kolom Excel: &quot;{c}&quot;
                      </option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
            <div className="flex justify-end gap-2 mt-5">
              <button
                onClick={() => setMapModalOpen(false)}
                className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-sm text-slate-600"
              >
                Batal
              </button>
              <button
                onClick={confirmColumnMapping}
                className="px-5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-bold text-sm"
              >
                <Zap className="lucide" /> Pelajari Struktur & Proses Data
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}