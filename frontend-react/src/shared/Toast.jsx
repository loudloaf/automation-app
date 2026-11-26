/* ============================================================================
 * PAGE    : SHARED: Toast
 * FILE    : src/shared/Toast.jsx
 * ROUTE   : (semua)
 * ORIGIN  : #toast + showToast() di index.html lama
 * API     : -
 * STORE   : toastStore
 * UPDATE  : paste THIS file only into an AI
 * ========================================================================== */
import { CheckCircle2, AlertTriangle, AlertCircle } from 'lucide-react'
import { useToastStore } from '../stores/toastStore'

const KIND = {
  ok: { Icon: CheckCircle2, color: '#047857' },
  warn: { Icon: AlertTriangle, color: '#B45309' },
  error: { Icon: AlertCircle, color: '#BE123C' },
}

/** [TOAST-UI] */
export default function Toast() {
  const toast = useToastStore((s) => s.toast)
  if (!toast) return null
  const { Icon, color } = KIND[toast.kind] || KIND.ok
  return (
    <div className="fixed bottom-6 right-6 z-50 panel rounded-xl px-5 py-4 flex items-center gap-4 max-w-md" role="status">
      <span><Icon style={{ color, margin: 0 }} /></span>
      <p className="text-sm font-medium">{toast.msg}</p>
    </div>
  )
}
