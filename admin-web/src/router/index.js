import { createRouter, createWebHistory } from 'vue-router'
import { hasAcademicSession, isMockMode } from '../api'

const routes = [
  {
    path: '/',
    redirect: '/courses',
  },
  {
    path: '/courses',
    name: 'courses',
    component: () => import('../views/CoursesView.vue'),
    meta: { title: '课程管理' },
  },
  {
    path: '/approvals',
    name: 'approvals',
    component: () => import('../views/ApprovalsView.vue'),
    meta: { title: '审批中心' },
  },
  {
    path: '/audits',
    name: 'audits',
    component: () => import('../views/AuditsView.vue'),
    meta: { title: '审计日志' },
  },
  {
    path: '/runs',
    name: 'runs',
    component: () => import('../views/RunsView.vue'),
    meta: { title: '重算记录' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  if (isMockMode()) {
    next()
    return
  }
  if (!hasAcademicSession()) {
    const portalUrl = import.meta.env.VITE_PORTAL_URL || 'http://127.0.0.1:5173/login'
    window.location.replace(portalUrl)
    return
  }
  next()
})

export default router
