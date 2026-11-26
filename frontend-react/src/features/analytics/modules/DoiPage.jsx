/* ============================================================================
 * PAGE    : Dashboard DOI (Stok vs Omset)
 * FILE    : src/features/analytics/modules/DoiPage.jsx
 * ROUTE   : /analytics/doi
 * ORIGIN  : #dash-view-doi + paintDoiDashboard() di index.html lama
 * API     : GET /api/dashboard/doi/data · GET /api/dashboard/doi/export.csv
 * STORE   : dashboardStore
 * UPDATE  : paste THIS file only into an AI
 * ========================================================================== */
import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Upload, Lightbulb, Download } from 'lucide-react'
import usePageTitle from '../../../shared/usePageTitle'
import { useDashboardStore } from '../../../stores/dashboardStore'
import DashboardToolbar from '../shared/DashboardToolbar'
import { ENDPOINTS } from '../../../config/endpoints'

export default function DoiPage() {
  usePageTitle('Dashboard DOI (Stok vs Omset)')
  const navigate = useNavigate()
  const payload = useDashboardStore((s) => s.payloads.doi)
  const loadDoiData = useDashboardStore((s) => s.loadDoiData)

  const [activeTab, setActiveTab] = useState('summary')
  const [branchFilter, setBranchFilter] = useState(() => payload?.selected_cabang || payload?.all_cabang || [])
  const [principalFilter, setPrincipalFilter] = useState(() => payload?.selected_principal || payload?.all_principal || [])
  const [statusFilter, setStatusFilter] = useState(() => payload?.selected_status || payload?.all_status || [])
  const [searchQuery, setSearchQuery] = useState(() => payload?.selected_cari || '')
  const [perBranch, setPerBranch] = useState(() => Boolean(payload?.selected_per_cabang))
  const [sortBy, setSortBy] = useState(() => payload?.selected_sort_by || 'lebih_kurang')
  const [sortDesc, setSortDesc] = useState(() => payload?.selected_sort_desc !== false)

  const [branchMenuOpen, setBranchMenuOpen] = useState(false)
  const [principalMenuOpen, setPrincipalMenuOpen] = useState(false)
  const [statusMenuOpen, setStatusMenuOpen] = useState(false)
  const [branchSearch, setBranchSearch] = useState('')
  const [principalSearch, setPrincipalSearch] = useState('')
  const [statusSearch, setStatusSearch] = useState('')

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
      ['chart-doi-std', chartsJson.doi_std],
      ['chart-doi-lk', chartsJson.lebih_kurang],
      ['chart-doi-porsi', chartsJson.porsi],
      ['chart-doi-bucket', chartsJson.bucket],
      ['chart-doi-scatter', chartsJson.scatter],
      ['chart-doi-lebih', chartsJson.top_lebih],
      ['chart-doi-kritis', chartsJson.top_kritis],
      ['chart-doi-tren', chartsJson.tren],
      ['chart-doi-gudang', chartsJson.gudang],
    ]

    requestAnimationFrame(() => {
      map.forEach(([id, fig]) => {
        const el = document.getElementById(id)
        if (el && fig) {
          const styled = applyTheme(fig)
          Plotly.react(el, styled.data, styled.layout, config)
        }
      })
    })
  }, [])

  const refreshData = useCallback(async (customQuery = '') => {
    const data = await loadDoiData(customQuery)
    if (data?.ready && data.selected_cabang) {
      setBranchFilter(data.selected_cabang)
      setPrincipalFilter(data.selected_principal)
      setStatusFilter(data.selected_status)
      setPerBranch(Boolean(data.selected_per_cabang))
      setSearchQuery(data.selected_cari || '')
      setSortBy(data.selected_sort_by || 'lebih_kurang')
      setSortDesc(data.selected_sort_desc !== false)
      paintCharts(data.charts)
    }
  }, [loadDoiData, paintCharts])

  useEffect(() => {
    if (payload?.ready && payload.charts) {
      paintCharts(payload.charts)
    } else {
      refreshData()
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const buildQueryString = () => {
    const q = new URLSearchParams()
    if (branchFilter.length) q.set('cabang', branchFilter.join(','))
    if (principalFilter.length) q.set('principal', principalFilter.join(','))
    if (statusFilter.length) q.set('status', statusFilter.join(','))
    if (searchQuery.trim()) q.set('cari', searchQuery.trim())
    q.set('per_cabang', perBranch)
    q.set('sort_by', sortBy)
    q.set('sort_desc', sortDesc)
    return q.toString()
  }

  const handleApplyFilters = () => {
    refreshData(buildQueryString())
  }

  const handleResetFilters = () => {
    if (!payload) return
    setBranchFilter(payload.all_cabang || [])
    setPrincipalFilter(payload.all_principal || [])
    setStatusFilter(payload.all_status || [])
    setSearchQuery('')
    setPerBranch(false)
    setSortBy('lebih_kurang')
    setSortDesc(true)
    refreshData('')
  }

  const handleDownloadHtml = () => {
    if (!payload || !payload.charts) return
    useDashboardStore.getState().downloadDashboardHtml?.('doi')
  }

  const toggleSelectAll = (type, selectAll) => {
    if (type === 'branch') setBranchFilter(selectAll ? payload.all_cabang || [] : [])
    else if (type === 'principal') setPrincipalFilter(selectAll ? payload.all_principal || [] : [])
    else setStatusFilter(selectAll ? payload.all_status || [] : [])
  }

  const toggleOption = (type, val) => {
    if (type === 'branch') {
      setBranchFilter((prev) => (prev.includes(val) ? prev.filter((x) => x !== val) : [...prev, val]))
    } else if (type === 'principal') {
      setPrincipalFilter((prev) => (prev.includes(val) ? prev.filter((x) => x !== val) : [...prev, val]))
    } else {
      setStatusFilter((prev) => (prev.includes(val) ? prev.filter((x) => x !== val) : [...prev, val]))
    }
  }

  const switchTab = (tab) => {
    setActiveTab(tab)
    if (tab === 'map' || tab === 'trends') {
      const ids = tab === 'map' ? ['chart-doi-scatter', 'chart-doi-lebih', 'chart-doi-kritis'] : ['chart-doi-tren', 'chart-doi-gudang']
      requestAnimationFrame(() => {
        ids.forEach((id) => {
          const el = document.getElementById(id)
          if (el && el._fullLayout && window.Plotly) window.Plotly.Plots.resize(el)
        })
      })
    }
  }

  const ready = Boolean(payload?.ready)
  const kpi = payload?.kpi || {}
  const insights = payload?.insights || []
  const allBranches = payload?.all_cabang || []
  const allPrincipals = payload?.all_principal || []
  const allStatuses = payload?.all_status || []
  const skuTable = payload?.sku_table || []
  const skuTotal = payload?.sku_total || skuTable.length

  const filteredBranches = allBranches.filter((b) => b.toLowerCase().includes(branchSearch.toLowerCase()))
  const filteredPrincipals = allPrincipals.filter((p) => p.toLowerCase().includes(principalSearch.toLowerCase()))
  const filteredStatuses = allStatuses.filter((s) => s.toLowerCase().includes(statusSearch.toLowerCase()))

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

      <DashboardToolbar kind="doi" onUploadSuccess={() => refreshData('')} onExportHtml={handleDownloadHtml} />

      {!ready ? (
        <div id="doiDashEmpty" className="panel rounded-xl p-12 text-center text-slate-500 text-sm">
          Belum ada laporan DOI aktif. Jalankan <b>Laporan DOI per Cabang</b> terlebih dahulu atau seret file ke kotak <b><Upload style={{ display: 'inline', width: 16, height: 16 }} /> Sumber Data Visualisasi DOI</b> di atas.
        </div>
      ) : (
        <div id="doiDashContent" className="space-y-6">
          {/* KPI Grid */}
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-5" id="doiKpiGrid">
            <div className="panel min-w-0 rounded-xl p-5">
              <small className="text-sm text-slate-500">Nilai stok</small>
              <b className="mt-1 block break-words text-2xl font-extrabold text-slate-900">{kpi.saldo}</b>
              <small className="text-xs text-slate-500">Nilai jual, per {kpi.stock_date || 'tanggal tiap laporan'}</small>
            </div>
            <div className="panel min-w-0 rounded-xl p-5">
              <small className="text-sm text-slate-500">Omset per bulan (AMS)</small>
              <b className="mt-1 block break-words text-2xl font-extrabold text-slate-900">{kpi.ams}</b>
              <small className="text-xs text-slate-500">{kpi.ams_period || 'Rata-rata omset bulanan'}</small>
            </div>
            <div className="panel min-w-0 rounded-xl p-5">
              <small className="text-sm text-slate-500">DOI total</small>
              <b className="mt-1 block break-words text-2xl font-extrabold text-emerald-700">{kpi.doi}</b>
              <small className="text-xs text-slate-500">{kpi.std_doi || 'Standar DOI tidak tersedia'}</small>
            </div>
            <div className="panel min-w-0 rounded-xl p-5">
              <small className="text-sm text-slate-500">SKU aktif</small>
              <b className="mt-1 block break-words text-2xl font-extrabold text-slate-900">{kpi.n_sku}</b>
              <small className="text-xs text-slate-500">
                {kpi.n_mati} stok mati · {kpi.n_tanpa_harga ?? '-'} tanpa harga
              </small>
            </div>
            <div className="panel min-w-0 rounded-xl p-5">
              <small className="text-sm text-slate-500">Hampir habis / kosong</small>
              <b className="mt-1 block break-words text-2xl font-extrabold text-rose-600">{kpi.kritis_kosong}</b>
              <small className="text-xs text-slate-500">Omset {kpi.ams_terancam}/bln terancam</small>
            </div>
            <div className="panel min-w-0 rounded-xl p-5">
              <small className="text-sm text-slate-500">Stok mati</small>
              <b className="mt-1 block break-words text-2xl font-extrabold text-slate-900">{kpi.n_mati}</b>
              <small className="text-xs text-slate-500">Ada stok tanpa penjualan di bulan data</small>
            </div>
          </div>

          {/* Filter DOI */}
          <div className="panel rounded-xl p-5">
            <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
              <div>
                <h4 className="text-sm font-bold text-slate-900">Filter DOI</h4>
                <p className="text-xs text-slate-500 mt-1">Filter cabang, principal, status SKU, atau cari nama/kode.</p>
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

            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
              <label className="filter-field">
                Cabang
                <details open={branchMenuOpen} onToggle={(e) => setBranchMenuOpen(e.target.open)} className="filter-control">
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
                          <input type="checkbox" checked={branchFilter.includes(b)} onChange={() => toggleOption('branch', b)} />
                          <span className="min-w-0 break-words">{b}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                </details>
              </label>

              <label className="filter-field">
                Principal
                <details open={principalMenuOpen} onToggle={(e) => setPrincipalMenuOpen(e.target.open)} className="filter-control">
                  <summary className="filter-trigger">
                    {principalFilter.length === allPrincipals.length && allPrincipals.length > 0
                      ? `Semua (${allPrincipals.length})`
                      : principalFilter.length > 0
                      ? `${principalFilter.length} dipilih`
                      : 'Tidak ada dipilih'}
                  </summary>
                  <div className="filter-options">
                    <input
                      type="search"
                      value={principalSearch}
                      onChange={(e) => setPrincipalSearch(e.target.value)}
                      placeholder="Cari opsi..."
                      aria-label="Cari opsi principal"
                    />
                    <div className="filter-menu-actions">
                      <button type="button" onClick={() => toggleSelectAll('principal', true)}>Pilih semua</button>
                      <button type="button" onClick={() => toggleSelectAll('principal', false)}>Hapus pilihan</button>
                    </div>
                    <div className="pt-1">
                      {filteredPrincipals.map((p) => (
                        <label key={p} className="filter-option" data-filter-row={p}>
                          <input type="checkbox" checked={principalFilter.includes(p)} onChange={() => toggleOption('principal', p)} />
                          <span className="min-w-0 break-words">{p}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                </details>
              </label>

              <label className="filter-field">
                Status SKU
                <details open={statusMenuOpen} onToggle={(e) => setStatusMenuOpen(e.target.open)} className="filter-control">
                  <summary className="filter-trigger">
                    {statusFilter.length === allStatuses.length && allStatuses.length > 0
                      ? `Semua (${allStatuses.length})`
                      : statusFilter.length > 0
                      ? `${statusFilter.length} dipilih`
                      : 'Tidak ada dipilih'}
                  </summary>
                  <div className="filter-options">
                    <input
                      type="search"
                      value={statusSearch}
                      onChange={(e) => setStatusSearch(e.target.value)}
                      placeholder="Cari opsi..."
                      aria-label="Cari opsi status"
                    />
                    <div className="filter-menu-actions">
                      <button type="button" onClick={() => toggleSelectAll('status', true)}>Pilih semua</button>
                      <button type="button" onClick={() => toggleSelectAll('status', false)}>Hapus pilihan</button>
                    </div>
                    <div className="pt-1">
                      {filteredStatuses.map((st) => (
                        <label key={st} className="filter-option" data-filter-row={st}>
                          <input type="checkbox" checked={statusFilter.includes(st)} onChange={() => toggleOption('status', st)} />
                          <span className="min-w-0 break-words">{st}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                </details>
              </label>

              <div className="space-y-3">
                <label className="text-xs font-semibold text-slate-600 block">
                  Cari SKU / kode
                  <input
                    type="search"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Ketik nama atau kode SKU"
                    className="mt-1 block w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm"
                  />
                </label>
                <label className="flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={perBranch}
                    onChange={(e) => setPerBranch(e.target.checked)}
                    className="rounded border-slate-300 text-blue-600"
                  />
                  Pisahkan per cabang
                </label>
              </div>
            </div>
          </div>

          {/* Temuan Otomatis DOI */}
          <div className="panel rounded-xl p-6">
            <h4 className="text-sm font-bold text-slate-900 mb-2">
              <Lightbulb className="lucide" /> Temuan Otomatis DOI
            </h4>
            <ul id="doiInsightsList" className="list-disc pl-5 space-y-1 text-sm text-slate-600">
              {insights.map((item, idx) => (
                <li key={idx} dangerouslySetInnerHTML={{ __html: item }} />
              ))}
            </ul>
          </div>

          {/* 4 Tabs */}
          <div className="flex flex-wrap gap-2" role="tablist" aria-label="Halaman visualisasi DOI">
            <button
              onClick={() => switchTab('summary')}
              className={`px-3.5 py-2 rounded-lg text-sm font-semibold ${activeTab === 'summary' ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-700'}`}
              aria-selected={activeTab === 'summary'}
            >
              Ringkasan principal
            </button>
            <button
              onClick={() => switchTab('map')}
              className={`px-3.5 py-2 rounded-lg text-sm font-semibold ${activeTab === 'map' ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-700'}`}
              aria-selected={activeTab === 'map'}
            >
              Peta SKU
            </button>
            <button
              onClick={() => switchTab('trends')}
              className={`px-3.5 py-2 rounded-lg text-sm font-semibold ${activeTab === 'trends' ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-700'}`}
              aria-selected={activeTab === 'trends'}
            >
              Tren & gudang
            </button>
            <button
              onClick={() => switchTab('table')}
              className={`px-3.5 py-2 rounded-lg text-sm font-semibold ${activeTab === 'table' ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-700'}`}
              aria-selected={activeTab === 'table'}
            >
              Tabel SKU
            </button>
          </div>

          {/* Tab 1: Summary */}
          <div id="doi-tab-summary" className={`space-y-5 ${activeTab !== 'summary' ? 'hidden' : ''}`}>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              <div className="panel rounded-xl p-6">
                <h4 className="text-sm font-bold text-slate-900">DOI vs Standar</h4>
                <div id="chart-doi-std" className="w-full h-[380px]" />
              </div>
              <div className="panel rounded-xl p-6">
                <h4 className="text-sm font-bold text-slate-900">Kelebihan / Kekurangan Stok (Rp)</h4>
                <div id="chart-doi-lk" className="w-full h-[380px]" />
              </div>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              <div className="panel rounded-xl p-6">
                <h4 className="text-sm font-bold text-slate-900">Porsi Omset vs Porsi Stok</h4>
                <div id="chart-doi-porsi" className="w-full h-[400px]" />
              </div>
              <div className="panel rounded-xl p-6">
                <h4 className="text-sm font-bold text-slate-900">Sebaran SKU per Rentang DOI</h4>
                <div id="chart-doi-bucket" className="w-full h-[420px]" />
              </div>
            </div>
          </div>

          {/* Tab 2: Map */}
          <div id="doi-tab-map" className={`space-y-5 ${activeTab !== 'map' ? 'hidden' : ''}`}>
            <div className="panel rounded-xl p-6">
              <h4 className="text-sm font-bold text-slate-900">Peta Kuadran SKU: Omset vs Nilai Stok</h4>
              <div id="chart-doi-scatter" className="w-full h-[560px]" />
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              <div className="panel rounded-xl p-6">
                <h4 className="text-sm font-bold text-slate-900">15 SKU Kelebihan Stok Terbesar</h4>
                <div id="chart-doi-lebih" className="w-full h-[360px]" />
              </div>
              <div className="panel rounded-xl p-6">
                <h4 className="text-sm font-bold text-slate-900">15 SKU Hampir Habis / Kosong Terbesar</h4>
                <div id="chart-doi-kritis" className="w-full h-[360px]" />
              </div>
            </div>
          </div>

          {/* Tab 3: Trends */}
          <div id="doi-tab-trends" className={`space-y-5 ${activeTab !== 'trends' ? 'hidden' : ''}`}>
            <div className="panel rounded-xl p-6">
              <h4 className="text-sm font-bold text-slate-900">Tren Omset Bulanan</h4>
              <div id="chart-doi-tren" className="w-full h-[430px]" />
            </div>
            <div className="panel rounded-xl p-6">
              <h4 className="text-sm font-bold text-slate-900">Nilai Stok per Gudang</h4>
              <div id="chart-doi-gudang" className="w-full h-[360px]" />
            </div>
          </div>

          {/* Tab 4: Table */}
          <div id="doi-tab-table" className={`panel rounded-xl p-6 ${activeTab !== 'table' ? 'hidden' : ''}`}>
            <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
              <div>
                <h4 className="text-sm font-bold text-slate-900">Tabel SKU</h4>
                <p id="doiSkuCount" className="text-xs text-slate-500 mt-1">
                  Menampilkan {skuTable.length.toLocaleString('id-ID')} dari {Number(skuTotal).toLocaleString('id-ID')} SKU terfilter
                </p>
              </div>
              <a
                href={`${ENDPOINTS.dashboard.doiExportCsv}?${buildQueryString()}`}
                className="px-3.5 py-2 rounded-lg bg-white hover:bg-slate-50 border border-slate-300 text-sm font-semibold text-slate-700 inline-flex items-center gap-1.5"
              >
                <Download style={{ margin: 0, width: 16, height: 16 }} /> Unduh CSV angka penuh
              </a>
            </div>

            <div className="flex flex-wrap items-end gap-3 mb-4">
              <label className="text-xs font-semibold text-slate-600">
                Urutkan berdasarkan
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="mt-1 block bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm"
                >
                  <option value="lebih_kurang">Lebih / kurang (Rp)</option>
                  <option value="saldo">Nilai stok</option>
                  <option value="ams">AMS</option>
                  <option value="doi">DOI</option>
                  <option value="nama">Nama SKU</option>
                </select>
              </label>
              <label className="flex items-center gap-2 pb-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={sortDesc}
                  onChange={(e) => setSortDesc(e.target.checked)}
                  className="rounded border-slate-300 text-blue-600"
                />
                Terbesar dulu
              </label>
              <button onClick={handleApplyFilters} className="px-3 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-semibold">
                Urutkan
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                  <tr>
                    {['Cabang', 'Principal', 'Kode', 'Nama', 'Stok', 'Satuan', 'Nilai stok', 'AMS / bln', 'DOI (hari)', 'Standar', 'Lebih / kurang', 'Status'].map((col) => (
                      <th key={col} className="whitespace-nowrap px-3 py-3">{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {skuTable.length > 0 ? (
                    skuTable.map((row, idx) => (
                      <tr key={idx} className="hover:bg-slate-50">
                        <td className="whitespace-nowrap px-3 py-3 text-slate-700">{row.cabang}</td>
                        <td className="whitespace-nowrap px-3 py-3 text-slate-700">{row.principal}</td>
                        <td className="whitespace-nowrap px-3 py-3 text-slate-700">{row.kode}</td>
                        <td className="whitespace-nowrap px-3 py-3 text-slate-700">{row.nama}</td>
                        <td className="whitespace-nowrap px-3 py-3 text-slate-700">{row.stok}</td>
                        <td className="whitespace-nowrap px-3 py-3 text-slate-700">{row.sat}</td>
                        <td className="whitespace-nowrap px-3 py-3 text-slate-700">{row.saldo}</td>
                        <td className="whitespace-nowrap px-3 py-3 text-slate-700">{row.ams}</td>
                        <td className="whitespace-nowrap px-3 py-3 text-slate-700">{row.doi}</td>
                        <td className="whitespace-nowrap px-3 py-3 text-slate-700">{row.std}</td>
                        <td className="whitespace-nowrap px-3 py-3 text-slate-700">{row.lebih_kurang}</td>
                        <td className="whitespace-nowrap px-3 py-3 text-slate-700">{row.status}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={12} className="px-3 py-8 text-center text-slate-500">
                        Tidak ada SKU yang cocok dengan filter.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}