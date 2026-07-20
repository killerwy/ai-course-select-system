<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import AsyncState from '../components/AsyncState.vue'
import { listCourses, listEnrollments, listWaitlists, requestEnrollment } from '../api/student'
import { errorMessage } from '../api/client'
import { mergeSelections } from '../utils/selections'

const enrollments = ref([]), waitlists = ref([]), courses = ref([]), loading = ref(false), error = ref(''), busy = ref('')
const courseOf = id => courses.value.find(item => item.id === id)
const records = computed(() => mergeSelections(enrollments.value, waitlists.value))
async function load() { loading.value = true; error.value = ''; try { [enrollments.value, waitlists.value, courses.value] = await Promise.all([listEnrollments(), listWaitlists(), listCourses()]) } catch (err) { error.value = errorMessage(err) } finally { loading.value = false } }
async function drop(id) { busy.value = id; try { const result = await requestEnrollment(id, 'DROP'); ElMessage.success(`服务端状态：${result.status}`); await load() } catch (err) { ElMessage.error(errorMessage(err)) } finally { busy.value = '' } }
onMounted(load)
</script>

<template><section><div class="page-title"><div><p class="eyebrow">MY COURSES</p><h1>我的选课</h1></div><el-button @click="load">刷新</el-button></div>
  <AsyncState :loading="loading" :error="error" :empty="!records.length" empty-text="暂无选课记录" @retry="load"><el-table :data="records" stripe>
    <el-table-column label="课程"><template #default="scope">{{ courseOf(scope.row.course_id)?.code }} {{ courseOf(scope.row.course_id)?.name }}</template></el-table-column>
    <el-table-column label="状态" width="110"><template #default="scope"><el-tag :type="scope.row.display_status === '已选' ? 'success' : 'warning'">{{ scope.row.display_status }}</el-tag></template></el-table-column>
    <el-table-column label="操作" width="140"><template #default="scope"><el-button type="danger" text :loading="busy === scope.row.course_id" @click="drop(scope.row.course_id)">{{ scope.row.display_status === '已选' ? '退课' : '退出候补' }}</el-button></template></el-table-column>
  </el-table></AsyncState>
</section></template>
