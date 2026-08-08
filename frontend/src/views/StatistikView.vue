<template>
  <div>
    <div class="page-head">
      <h1>Statistik</h1>
    </div>

    <div v-if="error" class="alert error">{{ error }}</div>

    <!-- Card total -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 20px">
      <div class="card" style="margin-bottom: 0; text-align: center">
        <div style="font-size: 13px; color: var(--text-muted)">Total Kunjungan</div>
        <div style="font-size: 36px; font-weight: 800; color: var(--primary)">{{ stats.total_kunjungan ?? '—' }}</div>
      </div>
    </div>

    <div class="card">
      <h2>Kunjungan 7 Hari Terakhir</h2>
      <div v-if="maxJumlah > 0" class="bar-chart">
        <div v-for="d in stats.kunjungan_7_hari" :key="d.tanggal" class="bar-col">
          <div class="bar-value">{{ d.jumlah }}</div>
          <div class="bar" :style="{ height: barHeight(d.jumlah) + 'px' }" :title="d.tanggal"></div>
          <div class="bar-label">{{ shortDate(d.tanggal) }}</div>
        </div>
      </div>
      <div v-else class="empty">Belum ada kunjungan</div>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px">
      <div class="card">
        <h2>Diagnosa Terbanyak</h2>
        <table v-if="stats.diagnosa_terbanyak?.length">
          <thead>
            <tr><th>Diagnosa</th><th style="text-align: right">Jumlah</th></tr>
          </thead>
          <tbody>
            <tr v-for="(d, i) in stats.diagnosa_terbanyak" :key="i">
              <td>{{ d.diagnosa }}</td>
              <td style="text-align: right; font-weight: 600">{{ d.jumlah }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty">Belum ada data</div>
      </div>

      <div class="card">
        <h2>Dokter Teraktif</h2>
        <table v-if="stats.dokter_teraktif?.length">
          <thead>
            <tr><th>Dokter</th><th style="text-align: right">Pemeriksaan</th></tr>
          </thead>
          <tbody>
            <tr v-for="(d, i) in stats.dokter_teraktif" :key="i">
              <td>{{ d.nama }}</td>
              <td style="text-align: right; font-weight: 600">{{ d.jumlah }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty">Belum ada data</div>
      </div>
    </div>

    <p class="muted" style="font-size: 12px; margin-top: 14px">
      * Diagnosa dikelompokkan berdasar teks apa adanya (free-text, bukan kode ICD-10).
    </p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api, { apiErrorMessage } from '../api/client'

const stats = ref({})
const error = ref('')

const maxJumlah = computed(() =>
  Math.max(1, ...(stats.value.kunjungan_7_hari || []).map((d) => d.jumlah))
)

function barHeight(n) {
  return Math.max(4, Math.round((n / maxJumlah.value) * 160))
}

function shortDate(iso) {
  const [, m, d] = iso.split('-')
  return `${d}/${m}`
}

onMounted(async () => {
  try {
    const { data } = await api.get('/stats/overview')
    stats.value = data
  } catch (err) {
    error.value = apiErrorMessage(err, 'Gagal memuat statistik')
  }
})
</script>

<style scoped>
.bar-chart {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  height: 210px;
  padding-top: 8px;
}
.bar-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  height: 100%;
}
.bar {
  width: 70%;
  background: linear-gradient(180deg, var(--primary), var(--primary-dark));
  border-radius: 6px 6px 0 0;
  min-height: 4px;
}
.bar-value { font-size: 12px; font-weight: 700; margin-bottom: 4px; }
.bar-label { font-size: 11px; color: var(--text-muted); margin-top: 6px; }
@media (max-width: 768px) {
  .bar-chart { gap: 4px; }
  .bar { width: 80%; }
}
</style>
