/* ============================================================================
 * PAGE    : Kerangka aplikasi (sidebar + topbar)
 * FILE    : src/shell/AppShell.jsx
 * ROUTE   : (membungkus semua halaman setelah login)
 * ORIGIN  : <aside class="sidebar"> + <header class="topbar"> + renderNav() di index.html lama
 * API     : POST /api/auth/logout (lewat authStore)
 * STORE   : authStore, uiStore
 * UPDATE  : paste THIS file only into an AI
 * ========================================================================== */
import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { LayoutDashboard, Workflow, BarChart3, Database, ShieldCheck, LogOut } from 'lucide-react'
import { useAuthStore } from '../stores/authStore'
import { useUiStore } from '../stores/uiStore'

/* ───── [SHELL-1] MENU SIDEBAR (hanya 5 menu utama) ───── */
const NAV_ITEMS = [
  { to: '/', end: true, icon: LayoutDashboard, label: 'Overview' },
  { to: '/automation', icon: Workflow, label: 'Automation Scripts' },
  { to: '/analytics', icon: BarChart3, label: 'Analytics & Forecast' },
  { to: '/master', icon: Database, label: 'Master Data Hub' },
  { to: '/access', icon: ShieldCheck, label: 'Izin Akses' },
]

export default function AppShell() {
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const pageTitle = useUiStore((s) => s.pageTitle)
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const isAdmin = Boolean(user?.is_admin)
  const [avatarFailed, setAvatarFailed] = useState(false) // foto Google gagal dimuat -> pakai huruf awal
  const initial = (user?.name || user?.email || 'U').charAt(0).toUpperCase()

  useEffect(() => { setAvatarFailed(false) }, [user?.picture])
  useEffect(() => { window.scrollTo(0, 0) }, [pathname]) // lama: window.scrollTo(0, 0) di showLevel

  return (
    <div className="app">
      {/* ───── [SHELL-2] SIDEBAR ───── */}
      <aside className="sidebar">
        <div className="brand" onClick={() => navigate('/')}>
          <div className="brand-mark">
            <img
              src="/bbi-logo.png"
              alt="BBI"
              onError={(e) => { e.currentTarget.style.display = 'none'; e.currentTarget.nextElementSibling.style.display = 'grid' }}
            />
            <span className="brand-fallback">B</span>
          </div>
          <span className="brand-name">BBI Automation</span>
        </div>
        <nav className="flex flex-col gap-1" aria-label="Navigasi utama">
          {NAV_ITEMS.map(({ to, end, icon: Icon, label }) => (
            <NavLink key={to} to={to} end={end} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <Icon />{label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="min-w-0">
        {/* ───── [SHELL-3] TOPBAR ───── */}
        <header className="topbar">
          <h1 className="text-xl font-semibold">{pageTitle}</h1>
          <div className="flex items-center gap-4">
            <div className="text-right hidden md:block">
              <span className="text-xs text-slate-500 block">Pengguna aktif</span>
              <span className={`text-xs font-semibold ${isAdmin ? 'text-emerald-700' : 'text-amber-700'}`}>
                {isAdmin ? 'ADMIN ACCESS (Full)' : 'STAFF (View & Add Only)'}
              </span>
            </div>
            <div className="flex items-center gap-2.5 bg-slate-50 border border-slate-200 rounded-full pl-2 pr-3.5 py-1.5">
              {user?.picture && !avatarFailed ? (
                <img src={user.picture} alt="Avatar" referrerPolicy="no-referrer" onError={() => setAvatarFailed(true)} className="w-8 h-8 rounded-full object-cover bg-blue-600 text-white" />
              ) : (
                <div className="w-8 h-8 rounded-full bg-blue-600 text-white text-xs font-bold grid place-items-center">{initial}</div>
              )}
              <div className="text-left leading-tight max-w-[180px]">
                <span className="text-xs font-bold text-slate-900 block truncate">{user?.name || user?.email}</span>
                <span className="text-[11px] font-mono text-slate-500 block truncate">{user?.email}</span>
              </div>
            </div>
            <button onClick={logout} title="Keluar (Logout)" className="px-3 py-2 rounded-lg bg-white hover:bg-rose-50 border border-slate-300 hover:border-rose-200 text-slate-700 hover:text-rose-700 text-xs font-semibold transition-all flex items-center gap-1.5">
              <LogOut style={{ margin: 0, width: 15, height: 15 }} />
              <span className="hidden sm:inline">Keluar</span>
            </button>
          </div>
        </header>

        {/* ───── [SHELL-4] ISI HALAMAN ───── */}
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}