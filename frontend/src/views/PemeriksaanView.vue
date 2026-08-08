<template>
  <div>
    <div class="page-head">
      <h1>Pemeriksaan</h1>
      <router-link to="/antrian" class="btn secondary">← Kembali ke Antrian</router-link>
    </div>

    <div v-if="visit" class="card">
      <div style="display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px">
        <div>
          <h2 style="margin-bottom: 4px">{{ visit.patient?.nama }}</h2>
          <div class="muted">
            {{ visit.patient?.no_rm }} · Antrian No. <strong>{{ visit.antrian_no }}</strong>
            <span class="badge" :class="visit.status" style="margin-left: 8px">{{ visit.status }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ⚠ Riwayat alergi obat — SELALU tampil sebelum anamnesis -->
    <div v-if="visit" class="card alert-alergi-obat" :class="{ kosong: !visit.patient?.riwayat_alergi_obat }">
      <div class="alert-icon">⚠️</div>
      <div>
        <div class="alert-title">Riwayat Alergi Obat</div>
        <div class="alert-content">
          {{ visit.patient?.riwayat_alergi_obat || 'Tidak ada alergi obat tercatat' }}
        </div>
      </div>
    </div>

    <div v-if="visit" class="card">
      <div v-if="error" class="alert error">{{ error }}</div>
      <div v-if="success" class="alert success">{{ success }}</div>

      <form @submit.prevent="submit">
        <h3>Anamnesa</h3>
        <div class="form-grid" style="margin-bottom: 14px">
          <div class="form-group full">
            <label>Keluhan / Anamnesa</label>
            <textarea v-model="form.anamnesa" rows="3" placeholder="Keluhan utama, riwayat penyakit, dll."></textarea>
          </div>
        </div>

        <h3>Tanda Vital</h3>
        <div class="form-grid" style="margin-bottom: 14px">
          <div class="form-group"><label>TB (cm)</label><input v-model.number="form.tb" type="number" step="0.1" /></div>
          <div class="form-group"><label>BB (kg)</label><input v-model.number="form.bb" type="number" step="0.1" /></div>
          <div class="form-group"><label>TD (mmHg)</label><input v-model="form.td" placeholder="120/80" /></div>
          <div class="form-group"><label>Suhu (°C)</label><input v-model.number="form.suhu" type="number" step="0.1" /></div>
          <div class="form-group"><label>HR (nadi/menit)</label><input v-model.number="form.hr" type="number" /></div>
          <div class="form-group"><label>RR (napas/menit)</label><input v-model.number="form.rr" type="number" /></div>
        </div>

        <h3>Pemeriksaan & Diagnosis</h3>
        <div class="form-grid">
          <div class="form-group full">
            <label>Pemeriksaan Fisik</label>
            <textarea v-model="form.pemeriksaan_fisik" rows="3"></textarea>
          </div>
          <div class="form-group full">
            <label>Diagnosa</label>
            <textarea v-model="form.diagnosa" rows="2"></textarea>
          </div>
          <div class="form-group full">
            <label>Terapi</label>
            <textarea v-model="form.terapi" rows="2" placeholder="Obat, tindakan, rujukan..."></textarea>
          </div>
          <div class="form-group">
            <label>Tanggal Pemeriksaan</label>
            <input v-model="form.tgl_pemeriksaan" type="date" />
          </div>
        </div>

        <div class="form-actions">
          <button class="btn" :disabled="loading">{{ loading ? 'Menyimpan...' : 'Simpan Pemeriksaan' }}</button>
          <button type="button" class="btn secondary" @click="cetak('rekam-medis')">🖨️ Rekam Medis</button>
          <button type="button" class="btn secondary" @click="cetak('resep')">🖨️ Resep</button>
        </div>
        <p class="muted" style="margin-top: 10px; font-size: 12px">
          Terisi diagnosa + terapi → status otomatis <strong>selesai</strong> dan masuk riwayat pasien.
        </p>
      </form>
    </div>
    <div v-else class="empty">Memuat data pemeriksaan...</div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api, { apiErrorMessage, openPdf } from '../api/client'

const route = useRoute()
const router = useRouter()
const visit = ref(null)
const form = ref({
  tgl_pemeriksaan: new Date().toISOString().slice(0, 10),
  anamnesa: '',
  tb: null, bb: null, td: '', suhu: null, hr: null, rr: null,
  pemeriksaan_fisik: '',
  diagnosa: '',
  terapi: '',
})
const loading = ref(false)
const error = ref('')
const success = ref('')

onMounted(async () => {
  try {
    const { data } = await api.get(`/visits/${route.params.visitId}`)
    visit.value = data
    form.value = {
      tgl_pemeriksaan: data.tgl_pemeriksaan || new Date().toISOString().slice(0, 10),
      anamnesa: data.anamnesa || '',
      tb: data.tb, bb: data.bb, td: data.td || '', suhu: data.suhu, hr: data.hr, rr: data.rr,
      pemeriksaan_fisik: data.pemeriksaan_fisik || '',
      diagnosa: data.diagnosa || '',
      terapi: data.terapi || '',
    }
  } catch (err) {
    error.value = apiErrorMessage(err, 'Gagal memuat pemeriksaan')
  }
})

async function cetak(jenis) {
  try {
    await openPdf(`/visits/${route.params.visitId}/pdf/${jenis}`)
  } catch (err) {
    error.value = apiErrorMessage(err, 'Gagal membuat PDF')
  }
}

async function submit() {
  loading.value = true
  error.value = success.value = ''
  const body = {}
  for (const [k, v] of Object.entries(form.value)) {
    if (v !== null && v !== '') body[k] = v
  }
  try {
    const { data } = await api.put(`/visits/${route.params.visitId}`, body)
    visit.value = data
    success.value = data.status === 'selesai'
      ? 'Pemeriksaan selesai dan tersimpan ke riwayat pasien.'
      : 'Tersimpan (draft). Lengkapi diagnosa & terapi untuk menyelesaikan.'
  } catch (err) {
    error.value = apiErrorMessage(err, 'Gagal menyimpan pemeriksaan')
  } finally {
    loading.value = false
  }
}
</script>
