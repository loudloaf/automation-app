/* ============================================================================
 * PAGE    : Rangkuman Penjualan (Orlan & Zeta)
 * FILE    : src/features/automation/scripts/RangkumanPage.jsx
 * ROUTE   : /automation/rangkuman
 * ORIGIN  : #ws-rangkuman + runRangkumanPenjualan() + runRangkumanGSheets() + renderRkReports()
 * API     : POST /api/automate/rangkuman-penjualan · POST /api/automate/rangkuman-gsheets
 * STORE   : automationStore, authStore
 * UPDATE  : paste THIS file only into an AI
 * ========================================================================== */
import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  UploadCloud,
  AlertTriangle,
  Plus,
  Play,
  Trash2,
  Check,
  Download,
  BarChart3,
  CloudUpload,
} from 'lucide-react'
import usePageTitle from '../../../shared/usePageTitle'
import BusyContent from '../../../shared/BusyContent'
import { useAutomationStore } from '../../../stores/automationStore'
import { useAuthStore } from '../../../stores/authStore'
import { ENDPOINTS } from '../../../config/endpoints'

/* ───── [RK-1] REUSABLE DROPZONE + QUEUE SLOT (lama: autoPick, autoDrop, autoRender) ───── */
function DropzoneSlot({ slot, title, hint, compact = false, disabled = false }) {
  const inputRef = useRef(null)
  const [dragActive, setDragActive] = useState(false)
  const queue = useAutomationStore((s) => s.queues[slot])
  const autoAddFiles = useAutomationStore((s) => s.autoAddFiles)
  const autoRemove = useAutomationStore((s) => s.autoRemove)
  const autoClear = useAutomationStore((s) => s.autoClear)

  const handlePick = () => {
    if (!disabled && inputRef.current) inputRef.current.click()
  }

  return (
    <div className="space-y-3">
      <div
        role="button"
        tabIndex={0}
        aria-label={title}
        aria-disabled={disabled}
        onClick={handlePick}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            handlePick()
          }
        }}
        onDragOver={(e) => {
          e.preventDefault()
          if (!disabled) setDragActive(true)
        }}
        onDragLeave={(e) => {
          if (!e.currentTarget.contains(e.relatedTarget)) setDragActive(false)
        }}
        onDrop={(e) => {
          e.preventDefault()
          setDragActive(false)
          if (!disabled) autoAddFiles(slot, e.dataTransfer.files)
        }}
        className={`flex ${compact ? 'min-h-[56px] bg-white py-2' : 'min-h-[64px] bg-slate-50 py-3'} min-w-0 cursor-pointer items-center justify-center gap-3 rounded-lg border-2 border-dashed ${
          dragActive ? 'border-blue-600 bg-blue-50' : 'border-slate-300'
        } px-4 text-center transition-colors hover:border-blue-400 hover:bg-blue-50 ${
          disabled ? 'pointer-events-none opacity-60' : ''
        }`}
      >
        <UploadCloud className="text-blue-600 lucide" />
        <span className="text-left">
          <b className={`block ${compact ? 'text-xs' : 'text-sm'} text-slate-800`}>{title}</b>
          <span className={`${compact ? 'text-[11px]' : 'text-xs'} text-slate-500`}>{hint}</span>
        </span>
      </div>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".xlsx,.xls,.xlsm,.csv"
        disabled={disabled}
        className="hidden"
        onChange={(e) => {
          autoAddFiles(slot, e.target.files)
          e.target.value = ''
        }}
      />
      {queue.length > 0 && (
        <div className={`border-t border-slate-200 ${compact ? 'pt-2 text-xs' : 'pt-3 text-sm'} text-slate-600`}>
          <div className="flex flex-wrap items-center gap-2">
            <b>{queue.length} file dalam antrean:</b>
            {queue.map((f, i) => (
              <span key={`${f.name}-${i}`} className="inline-flex items-center gap-1 rounded-lg bg-slate-100 px-2.5 py-1 text-xs">
                {f.name}
                <button
                  type="button"
                  disabled={disabled}
                  aria-label={`Hapus ${f.name} dari antrean`}
                  onClick={() => autoRemove(slot, i)}
                  className="ml-1 text-slate-500 hover:text-rose-700"
                >
                  &times;
                </button>
              </span>
            ))}
            <button
              type="button"
              disabled={disabled}
              onClick={() => autoClear(slot)}
              className="ml-auto inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Kosongkan antrean
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

/* ───── [RK-2] PER-FILE AUDIT TABLES (lama: renderRkReports) ───── */
function RkPerFileTables({ reports }) {
  if (!reports || !reports.length) return null

  const renderTable = (rows, isRingkas) => {
    if (!rows || !rows.length) return null
    const cols = Object.keys(rows[0])
    const fmt = (c, v) => {
      if (isRingkas && (c === 'Omset' || c === 'Retur') && typeof v === 'number') {
        return Math.round(v).toLocaleString('id-ID')
      }
      return String(v ?? '')
    }
    return (
      <div className="overflow-x-auto rounded-lg border border-slate-200">
        <table className="w-full text-sm">
          <thead className="bg-slate-50">
            <tr className="text-left text-slate-600 border-b border-slate-200">
              {cols.map((c) => (
                <th key={c} className="py-2.5 px-3.5 font-semibold">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, idx) => (
              <tr key={idx} className="border-b border-slate-100 hover:bg-slate-50">
                {cols.map((c) => (
                  <td key={c} className="py-2 px-3.5 align-top">
                    {fmt(c, r[c])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  return (
    <details className="panel rounded-xl px-6 py-4">
      <summary className="text-sm font-semibold text-slate-800 cursor-pointer">
        Tabel ringkasan cabang & 21 log pembersihan ({reports.length} file)
      </summary>
      <div className="mt-4 space-y-6">
        {reports.map((r, idx) => (
          <div key={`${r.file}-${idx}`} className="space-y-3">
            {idx > 0 && <hr className="border-slate-200 pb-3" />}
            <p className="text-sm">
              <b className="font-mono text-blue-700">
                [{r.sumber}] {r.file}
              </b>{' '}
              &mdash; periode <span className="font-mono font-semibold">{r.periode}</span>
            </p>
            {renderTable(r.ringkas, true)}
            {renderTable(r.log, false)}
          </div>
        ))}
      </div>
    </details>
  )
}

/* ───── [RK-3] MAIN PAGE COMPONENT ───── */
export default function RangkumanPage() {
  usePageTitle('Rangkuman Penjualan (Orlan & Zeta)')
  const navigate = useNavigate()
  const resultRef = useRef(null)

  const user = useAuthStore((s) => s.user)
  const busyRk = useAutomationStore((s) => s.busy.rk)
  const busyGs = useAutomationStore((s) => s.busy.gs)
  const statusRk = useAutomationStore((s) => s.status.rk)
  const errorRk = useAutomationStore((s) => s.errors.rk)
  const rkUseMasterSupplier = useAutomationStore((s) => s.rkUseMasterSupplier)
  const setRkUseMasterSupplier = useAutomationStore((s) => s.setRkUseMasterSupplier)
  const rkPaksaSummary = useAutomationStore((s) => s.rkPaksaSummary)
  const setRkPaksaSummary = useAutomationStore((s) => s.setRkPaksaSummary)
  const rkResult = useAutomationStore((s) => s.rkResult)
  const rkGsResult = useAutomationStore((s) => s.rkGsResult)
  const runRangkumanPenjualan = useAutomationStore((s) => s.runRangkumanPenjualan)
  const runRangkumanGSheets = useAutomationStore((s) => s.runRangkumanGSheets)
  const resetRkWorkspace = useAutomationStore((s) => s.resetRkWorkspace)

  const isRkDone = Boolean(rkResult)

  const handleRun = async () => {
    const ok = await runRangkumanPenjualan()
    if (ok && resultRef.current) {
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 60)
    }
  }

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

      <div id="ws-rangkuman" className="space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: 1. Upload Data Utama */}
          <div className="lg:col-span-7 panel rounded-xl p-7 space-y-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold text-slate-900">1. Upload data utama</h2>
                <p className="text-sm text-slate-500 mt-1">
                  <code className="text-slate-700">Supplier.xlsx</code> + data penjualan Orlan / Zeta.
                </p>
              </div>
              <span className="text-xs font-mono font-semibold px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 whitespace-nowrap">
                ↗ Sel 5–7
              </span>
            </div>

            {/* Main File Dropzone */}
            <div className="space-y-4">
              <DropzoneSlot
                slot="rkMain"
                title="Seret file penjualan & Supplier.xlsx ke sini"
                hint="atau klik untuk memilih file (.xlsx, .xls, .xlsm, .csv)"
                disabled={busyRk}
              />
            </div>

            {/* Toggle Fallback to Master Supplier DB */}
            <label className="flex items-start gap-4 p-4 rounded-lg bg-blue-50 border border-blue-200 cursor-pointer">
              <input
                type="checkbox"
                checked={rkUseMasterSupplier}
                onChange={(e) => setRkUseMasterSupplier(e.target.checked)}
                className="mt-0.5 rounded text-blue-700 focus:ring-blue-500"
              />
              <div className="text-sm">
                <span className="font-semibold text-slate-900 block">
                  Opsi Fallback: Gunakan <code className="text-blue-700">Supplier.xlsx</code> dari Master Data Hub bila saya tidak ikut meng-upload file Supplier
                </span>
                <span className="text-xs text-slate-500">
                  Jika Anda tetap meng-upload file <code className="text-slate-600">Supplier.xlsx</code> di atas, sistem otomatis memakai file yang Anda upload sekaligus memperbarui isi Master Data Hub.
                </span>
              </div>
            </label>
            <div className={`fallback-warn ${rkUseMasterSupplier ? 'is-active' : ''}`} role="alert">
              <AlertTriangle className="lucide" />
              <span>Warning: Master data may not be completely updated or accurate for this execution.</span>
            </div>

            {/* Optional Comparison Months (Sel 8) */}
            <details className="rounded-lg bg-slate-50 border border-slate-200 p-5">
              <summary className="text-sm font-semibold text-slate-700 cursor-pointer">
                <Plus className="lucide" /> Opsional (Sel 8): file bulan pembanding
              </summary>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 mt-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-500 mb-1.5">Bulan lalu (Opsional)</label>
                  <DropzoneSlot
                    slot="rkBl"
                    title="Seret file bulan lalu ke sini"
                    hint="atau klik pilih file"
                    compact
                    disabled={busyRk}
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-500 mb-1.5">Tahun lalu (Opsional)</label>
                  <DropzoneSlot
                    slot="rkTl"
                    title="Seret file tahun lalu ke sini"
                    hint="atau klik pilih file"
                    compact
                    disabled={busyRk}
                  />
                </div>
              </div>
            </details>

            {errorRk && (
              <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800" role="alert">
                {errorRk}
              </div>
            )}

            {statusRk.visible && (
              <div
                className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800"
                role="status"
                aria-live="polite"
                aria-busy="true"
              >
                <div className="flex items-center gap-2">
                  <span className="dashboard-spinner" aria-hidden="true" />
                  <span>{statusRk.msg}</span>
                </div>
                <div
                  className="dashboard-progress-track mt-2"
                  role="progressbar"
                  aria-label="Progres upload"
                  aria-valuenow={statusRk.determinate ? statusRk.percent : undefined}
                >
                  <div
                    id="auto-bar-rk"
                    className={`dashboard-progress-bar ${statusRk.determinate ? 'is-determinate' : ''}`}
                    style={{ width: statusRk.determinate ? `${statusRk.percent}%` : '' }}
                  />
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <button
                onClick={handleRun}
                disabled={busyRk}
                className="sm:col-span-2 py-3.5 px-4 rounded-lg text-white font-bold text-sm transition-all bg-blue-600 hover:bg-blue-700 flex items-center justify-center gap-2"
              >
                <BusyContent busy={busyRk} label="Memproses 21 pemeriksaan & merakit ZIP...">
                  <Play style={{ margin: 0 }} />
                  <span>Jalankan pembersihan & buat ZIP (Sel 5–9)</span>
                </BusyContent>
              </button>
              <button
                onClick={resetRkWorkspace}
                disabled={busyRk}
                className="py-3.5 px-4 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-sm transition-all flex items-center justify-center gap-2"
              >
                <Trash2 style={{ margin: 0 }} />
                <span>Bersihkan File</span>
              </button>
            </div>
          </div>

          {/* Right Column: Syarat File (Checklist) */}
          <div className="lg:col-span-5 panel rounded-xl p-7 space-y-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-base font-bold text-slate-900">Syarat file</h3>
                <p className="text-xs text-slate-500 mt-0.5">Aturan deteksi file yang di-upload.</p>
              </div>
              <span className="text-xs font-mono font-semibold px-3 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
                ↗ Checklist
              </span>
            </div>
            <div className="space-y-3 text-sm">
              <div className="flex items-start gap-3 p-4 rounded-lg bg-slate-50 border border-slate-200">
                <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 font-bold text-xs flex items-center justify-center shrink-0 mt-0.5">
                  1
                </span>
                <div>
                  <b className="text-slate-900 block">
                    Wajib 1 file <code className="text-blue-700">Supplier.xlsx</code>
                  </b>
                  <span className="text-xs text-slate-500">
                    Memiliki sheet <b>Rekap</b> dan <b>Per Cabang</b> (atau aktifkan opsi Fallback Master Data).
                  </span>
                </div>
              </div>
              <div className="flex items-start gap-3 p-4 rounded-lg bg-slate-50 border border-slate-200">
                <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 font-bold text-xs flex items-center justify-center shrink-0 mt-0.5">
                  2
                </span>
                <div>
                  <b className="text-slate-900 block">Data ORLAN (bila ada)</b>
                  <span className="text-xs text-slate-500">
                    Kolom <code className="text-slate-700">EntityID_</code> (BB/BF/BK/BL/BM) dan{' '}
                    <code className="text-slate-700">No_SI</code>; satu file dipecah per cabang.
                  </span>
                </div>
              </div>
              <div className="flex items-start gap-3 p-4 rounded-lg bg-slate-50 border border-slate-200">
                <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 font-bold text-xs flex items-center justify-center shrink-0 mt-0.5">
                  3
                </span>
                <div>
                  <b className="text-slate-900 block">Data ZETA (bila ada)</b>
                  <span className="text-xs text-slate-500">
                    Judul <code className="text-slate-700">Laporan Rincian Penjualan</code> dan kode cabang di nama file (NSD, KLK, SGR, MTR, PRY, CARGO).
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ───── [RK-4] CARD 2 (ZIP) & CARD 3 (GSHEETS) — SELALU TAMPIL SEJAK AWAL ───── */}
        <div ref={resultRef} id="rkResultBox" className="space-y-5">
          {isRkDone && (
            <div className="panel rounded-xl px-5 py-3.5 flex items-center justify-between gap-4 border-emerald-200 bg-emerald-50/60">
              <div className="flex items-center gap-2.5 text-sm font-semibold text-emerald-900">
                <Check className="text-emerald-600" style={{ margin: 0 }} />
                <span>Sel 5–9 selesai. ZIP laporan cabang siap diunduh.</span>
              </div>
              <span className="text-xs font-mono text-slate-500">
                Master Supplier: {rkResult.supplier_source}
              </span>
            </div>
          )}

          {/* 2 Side-by-Side Cards: 2. Paket ZIP (Left) & 3. Google Sheets Sync (Right) */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Card 2: Paket ZIP laporan cabang */}
            <div className="lg:col-span-5 panel rounded-xl p-7 space-y-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-base font-bold text-slate-900">2. Paket ZIP laporan cabang</h3>
                  <p className="text-xs text-slate-500 mt-0.5">Laporan 5-sheet, CSV bersih, dan log audit.</p>
                </div>
                <span className="text-xs font-mono font-semibold px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 whitespace-nowrap">
                  ↗ Sel 9
                </span>
              </div>
              {isRkDone ? (
                <div className="space-y-2.5 pt-1">
                  {(rkResult.zip_files || []).map((z) => (
                    <a
                      key={z}
                      href={ENDPOINTS.downloadOutput(z)}
                      className="w-full py-3 px-4 rounded-full bg-blue-600 hover:bg-blue-700 text-white text-sm font-bold flex items-center justify-center gap-2 shadow-sm transition-all"
                    >
                      <Download style={{ margin: 0 }} />
                      <span>{z}</span>
                    </a>
                  ))}
                  <button
                    onClick={() => navigate('/analytics/penjualan')}
                    className="w-full py-3 px-4 rounded-full bg-slate-100 hover:bg-slate-200 border border-slate-300 text-slate-800 text-sm font-semibold flex items-center justify-center gap-2 transition-all"
                  >
                    <BarChart3 style={{ margin: 0 }} />
                    <span>Buka Visualisasi Penjualan</span>
                  </button>
                </div>
              ) : (
                <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-500">
                  Jalankan langkah <b>1. Upload data utama (Sel 5–9)</b> di atas terlebih dahulu untuk menghasilkan paket ZIP laporan per cabang.
                </div>
              )}
            </div>

            {/* Card 3: Google Sheets Master & Summary Target (Selalu tampil, tombol aktif setelah Sel 5-9 selesai) */}
            <div className="lg:col-span-7 panel rounded-xl p-7 space-y-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-base font-bold text-slate-900">3. Google Sheets Master & Summary Target</h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Terhubung sebagai <b className="text-slate-700">{user?.email}</b>
                  </p>
                </div>
                <span className="text-xs font-mono font-semibold px-3 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200 whitespace-nowrap">
                  ↗ Sel 10–11c
                </span>
              </div>
              <label className="flex items-center gap-2.5 text-sm text-slate-700 pt-1 cursor-pointer">
                <input
                  type="checkbox"
                  checked={rkPaksaSummary}
                  onChange={(e) => setRkPaksaSummary(e.target.checked)}
                  disabled={!isRkDone || busyGs}
                  className="rounded border-slate-300 text-blue-600 disabled:opacity-50"
                />
                <span className={!isRkDone ? 'text-slate-400' : ''}>
                  Paksa timpa Summary Target bila upload bulan lama
                </span>
              </label>
              <button
                onClick={runRangkumanGSheets}
                disabled={!isRkDone || busyGs}
                title={!isRkDone ? 'Jalankan pembersihan & buat ZIP (Sel 5–9) terlebih dahulu' : ''}
                className="w-full py-3 px-4 rounded-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-200 disabled:text-slate-500 disabled:cursor-not-allowed text-white font-bold text-sm transition-all flex items-center justify-center gap-2 shadow-sm"
              >
                <BusyContent busy={busyGs} label="Menghubungkan ke Google Sheets & menjalankan Sel 10–11c...">
                  <CloudUpload style={{ margin: 0 }} />
                  <span>
                    {isRkDone
                      ? 'Sinkronkan ke Google Sheets & buat Summary Target'
                      : 'Sinkronkan ke Google Sheets (Jalankan Sel 5–9 dulu)'}
                  </span>
                </BusyContent>
              </button>
              {rkGsResult?.summary_excel_name && (
                <div className="pt-1">
                  <a
                    href={ENDPOINTS.downloadOutput(rkGsResult.summary_excel_name)}
                    className="w-full py-2.5 px-4 rounded-full bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 text-emerald-800 text-sm font-bold flex items-center justify-center gap-2 transition-all"
                  >
                    <Download style={{ margin: 0 }} />
                    <span>Unduh {rkGsResult.summary_excel_name} (Sel 11b)</span>
                  </a>
                </div>
              )}
            </div>
          </div>

          {/* Expanders for Logs & Tables */}
          {rkGsResult?.logs && (
            <details open className="panel rounded-xl px-6 py-4">
              <summary className="text-sm font-semibold text-slate-800 cursor-pointer">
                Log sinkronisasi Google Sheets (Sel 10, 10b, 11, 11c)
              </summary>
              <pre className="mt-3 p-4 rounded-lg bg-slate-50 border border-slate-200 text-xs font-mono text-slate-600 whitespace-pre-wrap overflow-x-auto">
                {rkGsResult.logs}
              </pre>
            </details>
          )}

          {isRkDone && (
            <>
              <RkPerFileTables reports={rkResult.per_file_reports} />

              <details className="panel rounded-xl px-6 py-4">
                <summary className="text-sm font-semibold text-slate-800 cursor-pointer">
                  Console log Sel 7–9
                </summary>
                <pre className="mt-3 p-4 rounded-lg bg-slate-50 border border-slate-200 text-xs font-mono text-slate-600 whitespace-pre-wrap overflow-x-auto">
                  {rkResult.logs || ''}
                </pre>
              </details>
            </>
          )}
        </div>
      </div>
    </section>
  )
}