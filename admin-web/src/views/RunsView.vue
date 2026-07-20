<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listRuns } from '../api'
import { userMessageForError } from '../admin-state'

const runs = ref([])
const loading = ref(false)
const errorMessage = ref('')

async function loadRuns() {
  loading.value = true
  errorMessage.value = ''
  try {
    runs.value = await listRuns()
  } catch (error) {
    errorMessage.value = userMessageForError(error)
    ElMessage.error(errorMessage.value)
  } finally {
    loading.value = false
  }
}

function statusType(status) {
  switch (status) {
    case 'SUCCEEDED':
      return 'success'
    case 'FAILED':
      return 'danger'
    case 'RUNNING':
      return 'warning'
    case 'PENDING':
      return 'info'
    default:
      return 'info'
  }
}

onMounted(() => loadRuns())
</script>

<template>
  <div>
    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" class="global-alert" />
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>重算记录</span>
          <el-button @click="loadRuns()">刷新</el-button>
        </div>
      </template>
      <el-table :data="runs" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="200" show-overflow-tooltip />
        <el-table-column prop="trigger_type" label="触发类型" width="120" />
        <el-table-column prop="course_id" label="课程ID" width="150" show-overflow-tooltip />
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column prop="finished_at" label="完成时间" width="180" />
      </el-table>
      <el-empty v-if="!loading && runs.length === 0" description="暂无重算记录" />
    </el-card>
  </div>
</template>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
