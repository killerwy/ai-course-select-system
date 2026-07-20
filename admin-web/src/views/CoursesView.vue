<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  cancelCourse,
  createCourse,
  expandCourse,
  listCourses,
  previewCourseChange,
  updateCourse,
} from '../api'
import { courseImpactDialogOptions, courseImpactMessage, isCourseEditorError, userMessageForError } from '../admin-state'
import CourseManagement from '../components/CourseManagement.vue'

const courses = ref([])
const loading = ref(false)
const saving = ref(false)
const filter = reactive({ keyword: '', status: '' })
const errorMessage = ref('')

function normalizedSchedules(schedules = []) {
  return schedules.map(item => ({
    weekday: Number(item.weekday),
    start_minute: Number(item.start_minute),
    end_minute: Number(item.end_minute),
    room: String(item.room || ''),
  }))
}

function courseImpactChanged(course, payload) {
  return (
    Number(course?.capacity) !== Number(payload?.capacity) ||
    courseSchedulesChanged(course, payload)
  )
}

function courseSchedulesChanged(course, payload) {
  return (
    JSON.stringify(normalizedSchedules(course?.schedules)) !==
    JSON.stringify(normalizedSchedules(payload?.schedules))
  )
}

async function confirmCourseImpact(courseId, payload) {
  const preview = await previewCourseChange(courseId, payload)
  try {
    await ElMessageBox.confirm(
      courseImpactMessage(preview),
      '课程变更影响确认',
      courseImpactDialogOptions()
    )
    return true
  } catch (reason) {
    if (reason === 'cancel' || reason === 'close') return false
    throw reason
  }
}

async function loadCourses(filters = filter) {
  loading.value = true
  try {
    Object.assign(filter, filters)
    courses.value = await listCourses(filter)
  } catch (error) {
    errorMessage.value = userMessageForError(error)
    ElMessage.error(errorMessage.value)
  } finally {
    loading.value = false
  }
}

async function saveCourse(courseId, payload) {
  errorMessage.value = ''
  try {
    if (courseId) {
      const course = courses.value.find(item => item.id === courseId)
      if (course && courseImpactChanged(course, payload)) {
        const previewPayload = { operation: 'UPDATE', capacity: payload.capacity }
        if (courseSchedulesChanged(course, payload)) {
          previewPayload.schedules = payload.schedules
        }
        const confirmed = await confirmCourseImpact(courseId, previewPayload)
        if (!confirmed) return { cancelled: true }
      }
    }
    saving.value = true
    const result = courseId
      ? await updateCourse(courseId, payload)
      : await createCourse(payload)
    ElMessage.success(
      courseId ? '课程编辑申请已提交审批' : '新增课程申请已提交审批'
    )
    await loadCourses()
    return result
  } catch (error) {
    if (isCourseEditorError(error)) throw error
    errorMessage.value = userMessageForError(error)
    ElMessage.error(errorMessage.value)
    throw error
  } finally {
    saving.value = false
  }
}

async function handleCancel(course, reason) {
  try {
    const confirmed = await confirmCourseImpact(course.id, {
      operation: 'CANCEL',
    })
    if (!confirmed) return { cancelled: true }
    saving.value = true
    const result = await cancelCourse(course.id, reason)
    ElMessage.success('删除课程申请已提交审批')
    await loadCourses()
    return result
  } catch (error) {
    errorMessage.value = userMessageForError(error)
    ElMessage.error(errorMessage.value)
    throw error
  } finally {
    saving.value = false
  }
}

async function handleExpand(course, capacityDelta) {
  errorMessage.value = ''
  try {
    const confirmed = await confirmCourseImpact(course.id, {
      operation: 'EXPAND',
      capacity: Number(course.capacity) + Number(capacityDelta),
    })
    if (!confirmed) return { cancelled: true }
    saving.value = true
    const result = await expandCourse(course.id, capacityDelta)
    ElMessage.success(`课程容量已增加 ${capacityDelta} 人，正在处理候补队列`)
    await loadCourses()
    return result
  } catch (error) {
    errorMessage.value = userMessageForError(error)
    ElMessage.error(errorMessage.value)
    throw error
  } finally {
    saving.value = false
  }
}

onMounted(() => loadCourses())
</script>

<template>
  <div>
    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" class="global-alert" />
    <CourseManagement
      :courses="courses"
      :loading="loading"
      :saving="saving"
      :on-save="saveCourse"
      :on-expand="handleExpand"
      :on-cancel="handleCancel"
      :on-refresh="loadCourses"
    />
  </div>
</template>
