<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import AsyncState from '../components/AsyncState.vue'
import RecommendationCard from '../components/RecommendationCard.vue'
import { createRecommendation, listCourses, requestEnrollment } from '../api/student'
import { errorMessage } from '../api/client'
import { useLiveQuery } from '../composables/useLiveQuery'
import { buildRecommendationPayload, ragStatusMessage } from '../utils/recommendation'

const form = reactive({
  goals: '希望学习人工智能与软件工程',
  preferencesText: '偏好实践课程',
})
const session = ref(null)
const loading = ref(false)
const error = ref('')
const busyCourse = ref('')
const ragEnabled = ref(false)

const { data: courses, refreshing: courseRefreshing, refresh: refreshCourses } = useLiveQuery(
  () => listCourses(),
  { initialValue: [], errorFallback: '课程目录同步失败', isEmpty: value => !value?.length },
)

async function submit(useRag = ragEnabled.value) {
  if (!form.goals.trim()) {
    ElMessage.error('请输入学习目标')
    return
  }
  loading.value = true
  error.value = ''
  ragEnabled.value = useRag
  try {
    await refreshCourses()
    session.value = await createRecommendation(buildRecommendationPayload(form.goals, form.preferencesText, useRag))
  } catch (err) {
    error.value = errorMessage(err, '推荐生成失败')
  } finally {
    loading.value = false
  }
}

async function act(courseId, type) {
  busyCourse.value = courseId
  try {
    const result = await requestEnrollment(courseId, type)
    ElMessage.success(`服务端状态：${result.status}`)
  } catch (err) {
    ElMessage.error(errorMessage(err))
  } finally {
    busyCourse.value = ''
  }
}
</script>

<template>
  <section>
    <div class="page-title">
      <div>
        <p class="eyebrow">AI + RULES</p>
        <h1>课程推荐</h1>
      </div>
      <div class="page-title-tags">
        <el-tag v-if="courseRefreshing" type="info">课程目录同步中</el-tag>
        <el-tag type="warning">推荐 ≠ 选课资格</el-tag>
      </div>
    </div>

    <el-card class="form-card" shadow="never">
      <el-form label-position="top">
        <el-form-item label="学习目标">
          <el-input v-model="form.goals" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="偏好（逗号分隔）">
          <el-input v-model="form.preferencesText" />
        </el-form-item>
        <el-alert
          title="推荐会自动读取当前账号的已选课程和课表。冲突课程仍可展示，但最终资格由提交时的服务端规则判断。"
          type="info"
          :closable="false"
        />
        <div class="recommendation-actions">
          <el-button type="primary" :loading="loading && !ragEnabled" :disabled="loading" @click="submit(false)">获取推荐</el-button>
          <el-button type="success" :loading="loading && ragEnabled" :disabled="loading" @click="submit(true)">使用 RAG 加强</el-button>
        </div>
      </el-form>
    </el-card>

    <AsyncState
      :loading="loading"
      :error="error"
      :empty="Boolean(session && !session.items.length)"
      empty-text="当前没有可推荐课程"
      @retry="session ? submit(ragEnabled) : refreshCourses()"
    >
      <template v-if="session">
        <el-alert
          v-if="session.rag_status === 'USED'"
          title="RAG 已启用：已从本地课程知识库检索，并结合 DeepSeek 生成推荐。"
          type="success"
          :closable="false"
        />
        <el-alert
          v-else-if="session.rag_status === 'UNAVAILABLE'"
          :title="`RAG 当前不可用（${ragStatusMessage(session.rag_message)}），已使用可用的推荐兜底。`"
          type="warning"
          :closable="false"
        />
        <el-alert
          v-else-if="session.status === 'FALLBACK'"
          title="DeepSeek 当前不可用，已使用固定规则生成推荐。"
          type="warning"
          :closable="false"
        />
        <div class="recommendations">
          <RecommendationCard
            v-for="item in session.items"
            :key="item.course_id"
            :item="item"
            :course="courses.find(course => course.id === item.course_id)"
            :busy="busyCourse === item.course_id"
            @enroll="id => act(id, 'ENROLL')"
            @waitlist="id => act(id, 'WAITLIST')"
          />
        </div>
      </template>
    </AsyncState>
  </section>
</template>
