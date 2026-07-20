<script setup>
defineProps({ loading: Boolean, error: String, empty: Boolean, emptyText: { type: String, default: '暂无数据' } })
defineEmits(['retry'])
</script>

<template>
  <el-skeleton v-if="loading" :rows="4" animated />
  <el-result v-else-if="error" icon="error" title="加载失败" :sub-title="error">
    <template #extra><el-button type="primary" @click="$emit('retry')">重试</el-button></template>
  </el-result>
  <el-empty v-else-if="empty" :description="emptyText" />
  <slot v-else />
</template>
