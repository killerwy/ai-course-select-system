<script setup>
import { computed, ref } from 'vue'
import AsyncState from '../components/AsyncState.vue'
import { listCourses } from '../api/student'
import { matchesCourse } from '../utils/course-search'
import { COURSE_PERIOD_OPTIONS, WEEKDAY_OPTIONS, courseMatchesSchedule } from '../utils/course-time'
import { useLiveQuery } from '../composables/useLiveQuery'

const query = ref('')
const selectedWeekday = ref('')
const selectedPeriod = ref('')
const { data: courses, loading, refreshing, error, lastSyncedAt, refresh } = useLiveQuery(
  () => listCourses(),
  { initialValue: [], errorFallback: '课程加载失败', isEmpty: value => !value?.length },
)
const filteredCourses = computed(() => courses.value.filter(course =>
  matchesCourse(course, query.value) && courseMatchesSchedule(course, selectedWeekday.value, selectedPeriod.value),
))
const syncLabel = computed(() => refreshing.value ? '正在同步数据库' : (lastSyncedAt.value ? `已同步 ${lastSyncedAt.value.toLocaleTimeString()}` : '等待同步'))
</script>

<template><section>
  <div class="page-title"><div><p class="eyebrow">COURSE CATALOG</p><h1>课程列表</h1><p class="live-sync-status"><span class="live-dot" :class="{ syncing: refreshing }"></span>{{ syncLabel }} · 每 5 秒检查教师端变更</p></div><el-button :loading="loading" @click="refresh">刷新</el-button></div>
  <div class="course-filters"><el-input v-model="query" class="course-search" clearable placeholder="搜索课程名称、代码或教师" /><el-select v-model="selectedWeekday" clearable placeholder="星期" class="course-filter-select"><el-option v-for="item in WEEKDAY_OPTIONS" :key="item.value" v-bind="item" /></el-select><el-select v-model="selectedPeriod" clearable placeholder="课程时间" class="course-filter-select"><el-option v-for="item in COURSE_PERIOD_OPTIONS" :key="item.value" v-bind="item" /></el-select></div>
  <AsyncState :loading="loading" :error="error" :empty="!filteredCourses.length" empty-text="没有匹配的课程" @retry="refresh">
    <div class="course-grid"><router-link v-for="course in filteredCourses" :key="course.id" :to="`/courses/${course.id}`" class="course-link">
      <el-card shadow="hover"><div class="course-heading"><strong>{{ course.code }}</strong><el-tag :type="course.status === 'OPEN' ? 'success' : 'info'">{{ course.status }}</el-tag></div>
        <h3>{{ course.name }}</h3><p>{{ course.teacher_name || '教师待定' }}</p><p>{{ course.credits }} 学分 · {{ course.enrolled_count }}/{{ course.capacity }} 人</p><p class="muted">候补 {{ course.waitlist_count }} 人</p>
      </el-card></router-link></div>
  </AsyncState>
</section></template>
