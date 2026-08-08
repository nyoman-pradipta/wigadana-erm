<template>
  <div>
    <div class="page-head">
      <h1>{{ editMode ? 'Edit Pasien' : 'Pasien Baru' }}</h1>
    </div>

    <div class="card" style="max-width: 720px">
      <div v-if="error" class="alert error">{{ error }}</div>

      <form @submit.prevent="submit">
        <div class="form-grid">
          <div class="form-group full">
            <label>Nama Lengkap *</label>
            <input v-model="form.nama" required />
          </div>
          <div class="form-group full">
            <label>Alamat</label>
            <textarea v-model="form.alamat" rows="2"></textarea>
          </div>
          <div class="form-group">
            <label>Jenis Identitas</label>
            <select v-model="form.jenis_identitas">
              <option>KTP</option>
              <option>KITAS</option>
              <option>PASSPORT</option>
            </select>
          </div>
          <div class="form-group">
            <label>No. KTP / KITAS / PASSPORT</label>
            <input v-model="form.no_identitas" />
          </div>
          <div class="form-group">
            <label>No. HP</label>
            <input v-model="form.no_hp" placeholder="08xxxxxxxxxx" />
          </div>
          <div class="form-group full">
            <label>Riwayat Alergi Obat *</label>
            <textarea v-model="form.riwayat_alergi_obat" rows="2" placeholder="cth: penisilin, amoxicillin — kosongkan kalau TIDAK ADA alergi obat"></textarea>
          </div>
          <div class="form-group full">
            <label>Alergi Lain (makanan, debu, dll)</label>
            <textarea v-model="form.riwayat_alergi" rows="2" placeholder="cth: seafood, kacang, debu..."></textarea>
          </div>
        </div>

        <div class="form-actions">
          <button class="btn" :disabled="loading">{{ loading ? 'Menyimpan...' : 'Simpan' }}</button>
          <router-link to="/pasien" class="btn secondary">Batal</router-link>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api, { apiErrorMessage } from '../api/client'

const route = useRoute()
const router = useRouter()
const editMode = ref(!!route.params.id)

const form = ref({
  nama: '',
  alamat: '',
  jenis_identitas: 'KTP',
  no_identitas: '',
  no_hp: '',
  riwayat_alergi: '',
  riwayat_alergi_obat: '',
})
const loading = ref(false)
const error = ref('')

onMounted(async () => {
  if (!editMode.value) return
  try {
    const { data } = await api.get(`/patients/${route.params.id}`)
    form.value = {
      nama: data.nama,
      alamat: data.alamat,
      jenis_identitas: data.jenis_identitas,
      no_identitas: data.no_identitas,
      no_hp: data.no_hp,
      riwayat_alergi: data.riwayat_alergi,
      riwayat_alergi_obat: data.riwayat_alergi_obat,
    }
  } catch (err) {
    error.value = apiErrorMessage(err, 'Gagal memuat data pasien')
  }
})

async function submit() {
  loading.value = true
  error.value = ''
  try {
    if (editMode.value) {
      await api.put(`/patients/${route.params.id}`, form.value)
    } else {
      await api.post('/patients', form.value)
    }
    router.push('/pasien')
  } catch (err) {
    error.value = apiErrorMessage(err, 'Gagal menyimpan pasien')
  } finally {
    loading.value = false
  }
}
</script>
