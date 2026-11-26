/* ============================================================================
 * PAGE    : Penjaga login + tabel rute
 * FILE    : src/App.jsx
 * ROUTE   : (semua)
 * ORIGIN  : onUserSwitch() + switchMainTab() di index.html lama
 * API     : GET /api/auth/me (lewat authStore)
 * STORE   : authStore
 * UPDATE  : paste THIS file only into an AI
 * NOTE    : Rute halaman script/dashboard dibuat otomatis dari registry/.
 * ========================================================================== */
import { Suspense, lazy, useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import AppShell from './shell/AppShell'
import LoginPage from './pages/LoginPage'
import Toast from './shared/Toast'
import { automationScripts } from './registry/automationScripts'
import { analyticsModules } from './registry/analyticsModules'

/* ───── [APP-1] HALAMAN (dimuat saat dibuka saja) ───── */
const OverviewPage = lazy(() => import('./pages/OverviewPage'))
const DirectoryPage = lazy(() => import('./pages/DirectoryPage'))
const MasterDataPage = lazy(() => import('./pages/MasterDataPage'))
const AccessPage = lazy(() => import('./pages/AccessPage'))

export default function App() {
  const status = useAuthStore((s) => s.status)
  useEffect(() => { useAuthStore.getState().loadSession() }, [])

  return (
    <>
      {status === 'loading' && <div className="fixed inset-0 bg-slate-100" />}
      {status === 'anon' && <LoginPage />}
      {status === 'authed' && (
        <Suspense fallback={<div className="py-10 text-center text-sm text-slate-500">Memuat...</div>}>
          <Routes>
            {/* ───── [APP-2] RUTE ───── */}
            <Route element={<AppShell />}>
              <Route index element={<OverviewPage />} />
              <Route path="automation" element={<DirectoryPage kind="automation" />} />
              {automationScripts.map((s) => <Route key={s.id} path={`automation/${s.id}`} element={<s.component />} />)}
              <Route path="analytics" element={<DirectoryPage kind="dashboard" />} />
              {analyticsModules.map((m) => <Route key={m.id} path={`analytics/${m.id}`} element={<m.component />} />)}
              <Route path="master" element={<MasterDataPage />} />
              <Route path="access" element={<AccessPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </Suspense>
      )}
      <Toast />
    </>
  )
}
