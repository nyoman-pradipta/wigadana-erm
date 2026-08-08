<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="brand">🏥 ERM Klinik</div>
      <nav>
        <router-link to="/antrian">🪪 Antrian</router-link>
        <router-link to="/pasien">👥 Pasien</router-link>
        <router-link v-if="auth.role === 'admin'" to="/pengguna">👤 Pengguna</router-link>
        <router-link v-if="auth.role === 'admin'" to="/statistik">📊 Statistik</router-link>
      </nav>
      <div class="user-box">
        <div class="name">{{ auth.user?.nama }}</div>
        <div class="role">{{ auth.user?.role }}</div>
        <div class="row-actions" style="margin-top: 8px">
          <router-link to="/profil" class="btn secondary small">⚙️ Profil</router-link>
          <button class="btn small" @click="logout">Keluar</button>
        </div>
      </div>
    </aside>
    <main class="main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

function logout() {
  auth.logout()
  router.push('/login')
}
</script>
