<template>
  <div>
    <div class="page-head">
      <h1>Antrian Hari Ini</h1>
      <div class="row-actions">
        <router-link to="/pasien" class="btn secondary">Cari Pasien</router-link>
        <router-link to="/pasien/baru" class="btn" v-if="canDaftar">+ Pasien Baru</router-link>
      </div>
    </div>

    <!-- Nomor sedang dipanggil -->
    <div class="now-banner" v-if="saatIni">
      <div>
        <div class="label">Sedang Dipanggil</div>
        <div class="number">{{ saatIni.visit.antrian_no }}</div>
      </div>
      <div class="patient">
        <div class="name">{{ saatIni.patient.nama }}</div>
        <div class="label">{{ saatIni.patient.no_rm }}</div>
      </div>
    </div>
    <div class="now-banner empty" v-else>
      <div>
        <div class="label">Sedang Dipanggil</div>
        <div class="number" style="font-size: 28px">—</div>
      </div>
      <div class="patient"><div class="label">Belum ada pasien dipanggil</div></div>
    </div>

    <!-- Pasien berikutnya: satu tombol raksasa untuk aksi utama -->
    <div class="card next-action" v-if="canPanggil && berikutnya">
      <div class="next-label">➡️ Pasien Berikutnya</div>
      <div class="next-name">{{ berikutnya.patient.nama }} <span class="next-no">No. {{ berikutnya.visit.antrian_no }}</span></div>
      <button class="btn-giant" @click="panggil(berikutnya)">📢 Panggil Pasien Ini</button>
    </div>

    <!-- Daftarkan pasien ke antrian -->
    <div class="card" v-if="canDaftar">
      <h2>Daftarkan Pasien ke Antrian</h2>
      <div class="search-row">
        <input
          v-model="cari"
          placeholder="Cari pasien (nama / nomor RM)..."
          @input="cariPasien"
        />
        <select v-model="selectedPatientId" style="padding: 9px 12px; border: 1px solid var(--border); border-radius: 8px; min-width: 220px">
          <option :value="null" disabled>Pilih pasien</option>
          <option v-for="p in hasilCari" :key="p.id" :value="p.id">
            {{ p.no_rm }} — {{ p.nama }}
          </option>
        </select>
        <button class="btn" :disabled="!selectedPatientId || loadingDaftar" @click="daftarAntrian">
          {{ loadingDaftar ? '...' : 'Ambil Antrian' }}
        </button>
      </div>
      <p v-if="daftarMsg" class="alert success">{{ daftarMsg }}</p>
      <p v-if="daftarErr" class="alert error">{{ daftarErr }}</p>
    </div>

    <!-- Daftar antrian aktif -->
    <div class="card">
      <h2>Daftar Antrian ({{ total }})</h2>
      <table v-if="antrian.length">
        <thead>
          <tr>
            <th>No</th>
            <th>Pasien</th>
            <th>Status</th>
            <th>Dokter</th>
            <th style="text-align: right">Aksi</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in antrian" :key="item.visit.id">
            <td style="font-weight: 700">{{ item.visit.antrian_no }}</td>
            <td>
              <router-link :to="`/pasien/${item.patient.id}`" style="color: var(--primary); font-weight: 600">
                {{ item.patient.nama }}
              </router-link>
              <div class="muted" style="font-size: 12px">{{ item.patient.no_rm }}</div>
            </td>
            <td><span class="badge" :class="item.visit.status">{{ statusLabel(item.visit.status) }}</span></td>
            <td>{{ item.doctor?.nama || '—' }}</td>
            <td>
              <div class="row-actions" style="justify-content: flex-end">
                <button
                  v-if="canPanggil && ['menunggu', 'diperiksa'].includes(item.visit.status)"
                  class="btn small"
                  @click="panggil(item)"
                >
                  📢 {{ item.visit.status === 'diperiksa' ? 'Panggil Ulang' : 'Panggil' }}
                </button>
                <router-link
                  v-if="canPeriksa && ['dipanggil', 'diperiksa'].includes(item.visit.status)"
                  :to="`/pemeriksaan/${item.visit.id}`"
                  class="btn small secondary"
                >
                  ✍️ Periksa
                </router-link>
                <router-link v-if="canPeriksa && item.visit.status === 'menunggu'" :to="`/pemeriksaan/${item.visit.id}`" class="btn small secondary">Periksa</router-link>
                <button
                  v-if="canPanggil && ['menunggu', 'dipanggil', 'diperiksa'].includes(item.visit.status)"
                  class="btn small danger"
                  @click="batalkan(item)"
                >
                  ✕ Batal
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty">Tidak ada antrian aktif</div>
      <Pagination :page="page" :total-pages="totalPages" :total="total" @update:page="onPageChange" />
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import api, { apiErrorMessage } from '../api/client'
import { useAuthStore } from '../stores/auth'
import Pagination from '../components/Pagination.vue'

