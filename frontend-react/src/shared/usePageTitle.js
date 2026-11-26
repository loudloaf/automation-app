/* ============================================================================
 * PAGE    : SHARED: set judul topbar
 * FILE    : src/shared/usePageTitle.js
 * ROUTE   : -
 * ORIGIN  : page-title di index.html lama
 * API     : -
 * STORE   : uiStore
 * UPDATE  : paste THIS file only into an AI
 * ========================================================================== */
import { useEffect } from 'react'
import { useUiStore } from '../stores/uiStore'

/** [TITLE-1] Panggil di awal setiap halaman: usePageTitle('Judul') */
export default function usePageTitle(title) {
  const setPageTitle = useUiStore((s) => s.setPageTitle)
  useEffect(() => { setPageTitle(title) }, [title, setPageTitle])
}
