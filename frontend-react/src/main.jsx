/* ============================================================================
 * PAGE    : Entry point
 * FILE    : src/main.jsx
 * ROUTE   : (semua)
 * ORIGIN  : index.html lama (bootstrap)
 * API     : -
 * STORE   : -
 * UPDATE  : paste THIS file only into an AI
 * ========================================================================== */
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './styles/global.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <BrowserRouter>
    <App />
  </BrowserRouter>,
)
