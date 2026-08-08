<template>
  <div>
    <div class="page-head">
      <h1>Riwayat Pasien</h1>
      <router-link to="/pasien" class="btn secondary">← Kembali</router-link>
    </div>

    <div v-if="pasien" class="card">
      <div style="display: flex; justify-content: space-between; flex-wrap: wrap; gap: 10px">
        <div>
          <h2 style="margin-bottom: 6px">{{ pasien.nama }}</h2>
          <div class="muted" style="line-height: 1.7">
            <strong>{{ pasien.no_rm }}</strong> · {{ pasien.jenis_identitas }} {{ pasien.no_identitas || '—' }}
            <span v-if="pasien.usia != null"> · {{ pasien.usia }} tahun</span><br />
            {{ pasien.alamat || '—' }} · HP: {{ pasien.no_hp || '—' }}<br />
            <span class="muted" style="font-size: 12px">
              {{ pasien.pekerjaan || '—' }} · {{ pasien.agama || '—' }} · {{ pasien.kewarganegaraan || '—' }} · {{ pasien.status_perkawinan || '—' }}
            </span>
          </div>
          <div v-if="pasien.riwayat_alergi" style="margin-top: 8px">
            <span class="badge" style="background: #fef2f2; color: var(--danger)">⚠️ Alergi: {{ pasien.riwayat_alergi }}</span>
          </div>
        </div>
        <div class="row-actions">
          <router-link :to="`/pasien/${pasien.id}/edit`" class="btn small secondary" v-if="canTambah">Edit</router-link>
          <button v-if="canDaftar" class="btn small" @click="daftarAntrian">+ Daftar Antrian</button>
        </div>
      </div>
    </div>

    <div class="card">
      <h2>Riwayat Pemeriksaan ({{ riwayat.length }})</h2>

      <table v-if="riwayat.length">
        <thead>
          <tr>
            <th>Tanggal</th>
            <th>Dokter</th>
            <th>Diagnosa</th>
            <th>Terapi</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="v in riwayat" :key="v.id">
            <td style="white-space: nowrap">{{ v.tgl_pemeriksaan || '—' }}</td>
            <td>{{ v.doctor?.nama || '—' }}</td>
            <td>{{ v.diagnosa || '—' }}</td>
            <td>{{ v.terapi || '—' }}</td>
            <td>
              <button class="btn small secondary" @click="toggle(v.id)">
                {{ expanded === v.id ? 'Tutup' : 'Detail' }}
              </button>
            </td>
          </tr>
          <tr v-if="expandedVisit">
            <td colspan="5" style="background: #f8fafc">
              <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-bottom: 12px">
                <div><strong>TB:</strong> {{ expandedVisit.tb ?? '—' }} cm</div>
                <div><strong>BB:</strong> {{ expandedVisit.bb ?? '—' }} kg</div>
                <div><strong>TD:</strong> {{ expandedVisit.td || '—' }} mmHg</div>
                <div><strong>Suhu:</strong> {{ expandedVisit.suhu ?? '—' }} °C</div>
                <div><strong>HR:</strong> {{ expandedVisit.hr ?? '—' }} x/menit</div>
                <div><strong>RR:</strong> {{ expandedVisit.rr ?? '—' }} x/menit</div>
              </div>
              <div style="line-height: 1.7">
                <p><strong>Anamnesa:</strong> {{ expandedVisit.anamnesa || '—' }}</p>
                <p><strong>Pemeriksaan Fisik:</strong> {{ expandedVisit.pemeriksaan_fisik || '—' }}</p>
                <p><strong>Diagnosa:</strong> {{ expandedVisit.diagnosa || '—' }}</p>
                <p><strong>Terapi:</strong> {{ expandedVisit.terapi || '—' }}</p>
              </div>
              <div class="row-actions" style="margin-top: 12px">
                <button class="btn small secondary" @click="cetak(`/visits/${expandedVisit.id}/pdf/rekam-medis`)">🖨️ Cetak Rekam Medis</button>
                <button class="btn small secondary" @click="cetak(`/visits/${expandedVisit.id}/pdf/resep`)">🖨️ Cetak Resep</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty">Belum ada riwayat pemeriksaan</div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import api, { apiErrorMessage, openPdf } from '../api/client'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const auth = useAuthStore()
const pasien = ref(null)
const riwayat = ref([])
const expanded = ref(null)

const canTambah = computed(() => ['admin', 'dokter'].includes(auth.role))
const canDaftar = computed(() => ['admin', 'dokter'].includes(auth.role))
const expandedVisit = computed(() => riwayat.value.find((v) => v.id === expanded.value))

function toggle(id) {
  expanded.value = expanded.value === id ? null : id
}

async function cetak(url) {
  try {
    await openPdf(url)
  } catch (err) {
    alert(apiErrorMessage(err, 'Gagal membuat PDF'))
  }
}

async function daftarAntrian() {
  try {
    const { data } = await api.post('/antrian', { patient_id: pasien.value.id })
    alert(`${pasien.value.nama} dapat nomor antrian ${data.antrian_no}`)
  } catch (err) {
    alert(apiErrorMessage(err, 'Gagal daftar antrian'))
  }
}

onMounted(async () => {
  try {
    const [pRes, rRes] = await Promise.all([
      api.get(`/patients/${route.params.id}`),
      api.get(`/visits/riwayat/${route.params.id}`),
    ])
    pasien.value = pRes.data
    riwayat.value = rRes.data
  } catch (err) {
    alert(apiErrorMessage(err, 'Gagal memuat data'))
  }
})
</script>
