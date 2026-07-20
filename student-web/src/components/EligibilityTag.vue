<script setup>
import { computed } from 'vue'

const props = defineProps({ eligibility: { type: Object, required: true } })
const labels = {
  ELIGIBLE: '当前可选', CONFLICT: '时间冲突', TIME_CONFLICT: '时间冲突', PREREQUISITE_MISSING: '缺少前置课程',
  DUPLICATE: '已选过该课程', WAITLIST_ALLOWED: '可加入候补', CAPACITY_FULL: '课程已满',
  COURSE_CLOSED: '课程关闭', COURSE_CANCELLED: '课程取消', EXCEPTION_REQUIRED: '需要审批',
}
const label = computed(() => labels[props.eligibility.decision] || props.eligibility.decision || '待检查')
const type = computed(() => props.eligibility.eligible ? 'success' : (props.eligibility.decision === 'WAITLIST_ALLOWED' ? 'warning' : 'danger'))
</script>

<template><el-tag :type="type">{{ label }}</el-tag></template>
