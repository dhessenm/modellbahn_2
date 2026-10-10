<script setup lang="ts">
defineProps<{
  title: string
  description?: string
}>()
</script>

<template>
  <main class="coming-soon">
    <h1>{{ title }}</h1>
    <p class="badge">In Entwicklung</p>
    <p v-if="description" class="desc">{{ description }}</p>
  </main>
</template>

<style scoped>
.coming-soon {
  max-width: 640px;
  margin: 0 auto;
  padding: 2rem 1rem;
  text-align: center;
}
h1 {
  margin: 0 0 0.5rem;
}
.badge {
  display: inline-block;
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  background: #3a3a1a;
  color: #e7e79b;
  font-size: 0.85rem;
}
.desc {
  opacity: 0.7;
  margin-top: 1rem;
}
</style>
