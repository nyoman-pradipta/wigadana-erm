import axios from 'axios'

const api = axios.create({
  // Dev: proxied ke backend via vite.config.js
  // Prod: set VITE_API_URL=https://api.domainmu.com saat build di Vercel
  baseURL: import.meta.env.VITE_API_URL || '/api',
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('erm_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('erm_token')
      localStorage.removeItem('erm_user')
      if (!location.pathname.startsWith('/login')) location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export function apiErrorMessage(err, fallback = 'Terjadi kesalahan') {
  return err?.response?.data?.detail || err?.message || fallback
}

/** Fetch PDF via axios (token interceptor) lalu buka di tab baru untuk print. */
export async function openPdf(url) {
  const res = await api.get(url, { responseType: 'blob' })
  const blobUrl = URL.createObjectURL(res.data)
  window.open(blobUrl, '_blank')
}

export default api
