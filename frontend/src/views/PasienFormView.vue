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
          <div class="form-group">
            <label>Tanggal Lahir</label>
            <input v-model="form.tgl_lahir" type="date" />
          </div>
          <div class="form-group">
            <label>Pekerjaan</label>
            <input v-model="form.pekerjaan" />
          </div>
          <div class="form-group">
            <label>Agama</label>
            <select v-model="form.agama">
              <option value="">— pilih —</option>
              <option>Islam</option>
              <option>Kristen</option>
              <option>Katolik</option>
              <option>Hindu</option>
              <option>Buddha</option>
              <option>Konghucu</option>
              <option>Lainnya</option>
            </select>
          </div>
          <div class="form-group">
            <label>Kewarganegaraan</label>
            <select v-model="form.kewarganegaraan">
              <option>WNI</option>
              <option>WNA</option>
            </select>
          </div>
          <div class="form-group">
            <label>Status Perkawinan</label>
            <select v-model="form.status_perkawinan">
              <option value="">— pilih —</option>
              <option>Belum Menikah</option>
              <option>Menikah</option>
              <option>Cerai Hidup</option>
              <option>Cerai Mati</option>
            </select>
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
  tgl_lahir: '',
  pekerjaan: '',
  agama: '',
  kewarganegaraan: 'WNI',
  status_perkawinan: '',
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
      tgl_lahir: data.tgl_lahir || '',
      pekerjaan: data.pekerjaan || '',
      agama: data.agama || '',
      kewarganegaraan: data.kewarganegaraan || 'WNI',
      status_perkawinan: data.status_perkawinan || '',
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
