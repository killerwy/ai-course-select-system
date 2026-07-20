<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import CourseEditorDialog from './CourseEditorDialog.vue'
import { formatScheduleText, statusTagType, userMessageForError, validateRequiredText } from '../admin-state'
import { COURSE_PERIOD_OPTIONS, WEEKDAY_OPTIONS, courseMatchesSchedule } from '../course-time.js'

const props = defineProps({
  courses: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  saving: { type: Boolean, default: false },
  onSave: { type: Function, required: true },
  onExpand: { type: Function, required: true },
  onCancel: { type: Function, required: true },
  onRefresh: { type: Function, required: true },
})

const filter = ref({ keyword: '', status: '', weekday: '', period: '' })
const editorVisible = ref(false)
const editingCourse = ref(null)
const editorError = ref('')
const expandVisible = ref(false)
const expandTarget = ref(null)
const capacityDelta = ref(1)
const cancelVisible = ref(false)
const cancelCourse = ref(null)
const cancelReason = ref('')
const visibleCourses = computed(() => props.courses.filter(course => courseMatchesSchedule(course, filter.value.weekday, filter.value.period)))
const filteredCountLabel = computed(() => `${visibleCourses.value.length} 门课程`)
const expandedCapacity = computed(() => Number(expandTarget.value?.capacity || 0) + Number(capacityDelta.value || 0))
const promotableCount = computed(() => Math.min(Number(capacityDelta.value || 0), Number(expandTarget.value?.waitlist_count || 0)))

function openCreate() {
  editingCourse.value = null
  editorError.value = ''
  editorVisible.value = true
}

function openEdit(course) {
  editingCourse.value = course
  editorError.value = ''
  editorVisible.value = true
}

async function saveCourse(payload) {
  try {
    const result = await props.onSave(editingCourse.value?.id || null, payload)
    if (result?.cancelled) return
    editorVisible.value = false
  } catch (error) {
    editorError.value = userMessageForError(error)
  }
}

function search() {
  props.onRefresh({ ...filter.value })
}

function requestExpand(course) {
  expandTarget.value = course
  capacityDelta.value = 1
  expandVisible.value = true
}

async function submitExpand() {
  const delta = Number(capacityDelta.value)
  if (!Number.isInteger(delta) || delta <= 0) return ElMessage.warning('扩容人数必须为正整数')
  try {
    const result = await props.onExpand(expandTarget.value, delta)
    if (result?.cancelled) return
    expandVisible.value = false
  } catch (reason) {
    if (reason !== 'cancel' && reason !== 'close') ElMessage.error(reason?.message || '课程扩容失败')
  }
}

function requestCancel(course) {
  cancelCourse.value = course
  cancelReason.value = ''
  cancelVisible.value = true
}

async function submitCancel() {
  const error = validateRequiredText(cancelReason.value, '删除原因')
  if (error) return ElMessage.warning(error)
  try {
    const result = await props.onCancel(cancelCourse.value, cancelReason.value.trim())
    if (result?.cancelled) return
    cancelVisible.value = false
  } catch (reason) {
    if (reason !== 'cancel' && reason !== 'close') ElMessage.error(reason?.message || '删除课程失败')
  }
}
</script>

