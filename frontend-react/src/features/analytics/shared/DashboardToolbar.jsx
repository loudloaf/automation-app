/* ============================================================================
 * PAGE    : SHARED: Toolbar, Parameter Input & Kotak Syarat File Analytics
 * FILE    : src/features/analytics/shared/DashboardToolbar.jsx
 * ROUTE   : /analytics/penjualan · /analytics/doi
 * ORIGIN  : #dash-toolbar + Syarat File Checklist + Parameter DOI
 * API     : POST /api/dashboard/penjualan/upload · POST /api/dashboard/doi/upload
 * STORE   : dashboardStore
 * UPDATE  : paste THIS file only into an AI
 * ========================================================================== */
import { useRef, useState } from 'react'
import { UploadCloud, Play, ListX, Trash2, RotateCcw, Download, AlertTriangle } from 'lucide-react'
import { useDashboardStore } from '../../../stores/dashboardStore'

export default function DashboardToolbar({ kind = 'sales', onUploadSuccess, onExportHtml }) {
  const inputRef = useRef(null)
  const [dragActive, setDragActive] = useState(false)

  const queue = useDashboardStore((s) => s.queues[kind])
  const payload = useDashboardStore((s) => s.payloads[kind])
  const canRestore = useDashboardStore((s) => s.canRestore[kind])
  const busy = useDashboardStore((s) => s.busy)
  const status = useDashboardStore((s) => s.status)

  const salesUseMasterSupplier = useDashboardStore((s) => s.salesUseMasterSupplier)
  const setSalesUseMasterSupplier = useDashboardStore((s) => s.setSalesUseMasterSupplier)
  const doiUseMasterDaftar = useDashboardStore((s) => s.doiUseMasterDaftar)
  const setDoiUseMasterDaftar = useDashboardStore((s) => s.setDoiUseMasterDaftar)
  const doiUploadParams = useDashboardStore((s) => s.doiUploadParams)
  const setDoiUploadParam = useDashboardStore((s) => s.setDoiUploadParam)

  const addFiles = useDashboardStore((s) => s.addFiles)
  const removeFile = useDashboardStore((s) => s.removeFile)
  const clearQueue = useDashboardStore((s) => s.clearQueue)
  const uploadSales = useDashboardStore((s) => s.uploadSales)
  const uploadDoi = useDashboardStore((s) => s.uploadDoi)
  const clearSales = useDashboardStore((s) => s.clearSales)
  const clearDoi = useDashboardStore((s) => s.clearDoi)
  const restoreSales = useDashboardStore((s) => s.restoreSales)
  const restoreDoi = useDashboardStore((s) => s.restoreDoi)

  const isDoi = kind === 'doi'
  const dropTitle = isDoi
    ? 'Seret Laporan_DOI_*.xlsx atau file mentah (Daftar Barang, Mutasi Stok, Penjualan)'
    : 'Seret file penjualan (Orlan/Zeta) & Supplier.xlsx ke sini'
  const dropHint = isDoi
    ? 'atau klik untuk memilih file (.xlsx, .xls, .xlsm, .csv)'
    : 'atau klik untuk memilih file (.xlsx, .xls, .xlsm, .csv)'

  const handlePick = () => {
    if (!busy && inputRef.current) inputRef.current.click()
  }

  const handleLoad = async () => {
    if (isDoi) await uploadDoi()
    else await uploadSales()
    if (onUploadSuccess) onUploadSuccess()
  }

  const handleClearData = async () => {
    if (isDoi) await clearDoi()
    else await clearSales()
  }

  const handleRestoreData = async () => {
    if (isDoi) await restoreDoi()
    else await restoreSales()
    if (onUploadSuccess) onUploadSuccess()
  }

  const hasFiles = queue.length > 0
  const ready = Boolean(payload?.ready)
  const showActions = ready || canRestore

  return (
    <div id="dash-toolbar" className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      {/* ───── KOLOM KIRI (7 KOLOM): DROPZONE, PARAMETER & TOMBOL AKSI ───── */}
      <div className="lg:col-span-7 panel rounded-xl p-7 space-y-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-slate-900">
              {isDoi ? 'Sumber Data Visualisasi DOI' : 'Sumber Data Visualisasi Penjualan'}
            </h2>
            <p className="text-sm text-slate-500 mt-1">
              {isDoi
                ? 'Otomatis memakai hasil script Laporan DOI terakhir, atau upload file secara mandiri di bawah ini.'
                : 'Otomatis memakai hasil script Rangkuman Penjualan terakhir, atau upload file penjualan secara mandiri.'}
            </p>
          </div>
          <span className="text-xs font-mono font-semibold px-3 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200 whitespace-nowrap">
            ↗ Auto-Sync / Manual
          </span>
        </div>

        {/* Dropzone */}
        <div className="space-y-3">
          <div
            role="button"
            tabIndex={0}
            aria-label="Seret dan lepaskan file dashboard"
            aria-disabled={busy}
            onClick={handlePick}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                handlePick()
              }
            }}
            onDragOver={(e) => {
              e.preventDefault()
              if (!busy) setDragActive(true)
            }}
            onDragLeave={(e) => {
              if (!e.currentTarget.contains(e.relatedTarget)) setDragActive(false)
            }}
            onDrop={(e) => {
              e.preventDefault()
              setDragActive(false)
              if (!busy) addFiles(kind, e.dataTransfer.files)
            }}
            className={`flex min-h-[64px] min-w-0 cursor-pointer items-center justify-center gap-3 rounded-lg border-2 border-dashed ${
              dragActive ? 'border-blue-600 bg-blue-50' : 'border-slate-300 bg-slate-50'
            } px-4 py-3 text-center transition-colors hover:border-blue-400 hover:bg-blue-50 ${
              busy ? 'pointer-events-none opacity-60' : ''
            }`}
          >
            <UploadCloud className="text-blue-600 lucide" />
            <span className="text-left">
              <b className="block text-sm text-slate-800">{dropTitle}</b>
              <span className="text-xs text-slate-500">{dropHint}</span>
            </span>
          </div>
          <input
            ref={inputRef}
            type="file"
            multiple
            accept=".xlsx,.xls,.xlsm,.csv"
            disabled={busy}
            className="hidden"
            onChange={(e) => {
              addFiles(kind, e.target.files)
              e.target.value = ''
            }}
          />

          {queue.length > 0 && (
            <div className="border-t border-slate-200 pt-3 text-sm text-slate-600">
              <div className="flex flex-wrap items-center gap-2">
                <b>{queue.length} file dalam antrean:</b>
                {queue.map((f, i) => (
                  <span key={`${f.name}-${i}`} className="inline-flex items-center gap-1 rounded-lg bg-slate-100 px-2.5 py-1 text-xs">
                    {f.name}
                    <button
                      type="button"
                      disabled={busy}
                      aria-label={`Hapus ${f.name} dari antrean`}
                      onClick={() => removeFile(kind, i)}
                      className="ml-1 text-slate-500 hover:text-rose-700"
                    >
                      &times;
                    </button>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Fallback Toggle & Parameter Khusus (Penjualan vs DOI) */}
        {!isDoi ? (
          <>
            <label className="flex items-start gap-4 p-4 rounded-lg bg-blue-50 border border-blue-200 cursor-pointer">
              <input
                type="checkbox"
                checked={salesUseMasterSupplier}
                onChange={(e) => setSalesUseMasterSupplier(e.target.checked)}
                className="mt-0.5 rounded text-blue-700 focus:ring-blue-500"
              />
              <div className="text-sm">
                <span className="font-semibold text-slate-900 block">
                  Opsi Fallback: Gunakan <code className="text-blue-700">Supplier.xlsx</code> dari Master Data Hub bila saya tidak ikut meng-upload file Supplier
                </span>
                <span className="text-xs text-slate-500">
                  Jika Anda meng-upload file <code className="text-slate-600">Supplier.xlsx</code> bersama data penjualan, sistem otomatis memperbarui Master Data Hub.
                </span>
              </div>
            </label>
            <div className={`fallback-warn ${salesUseMasterSupplier ? 'is-active' : ''}`} role="alert">
              <AlertTriangle className="lucide" />
              <span>Warning: Master data may not be completely updated or accurate for this execution.</span>
            </div>
          </>
        ) : (
          <>
            <label className="flex items-start gap-4 p-4 rounded-lg bg-emerald-50 border border-emerald-200 cursor-pointer">
              <input
                type="checkbox"
                checked={doiUseMasterDaftar}
                onChange={(e) => setDoiUseMasterDaftar(e.target.checked)}
                className="mt-0.5 rounded text-blue-700"
              />
              <div className="text-sm">
                <span className="font-semibold text-slate-900 block">
                  Opsi Fallback: Gunakan <code className="text-emerald-700">Daftar Barang</code> dari Master Data Hub bila upload file mentah tanpa Daftar Barang
                </span>
                <span className="text-xs text-slate-500">
                  Jika Anda meng-upload file jadi <code className="text-slate-600">Laporan_DOI_*.xlsx</code>, parameter di bawah otomatis dibaca langsung dari isi sheet laporan tersebut.
                </span>
              </div>
            </label>

            {/* Parameter DOI Expander di Analytics DOI */}
            <details className="rounded-lg bg-slate-50 border border-slate-200 p-5">
              <summary className="text-sm font-semibold text-slate-700 cursor-pointer">
                Parameter DOI (opsional bila upload file mentah Mutasi Stok & Penjualan)
              </summary>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
                <div>
                  <label className="text-xs text-slate-500 block mb-1">Nama cabang (kosong = otomatis)</label>
                  <input
                    type="text"
                    value={doiUploadParams.cabang}
                    onChange={(e) => setDoiUploadParam('cabang', e.target.value)}
                    placeholder="Otomatis"
                    className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-900"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-500 block mb-1">Hari kerja / bulan</label>
                  <input
                    type="number"
                    value={doiUploadParams.hari_kerja}
                    min={1}
                    max={31}
                    onChange={(e) => setDoiUploadParam('hari_kerja', e.target.value)}
                    className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-900"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-500 block mb-1">Standar DOI default (hari)</label>
                  <input
                    type="number"
                    value={doiUploadParams.standar_doi_default}
                    min={1}
                    onChange={(e) => setDoiUploadParam('standar_doi_default', e.target.value)}
                    className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-900"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-500 block mb-1">Ambang AMS minimum (Rp)</label>
                  <input
                    type="number"
                    value={doiUploadParams.ambang_ams_min}
                    step={1000}
                    onChange={(e) => setDoiUploadParam('ambang_ams_min', e.target.value)}
                    className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-900"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-500 block mb-1">Bulan yang sama dengan tanggal akhir Mutasi Stok</label>
                  <select
                    value={doiUploadParams.bulan_stok_masuk_ams}
                    onChange={(e) => setDoiUploadParam('bulan_stok_masuk_ams', e.target.value)}
                    className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-900"
                  >
                    <option value="auto">Otomatis (disarankan)</option>
                    <option value="ya">Selalu masuk AMS</option>
                    <option value="tidak">Selalu jadi OMS</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-slate-500 block mb-1">Batasi AMS ke N bulan terakhir (0 = semua)</label>
                  <input
                    type="number"
                    value={doiUploadParams.maks_bulan_ams}
                    min={0}
                    max={24}
                    onChange={(e) => setDoiUploadParam('maks_bulan_ams', e.target.value)}
                    className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-900"
                  />
                </div>
              </div>
            </details>
          </>
        )}

        {/* Status Progress Bar */}
        {status.visible && (
          <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800" role="status" aria-live="polite" aria-busy="true">
            <div className="flex items-center gap-2">
              <span className="dashboard-spinner" aria-hidden="true" />
              <span>{status.msg}</span>
            </div>
            <div className="dashboard-progress-track mt-2" role="progressbar" aria-label="Progres upload" aria-valuenow={status.determinate ? status.percent : undefined}>
              <div
                className={`dashboard-progress-bar ${status.determinate ? 'is-determinate' : ''}`}
                style={{ width: status.determinate ? `${status.percent}%` : '' }}
              />
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex flex-col gap-2">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            <button
              onClick={handleLoad}
              disabled={busy || !hasFiles}
              className="flex w-full items-center justify-center gap-1.5 rounded-xl bg-blue-600 px-4 py-3 text-sm font-bold text-white transition-all hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Play className="lucide" style={{ margin: 0 }} /> Muat & Visualisasikan File Terpilih
            </button>
            <button
              onClick={() => clearQueue(kind)}
              disabled={busy || !hasFiles}
              className="flex w-full items-center justify-center gap-1.5 rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <ListX className="lucide" style={{ margin: 0 }} /> Kosongkan Antrean
            </button>
          </div>

          {showActions && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1">
              {ready && (
                <button
                  onClick={handleClearData}
                  className="flex w-full items-center justify-center gap-1 rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-xs font-semibold text-rose-700 hover:bg-rose-100"
                >
                  <Trash2 className="lucide" /> Bersihkan data
                </button>
              )}
              {canRestore && (
                <button
                  onClick={handleRestoreData}
                  className="flex w-full items-center justify-center gap-1 rounded-xl border border-emerald-200 bg-emerald-50 px-3.5 py-2.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-100"
                >
                  <RotateCcw className="lucide" /> Pulihkan hasil automation
                </button>
              )}
              {ready && onExportHtml && (
                <button
                  onClick={onExportHtml}
                  className="flex w-full items-center justify-center gap-1 rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                >
                  <Download className="lucide" /> Unduh dashboard HTML
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ───── KOLOM KANAN (5 KOLOM): KOTAK SYARAT FILE & KETENTUAN ANALYTICS ───── */}
      <div className="lg:col-span-5 panel rounded-xl p-7 space-y-4 text-sm text-slate-500">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="text-base font-bold text-slate-900">Syarat & ketentuan file</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              {isDoi
                ? 'Aturan file untuk membuka visualisasi Dashboard DOI.'
                : 'Aturan file untuk membuka visualisasi Dashboard Penjualan & Forecast.'}
            </p>
          </div>
          <span className="text-xs font-mono font-semibold px-3 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
            ↗ Checklist
          </span>
        </div>

        {!isDoi ? (
          <div className="space-y-3 text-sm">
            <div className="flex items-start gap-3 p-4 rounded-lg bg-slate-50 border border-slate-200">
              <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 font-bold text-xs flex items-center justify-center shrink-0 mt-0.5">
                1
              </span>
              <div>
                <b className="text-slate-900 block">Otomatis dari Script (Tanpa Upload Ulang)</b>
                <span className="text-xs text-slate-500">
                  Jika Anda baru saja menjalankan <b>Rangkuman Penjualan</b>, data bersih seluruh cabang otomatis tampil di sini.
                </span>
              </div>
            </div>
            <div className="flex items-start gap-3 p-4 rounded-lg bg-slate-50 border border-slate-200">
              <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 font-bold text-xs flex items-center justify-center shrink-0 mt-0.5">
                2
              </span>
              <div>
                <b className="text-slate-900 block">Upload Mandiri: Data Mentah Orlan / Zeta</b>
                <span className="text-xs text-slate-500">
                  Menerima file mentah Orlan (<code className="text-slate-700">EntityID_</code> & <code className="text-slate-700">No_SI</code>) maupun Zeta (<code className="text-slate-700">Laporan Rincian Penjualan</code>) beserta <code className="text-blue-700">Supplier.xlsx</code> (atau gunakan Fallback Master Data).
                </span>
              </div>
            </div>
            <div className="flex items-start gap-3 p-4 rounded-lg bg-slate-50 border border-slate-200">
              <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 font-bold text-xs flex items-center justify-center shrink-0 mt-0.5">
                3
              </span>
              <div>
                <b className="text-slate-900 block">Upload Mandiri: CSV / Excel Hasil Rangkuman</b>
                <span className="text-xs text-slate-500">
                  Bisa juga langsung meng-upload file <code className="text-slate-700">.csv</code> bersih atau laporan 5-sheet cabang dari hasil eksekusi sebelumnya.
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-3 text-sm">
            <div className="flex items-start gap-3 p-4 rounded-lg bg-slate-50 border border-slate-200">
              <span className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 font-bold text-xs flex items-center justify-center shrink-0 mt-0.5">
                1
              </span>
              <div>
                <b className="text-slate-900 block">
                  Cara 1: Upload File Jadi <code className="text-emerald-700">Laporan_DOI_*.xlsx</code>
                </b>
                <span className="text-xs text-slate-500">
                  Upload 1 atau beberapa file <code className="text-slate-700">Laporan_DOI_&lt;Cabang&gt;.xlsx</code> sekaligus untuk menggabungkan dan membandingkan multi-cabang.
                </span>
              </div>
            </div>
            <div className="flex items-start gap-3 p-4 rounded-lg bg-slate-50 border border-slate-200">
              <span className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 font-bold text-xs flex items-center justify-center shrink-0 mt-0.5">
                2
              </span>
              <div>
                <b className="text-slate-900 block">Cara 2: Upload File Mentah (Stok & Penjualan)</b>
                <span className="text-xs text-slate-500">
                  Bisa juga drop langsung 1 file <b>Mutasi Stok</b> + minimal 1 file <b>Penjualan</b> + 1 file <b>Daftar Barang</b> (atau aktifkan Fallback Master Data).
                </span>
              </div>
            </div>
            <div className="flex items-start gap-3 p-4 rounded-lg bg-slate-50 border border-slate-200">
              <span className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 font-bold text-xs flex items-center justify-center shrink-0 mt-0.5">
                3
              </span>
              <div>
                <b className="text-slate-900 block">Otomatis dari Script DOI</b>
                <span className="text-xs text-slate-500">
                  Bila Anda baru saja menjalankan script <b>Laporan DOI per Cabang</b>, hasilnya sudah langsung aktif di halaman ini.
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}