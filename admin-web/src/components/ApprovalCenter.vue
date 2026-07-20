<script setup>
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  auditActionLabel,
  auditChangeDescription,
  auditDescription,
  auditResourceLabel,
  describeCourseOperation,
  describeRunResult,
  statusTagType,
  validateRequiredText,
} from '../admin-state'

const props = defineProps({
  courseOperations: { type: Array, default: () => [] },
  audits: { type: Array, default: () => [] },
  courses: { type: Array, default: () => [] },
  latestRun: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  auditLoading: { type: Boolean, default: false },
  auditMeta: { type: Object, default: () => ({ page: 1, page_size: 5, total: 0 }) },
  onRefresh: { type: Function, required: true },
  onOperationDecide: { type: Function, required: true },
  onAuditPage: { type: Function, required: true },
})

const filters = ref({ status: '', course_id: '' })
const auditFilters = ref({ action: '', course_id: '' })
const selectedAudit = ref(null)
const auditVisible = ref(false)
const operationDecisionVisible = ref(false)
const selectedOperation = ref(null)
const operationDecision = ref('approve')
const operationComment = ref('')
const runResults = computed(() => props.latestRun?.results || [])

const STATUS_LABELS = {
  OPEN: '开放', PENDING_APPROVAL: '待审批', CANCELLED: '已取消', SUCCEEDED: '已完成',
  FAILED: '失败', RUNNING: '执行中', PENDING: '待处理', APPROVED: '已通过', REJECTED: '已拒绝',
  PROMOTED: '候补通过', SKIPPED: '已跳过', WAITING: '候补中', CLOSED: '已关闭',
  ENROLLED: '已选课', CONFLICT_REVIEW: '冲突复核中', CANCELLED_BY_ADMIN: '因课程删除而关闭',
}

function statusLabel(status) {
  return STATUS_LABELS[status] || status || '-'
}

function operationLabel(operation) {
  return { CREATE: '新增课程', UPDATE: '编辑课程', CANCEL: '删除课程' }[operation] || '课程变更'
}

function courseForAudit(audit) {
  const after = audit?.after_json || {}
  const before = audit?.before_json || {}
  const courseId = after.course_id || after.payload?.course_id || before.course_id || before.payload?.course_id || audit?.resource_id || ''
  return props.courses.find(course => course.id === courseId) || null
}

function refresh() {
  props.onRefresh({ ...filters.value }, { ...auditFilters.value })
}

function openAudit(audit) {
  selectedAudit.value = { ...audit }
  auditVisible.value = true
}

function openOperationDecision(operation, nextDecision) {
  selectedOperation.value = operation
  operationDecision.value = nextDecision
  operationComment.value = ''
  operationDecisionVisible.value = true
}

async function submitOperationDecision() {
  const error = validateRequiredText(operationComment.value, '审批意见')
  if (error) return ElMessage.warning(error)
  try {
    await ElMessageBox.confirm(operationDecision.value === 'approve' ? '批准后会正式写入课程数据库，确认继续吗？' : '确认拒绝这条课程操作申请吗？', '课程操作审批', { type: operationDecision.value === 'approve' ? 'warning' : 'info', confirmButtonText: '确认提交', cancelButtonText: '返回' })
    await props.onOperationDecide(selectedOperation.value, operationDecision.value, operationComment.value.trim())
    operationDecisionVisible.value = false
  } catch (reason) {
    if (reason !== 'cancel' && reason !== 'close') ElMessage.error(reason?.message || '课程操作审批失败')
  }
}
</script>

