<template>
  <div class="login-wrap">
    <div class="card login-card">
      <div class="brand">🏥 ERM Klinik</div>
      <div class="sub">Sistem Rekam Medis Elektronik — silakan masuk</div>

      <div v-if="error" class="alert error">{{ error }}</div>

      <form @submit.prevent="submit">
        <div class="form-group" style="margin-bottom: 12px">
          <label>Username</label>
          <input v-model="username" autocomplete="username" required />
        </div>
        <div class="form-group" style="margin-bottom: 18px">
          <label>Password</label>
          <input v-model="password" type="password" autocomplete="current-password" required />
        </div>
        <button class="btn block" :disabled="loading">
          {{ loading ? 'Masuk...' : 'Masuk' }}
        </button>
      </form>

      <p class="muted" style="margin-top: 14px; font-size: 12px; text-align: center">
        Demo: admin/123456 · wigadana/123456
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function submit() {
  loading.value = true
  error.value = ''
  const res = await auth.login(username.value, password.value)
  loading.value = false
  if (res.ok) {
    router.push('/antrian')
  } else {
    error.value = res.error
  }
}
</script>
