/* ============================================================================
 * PAGE    : Direktori Automation & Analytics
 * FILE    : src/pages/DirectoryPage.jsx
 * ROUTE   : /automation  ·  /analytics
 * ORIGIN  : #dir-automation / #dir-dashboard + renderDirectory() di index.html lama
 * API     : -
 * STORE   : registry (automationScripts, analyticsModules)
 * UPDATE  : paste THIS file only into an AI
 * ========================================================================== */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import usePageTitle from '../shared/usePageTitle'
import { automationScripts } from '../registry/automationScripts'
import { analyticsModules } from '../registry/analyticsModules'

const CONFIG = {
  automation: {
    topbarTitle: 'Automation Scripts Directory',
    heading: 'Automation Scripts Directory',
    sub: 'Pilih script yang ingin dijalankan.',
    placeholder: 'Cari script...',
    cta: 'Buka Console / Jalankan',
    basePath: '/automation',
    items: automationScripts,
  },
  dashboard: {
    topbarTitle: 'Analytics & Forecast Directory',
    heading: 'Analytics Dashboard Directory',
    sub: 'Pilih laporan atau visualisasi yang ingin dibuka.',
    placeholder: 'Cari laporan...',
    cta: 'Lihat Visualisasi',
    basePath: '/analytics',
    items: analyticsModules,
  },
}

export default function DirectoryPage({ kind = 'automation' }) {
  const cfg = CONFIG[kind] || CONFIG.automation
  usePageTitle(cfg.topbarTitle)
  const navigate = useNavigate()
  const [query, setQuery] = useState('')

  const q = query.toLowerCase().trim()
  const hits = cfg.items.filter(
    (n) => !q || `${n.label} ${n.desc} ${n.kw}`.toLowerCase().includes(q)
  )

  return (
    <section className="space-y-6">
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-semibold">{cfg.heading}</h2>
          <p className="text-slate-500 mt-1">{cfg.sub}</p>
        </div>

        <div className="search-wrap">
          <Search className="lucide" />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={cfg.placeholder}
            autoComplete="off"
            aria-label={cfg.placeholder}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {hits.length ? (
            hits.map((n) => {
              const Icon = n.icon
              return (
                <article key={n.id} className="panel rounded-xl p-7 flex flex-col gap-4">
                  <div className="flex items-center justify-between gap-3">
                    <span className="w-11 h-11 rounded-lg bg-blue-50 text-blue-700 grid place-items-center">
                      <Icon style={{ margin: 0, width: 22, height: 22 }} />
                    </span>
                    <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-slate-100 text-slate-600">
                      {n.badge}
                    </span>
                  </div>
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold leading-snug">{n.label}</h3>
                    <p className="text-sm text-slate-500 mt-2">{n.desc}</p>
                  </div>
                  <button
                    onClick={() => navigate(`${cfg.basePath}/${n.id}`)}
                    className="w-full py-3 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold"
                  >
                    {cfg.cta}
                  </button>
                </article>
              )
            })
          ) : (
            <p className="text-slate-500 col-span-full py-10 text-center">
              Tidak ada hasil untuk pencarian ini.
            </p>
          )}
        </div>
      </div>
    </section>
  )
}