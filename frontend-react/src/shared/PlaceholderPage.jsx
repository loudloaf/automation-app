/* ============================================================================
 * PAGE    : SHARED: halaman sementara
 * FILE    : src/shared/PlaceholderPage.jsx
 * ROUTE   : -
 * ORIGIN  : -
 * API     : -
 * STORE   : -
 * UPDATE  : paste THIS file only into an AI
 * NOTE    : Hilang otomatis saat halaman aslinya dipindahkan.
 * ========================================================================== */
import usePageTitle from './usePageTitle'

export default function PlaceholderPage({ title, origin }) {
  usePageTitle(title)
  return (
    <div className="panel rounded-xl p-7 text-sm text-slate-600">
      Halaman ini dipindahkan dari <code className="font-mono">{origin}</code> pada langkah berikutnya.
    </div>
  )
}
