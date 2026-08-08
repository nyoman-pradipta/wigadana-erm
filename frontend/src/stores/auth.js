import { defineStore } from 'pinia'
import api, { apiErrorMessage } from '../api/client'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('erm_token') || '',
    user: JSON.parse(localStorage.getItem('erm_user') || 'null'),
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
    role: (s) => s.user?.role || '',
  },
  actions: {
    async login(username, password) {
      try {
        const { data } = await api.post('/auth/login', { username, password })
        this.token = data.access_token
        this.user = data.user
        localStorage.setItem('erm_token', data.access_token)
        localStorage.setItem('erm_user', JSON.stringify(data.user))
        return { ok: true }
      } catch (err) {
        return { ok: false, error: apiErrorMessage(err, 'Login gagal') }
      }
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('erm_token')
      localStorage.removeItem('erm_user')
    },
    updateUser(patch) {
      this.user = { ...this.user, ...patch }
      localStorage.setItem('erm_user', JSON.stringify(this.user))
    },
  },
})
