import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/LoginView.vue') },
  {
    path: '/',
    component: () => import('../layout/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/antrian' },
      { path: 'antrian', name: 'antrian', component: () => import('../views/DashboardView.vue') },
      { path: 'pasien', name: 'pasien', component: () => import('../views/PasienView.vue') },
      { path: 'pasien/baru', name: 'pasien-baru', component: () => import('../views/PasienFormView.vue') },
      { path: 'pasien/:id/edit', name: 'pasien-edit', component: () => import('../views/PasienFormView.vue') },
      { path: 'pasien/:id', name: 'riwayat', component: () => import('../views/RiwayatView.vue') },
      { path: 'pemeriksaan/:visitId', name: 'pemeriksaan', component: () => import('../views/PemeriksaanView.vue') },
      { path: 'pengguna', name: 'pengguna', component: () => import('../views/UserManagementView.vue'), meta: { roles: ['admin'] } },
      { path: 'statistik', name: 'statistik', component: () => import('../views/StatistikView.vue'), meta: { roles: ['admin'] } },
      { path: 'profil', name: 'profil', component: () => import('../views/ProfilView.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) return { name: 'login' }
  if (to.name === 'login' && auth.isLoggedIn) return { name: 'antrian' }
  if (to.meta.roles && !to.meta.roles.includes(auth.role)) return { name: 'antrian' }
})

export default router
