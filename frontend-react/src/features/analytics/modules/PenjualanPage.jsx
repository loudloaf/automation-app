/* ============================================================================
 * PAGE    : Dashboard Penjualan & Forecast 30 Hari
 * FILE    : src/features/analytics/modules/PenjualanPage.jsx
 * ROUTE   : /analytics/penjualan
 * ORIGIN  : #dash-view-penjualan + paintSalesDashboard() di index.html lama
 * API     : GET /api/dashboard/penjualan/data
 * STORE   : dashboardStore
 * UPDATE  : paste THIS file only into an AI
 * ========================================================================== */
import { useEffect, useState, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Upload, Lightbulb } from 'lucide-react'
import usePageTitle from '../../../shared/usePageTitle'
import { useDashboardStore } from '../../../stores/dashboardStore'
import DashboardToolbar from '../shared/DashboardToolbar'

export default function PenjualanPage() {
  usePageTitle('Dashboard Penjualan & Forecast 30 Hari')
  const navigate = useNavigate()
  const payload = useDashboardStore((s) => s.payloads.sales)
  const loadSalesData = useDashboardStore((s) => s.loadSalesData)

  const [branchFilter, setBranchFilter] = useState(() => payload?.selected_cabang || payload?.all_cabang || [])
  const [sourceFilter, setSourceFilter] = useState(() => payload?.selected_sumber || payload?.all_sumber || [])
  const [branchMenuOpen, setBranchMenuOpen] = useState(false)
  const [sourceMenuOpen, setSourceMenuOpen] = useState(false)
  const [branchSearch, setBranchSearch] = useState('')
  const [sourceSearch, setSourceSearch] = useState('')

  const chartsRef = useRef({})

  const paintCharts = useCallback((chartsJson) => {
    const Plotly = window.Plotly
    if (!chartsJson || !Plotly) return
    const config = { displaylogo: false, responsive: true }
    const applyTheme = (fig) => ({
      ...fig,
      layout: {
        ...(fig.layout || {}),
        template: {},
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { ...(fig.layout?.font || {}), color: '#334155', family: 'IBM Plex Sans, sans-serif' },
      },
    })

    const map = [
      ['chart-sales-tren', chartsJson.tren],
      ['chart-sales-retur', chartsJson.retur],
      ['chart-sales-cabang', chartsJson.cabang],
      ['chart-sales-principal', chartsJson.principal],
      ['chart-sales-hari', chartsJson.hari],
      ['chart-sales-customer', chartsJson.customer],
      ['chart-sales-pareto', chartsJson.pareto],
    ]

    requestAnimationFrame(() => {
      map.forEach(([id, fig]) => {
        const el = document.getElementById(id)
        if (el && fig) {
          const styled = applyTheme(fig)
          Plotly.react(el, styled.data, styled.layout, config)
          chartsRef.current[id] = el
        }
      })
    })
  }, [])

  const refreshData = useCallback(async (customQuery = '') => {
    const data = await loadSalesData(customQuery)
    if (data?.ready && data.selected_cabang) {
      setBranchFilter(data.selected_cabang)
      setSourceFilter(data.selected_sumber)
      paintCharts(data.charts)
    }
  }, [loadSalesData, paintCharts])

  useEffect(() => {
    if (payload?.ready && payload.charts) {
      paintCharts(payload.charts)
    } else {
      refreshData()
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleApplyFilters = () => {
    const q = new URLSearchParams()
    if (branchFilter.length) q.set('cabang', branchFilter.join(','))
    if (sourceFilter.length) q.set('sumber', sourceFilter.join(','))
    refreshData(q.toString())
  }

  const handleResetFilters = () => {
    if (!payload) return
    setBranchFilter(payload.all_cabang || [])
    setSourceFilter(payload.all_sumber || [])
    refreshData('')
  }

  const handleDownloadHtml = () => {
    if (!payload || !payload.charts) return
    useDashboardStore.getState().downloadDashboardHtml?.('sales')
  }

  const toggleSelectAll = (type, selectAll) => {
    if (type === 'branch') {
      setBranchFilter(selectAll ? payload.all_cabang || [] : [])
    } else {
      setSourceFilter(selectAll ? payload.all_sumber || [] : [])
    }
  }

  const toggleOption = (type, val) => {
    if (type === 'branch') {
      setBranchFilter((prev) => (prev.includes(val) ? prev.filter((x) => x !== val) : [...prev, val]))
    } else {
      setSourceFilter((prev) => (prev.includes(val) ? prev.filter((x) => x !== val) : [...prev, val]))
    }
  }

  const ready = Boolean(payload?.ready)
  const kpi = payload?.kpi || {}
  const insights = payload?.insights || []
  const allBranches = payload?.all_cabang || []
  const allSources = payload?.all_sumber || []

  const filteredBranches = allBranches.filter((b) => b.toLowerCase().includes(branchSearch.toLowerCase()))
  const filteredSources = allSources.filter((s) => s.toLowerCase().includes(sourceSearch.toLowerCase()))

  return (
    <section className="space-y-6">
      {/* Tombol Kembali ke Direktori (#back-dashboard) */}
      <div id="back-dashboard">
        <button
          onClick={() => navigate('/analytics')}
          className="px-4 py-2.5 rounded-lg bg-white border border-slate-300 hover:bg-slate-50 text-sm font-semibold"
        >
          <ArrowLeft className="lucide" />
          Kembali ke Direktori
        </button>
      </div>

      <DashboardToolbar kind="sales" onUploadSuccess={() => refreshData('')} onExportHtml={handleDownloadHtml} />

      {!ready ? (
        <div id="salesDashEmpty" className="panel rounded-xl p-12 text-center text-slate-500 text-sm">
          Belum ada data penjualan aktif di memori. Jalankan <b>Rangkuman Penjualan</b> terlebih dahulu atau seret file penjualan ke kotak <b><Upload style={{ display: 'inline', width: 16, height: 16 }} /> Sumber Data Visualisasi Penjualan</b> di atas.
        </div>
      ) : (
        <div id="salesDashContent" className="space-y-6">
          {/* Filters Panel */}
          <div className="panel rounded-xl p-5">
            <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
              <div>
                <h4 className="text-sm font-bold text-slate-900">Filter Penjualan</h4>
                <p className="text-xs text-slate-500 mt-1">Pilih satu atau beberapa cabang dan sumber.</p>
              </div>
              <div className="flex gap-2">
                <button onClick={handleApplyFilters} className="px-3 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold">
                  Terapkan
                </button>
                <button onClick={handleResetFilters} className="px-3 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-semibold">
                  Reset filter
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <label className="filter-field">
                Cabang
                <details
                  open={branchMenuOpen}
                  onToggle={(e) => setBranchMenuOpen(e.target.open)}
                  className="filter-control"
                >
                  <summary className="filter-trigger">
                    {branchFilter.length === allBranches.length && allBranches.length > 0
                      ? `Semua (${allBranches.length})`
                      : branchFilter.length > 0
                      ? `${branchFilter.length} dipilih`
                      : 'Tidak ada dipilih'}
                  </summary>
                  <div className="filter-options">
                    <input
                      type="search"
                      value={branchSearch}
                      onChange={(e) => setBranchSearch(e.target.value)}
                      placeholder="Cari opsi..."
                      aria-label="Cari opsi cabang"
                    />
                    <div className="filter-menu-actions">
                      <button type="button" onClick={() => toggleSelectAll('branch', true)}>Pilih semua</button>
                      <button type="button" onClick={() => toggleSelectAll('branch', false)}>Hapus pilihan</button>
                    </div>
                    <div className="pt-1">
                      {filteredBranches.map((b) => (
                        <label key={b} className="filter-option" data-filter-row={b}>
                          <input
                            type="checkbox"
                            checked={branchFilter.includes(b)}
                            onChange={() => toggleOption('branch', b)}
                          />
                          <span className="min-w-0 break-words">{b}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                </details>
              </label>

              <label className="filter-field">
                Sumber
                <details
                  open={sourceMenuOpen}
                  onToggle={(e) => setSourceMenuOpen(e.target.open)}
                  className="filter-control"
                >
                  <summary className="filter-trigger">
                    {sourceFilter.length === allSources.length && allSources.length > 0
                      ? `Semua (${allSources.length})`
                      : sourceFilter.length > 0
                      ? `${sourceFilter.length} dipilih`
                      : 'Tidak ada dipilih'}
                  </summary>
                  <div className="filter-options">
                    <input
                      type="search"
                      value={sourceSearch}
                      onChange={(e) => setSourceSearch(e.target.value)}
                      placeholder="Cari opsi..."
                      aria-label="Cari opsi sumber"
                    />
                    <div className="filter-menu-actions">
                      <button type="button" onClick={() => toggleSelectAll('source', true)}>Pilih semua</button>
                      <button type="button" onClick={() => toggleSelectAll('source', false)}>Hapus pilihan</button>
                    </div>
                    <div className="pt-1">
                      {filteredSources.map((s) => (
                        <label key={s} className="filter-option" data-filter-row={s}>
                          <input
                            type="checkbox"
                            checked={sourceFilter.includes(s)}
                            onChange={() => toggleOption('source', s)}
                          />
                          <span className="min-w-0 break-words">{s}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                </details>
              </label>
            </div>
          </div>

          {/* KPI Grid */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-5" id="salesKpiGrid">
            <div className="panel rounded-xl p-6">
              <small className="text-sm text-slate-500">Omset Bersih</small>
              <b className="block text-2xl font-extrabold text-slate-900 mt-1">{kpi.omset}</b>
              <small className="text-xs text-emerald-700">
                {kpi.delta || ''} ({kpi.d7_vs_p7})
              </small>
            </div>
            <div className="panel rounded-xl p-6">
              <small className="text-sm text-slate-500">Faktur & Periode</small>
              <b className="block text-2xl font-extrabold text-slate-900 mt-1">{kpi.faktur}</b>
              <small className="text-xs text-slate-500">{kpi.periode}</small>
            </div>
            <div className="panel rounded-xl p-6">
              <small className="text-sm text-slate-500">Outlet Aktif</small>
              <b className="block text-2xl font-extrabold text-slate-900 mt-1">{kpi.outlet}</b>
              <small className="text-xs text-slate-500">
                Rata-rata {kpi.rata} / hari ({kpi.hari} HK)
              </small>
            </div>
            <div className="panel rounded-xl p-6">
              <small className="text-sm text-slate-500">Proyeksi 30 Hari Ke Depan</small>
              <b className="block text-2xl font-extrabold text-blue-700 mt-1">{kpi.forecast_30d}</b>
              <small className="text-xs text-slate-500">{kpi.forecast_range}</small>
            </div>
          </div>

          {/* Insights Card */}
          <div className="panel rounded-xl p-6">
            <h4 className="text-sm font-bold text-slate-900 mb-2">
              <Lightbulb className="lucide" /> AI Insight & Temuan Otomatis
            </h4>
            <ul id="salesInsightsList" className="list-disc pl-5 space-y-1 text-sm text-slate-600">
              {insights.map((item, idx) => (
                <li key={idx} dangerouslySetInnerHTML={{ __html: item }} />
              ))}
            </ul>
          </div>

          {/* Charts Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            <div className="lg:col-span-2 panel rounded-xl p-6">
              <h4 className="text-sm font-bold text-slate-900">Tren Omset Harian & Forecast 30 Hari</h4>
              <div id="chart-sales-tren" className="w-full h-[380px]" />
            </div>
            <div className="panel rounded-xl p-6">
              <h4 className="text-sm font-bold text-slate-900">Rasio Retur vs Penjualan</h4>
              <div id="chart-sales-retur" className="w-full h-[280px]" />
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            <div className="panel rounded-xl p-6">
              <h4 className="text-sm font-bold text-slate-900">Omset per Cabang</h4>
              <div id="chart-sales-cabang" className="w-full h-[360px]" />
            </div>
            <div className="panel rounded-xl p-6">
              <h4 className="text-sm font-bold text-slate-900">Top 10 Principal</h4>
              <div id="chart-sales-principal" className="w-full h-[380px]" />
            </div>
            <div className="panel rounded-xl p-6">
              <h4 className="text-sm font-bold text-slate-900">Pola Hari Kerja</h4>
              <div id="chart-sales-hari" className="w-full h-[380px]" />
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <div className="panel rounded-xl p-6">
              <h4 className="text-sm font-bold text-slate-900">Top 10 Customer</h4>
              <div id="chart-sales-customer" className="w-full h-[400px]" />
            </div>
            <div className="panel rounded-xl p-6">
              <h4 className="text-sm font-bold text-slate-900">Konsentrasi Outlet (Pareto)</h4>
              <div id="chart-sales-pareto" className="w-full h-[400px]" />
            </div>
          </div>
        </div>
      )}
    </section>
  )
}