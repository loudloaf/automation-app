/* ============================================================================
 * PAGE    : Izin Akses (Role-Based Access Control)
 * FILE    : src/pages/AccessPage.jsx
 * ROUTE   : /access
 * ORIGIN  : #view-permissions + loadUsers() + saveUserRole() di index.html lama
 * API     : GET /api/users · POST /api/users
 * STORE   : toastStore, uiStore
 * UPDATE  : paste THIS file only into an AI
 * ========================================================================== */
import { useEffect, useState, useCallback } from 'react'
import { ShieldCheck } from 'lucide-react'
import usePageTitle from '../shared/usePageTitle'
import { apiFetch } from '../api/http'
import { ENDPOINTS } from '../config/endpoints'
import { useToastStore } from '../stores/toastStore'
import { useAppDataStore } from '../stores/appDataStore'

export default function AccessPage() {
  usePageTitle('Izin Akses')
  const showToast = useToastStore((s) => s.showToast)

  const users = useAppDataStore((s) => s.users)
  const loadUsers = useAppDataStore((s) => s.loadUsers)
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [role, setRole] = useState('admin')

  useEffect(() => {
    loadUsers()
  }, [loadUsers])

  /* ───── [ACCESS-2] SAVE USER ROLE (lama: saveUserRole) ───── */
  const saveUserRole = async () => {
    const fd = new FormData()
    fd.append('email', email)
    fd.append('name', name)
    fd.append('role', role)

    try {
      const res = await apiFetch(ENDPOINTS.users, { method: 'POST', body: fd })
      const data = await res.json()
      if (!res.ok) {
        showToast(data.detail || 'Hanya Admin', 'error')
        return
      }
      showToast(data.message, 'ok')
      setEmail('')
      setName('')
      await loadUsers()
    } catch {
      showToast('Gagal menyimpan izin akses', 'error')
    }
  }

  return (
    <section id="view-permissions" className="space-y-6">
      <div className="panel rounded-xl p-7 max-w-3xl">
        <h2 className="text-lg font-bold text-slate-900">
          <ShieldCheck className="lucide" /> Pengaturan Izin Akses (Role-Based Access Control)
        </h2>
        <p className="text-sm text-slate-500 mt-1">
          Semua pengguna dapat <b>Menjalankan Script</b>, <b>Melihat</b>, dan <b>Menambah</b> data Master. Namun fitur <b>Edit</b>, <b>Hapus</b>, dan <b>Kosongkan Tabel</b> dikunci khusus untuk pengguna berstatus <span className="text-emerald-700 font-mono">admin</span>.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mt-5 p-5 rounded-lg bg-slate-50 border border-slate-200">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="email@company.com"
            className="bg-white border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-900"
          />
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Nama Lengkap"
            className="bg-white border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-900"
          />
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="bg-white border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-900"
          >
            <option value="admin">Admin (Full Access)</option>
            <option value="staff">Staff (View & Add Only)</option>
          </select>
          <button
            onClick={saveUserRole}
            className="bg-blue-600 hover:bg-blue-700 text-white rounded-xl px-4 py-2 text-sm font-semibold transition-all"
          >
            Simpan Izin
          </button>
        </div>

        <div id="users-list" className="mt-5 space-y-2">
          {users.map((u) => (
            <div
              key={u.email}
              className="flex items-center justify-between p-3 rounded-lg bg-slate-50 border border-slate-200"
            >
              <div>
                <span className="text-sm font-mono font-semibold text-slate-900">{u.email}</span>
                <span className="text-sm text-slate-500 ml-2">{u.name || ''}</span>
              </div>
              <span
                className={`text-xs font-mono uppercase px-2.5 py-0.5 rounded-full ${
                  u.role === 'admin'
                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    : 'bg-slate-100 text-slate-600'
                }`}
              >
                {u.role}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}