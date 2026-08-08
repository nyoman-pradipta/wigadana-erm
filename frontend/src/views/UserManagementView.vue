<template>
  <div>
    <div class="page-head">
      <h1>Kelola Pengguna</h1>
      <button class="btn" @click="openCreate">+ User Baru</button>
    </div>

    <div v-if="error" class="alert error">{{ error }}</div>
    <div v-if="success" class="alert success">{{ success }}</div>

    <div class="card">
      <div class="search-row">
        <input v-model="q" placeholder="Cari nama / username..." @keyup.enter="muat" />
        <select v-model="filterRole" style="padding: 9px 12px; border: 1px solid var(--border); border-radius: 8px" @change="muat">
          <option value="">Semua role</option>
          <option value="admin">admin</option>
          <option value="dokter">dokter</option>
        </select>
      </div>

      <table v-if="users.length">
        <thead>
          <tr>
            <th>Username</th>
            <th>Nama</th>
            <th>Role</th>
            <th>No. SIP</th>
            <th>Status</th>
            <th style="text-align: right">Aksi</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td style="font-weight: 600">{{ u.username }}</td>
            <td>{{ u.nama }}</td>
            <td><span class="badge" :class="u.role">{{ u.role }}</span></td>
            <td class="muted">{{ u.no_sip || '—' }}</td>
            <td>
              <button class="btn small" :class="u.is_active ? 'secondary' : ''"
                      :style="u.is_active ? 'color:var(--success)' : 'color:var(--danger)'"
                      @click="toggleAktif(u)">
                {{ u.is_active ? '● Aktif' : '○ Nonaktif' }}
              </button>
            </td>
            <td>
              <div class="row-actions" style="justify-content: flex-end">
                <button class="btn small secondary" @click="openReset(u)">Reset Password</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty">Tidak ada pengguna</div>
    </div>

    <!-- Modal: user baru -->
    <div v-if="showCreate" class="modal-overlay" @click.self="showCreate = false">
      <div class="modal">
        <h3>User Baru</h3>
        <div class="form-group" style="margin-bottom: 10px">
          <label>Username</label>
          <input v-model="form.username" placeholder="min. 3 karakter" />
        </div>
        <div class="form-group" style="margin-bottom: 10px">
          <label>Nama Lengkap</label>
          <input v-model="form.nama" />
        </div>
        <div class="form-group" style="margin-bottom: 10px">
          <label>Password</label>
          <input v-model="form.password" type="password" placeholder="min. 6 karakter" />
        </div>
        <div class="form-group" style="margin-bottom: 14px">
          <label>Role</label>
          <select v-model="form.role">
            <option value="dokter">dokter</option>
            <option value="admin">admin</option>
          </select>
        </div>
        <div class="form-actions">
          <button class="btn" :disabled="saving" @click="buatUser">{{ saving ? '...' : 'Simpan' }}</button>
          <button class="btn secondary" @click="showCreate = false">Batal</button>
        </div>
      </div>
    </div>

    <!-- Modal: reset password -->
    <div v-if="showReset" class="modal-overlay" @click.self="showReset = false">
      <div class="modal">
        <h3>Reset Password — {{ resetTarget?.nama }}</h3>
        <p class="muted" style="margin-bottom: 10px; font-size: 12px">
          User akan bisa login dengan password baru ini.
        </p>
        <div class="form-group" style="margin-bottom: 14px">
          <label>Password Baru</label>
          <input v-model="resetPassword" type="password" placeholder="min. 6 karakter" />
        </div>
        <div class="form-actions">
          <button class="btn" :disabled="saving" @click="resetPw">{{ saving ? '...' : 'Reset' }}</button>
          <button class="btn secondary" @click="showReset = false">Batal</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import api, { apiErrorMessage } from '../api/client'

const users = ref([])
const q = ref('')
const filterRole = ref('')
const error = ref('')
const success = ref('')

const showCreate = ref(false)
const showReset = ref(false)
const saving = ref(false)
const form = ref({ username: '', nama: '', password: '', role: 'dokter' })
const resetTarget = ref(null)
const resetPassword = ref('')

async function muat() {
  try {
    const { data } = await api.get('/users', { params: { q: q.value, role: filterRole.value } })
    users.value = data
  } catch (err) {
    error.value = apiErrorMessage(err, 'Gagal memuat pengguna')
  }
}

function openCreate() {
  form.value = { username: '', nama: '', password: '', role: 'dokter' }
  showCreate.value = true
}

async function buatUser() {
  saving.value = true
  error.value = success.value = ''
  try {
    await api.post('/users', form.value)
    showCreate.value = false
    success.value = `User ${form.value.username} dibuat`
    await muat()
  } catch (err) {
    error.value = apiErrorMessage(err, 'Gagal membuat user')
  } finally {
    saving.value = false
  }
}

async function toggleAktif(u) {
  error.value = success.value = ''
  try {
    await api.put(`/users/${u.id}`, { is_active: !u.is_active })
    await muat()
  } catch (err) {
    error.value = apiErrorMessage(err, 'Gagal mengubah status')
  }
}

function openReset(u) {
  resetTarget.value = u
  resetPassword.value = ''
  showReset.value = true
}

async function resetPw() {
  saving.value = true
  error.value = success.value = ''
  try {
    await api.post(`/users/${resetTarget.value.id}/reset-password`, { new_password: resetPassword.value })
    showReset.value = false
    success.value = `Password ${resetTarget.value.username} direset`
  } catch (err) {
    error.value = apiErrorMessage(err, 'Gagal reset password')
  } finally {
    saving.value = false
  }
}

onMounted(muat)
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}
.modal {
  background: #fff;
  border-radius: 12px;
  padding: 22px;
  width: 380px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.2);
}
.modal h3 { margin-bottom: 14px; font-size: 16px; }
</style>
