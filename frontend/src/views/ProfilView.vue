<template>
  <div>
    <div class="page-head">
      <h1>Profil Saya</h1>
    </div>

    <div class="card" style="max-width: 520px">
      <h2>Data Diri</h2>
      <div v-if="profileMsg" class="alert success">{{ profileMsg }}</div>
      <div v-if="profileErr" class="alert error">{{ profileErr }}</div>

      <form @submit.prevent="simpanProfil">
        <div class="form-group" style="margin-bottom: 12px">
          <label>Username</label>
          <input v-model="profil.username" required minlength="3" />
        </div>
        <div class="form-group" style="margin-bottom: 12px">
          <label>Nama Lengkap</label>
          <input v-model="profil.nama" required />
        </div>
        <div class="form-group" style="margin-bottom: 12px">
          <label>No. SIP (dokter)</label>
          <input v-model="profil.no_sip" placeholder="opsional — tampil di resep" />
        </div>
        <button class="btn" :disabled="savingProfil">{{ savingProfil ? 'Menyimpan...' : 'Simpan Profil' }}</button>
      </form>
    </div>

    <div class="card" style="max-width: 520px">
      <h2>Ganti Password</h2>
      <div v-if="pwMsg" class="alert success">{{ pwMsg }}</div>
      <div v-if="pwErr" class="alert error">{{ pwErr }}</div>

      <form @submit.prevent="gantiPassword">
        <div class="form-group" style="margin-bottom: 12px">
          <label>Password Lama</label>
          <input v-model="pw.old_password" type="password" required />
        </div>
        <div class="form-group" style="margin-bottom: 12px">
          <label>Password Baru</label>
          <input v-model="pw.new_password" type="password" minlength="6" required />
        </div>
        <button class="btn" :disabled="savingPw">{{ savingPw ? 'Mengganti...' : 'Ganti Password' }}</button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import api, { apiErrorMessage } from '../api/client'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()

const profil = ref({ username: '', nama: '', no_sip: '' })
const pw = ref({ old_password: '', new_password: '' })
const savingProfil = ref(false)
const savingPw = ref(false)
const profileMsg = ref('')
const profileErr = ref('')
const pwMsg = ref('')
const pwErr = ref('')

onMounted(() => {
  profil.value = { username: auth.user?.username || '', nama: auth.user?.nama || '', no_sip: auth.user?.no_sip || '' }
})

async function simpanProfil() {
  savingProfil.value = true
  profileMsg.value = profileErr.value = ''
  try {
    const { data } = await api.put('/auth/me', profil.value)
    auth.updateUser({ username: data.username, nama: data.nama, no_sip: data.no_sip })
    profileMsg.value = 'Profil tersimpan'
  } catch (err) {
    profileErr.value = apiErrorMessage(err, 'Gagal menyimpan profil')
  } finally {
    savingProfil.value = false
  }
}

async function gantiPassword() {
  savingPw.value = true
  pwMsg.value = pwErr.value = ''
  try {
    await api.post('/auth/me/password', pw.value)
    pw.value = { old_password: '', new_password: '' }
    pwMsg.value = 'Password berhasil diganti'
  } catch (err) {
    pwErr.value = apiErrorMessage(err, 'Gagal mengganti password')
  } finally {
    savingPw.value = false
  }
}
</script>
