<script setup>
import { computed } from 'vue'
import EligibilityTag from './EligibilityTag.vue'

const props = defineProps({ item: { type: Object, required: true }, course: { type: Object, default: null }, busy: Boolean })
defineEmits(['enroll', 'waitlist'])
const enrollDisabled = computed(() => !props.item.eligibility?.eligible)
</script>

<template>
  <el-card shadow="never" class="recommendation-card">
    <div class="course-heading">
      <div><span class="rank">#{{ item.rank }}</span> <strong>{{ course?.code || item.course_id }}</strong></div>
      <EligibilityTag :eligibility="item.eligibility || {}" />
    </div>
    <h3>{{ course?.name || '课程信息加载中' }}</h3>
    <div class="explanation">
      <p class="label">推荐理由</p><ul><li v-for="reason in item.reasons" :key="reason">{{ reason }}</li></ul>
      <p class="label">不确定点</p><ul class="uncertainties"><li v-for="point in item.uncertainties" :key="point">{{ point }}</li></ul>
      <p v-if="item.eligibility?.violations?.length" class="violation">{{ item.eligibility.violations.map(item => item.message).join('；') }}</p>
    </div>
    <el-alert v-if="item.eligibility?.decision === 'CONFLICT'" title="该课程与当前课程表冲突，仅可查看，无法提交选课。" type="error" :closable="false" />
    <div class="actions">
      <el-button type="primary" :loading="busy" :disabled="enrollDisabled" @click="$emit('enroll', item.course_id)">提交选课</el-button>
      <el-button :loading="busy" @click="$emit('waitlist', item.course_id)">加入候补</el-button>
    </div>
  </el-card>
</template>
