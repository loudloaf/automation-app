/* ============================================================================
 * PAGE    : CONFIG: endpoint API
 * FILE    : src/config/endpoints.js
 * ROUTE   : -
 * ORIGIN  : URL /api/... di index.html lama
 * API     : -
 * STORE   : -
 * UPDATE  : paste THIS file only into an AI
 * ========================================================================== */
export const ENDPOINTS = {
  auth: {
    me: '/api/auth/me',
    googleLogin: '/api/auth/google/login',
    logout: '/api/auth/logout',
  },
  overview: '/api/overview',
  users: '/api/users',
  master: {
    get: (entity) => `/api/master/${entity}`,
    upload: (entity) => `/api/master/${entity}/upload`,
    row: (entity, mode) => `/api/master/${entity}/row?mode=${mode}`,
    deleteRow: (entity, pkVal) => `/api/master/${entity}/row/${encodeURIComponent(pkVal)}`,
    clear: (entity) => `/api/master/${entity}/clear`,
  },
  automate: {
    rangkuman: '/api/automate/rangkuman-penjualan',
    rangkumanGsheets: '/api/automate/rangkuman-gsheets',
    doi: '/api/automate/doi-cabang',
  },
  dashboard: {
    salesUpload: '/api/dashboard/penjualan/upload',
    salesData: '/api/dashboard/penjualan/data',
    doiUpload: '/api/dashboard/doi/upload',
    doiData: '/api/dashboard/doi/data',
    doiExportCsv: '/api/dashboard/doi/export.csv',
  },
  downloadOutput: (filename) => `/api/download/output/${encodeURIComponent(filename)}`,
}