<template>
  <div>
    <div class="page-head">
      <h1>Data Pasien</h1>
      <router-link to="/pasien/baru" class="btn" v-if="canTambah">+ Pasien Baru</router-link>
    </div>

    <div class="card">
      <div class="search-row">
        <input v-model="q" placeholder="Cari nama atau nomor RM..." @keyup.enter="cari" />
        <button class="btn secondary" @click="cari">Cari</button>
      </div>

      <table v-if="pasien.length">
        <thead>
          <tr>
            <th>No. RM</th>
            <th>Nama</th>
            <th>Usia</th>
            <th>No. HP</th>
            <th>Identitas</th>
            <th>Alergi</th>
            <th style="text-align: right">Aksi</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in pasien" :key="p.id">
            <td style="font-weight: 600">{{ p.no_rm }}</td>
            <td>{{ p.nama }}</td>
            <td>{{ p.usia != null ? p.usia + ' th' : '—' }}</td>
            <td>{{ p.no_hp || '—' }}</td>
            <td class="muted" style="font-size: 12px">
              {{ p.jenis_identitas }} {{ p.no_identitas || '' }}
            </td>
            <td>{{ p.riwayat_alergi || '—' }}</td>
            <td>
              <div class="row-actions" style="justify-content: flex-end">
                <router-link :to="`/pasien/${p.id}`" class="btn small secondary">Riwayat</router-link>
                <router-link :to="`/pasien/${p.id}/edit`" class="btn small secondary" v-if="canTambah">Edit</router-link>
                <button v-if="canDaftar" class="btn small" @click="daftarAntrian(p)">+ Antrian</button>
                <button v-if="canHapus" class="btn small" style="color: var(--danger); border-color: var(--danger)" @click="hapusPasien(p)">Hapus</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty">Belum ada data pasien</div>
      <Pagination :page="page" :total-pages="totalPages" :total="total" @update:page="onPageChange" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api, { apiErrorMessage } from '../api/client'
import { useAuthStore } from '../stores/auth'
import Pagination from '../components/Pagination.vue'

const auth = useAuthStore()
const pasien = ref([])
const q = ref('')
const page = ref(1)
const totalPages = ref(1)
const total = ref(0)

const canTambah = computed(() => ['admin', 'dokter'].includes(auth.role))
const canDaftar = computed(() => ['admin', 'dokter'].includes(auth.role))
const canHapus = computed(() => auth.role === 'admin')

async function muat() {
  try {
    const { data } = await api.get('/patients', { params: { q: q.value, page: page.value } })
    pasien.value = data.items
    totalPages.value = data.total_pages
    total.value = data.total
  } catch (err) {
    alert(apiErrorMessage(err, 'Gagal memuat pasien'))
  }
}

function cari() {
  page.value = 1
  muat()
}

function onPageChange(p) {
  page.value = p
  muat()
}

async function daftarAntrian(p) {
  try {
    const { data } = await api.post('/antrian', { patient_id: p.id })
    alert(`${p.nama} dapat nomor antrian ${data.antrian_no}`)
  } catch (err) {
    alert(apiErrorMessage(err, 'Gagal daftar antrian'))
  }
}

async function hapusPasien(p) {
  if (!confirm(`Hapus data pasien "${p.nama}" (${p.no_rm}) secara permanen? Tindakan ini tidak bisa dibatalkan.`)) return
  try {
    await api.delete(`/patients/${p.id}`)
    await muat()
  } catch (err) {
    alert(apiErrorMessage(err, 'Gagal menghapus pasien'))
  }
}

onMounted(muat)
</script>
