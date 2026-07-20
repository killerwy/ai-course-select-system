<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listAuditsPage } from '../api'
import { userMessageForError } from '../admin-state'

const audits = ref([])
const loading = ref(false)
const meta = reactive({ page: 1, page_size: 5, total: 0 })
const filter = reactive({
  course_id: '',
  student_id: '',
  action: '',
  run_id: '',
  from: '',
  to: '',
  page: 1,
  page_size: 5,
})
const errorMessage = ref('')

async function loadAudits(filters = filter) {
  loading.value = true
  try {
    Object.assign(filter, filters)
    const page = await listAuditsPage(filter)
    audits.value = page.items
    Object.assign(meta, page.meta)
  } catch (error) {
    errorMessage.value = userMessageForError(error)
    ElMessage.error(errorMessage.value)
  } finally {
    loading.value = false
  }
}

function changePage(page) {
  filter.page = page
  loadAudits().catch(() => {})
}

onMounted(() => loadAudits())
</script>

<template>
  <div>
    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" class="global-alert" />
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>审计日志</span>
          <el-button @click="loadAudits()">刷新</el-button>
        </div>
      </template>
      <el-table :data="audits" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="120" show-overflow-tooltip />
        <el-table-column prop="action" label="操作" width="150" />
        <el-table-column prop="resource_type" label="资源类型" width="120" />
        <el-table-column prop="resource_id" label="资源ID" width="120" show-overflow-tooltip />
        <el-table-column prop="reason" label="原因" show-overflow-tooltip />
        <el-table-column prop="created_at" label="时间" width="180" />
      </el-table>
      <el-pagination
        v-if="meta.total > meta.page_size"
        :current-page="meta.page"
        :page-size="meta.page_size"
        :total="meta.total"
        layout="prev, pager, next"
        @current-change="changePage"
        class="pagination"
      />
    </el-card>
  </div>
</template>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}
</style>