<template>
  <section class="module-page">
    <div class="module-heading">
      <div><p class="eyebrow">REVIEW & AUDIT</p><h1>审批中心</h1><p class="module-description">集中查看课程操作审批、候补重算和课程变更审计，审批通过后才会写入最终状态。</p></div>
      <div class="heading-actions"><el-button @click="refresh">刷新状态</el-button></div>
    </div>

    <el-card v-if="latestRun" class="run-summary-card" shadow="never">
      <div class="run-summary-heading">
        <div><span class="section-kicker">最近一次候补重算</span><h2>{{ latestRun.course_id }} · {{ latestRun.trigger_type }}</h2></div>
        <el-tag :type="statusTagType(latestRun.status)">{{ statusLabel(latestRun.status) }}</el-tag>
      </div>
      <div class="summary-metrics">
        <div><strong>{{ latestRun.summary?.checked || 0 }}</strong><span>检查人数</span></div>
        <div><strong>{{ latestRun.summary?.promoted || 0 }}</strong><span>候补通过</span></div>
        <div><strong>{{ latestRun.summary?.skipped || 0 }}</strong><span>跳过</span></div>
        <div><strong>{{ latestRun.summary?.waiting || 0 }}</strong><span>仍在候补</span></div>
        <div><strong>{{ latestRun.summary?.errors || 0 }}</strong><span>错误</span></div>
      </div>
      <el-table v-if="runResults.length" :data="runResults" size="small" stripe class="run-results-table">
        <el-table-column prop="student_id" label="学生" width="150" />
        <el-table-column label="状态变化" width="220"><template #default="scope"><el-tag :type="statusTagType(scope.row.old_status)">{{ statusLabel(scope.row.old_status) }}</el-tag> → <el-tag :type="statusTagType(scope.row.new_status)">{{ statusLabel(scope.row.new_status) }}</el-tag></template></el-table-column>
        <el-table-column label="处理结果" min-width="300"><template #default="scope">{{ describeRunResult(scope.row) }}</template></el-table-column>
        <el-table-column prop="occurred_at" label="发生时间" width="200" />
      </el-table>
      <el-empty v-else description="本次重算没有逐人结果" />
    </el-card>

    <el-card class="search-card" shadow="never">
      <div class="search-row approval-search">
        <el-select v-model="filters.status" clearable placeholder="审批状态" @change="refresh"><el-option label="待审批" value="PENDING" /><el-option label="已批准" value="APPROVED" /><el-option label="已拒绝" value="REJECTED" /></el-select>
        <el-input v-model="filters.course_id" clearable placeholder="课程编号" /><el-button type="primary" plain @click="refresh">搜索审批</el-button>
      </div>
    </el-card>

    <div class="approval-section-title"><div><h2>课程操作审批</h2><span>新增、编辑和删除课程只有批准后才会写入正式课程库</span></div></div>
    <el-empty v-if="!courseOperations.length" description="暂无课程操作申请" />
    <el-card v-for="operation in courseOperations" v-else :key="operation.id" class="approval-card operation-approval-card" shadow="never">
      <div class="approval-card-heading"><div><span class="approval-id">{{ operation.id }}</span><h3>{{ operationLabel(operation.operation) }} · {{ operation.payload?.code || operation.course_id || '待生成课程' }}</h3></div><el-tag :type="statusTagType(operation.status)">{{ statusLabel(operation.status) }}</el-tag></div>
      <div class="approval-card-content"><span>申请人：{{ operation.requester_id }}</span><span>提交时间：{{ operation.created_at || '-' }}</span><span>{{ describeCourseOperation(operation) }}</span></div>
      <div class="approval-card-footer"><span>{{ operation.comment || '等待教务处理' }}</span><div><el-button size="small" type="primary" :disabled="operation.status !== 'PENDING'" @click="openOperationDecision(operation, 'approve')">批准</el-button><el-button size="small" type="danger" plain :disabled="operation.status !== 'PENDING'" @click="openOperationDecision(operation, 'reject')">拒绝</el-button></div></div>
    </el-card>

    <div class="approval-section-title audit-title"><div><h2>课程变更审计</h2><span>新增、编辑、删除、容量和课表变化都会用中文记录在这里</span></div></div>
    <el-card class="search-card" shadow="never"><div class="search-row"><el-input v-model="auditFilters.course_id" clearable placeholder="课程编号" /><el-input v-model="auditFilters.action" clearable placeholder="操作类型，例如 COURSE_UPDATED" /><el-button type="primary" plain @click="onRefresh({ ...filters }, { ...auditFilters })">搜索审计</el-button></div></el-card>
    <el-skeleton v-if="auditLoading" :rows="3" animated /><el-empty v-else-if="!audits.length" description="暂无审计记录" />
    <el-card v-else class="audit-card" shadow="never">
      <el-table :data="audits" stripe><el-table-column prop="created_at" label="时间" width="190" /><el-table-column label="操作" width="180"><template #default="scope">{{ auditActionLabel(scope.row.action) }}</template></el-table-column><el-table-column label="中文说明" min-width="300"><template #default="scope">{{ auditDescription(scope.row, courseForAudit(scope.row)) }}</template></el-table-column><el-table-column prop="actor_id" label="操作人" width="150" /><el-table-column label="详情" width="80"><template #default="scope"><el-button text type="primary" @click="openAudit(scope.row)">查看</el-button></template></el-table-column></el-table>
      <el-pagination v-if="auditMeta.total" class="pagination" background layout="prev, pager, next, total" :page-size="auditMeta.page_size" :current-page="auditMeta.page" :total="auditMeta.total" @current-change="onAuditPage" />
    </el-card>

    <el-dialog v-model="operationDecisionVisible" :title="operationDecision === 'approve' ? '批准课程操作' : '拒绝课程操作'" width="520px"><el-form label-position="top"><el-form-item label="审批意见" required><el-input v-model="operationComment" type="textarea" :rows="4" maxlength="300" show-word-limit /></el-form-item></el-form><template #footer><div class="dialog-footer"><el-button @click="operationDecisionVisible = false">取消</el-button><el-button :type="operationDecision === 'approve' ? 'primary' : 'danger'" @click="submitOperationDecision">确认提交</el-button></div></template></el-dialog>
    <el-drawer v-model="auditVisible" title="审计详情" size="520px"><template v-if="selectedAudit"><el-descriptions :column="1" border><el-descriptions-item label="审计编号">{{ selectedAudit.id }}</el-descriptions-item><el-descriptions-item label="操作">{{ auditActionLabel(selectedAudit.action) }}</el-descriptions-item><el-descriptions-item label="资源">{{ auditResourceLabel(selectedAudit.resource_type) }} · {{ selectedAudit.resource_id }}</el-descriptions-item><el-descriptions-item label="操作人">{{ selectedAudit.actor_id }}</el-descriptions-item><el-descriptions-item label="中文说明">{{ auditDescription(selectedAudit, courseForAudit(selectedAudit)) }}</el-descriptions-item><el-descriptions-item label="变更内容">{{ auditChangeDescription(selectedAudit) }}</el-descriptions-item></el-descriptions></template></el-drawer>
  </section>
</template>
