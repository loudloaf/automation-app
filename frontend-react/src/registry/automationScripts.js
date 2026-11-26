/* ============================================================================
 * PAGE    : REGISTRY: Daftar Automation Scripts
 * FILE    : src/registry/automationScripts.js
 * ROUTE   : menu direktori + rute otomatis
 * ORIGIN  : const NAV.automation di index.html lama
 * API     : -
 * STORE   : -
 * UPDATE  : paste THIS file only into an AI
 * NOTE    : TAMBAH ITEM BARU DI SINI (1 entri) + buat file halamannya. Kartu direktori & rute terbentuk otomatis.
 * ========================================================================== */
import { lazy } from 'react'
import { Package, Scale } from 'lucide-react'

export const automationScripts = [
  {
    id: "rangkuman",
    label: "Rangkuman Penjualan (Orlan & Zeta)",
    icon: Package,
    desc: "Pembersihan data, paket ZIP per cabang, dan sinkronisasi Google Sheets.",
    badge: "21 pemeriksaan audit",
    kw: "penjualan orlan zeta supplier zip gsheets",
    component: lazy(() => import('../features/automation/scripts/RangkumanPage')),
  },
  {
    id: "doi",
    label: "Laporan DOI per Cabang",
    icon: Scale,
    desc: "Laporan Excel Days of Inventory per cabang dengan 7 sheet berumus.",
    badge: "7 sheet rumus hidup",
    kw: "doi days inventory stok mutasi cabang",
    component: lazy(() => import('../features/automation/scripts/DoiCabangPage')),
  },
]
