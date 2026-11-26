/* ============================================================================
 * PAGE    : REGISTRY: Daftar Analytics & Forecast
 * FILE    : src/registry/analyticsModules.js
 * ROUTE   : menu direktori + rute otomatis
 * ORIGIN  : const NAV.dashboard di index.html lama
 * API     : -
 * STORE   : -
 * UPDATE  : paste THIS file only into an AI
 * NOTE    : TAMBAH ITEM BARU DI SINI (1 entri) + buat file halamannya. Kartu direktori & rute terbentuk otomatis.
 * ========================================================================== */
import { lazy } from 'react'
import { Compass, TrendingUp } from 'lucide-react'

export const analyticsModules = [
  {
    id: "penjualan",
    label: "Dashboard Penjualan & Forecast 30 Hari",
    icon: TrendingUp,
    desc: "Tren omset, retur, principal, customer, dan proyeksi 30 hari.",
    badge: "7 grafik",
    kw: "penjualan forecast omset retur",
    component: lazy(() => import('../features/analytics/modules/PenjualanPage')),
  },
  {
    id: "doi",
    label: "Dashboard DOI (Stok vs Omset)",
    icon: Compass,
    desc: "DOI vs standar, kelebihan stok, dan peta kuadran SKU.",
    badge: "9 grafik",
    kw: "doi stok omset kuadran gudang",
    component: lazy(() => import('../features/analytics/modules/DoiPage')),
  },
]
