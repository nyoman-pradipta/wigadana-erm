<template>
  <div class="pagination" v-if="totalPages > 1">
    <button class="btn small secondary" :disabled="page <= 1" @click="$emit('update:page', page - 1)">‹ Prev</button>
    <span class="pagination-info">Halaman {{ page }} / {{ totalPages }} ({{ total }} data)</span>
    <button class="btn small secondary" :disabled="page >= totalPages" @click="$emit('update:page', page + 1)">Next ›</button>
  </div>
</template>

<script setup>
defineProps({
  page: { type: Number, required: true },
  totalPages: { type: Number, required: true },
  total: { type: Number, required: true },
})
defineEmits(['update:page'])
</script>

<style scoped>
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid var(--border);
}
.pagination-info { font-size: 12px; color: var(--text-muted); }
</style>