<template>
  <section class="module-page">
    <div class="module-heading">
      <div><p class="eyebrow">COURSE OPERATIONS</p><h1>课程管理</h1><p class="module-description">新增、编辑和取消课程都先提交审批，批准后才会写入正式课程库。</p></div>
      <div class="heading-actions"><el-button @click="onRefresh({ ...filter })">刷新状态</el-button><el-button type="primary" @click="openCreate">新增课程</el-button></div>
    </div>

    <el-card class="search-card" shadow="never">
      <div class="search-row"><el-input v-model="filter.keyword" clearable placeholder="搜索课程编号或课程名称" @keyup.enter="search"><template #prefix>⌕</template></el-input><el-select v-model="filter.status" clearable placeholder="全部状态" @change="search"><el-option label="开放选课" value="OPEN" /><el-option label="审核中" value="PENDING_APPROVAL" /></el-select><el-select v-model="filter.weekday" clearable placeholder="星期" @change="search"><el-option v-for="item in WEEKDAY_OPTIONS" :key="item.value" v-bind="item" /></el-select><el-select v-model="filter.period" clearable placeholder="课程时间" @change="search"><el-option v-for="item in COURSE_PERIOD_OPTIONS" :key="item.value" v-bind="item" /></el-select><el-button type="primary" plain @click="search">搜索</el-button><span class="result-count">{{ filteredCountLabel }}</span></div>
    </el-card>

    <el-skeleton v-if="loading" :rows="6" animated class="course-skeleton" />
    <el-empty v-else-if="!visibleCourses.length" description="没有匹配的课程" class="empty-panel" />
    <div v-else class="course-grid">
      <el-card v-for="course in visibleCourses" :key="course.id" class="course-card" shadow="never">
        <div class="course-card-header"><div><div class="course-code">{{ course.code }}</div><h2>{{ course.name }}</h2></div><el-tag :type="statusTagType(course.status)" effect="light">{{ course.status === 'OPEN' ? '开放中' : course.status === 'PENDING_APPROVAL' ? '审核中' : course.status }}</el-tag></div>
        <div class="course-meta-line"><span>开设教师</span><strong>{{ course.teacher_name || '未填写' }}</strong></div>
        <div class="course-meta-line"><span>课程时间</span><strong>{{ formatScheduleText(course.schedules?.[0]) }}</strong></div>
        <div class="course-stat-row"><div><span>已选人数</span><strong>{{ course.enrolled_count || 0 }}<em>/{{ course.capacity }}</em></strong></div><div><span>候补人数</span><strong>{{ course.waitlist_count || 0 }}</strong></div><div><span>学分</span><strong>{{ course.credits }}</strong></div></div>
        <div class="course-card-footer"><span class="course-id">{{ course.pending_operation ? '操作申请：' + course.pending_operation.id : course.id }}</span><div><el-button v-if="Number(course.waitlist_count || 0) > 0 && Number(course.enrolled_count || 0) >= Number(course.capacity || 0)" text type="success" :disabled="course.status !== 'OPEN'" @click="requestExpand(course)">扩容候补</el-button><el-button text type="primary" :disabled="course.status !== 'OPEN'" @click="openEdit(course)">编辑课程</el-button><el-button text type="danger" :disabled="course.status !== 'OPEN'" @click="requestCancel(course)">删除课程</el-button></div></div>
      </el-card>
    </div>

    <CourseEditorDialog v-model="editorVisible" :course="editingCourse" :saving="saving" :error-message="editorError" @save="saveCourse" />
    <el-dialog v-model="expandVisible" title="扩容并处理候补" width="500px">
      <p class="dialog-warning">{{ expandTarget?.code }} 当前已选 {{ expandTarget?.enrolled_count || 0 }}/{{ expandTarget?.capacity || 0 }} 人，候补 {{ expandTarget?.waitlist_count || 0 }} 人。扩容后会立即按候补顺序重新校验资格。</p>
      <el-form label-position="top">
        <el-form-item label="增加容量"><el-input-number v-model="capacityDelta" :min="1" :max="10000" controls-position="right" /></el-form-item>
      </el-form>
      <el-alert :title="`新容量 ${expandedCapacity} 人，最多尝试补入 ${promotableCount} 人；资格不符者会被跳过并留下重算记录。`" type="info" show-icon :closable="false" />
      <template #footer><div class="dialog-footer"><el-button @click="expandVisible = false">返回</el-button><el-button type="success" :loading="saving" @click="submitExpand">确认扩容</el-button></div></template>
    </el-dialog>
    <el-dialog v-model="cancelVisible" title="删除课程" width="500px">
      <p class="dialog-warning">此操作会提交删除申请。审批通过后才会删除课程，并将 {{ cancelCourse?.enrolled_count || 0 }} 条已选记录和 {{ cancelCourse?.waitlist_count || 0 }} 条候补记录转为终态并写入重算记录。</p>
      <el-input v-model="cancelReason" type="textarea" :rows="4" maxlength="200" show-word-limit placeholder="请填写删除原因" />
      <template #footer><div class="dialog-footer"><el-button @click="cancelVisible = false">返回</el-button><el-button type="danger" :loading="saving" @click="submitCancel">确认删除课程</el-button></div></template>
    </el-dialog>
  </section>
</template>
