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
      <h2>Riwayat Pemeriksaan ({{ total }})</h2>

      <table v-if="riwayat.length">
        <thead>
          <tr>
            <th>Tanggal</th>
            <th>Dokter</th>
            <th>Diagnosa</th>
            <th>Terapi</th>
            <th style="text-align: right">Aksi</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="v in riwayat" :key="v.id">
            <td style="white-space: nowrap">{{ v.tgl_pemeriksaan || '—' }}</td>
            <td>{{ v.doctor?.nama || '—' }}</td>
            <td>{{ v.diagnosa || '—' }}</td>
            <td>{{ v.terapi || '—' }}</td>
            <td>
              <div class="row-actions" style="justify-content: flex-end">
                <button class="btn small secondary" @click="toggle(v.id)">
                  {{ expanded === v.id ? 'Tutup' : 'Detail' }}
                </button>
                <router-link v-if="canEditVisit(v)" :to="`/pemeriksaan/${v.id}`" class="btn small secondary">Edit</router-link>
                <button v-if="canHapus" class="btn small" style="color: var(--danger); border-color: var(--danger)" @click="hapusRiwayat(v)">Hapus</button>
              </div>
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
      <Pagination :page="page" :total-pages="totalPages" :total="total" @update:page="onPageChange" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import api, { apiErrorMessage, openPdf } from '../api/client'
import { useAuthStore } from '../stores/auth'
import Pagination from '../components/Pagination.vue'

const route = useRoute()
const auth = useAuthStore()
const pasien = ref(null)
const riwayat = ref([])
const expanded = ref(null)
const page = ref(1)
const totalPages = ref(1)
const total = ref(0)

const canTambah = computed(() => ['admin', 'dokter'].includes(auth.role))
const canDaftar = computed(() => ['admin', 'dokter'].includes(auth.role))
const canHapus = computed(() => auth.role === 'admin')
const expandedVisit = computed(() => riwayat.value.find((v) => v.id === expanded.value))

function canEditVisit(v) {
  if (auth.role === 'admin') return true
  return auth.role === 'dokter' && v.doctor_id === auth.user?.id
}

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

async function hapusRiwayat(v) {
  if (!confirm(`Hapus riwayat pemeriksaan tanggal ${v.tgl_pemeriksaan || '-'} secara permanen? Tindakan ini tidak bisa dibatalkan.`)) return
  try {
    await api.delete(`/visits/${v.id}`)
    if (expanded.value === v.id) expanded.value = null
    await muatRiwayat()
  } catch (err) {
    alert(apiErrorMessage(err, 'Gagal menghapus riwayat'))
  }
}

function onPageChange(p) {
  page.value = p
  muatRiwayat()
}

async function muatRiwayat() {
  const { data } = await api.get(`/visits/riwayat/${route.params.id}`, { params: { page: page.value } })
  riwayat.value = data.items
  totalPages.value = data.total_pages
  total.value = data.total
}

onMounted(async () => {
  try {
    const [pRes] = await Promise.all([
      api.get(`/patients/${route.params.id}`),
      muatRiwayat(),
    ])
    pasien.value = pRes.data
  } catch (err) {
    alert(apiErrorMessage(err, 'Gagal memuat data'))
  }
})
</script>