const auth = useAuthStore()
const antrian = ref([])
const saatIni = ref(null)
const cari = ref('')
const hasilCari = ref([])
const selectedPatientId = ref(null)
const loadingDaftar = ref(false)
const daftarMsg = ref('')
const daftarErr = ref('')
const page = ref(1)
const totalPages = ref(1)
const total = ref(0)

const canDaftar = computed(() => ['admin', 'dokter'].includes(auth.role))
const canPanggil = computed(() => ['admin', 'dokter'].includes(auth.role))
const canPeriksa = computed(() => ['admin', 'dokter'].includes(auth.role))

// Pasien antrian berikutnya (status menunggu, urutan terkecil — API sudah sort antrian_no asc)
const berikutnya = computed(() =>
  antrian.value.find(item => item.visit.status === 'menunggu')
)

// Label status manusiawi untuk dokter awam (murni display, backend tetap pakai kode status)
const STATUS_LABEL = {
  menunggu: 'Menunggu Giliran',
  dipanggil: 'Sedang Dipanggil',
  diperiksa: 'Sedang Diperiksa (Draft)',
  selesai: 'Selesai',
  batal: 'Dibatalkan',
}
function statusLabel(s) { return STATUS_LABEL[s] || s }

let timer = null

async function muatAntrian() {
  try {
    const [listRes, kiniRes] = await Promise.all([
      api.get('/antrian', { params: { page: page.value } }),
      api.get('/antrian/saat-ini'),
    ])
    antrian.value = listRes.data.items
    totalPages.value = listRes.data.total_pages
    total.value = listRes.data.total
    saatIni.value = kiniRes.data
  } catch (err) {
    daftarErr.value = apiErrorMessage(err, 'Gagal memuat antrian')
  }
}

function onPageChange(p) {
  page.value = p
  muatAntrian()
}

async function cariPasien() {
  if (!cari.value.trim()) { hasilCari.value = []; return }
  try {
    const { data } = await api.get('/patients', { params: { q: cari.value, per_page: 20 } })
    hasilCari.value = data.items
  } catch (err) {
    daftarErr.value = apiErrorMessage(err)
  }
}

async function daftarAntrian() {
  loadingDaftar.value = true
  daftarMsg.value = daftarErr.value = ''
  try {
    const { data } = await api.post('/antrian', { patient_id: selectedPatientId.value })
    daftarMsg.value = `${data.patient?.nama || 'Pasien'} dapat nomor antrian ${data.antrian_no}`
    selectedPatientId.value = null
    cari.value = ''
    hasilCari.value = []
    await muatAntrian()
  } catch (err) {
    daftarErr.value = apiErrorMessage(err, 'Gagal daftar antrian')
  } finally {
    loadingDaftar.value = false
  }
}

async function panggil(item) {
  daftarErr.value = ''
  try {
    await api.post(`/antrian/${item.visit.id}/panggil`)
    await muatAntrian()
  } catch (err) {
    daftarErr.value = apiErrorMessage(err, 'Gagal memanggil')
  }
}

async function batalkan(item) {
  if (!confirm(`Batalkan antrian no. ${item.visit.antrian_no} (${item.patient.nama})?`)) return
  daftarErr.value = ''
  try {
    await api.post(`/antrian/${item.visit.id}/batal`)
    await muatAntrian()
  } catch (err) {
    daftarErr.value = apiErrorMessage(err, 'Gagal membatalkan antrian')
  }
}

onMounted(() => {
  muatAntrian()
  timer = setInterval(muatAntrian, 5000) // refresh live tiap 5 detik
})
onBeforeUnmount(() => clearInterval(timer))
</script>
