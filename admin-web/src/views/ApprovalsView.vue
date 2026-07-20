<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  decideCourseOperation,
  getRecalculationRun,
  listCourseOperationApprovals,
  listCourses,
} from '../api'
import { isTerminalRun, userMessageForError } from '../admin-state'
import ApprovalCenter from '../components/ApprovalCenter.vue'

const courseOperations = ref([])
const courses = ref([])
const latestRun = ref(null)
const loading = ref(false)
const auditLoading = ref(false)
const auditMeta = reactive({ page: 1, page_size: 5, total: 0 })
const filter = reactive({ status: '', course_id: '' })
const auditFilter = reactive({
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
let pollTimer

async function loadCourses() {
  try {
    courses.value = await listCourses({})
  } catch (error) {
    errorMessage.value = userMessageForError(error)
    ElMessage.error(errorMessage.value)
  }
}

async function loadApprovals(filters = filter) {
  loading.value = true
  try {
    Object.assign(filter, filters)
    courseOperations.value = await listCourseOperationApprovals({
      status: filter.status,
      course_id: filter.course_id,
    })
  } catch (error) {
    errorMessage.value = userMessageForError(error)
    ElMessage.error(errorMessage.value)
  } finally {
    loading.value = false
  }
}

async function refreshApprovals(
  approvalFilters = filter,
  auditFilters = auditFilter
) {
  await Promise.allSettled([
    loadApprovals(approvalFilters),
    // loadAudits({ ...auditFilters, page: 1 }),
  ])
}

async function pollRun(runId, notifyTerminal = true) {
  if (!runId) return null
  let attempt = 0
  clearTimeout(pollTimer)
  const poll = async () => {
    const run = await getRecalculationRun(runId)
    latestRun.value = run
    attempt += 1
    if (isTerminalRun(run?.status) || attempt >= 30) return run
    await new Promise(resolve => {
      pollTimer = setTimeout(resolve, 500)
    })
    return poll()
  }
  try {
    const result = await poll()
    if (result?.status && !isTerminalRun(result.status)) {
      ElMessage.warning('重算仍在执行，请在审批中心刷新查看')
    }
    if (notifyTerminal && result?.status && isTerminalRun(result.status)) {
      notifyRun(result)
    }
    await loadApprovals()
    return result
  } catch (error) {
    errorMessage.value = userMessageForError(error)
    ElMessage.error(errorMessage.value)
    throw error
  }
}

function notifyRun(run) {
  const summary = run.summary || {}
  ElMessage({
    title: run.status === 'SUCCEEDED' ? '课程变更已生效' : '候补重算未完成',
    message: `检查 ${summary.checked || 0} 人 · 晋级 ${summary.promoted || 0} · 跳过 ${summary.skipped || 0} · 继续候补 ${summary.waiting || 0} · 错误 ${summary.errors || 0}。`,
    type: run.status === 'SUCCEEDED' ? 'success' : 'error',
    duration: 5200,
  })
}

async function handleCourseOperationDecision(operation, decision, comment) {
  try {
    const result = await decideCourseOperation(operation.id, decision, comment)
    ElMessage.success(
      decision === 'approve'
        ? '课程操作审批已通过，数据库已更新'
        : '课程操作申请已拒绝'
    )
    if (
      decision === 'approve' &&
      ['UPDATE', 'CANCEL'].includes(operation.operation) &&
      result?.run
    ) {
      if (result.run.id && !isTerminalRun(result.run.status)) {
        await pollRun(result.run.id, false)
      }
    }
    await loadApprovals()
    return result
  } catch (error) {
    errorMessage.value = userMessageForError(error)
    ElMessage.error(errorMessage.value)
    throw error
  }
}

onMounted(() => {
  loadCourses()
  loadApprovals()
})
</script>

<template>
  <div>
    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" class="global-alert" />
    <ApprovalCenter
      :course-operations="courseOperations"
      :audits="[]"
      :courses="courses"
      :latest-run="latestRun"
      :loading="loading"
      :audit-loading="auditLoading"
      :audit-meta="auditMeta"
      :on-refresh="refreshApprovals"
      :on-operation-decide="handleCourseOperationDecision"
    />
  </div>
</template>
