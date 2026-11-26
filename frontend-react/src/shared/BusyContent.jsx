/* ============================================================================
 * PAGE    : SHARED: isi tombol saat sibuk
 * FILE    : src/shared/BusyContent.jsx
 * ROUTE   : -
 * ORIGIN  : setBusy() di index.html lama
 * API     : -
 * STORE   : -
 * UPDATE  : paste THIS file only into an AI
 * ========================================================================== */
/** [BUSY-1] Tampilkan spinner + label saat busy, selain itu tampilkan children (sama seperti setBusy/restoreBtn lama) */
export default function BusyContent({ busy, label, children }) {
  if (!busy) return children
  return (
    <span className="inline-flex items-center justify-center gap-2">
      <span className="dashboard-spinner" aria-hidden="true" />
      <span>{label}</span>
    </span>
  )
}
