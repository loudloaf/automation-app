/* ============================================================================
 * PAGE    : Laporan DOI per Cabang
 * FILE    : src/features/automation/scripts/DoiCabangPage.jsx
 * ROUTE   : /automation/doi
 * ORIGIN  : #ws-doi + runDoiPipeline() di index.html lama
 * API     : POST /api/automate/doi-cabang
 * STORE   : automationStore
 * UPDATE  : paste THIS file only into an AI
 * ========================================================================== */
import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  UploadCloud,
  AlertTriangle,
  Play,
  Trash2,
  Check,
  Download,
  Compass,
} from 'lucide-react'
import usePageTitle from '../../../shared/usePageTitle'
import BusyContent from '../../../shared/BusyContent'
import { useAutomationStore } from '../../../stores/automationStore'
import { ENDPOINTS } from '../../../config/endpoints'

export default function DoiCabangPage() {
  usePageTitle('Laporan DOI per Cabang')
  const navigate = useNavigate()
  const inputRef = useRef(null)
  const resultRef = useRef(null)
  const [dragActive, setDragActive] = useState(false)

  const queue = useAutomationStore((s) => s.queues.doi)
  const busyDoi = useAutomationStore((s) => s.busy.doi)
  const statusDoi = useAutomationStore((s) => s.status.doi)
  const errorDoi = useAutomationStore((s) => s.errors.doi)
  const doiUseMasterDaftar = useAutomationStore((s) => s.doiUseMasterDaftar)
  const setDoiUseMasterDaftar = useAutomationStore((s) => s.setDoiUseMasterDaftar)
  const doiParams = useAutomationStore((s) => s.doiParams)
  const setDoiParam = useAutomationStore((s) => s.setDoiParam)
  const doiResult = useAutomationStore((s) => s.doiResult)
  const autoAddFiles = useAutomationStore((s) => s.autoAddFiles)
  const autoRemove = useAutomationStore((s) => s.autoRemove)
  const autoClear = useAutomationStore((s) => s.autoClear)
  const runDoiPipeline = useAutomationStore((s) => s.runDoiPipeline)
  const resetDoiWorkspace = useAutomationStore((s) => s.resetDoiWorkspace)

  const handlePick = () => {
    if (!busyDoi && inputRef.current) inputRef.current.click()
  }

  const handleRun = async () => {
    const ok = await runDoiPipeline()
    if (ok && resultRef.current) {
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 60)
    }
  }

  const summaryRows = doiResult?.summary_rows || []
  const summaryCols = summaryRows.length ? Object.keys(summaryRows[0]) : []
  const fmtCell = (v) =>
    typeof v === 'number'
      ? v.toLocaleString('id-ID', { maximumFractionDigits: 1 })
      : v == null
      ? '-'
      : String(v)

  return (
    <section className="space-y-6">
      <div>
        <button
          onClick={() => navigate('/automation')}
          className="px-4 py-2.5 rounded-lg bg-white border border-slate-300 hover:bg-slate-50 text-sm font-semibold"
        >
          <ArrowLeft className="lucide" />
          Kembali ke Direktori
        </button>
      </div>

      <div id="ws-doi" className="space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          <div className="lg:col-span-7 panel rounded-xl p-7 space-y-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold text-slate-900">Upload file sumber</h2>
                <p className="text-sm text-slate-500 mt-1">
                  Daftar Barang, Mutasi Stok, dan Penjualan dideteksi otomatis.
                </p>
              </div>
              <span className="text-xs font-mono font-semibold px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 whitespace-nowrap">
                ↗ Auto-detect
              </span>
            </div>

            <div className="space-y-3">
              <div
                role="button"
                tabIndex={0}
                aria-label="Seret file Mutasi Stok, Penjualan & Daftar Barang ke sini"
                aria-disabled={busyDoi}
                onClick={handlePick}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    handlePick()
                  }
                }}
                onDragOver={(e) => {
                  e.preventDefault()
                  if (!busyDoi) setDragActive(true)
                }}
                onDragLeave={(e) => {
                  if (!e.currentTarget.contains(e.relatedTarget)) setDragActive(false)
                }}
                onDrop={(e) => {
                  e.preventDefault()
                  setDragActive(false)
                  if (!busyDoi) autoAddFiles('doi', e.dataTransfer.files)
                }}
                className={`flex min-h-[64px] min-w-0 cursor-pointer items-center justify-center gap-3 rounded-lg border-2 border-dashed ${
                  dragActive ? 'border-blue-600 bg-blue-50' : 'border-slate-300 bg-slate-50'
                } px-4 py-3 text-center transition-colors hover:border-blue-400 hover:bg-blue-50 ${
                  busyDoi ? 'pointer-events-none opacity-60' : ''
                }`}
              >
                <UploadCloud className="text-blue-600 lucide" />
                <span className="text-left">
                  <b className="block text-sm text-slate-800">Drop semua file Excel di sini</b>
                  <span className="text-xs text-slate-500">atau klik untuk memilih file (.xlsx, .xls, .xlsm, .csv)</span>
                </span>
              </div>
              <input
                ref={inputRef}
                type="file"
                multiple
                accept=".xlsx,.xls,.xlsm,.csv"
                disabled={busyDoi}
                className="hidden"
                onChange={(e) => {
                  autoAddFiles('doi', e.target.files)
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
                          disabled={busyDoi}
                          aria-label={`Hapus ${f.name} dari antrean`}
                          onClick={() => autoRemove('doi', i)}
                          className="ml-1 text-slate-500 hover:text-rose-700"
                        >
                          &times;
                        </button>
                      </span>
                    ))}
                    <button
                      type="button"
                      disabled={busyDoi}
                      onClick={() => autoClear('doi')}
                      className="ml-auto inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      Kosongkan antrean
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Fallback Toggle for Daftar Barang */}
            <label className="flex items-start gap-4 p-4 rounded-lg bg-emerald-50 border border-emerald-200 cursor-pointer">
              <input
                type="checkbox"
                checked={doiUseMasterDaftar}
                onChange={(e) => setDoiUseMasterDaftar(e.target.checked)}
                className="mt-0.5 rounded text-blue-700"
              />
              <div className="text-sm">
                <span className="font-semibold text-slate-900 block">
                  Opsi Fallback: Gunakan <code className="text-emerald-700">Daftar Barang</code> dari Master Data Hub bila saya tidak ikut meng-upload file Daftar Barang
                </span>
                <span className="text-xs text-slate-500">
                  Jika Anda ikut meng-upload file Daftar Barang, sistem memakai file Anda sekaligus memperbarui tabel Master Produk.
                </span>
              </div>
            </label>
            <div className={`fallback-warn ${doiUseMasterDaftar ? 'is-active' : ''}`} role="alert">
              <AlertTriangle className="lucide" />
              <span>Warning: Master data may not be completely updated or accurate for this execution.</span>
            </div>

            {/* Parameter DOI Expander */}
            <details className="rounded-lg bg-slate-50 border border-slate-200 p-5">
              <summary className="text-sm font-semibold text-slate-700 cursor-pointer">
                Parameter DOI (opsional, default sama dengan Colab)
              </summary>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
                <div>
                  <label className="text-xs text-slate-500 block mb-1">Nama cabang (kosong = otomatis)</label>
                  <input
                    type="text"
                    value={doiParams.cabang}
                    onChange={(e) => setDoiParam('cabang', e.target.value)}
                    placeholder="Otomatis"
                    className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-900"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-500 block mb-1">Hari kerja / bulan</label>
                  <input
                    type="number"
                    value={doiParams.hari_kerja}
                    min={1}
                    max={31}
                    onChange={(e) => setDoiParam('hari_kerja', e.target.value)}
                    className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-900"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-500 block mb-1">Standar DOI default (hari)</label>
                  <input
                    type="number"
                    value={doiParams.standar_doi_default}
                    min={1}
                    onChange={(e) => setDoiParam('standar_doi_default', e.target.value)}
                    className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-900"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-500 block mb-1">Ambang AMS minimum (Rp)</label>
                  <input
                    type="number"
                    value={doiParams.ambang_ams_min}
                    step={1000}
                    onChange={(e) => setDoiParam('ambang_ams_min', e.target.value)}
                    className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-900"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-500 block mb-1">Bulan yang sama dengan tanggal akhir Mutasi Stok</label>
                  <select
                    value={doiParams.bulan_stok_masuk_ams}
                    onChange={(e) => setDoiParam('bulan_stok_masuk_ams', e.target.value)}
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
                    value={doiParams.maks_bulan_ams}
                    min={0}
                    max={24}
                    onChange={(e) => setDoiParam('maks_bulan_ams', e.target.value)}
                    className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-900"
                  />
                </div>
              </div>
            </details>

            {errorDoi && (
              <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800" role="alert">
                {errorDoi}
              </div>
            )}

            {statusDoi.visible && (
              <div
                className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800"
                role="status"
                aria-live="polite"
                aria-busy="true"
              >
                <div className="flex items-center gap-2">
                  <span className="dashboard-spinner" aria-hidden="true" />
                  <span>{statusDoi.msg}</span>
                </div>
                <div
                  className="dashboard-progress-track mt-2"
                  role="progressbar"
                  aria-label="Progres upload"
                  aria-valuenow={statusDoi.determinate ? statusDoi.percent : undefined}
                >
                  <div
                    id="auto-bar-doi"
                    className={`dashboard-progress-bar ${statusDoi.determinate ? 'is-determinate' : ''}`}
                    style={{ width: statusDoi.determinate ? `${statusDoi.percent}%` : '' }}
                  />
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <button
                onClick={handleRun}
                disabled={busyDoi}
                className="sm:col-span-2 py-3.5 px-4 rounded-lg text-white font-bold text-sm transition-all bg-blue-600 hover:bg-blue-700 flex items-center justify-center gap-2"
              >
                <BusyContent busy={busyDoi} label="Menjalankan kalkulasi DOI...">
                  <Play style={{ margin: 0 }} />
                  <span>Proses & buat laporan DOI</span>
                </BusyContent>
              </button>
              <button
                onClick={resetDoiWorkspace}
                disabled={busyDoi}
                className="py-3.5 px-4 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-sm transition-all flex items-center justify-center gap-2"
              >
                <Trash2 style={{ margin: 0 }} />
                <span>Bersihkan File</span>
              </button>
            </div>
          </div>

          <div className="lg:col-span-5 panel rounded-xl p-7 space-y-4 text-sm text-slate-500">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-base font-bold text-slate-900">Syarat file</h3>
                <p className="text-xs text-slate-500 mt-0.5">Pastikan file memenuhi syarat agar tidak error.</p>
              </div>
              <span className="text-xs font-mono font-semibold px-3 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
                ↗ Checklist
              </span>
            </div>
            <div className="flex items-start gap-3 p-4 rounded-lg bg-slate-50 border border-slate-200">
              <span className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 font-bold text-xs flex items-center justify-center shrink-0 mt-0.5">
                1
              </span>
              <div>
                <b className="text-slate-900 block">Tepat 1 file Daftar Barang</b>
                <span className="text-xs text-slate-500">
                  Baris pertama memuat kolom <code className="text-emerald-700">Kode, Konversi, Sat, Nama, Group, Divisi</code>.
                </span>
              </div>
            </div>
            <div className="flex items-start gap-3 p-4 rounded-lg bg-slate-50 border border-slate-200">
              <span className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 font-bold text-xs flex items-center justify-center shrink-0 mt-0.5">
                2
              </span>
              <div>
                <b className="text-slate-900 block">Tepat 1 file Mutasi Stok</b>
                <span className="text-xs text-slate-500">
                  Sel <code className="text-emerald-700">A1</code> memuat teks <code className="text-emerald-700">Mutasi Stok</code> dan baris atas berisi periode awal s/d akhir.
                </span>
              </div>
            </div>
            <div className="flex items-start gap-3 p-4 rounded-lg bg-slate-50 border border-slate-200">
              <span className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 font-bold text-xs flex items-center justify-center shrink-0 mt-0.5">
                3
              </span>
              <div>
                <b className="text-slate-900 block">Minimal 1 file Penjualan</b>
                <span className="text-xs text-slate-500">
                  Sel <code className="text-emerald-700">A1</code> memuat <code className="text-emerald-700">Penjualan</code> &{' '}
                  <code className="text-emerald-700">Customer</code>; boleh upload beberapa bulan sekaligus.
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* DOI Output Box */}
        {doiResult && (
          <div ref={resultRef} id="doiResultBox" className="space-y-5">
            <div className="panel rounded-xl px-5 py-3.5 flex items-center gap-2.5 text-sm font-semibold text-emerald-900 border-emerald-200 bg-emerald-50/60">
              <Check className="text-emerald-600" style={{ margin: 0 }} />
              <span>Selesai. File siap diunduh.</span>
            </div>

            {doiResult.peringatan?.length > 0 && (
              <div className="p-5 rounded-xl bg-amber-50 border border-amber-300 text-sm text-amber-800 space-y-1">
                <b className="block text-amber-800 mb-1">
                  <AlertTriangle className="lucide" /> Periksa dulu sebelum memakai laporan:
                </b>
                {doiResult.peringatan.map((w, i) => (
                  <div key={i}>• {w.replace(/^!!\s*(PERINGATAN:\s*)?/, '')}</div>
                ))}
              </div>
            )}

            {/* 4 KPI Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-5">
              <div className="panel rounded-xl p-5">
                <small className="text-xs font-semibold text-slate-500">Cabang</small>
                <b className="block text-2xl font-extrabold text-slate-900 mt-1">{doiResult.cabang}</b>
                <small className="text-xs text-slate-500">Terdeteksi dari Mutasi Stok</small>
              </div>
              <div className="panel rounded-xl p-5">
                <small className="text-xs font-semibold text-slate-500">Periode AMS</small>
                <b className="block text-2xl font-extrabold text-slate-900 mt-1">{doiResult.ams_months}</b>
                <small className="text-xs text-slate-500">Rata-rata penjualan historis</small>
              </div>
              <div className="panel rounded-xl p-5">
                <small className="text-xs font-semibold text-slate-500">SKU aktif</small>
                <b className="block text-2xl font-extrabold text-slate-900 mt-1">
                  {Number(doiResult.sku_count || 0).toLocaleString('id-ID')}
                </b>
                <small className="text-xs text-slate-500">Masuk ke laporan DOI</small>
              </div>
              <div className="panel rounded-xl p-5">
                <small className="text-xs font-semibold text-slate-500">Workbook</small>
                <b className="block text-2xl font-extrabold text-emerald-700 mt-1">Live formulas</b>
                <small className="text-xs text-slate-500">7 sheet rumus hidup</small>
              </div>
            </div>

            {/* Download & Action Bar */}
            <div className="panel rounded-xl p-6 flex flex-wrap items-center justify-between gap-5">
              <div>
                <h3 className="text-base font-bold text-slate-900">{doiResult.out_name}</h3>
                <p className="text-xs text-slate-500 mt-1">
                  7 sheet: DOI Principal, DOI Principal (2), DOI SKU, Master SKU, Data Stok, Parameter, Catatan.
                </p>
                <p className="text-xs text-slate-500 mt-0.5">Mode bulan: {doiResult.oms_mode}</p>
              </div>
              <div className="flex flex-wrap gap-3">
                <a
                  href={ENDPOINTS.downloadOutput(doiResult.out_name)}
                  className="px-5 py-2.5 rounded-full bg-blue-600 hover:bg-blue-700 text-white text-sm font-bold flex items-center gap-2 shadow-sm"
                >
                  <Download style={{ margin: 0 }} />
                  <span>Unduh Excel</span>
                </a>
                <button
                  onClick={() => navigate('/analytics/doi')}
                  className="px-5 py-2.5 rounded-full bg-slate-100 hover:bg-slate-200 border border-slate-300 text-slate-800 text-sm font-semibold flex items-center gap-2"
                >
                  <Compass style={{ margin: 0 }} />
                  <span>Lihat Visualisasi DOI</span>
                </button>
              </div>
            </div>

            {/* Summary Table per Principal */}
            {summaryRows.length > 0 && (
              <div className="panel rounded-xl p-6 space-y-3">
                <div>
                  <h4 className="text-base font-bold text-slate-900">Ringkasan DOI per Principal</h4>
                  <p className="text-xs text-slate-500">
                    Saldo stok (Rp), AMS, selisih terhadap standar DOI (OMS hanya muncul bila ada bulan berjalan).
                  </p>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm border border-slate-200 rounded-lg overflow-hidden">
                    <thead className="bg-slate-50 border-b border-slate-200 text-left text-xs uppercase text-slate-500">
                      <tr>
                        {summaryCols.map((c) => (
                          <th key={c} className="py-2.5 px-3.5">
                            {c}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {summaryRows.map((r, i) => (
                        <tr key={i} className={r.Principal === 'TOTAL' ? 'font-bold bg-slate-50' : 'hover:bg-slate-50'}>
                          {summaryCols.map((c) => (
                            <td key={c} className="py-2 px-3.5">
                              {fmtCell(r[c])}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            <details open className="panel rounded-xl px-6 py-4">
              <summary className="text-sm font-semibold text-slate-800 cursor-pointer">
                Log pemeriksaan & peringatan (!!)
              </summary>
              <pre className="mt-3 p-4 rounded-lg bg-slate-50 border border-slate-200 text-xs font-mono text-slate-600 whitespace-pre-wrap overflow-x-auto">
                {doiResult.logs || ''}
              </pre>
            </details>
          </div>
        )}
      </div>
    </section>
  )
}