<script setup>
import { computed, onMounted, ref } from 'vue'
import AsyncState from '../components/AsyncState.vue'
import { getSchedule } from '../api/student'
import { errorMessage } from '../api/client'
import { formatScheduleTime } from '../utils/course-time'

const weekdays = [{ value: 1, label: '周一' }, { value: 2, label: '周二' }, { value: 3, label: '周三' }, { value: 4, label: '周四' }, { value: 5, label: '周五' }, { value: 6, label: '周六' }, { value: 7, label: '周日' }]
const courses = ref([]), loading = ref(false), error = ref('')
const lessons = computed(() => courses.value.flatMap(course => (course.schedules || []).map(schedule => ({ ...schedule, course_id: course.id, code: course.code, name: course.name }))))
const lessonsFor = weekday => lessons.value.filter(item => item.weekday === weekday).sort((a, b) => a.start_minute - b.start_minute)
async function load() { loading.value = true; error.value = ''; try { courses.value = (await getSchedule()).courses } catch (err) { error.value = errorMessage(err, '课程表加载失败') } finally { loading.value = false } }
onMounted(load)
</script>

<template><section>
  <div class="page-title"><div><p class="eyebrow">MY TIMETABLE</p><h1>课程表</h1></div><el-button @click="load">刷新</el-button></div>
  <el-alert title="已选课程会自动进入课程表；候补课程不会占用课表时间。" type="info" :closable="false" />
  <AsyncState :loading="loading" :error="error" :empty="!lessons.length" empty-text="当前没有已选课程" @retry="load"><div class="schedule-board">
    <section v-for="day in weekdays" :key="day.value" class="schedule-day"><h3>{{ day.label }}</h3>
      <article v-for="lesson in lessonsFor(day.value)" :key="`${lesson.course_id}-${lesson.start_minute}`" class="lesson-card"><strong>{{ lesson.code }}</strong><span>{{ lesson.name }}</span><small>{{ formatScheduleTime(lesson) }}</small><small>{{ lesson.room }}</small></article>
      <p v-if="!lessonsFor(day.value).length" class="muted schedule-empty">无课程</p>
    </section>
  </div></AsyncState>
</section></template>
