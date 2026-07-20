<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import AsyncState from '../components/AsyncState.vue'
import { getCourse, listCourses, requestEnrollment } from '../api/student'
import { errorMessage } from '../api/client'
import { useLiveQuery } from '../composables/useLiveQuery'
import { prerequisiteCourseNames } from '../utils/course-display'
import { formatScheduleTime } from '../utils/course-time'

const route = useRoute(), busy = ref(false)
const weekdays = ['日', '一', '二', '三', '四', '五', '六', '日']
const { data: course, loading, refreshing, error, refresh } = useLiveQuery(
  () => getCourse(route.params.id),
  { initialValue: null, errorFallback: '课程详情加载失败' },
)
const { data: courseCatalog, refresh: refreshCatalog } = useLiveQuery(
  () => listCourses(),
  { initialValue: [], errorFallback: '先修课程目录加载失败' },
)
const prerequisiteNames = computed(() => prerequisiteCourseNames(course.value?.prerequisites, courseCatalog.value))
watch(() => route.params.id, () => { refresh(); refreshCatalog() })
async function act(type) { busy.value = true; try { const result = await requestEnrollment(course.value.id, type); ElMessage.success(`服务端状态：${result.status}`); await refresh() } catch (err) { ElMessage.error(errorMessage(err)) } finally { busy.value = false } }
</script>

<template><section><router-link to="/courses" class="back-link">← 返回课程列表</router-link>
  <AsyncState :loading="loading" :error="error" :empty="!course" @retry="refresh"><el-card v-if="course" class="detail-card" shadow="never">
    <div class="course-heading"><div><p class="eyebrow">{{ course.code }}</p><h1>{{ course.name }}</h1><p>{{ course.teacher_name || '教师待定' }}</p></div><el-tag :type="course.status === 'OPEN' ? 'success' : 'info'">{{ course.status }}</el-tag></div>
    <div class="detail-grid"><div><span>学分</span><strong>{{ course.credits }}</strong></div><div><span>容量</span><strong>{{ course.enrolled_count }}/{{ course.capacity }}</strong></div><div><span>候补</span><strong>{{ course.waitlist_count }}</strong></div></div>
    <h3>上课时间</h3><p v-for="item in course.schedules" :key="`${item.weekday}-${item.start_minute}`">周{{ weekdays[item.weekday] }} {{ formatScheduleTime(item) }} · {{ item.room }}</p>
    <h3>先修课程</h3><p>{{ prerequisiteNames.length ? prerequisiteNames.join('、') : '无' }}</p>
    <el-alert title="课程人数仅供参考，最终资格由服务端在提交时重新检查。" type="info" :closable="false" />
    <div class="actions"><el-button type="primary" :loading="busy" @click="act('ENROLL')">提交选课</el-button><el-button :loading="busy" @click="act('WAITLIST')">加入候补</el-button></div>
  </el-card></AsyncState>
</section></template>
