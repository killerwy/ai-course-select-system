<script setup>
import { computed, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  COURSE_PERIOD_OPTIONS,
  WEEKDAY_LABELS,
  minutesToPeriod,
  periodToMinutes,
  validateRequiredText,
  validateSchedule,
} from '../admin-state'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  course: { type: Object, default: null },
  saving: { type: Boolean, default: false },
  errorMessage: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue', 'save'])

const form = reactive({
  code: '',
  name: '',
  teacher_name: '',
  credits: 3,
  capacity: 30,
  prerequisitesText: '',
  weekday: 1,
  startPeriod: 1,
  endPeriod: 1,
  room: '待定',
})

const isEditing = computed(() => Boolean(props.course?.id))
const title = computed(() => isEditing.value ? '编辑课程信息' : '新增开设课程')
const weekdayOptions = WEEKDAY_LABELS.map((label, index) => ({ label: `周${label}`, value: index + 1 }))
const periodOptions = COURSE_PERIOD_OPTIONS

function resetForm(course) {
  const schedule = course?.schedules?.[0] || { weekday: 1, start_minute: periodToMinutes(1), end_minute: periodToMinutes(1) + 60, room: '待定' }
  const startPeriod = minutesToPeriod(schedule.start_minute) || 1
  const endPeriod = minutesToPeriod(Math.max(schedule.start_minute, Number(schedule.end_minute) - 60)) || startPeriod
  Object.assign(form, {
    code: course?.code || '',
    name: course?.name || '',
    teacher_name: course?.teacher_name || '',
    credits: course?.credits || 3,
    capacity: course?.capacity || 30,
    prerequisitesText: (course?.prerequisites || []).join(', '),
    weekday: schedule.weekday || 1,
    startPeriod,
    endPeriod: Math.max(startPeriod, endPeriod),
    room: schedule.room || '待定',
  })
}

watch(() => [props.modelValue, props.course], ([visible]) => {
  if (visible) resetForm(props.course)
}, { immediate: true })

function close() {
  emit('update:modelValue', false)
}

function submit() {
  const required = [
    validateRequiredText(form.code, '课程编号'),
    validateRequiredText(form.name, '课程名称'),
    validateRequiredText(form.teacher_name, '开设教师'),
    validateRequiredText(form.room, '上课地点'),
  ].find(Boolean)
  if (required) return ElMessage.warning(required)
  if (!Number.isInteger(Number(form.credits)) || form.credits <= 0) return ElMessage.warning('学分必须为正整数')
  if (!Number.isInteger(Number(form.capacity)) || form.capacity <= 0) return ElMessage.warning('课程容量必须为正整数')
  if (Number(form.endPeriod) < Number(form.startPeriod)) return ElMessage.warning('结束节次不能早于开始节次')
  const schedule = {
    weekday: Number(form.weekday),
    start_minute: periodToMinutes(form.startPeriod),
    end_minute: periodToMinutes(form.endPeriod) + 60,
    room: form.room.trim(),
  }
  const scheduleError = validateSchedule(schedule)
  if (scheduleError) return ElMessage.warning(scheduleError)
  emit('save', {
    code: form.code.trim(),
    name: form.name.trim(),
    teacher_name: form.teacher_name.trim(),
    credits: Number(form.credits),
    capacity: Number(form.capacity),
    schedules: [schedule],
    prerequisites: form.prerequisitesText.split(',').map((item) => item.trim()).filter(Boolean),
  })
}
</script>

<template>
  <el-dialog :model-value="modelValue" :title="title" width="640px" destroy-on-close @close="close">
    <div class="editor-intro">
      <span>{{ isEditing ? '保存后会记录课程审计；容量或课表变化会自动触发候补重算。' : '填写课程基础信息后提交，成功后会写入课程库并生成审计记录。' }}</span>
    </div>
    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" class="editor-error" />
    <el-form class="course-editor-form" label-position="top">
      <div class="form-grid form-grid-2">
        <el-form-item label="课程编号" required><el-input v-model="form.code" maxlength="20" show-word-limit placeholder="例如 CS401" :disabled="isEditing" /></el-form-item>
        <el-form-item label="课程名称" required><el-input v-model="form.name" maxlength="200" show-word-limit placeholder="例如 分布式系统" /></el-form-item>
        <el-form-item label="开设教师" required><el-input v-model="form.teacher_name" maxlength="100" placeholder="例如 王老师" /></el-form-item>
        <el-form-item label="学分" required><el-input-number v-model="form.credits" :min="1" :max="20" controls-position="right" /></el-form-item>
        <el-form-item label="课程容量" required><el-input-number v-model="form.capacity" :min="1" :max="10000" controls-position="right" /></el-form-item>
        <el-form-item label="先修课程编号"><el-input v-model="form.prerequisitesText" placeholder="多个编号用逗号分隔，可留空" /></el-form-item>
      </div>

      <div class="schedule-editor">
        <div class="schedule-editor-heading"><strong>课程表安排</strong><span>每节课 1 小时：上午 8-12、下午 14-18、晚上 19-21</span></div>
        <div class="form-grid form-grid-4">
          <el-form-item label="星期"><el-select v-model="form.weekday"><el-option v-for="item in weekdayOptions" :key="item.value" v-bind="item" /></el-select></el-form-item>
          <el-form-item label="开始节次"><el-select v-model="form.startPeriod"><el-option v-for="item in periodOptions" :key="item.value" v-bind="item" /></el-select></el-form-item>
          <el-form-item label="结束节次"><el-select v-model="form.endPeriod"><el-option v-for="item in periodOptions" :key="item.value" v-bind="item" /></el-select></el-form-item>
          <el-form-item label="教室"><el-input v-model="form.room" maxlength="50" /></el-form-item>
        </div>
      </div>
    </el-form>
    <template #footer>
      <div class="dialog-footer"><el-button @click="close">取消</el-button><el-button type="primary" :loading="saving" @click="submit">保存课程</el-button></div>
    </template>
  </el-dialog>
</template>
