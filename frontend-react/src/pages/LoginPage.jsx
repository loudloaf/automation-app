/* ============================================================================
 * PAGE    : Login dengan Google
 * FILE    : src/pages/LoginPage.jsx
 * ROUTE   : (tampil otomatis bila belum login)
 * ORIGIN  : #loginGate di index.html lama
 * API     : lewat authStore: GET /api/auth/google/login
 * STORE   : authStore
 * UPDATE  : paste THIS file only into an AI
 * NOTE    : Teks, urutan, dan kelas sama dengan #loginGate lama.
 * ========================================================================== */
import { CheckCircle2, LogIn } from 'lucide-react'
import { useAuthStore } from '../stores/authStore'
import BusyContent from '../shared/BusyContent'

/* ───── [LOGIN-1] DATA: poin fitur ───── */
const FEATURES = [
  { color: 'text-blue-600', bold: 'Rangkuman Penjualan (Orlan & Zeta):', text: ' 21 pemeriksaan audit, ZIP 5-sheet per cabang & sinkronisasi otomatis ke Google Sheets Master.' },
  { color: 'text-emerald-600', bold: 'Laporan DOI per Cabang:', text: ' Kalkulasi Days of Inventory multi-bulan dengan 7 sheet rumus hidup.' },
  { color: 'text-blue-600', bold: 'Analytics & Forecast:', text: ' Visualisasi interaktif 16 grafik Plotly & proyeksi 30 hari.' },
]

/* ───── [LOGIN-2] UI ───── */
export default function LoginPage() {
  const authError = useAuthStore((s) => s.authError)
  const signingIn = useAuthStore((s) => s.signingIn)
  const startGoogleLogin = useAuthStore((s) => s.startGoogleLogin)

  return (
    <div data-page="login" className="fixed inset-0 z-50 bg-slate-100 flex items-center justify-center p-5">
      <div className="panel rounded-2xl p-8 w-full max-w-md border border-slate-200 space-y-6 bg-white shadow-xl">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl bg-blue-600 text-white font-bold text-lg grid place-items-center shadow-sm">B</div>
          <div>
            <h2 className="text-base font-bold text-slate-900 leading-tight">BBI Automation</h2>
            <p className="text-xs text-slate-500">Internal Enterprise Automation & Analytics Suite</p>
          </div>
        </div>

        <div>
          <h1 className="text-xl font-bold text-slate-900">Masuk dengan Akun Google</h1>
          <p className="text-sm text-slate-500 mt-1 leading-relaxed">
            Gunakan akun Gmail pribadi/kantor Anda untuk menjalankan otomatisasi laporan, dashboard analitik, dan sinkronisasi langsung ke Google Sheets Master.
          </p>
        </div>

        <div className="space-y-2.5 p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600">
          {FEATURES.map((f) => (
            <div key={f.bold} className="flex items-start gap-2.5">
              <CheckCircle2 className={`${f.color} shrink-0 mt-0.5`} style={{ margin: 0, width: 16, height: 16 }} />
              <span><b>{f.bold}</b>{f.text}</span>
            </div>
          ))}
        </div>

        {authError && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-xs text-rose-800" role="alert">{authError}</div>
        )}

        <button
          onClick={startGoogleLogin}
          disabled={signingIn}
          className="w-full py-3.5 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm transition-all flex items-center justify-center gap-2 shadow-sm"
        >
          <BusyContent busy={signingIn} label="Membuka otorisasi Google di browser...">
            <LogIn style={{ margin: 0 }} />
            <span>Sign in with Google</span>
          </BusyContent>
        </button>
      </div>
    </div>
  )
}
