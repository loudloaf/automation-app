/* ============================================================================
 * PAGE    : Overview (Home)
 * FILE    : src/pages/OverviewPage.jsx
 * ROUTE   : /
 * ORIGIN  : #view-home + loadOverview() di index.html lama
 * API     : GET /api/overview · GET /api/download/output/:filename
 * STORE   : appDataStore, uiStore (via usePageTitle)
 * UPDATE  : paste THIS file only into an AI
 * ========================================================================== */
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Package, Scale, BarChart3, Folder, RefreshCw, Download, Lightbulb } from 'lucide-react'
import usePageTitle from '../shared/usePageTitle'
import { ENDPOINTS } from '../config/endpoints'
import { useAppDataStore } from '../stores/appDataStore'

export default function OverviewPage() {
  usePageTitle('Overview')
  const navigate = useNavigate()

  /* ───── [HOME-1] LOAD OVERVIEW (lama: loadOverview — disimpan di appDataStore agar tidak hilang saat pindah tab) ───── */
  const data = useAppDataStore((s) => s.overview)
  const loadOverview = useAppDataStore((s) => s.loadOverview)

  useEffect(() => {
    loadOverview()
  }, [loadOverview])

  const suppCnt = (data.master_counts?.supplier_rekap || 0) + (data.master_counts?.supplier_cabang || 0)
  const custProdCnt = (data.master_counts?.customer || 0) + (data.master_counts?.product || 0)

  return (
    <section id="view-home" className="space-y-6">
      {/* ───── [HOME-2] 4 KPI CARDS ───── */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
        <div className="panel rounded-xl p-6">
          <span className="text-sm text-slate-500 font-medium">Modul Otomatisasi</span>
          <div className="text-3xl font-extrabold text-slate-900 mt-2">
            2 <span className="text-sm font-mono font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 ml-1">Aktif</span>
          </div>
          <p className="text-xs text-slate-500 mt-1">Rangkuman Penjualan & Laporan DOI</p>
        </div>
        <div className="panel rounded-xl p-6">
          <span className="text-sm text-slate-500 font-medium">Master Supplier (2 Sheet)</span>
          <div id="home-kpi-supp" className="text-3xl font-extrabold text-blue-700 mt-2 font-mono">
            {suppCnt.toLocaleString('id-ID')}
          </div>
          <p className="text-xs text-slate-500 mt-1">Baris Rekap & Per Cabang Zeta</p>
        </div>
        <div className="panel rounded-xl p-6">
          <span className="text-sm text-slate-500 font-medium">Master Customer & SKU</span>
          <div id="home-kpi-cust" className="text-3xl font-extrabold text-blue-700 mt-2 font-mono">
            {custProdCnt.toLocaleString('id-ID')}
          </div>
          <p className="text-xs text-slate-500 mt-1">Outlet & Daftar Barang tersimpan</p>
        </div>
        <div className="panel rounded-xl p-6">
          <span className="text-sm text-slate-500 font-medium">File Output Server</span>
          <div id="home-kpi-out" className="text-3xl font-extrabold text-amber-700 mt-2 font-mono">
            {data.output_count || 0}
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Tersimpan di folder <code className="text-slate-600">./output</code>
          </p>
        </div>
      </div>

      {/* ───── [HOME-3] QUICK LAUNCH & OUTPUT LIST ───── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Quick Launch Modules */}
        <div className="lg:col-span-7 panel rounded-xl p-7 space-y-4">
          <div>
            <h2 className="text-lg font-bold text-slate-900">Mulai Bekerja (Quick Launch)</h2>
            <p className="text-sm text-slate-500">Pilih workspace otomatisasi atau buka visualisasi analitik interaktif.</p>
          </div>

          <div
            onClick={() => navigate('/automation/rangkuman')}
            className="p-5 rounded-lg bg-slate-50 hover:bg-slate-50 border border-slate-200 hover:border-blue-400 cursor-pointer transition-all flex items-center justify-between gap-5"
          >
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-sm text-slate-900">
                  <Package className="lucide" /> Rangkuman Penjualan per Cabang (Orlan & Zeta)
                </span>
                <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-blue-50 text-blue-700">21 Pemeriksaan Audit</span>
              </div>
              <p className="text-sm text-slate-500 mt-1">
                Pembersihan otomatis, pembuatan ZIP laporan 5-sheet per cabang, dan sinkronisasi Google Sheets Master (Sel 10–11c).
              </p>
            </div>
            <span className="text-blue-700 font-bold text-sm">Buka</span>
          </div>

          <div
            onClick={() => navigate('/automation/doi')}
            className="p-5 rounded-lg bg-slate-50 hover:bg-slate-50 border border-slate-200 hover:border-blue-400 cursor-pointer transition-all flex items-center justify-between gap-5"
          >
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-sm text-slate-900">
                  <Scale className="lucide" /> Laporan DOI per Cabang (Days of Inventory)
                </span>
                <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700">7 Sheet Rumus Hidup</span>
              </div>
              <p className="text-sm text-slate-500 mt-1">
                Olahan Daftar Barang, Mutasi Stok, dan Penjualan multi-bulan menjadi laporan Excel ber-rumus hidup.
              </p>
            </div>
            <span className="text-emerald-700 font-bold text-sm">Buka</span>
          </div>

          <div
            onClick={() => navigate('/analytics')}
            className="p-5 rounded-lg bg-slate-50 hover:bg-slate-50 border border-slate-200 hover:border-blue-400 cursor-pointer transition-all flex items-center justify-between gap-5"
          >
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-sm text-slate-900">
                  <BarChart3 className="lucide" /> Analytics Hub: Penjualan, Forecast 30 Hari & Peta DOI
                </span>
                <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-blue-50 text-blue-700">16 Grafik Plotly</span>
              </div>
              <p className="text-sm text-slate-500 mt-1">Auto-sync langsung dari hasil script atau upload file secara mandiri.</p>
            </div>
            <span className="text-blue-700 font-semibold text-sm">Buka</span>
          </div>
        </div>

        {/* Recent Generated Files in ./output */}
        <div className="lg:col-span-5 panel rounded-xl p-7 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-base font-bold text-slate-900">
                <Folder className="lucide" /> File Hasil Terbaru (<code className="text-sm text-blue-700">./output</code>)
              </h2>
              <button onClick={loadOverview} className="text-sm text-slate-500 hover:text-slate-900">
                <RefreshCw className="lucide" /> Refresh
              </button>
            </div>
            <div id="home-output-list" className="space-y-2 max-h-72 overflow-y-auto pr-1">
              {!data.output_files?.length ? (
                <p className="text-sm text-slate-500 py-8 text-center">Belum ada file di ./output</p>
              ) : (
                data.output_files.map((f) => (
                  <div key={f.name} className="flex items-center justify-between p-3 rounded-lg bg-slate-50 border border-slate-200">
                    <div className="truncate pr-3">
                      <span className="text-sm font-semibold text-slate-900 block truncate">{f.name}</span>
                      <span className="text-xs font-mono text-slate-500">
                        {f.size_kb} KB · {f.mtime}
                      </span>
                    </div>
                    <a
                      href={ENDPOINTS.downloadOutput(f.name)}
                      className="px-3 py-1.5 rounded-xl bg-blue-50 hover:bg-blue-700 text-blue-700 hover:text-white text-sm font-semibold whitespace-nowrap transition-all"
                    >
                      <Download className="lucide" /> Unduh
                    </a>
                  </div>
                ))
              )}
            </div>
          </div>
          <div className="mt-4 p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-500">
            <Lightbulb className="lucide" /> <b>Arsitektur Server Internal:</b> Seluruh pengguna di jaringan kantor dapat menjalankan laporan secara bersamaan tanpa saling mengunci berkat SQLite WAL & FastAPI.
          </div>
        </div>
      </div>
    </section>
  )
}