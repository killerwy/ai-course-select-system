import { createRouter, createWebHistory } from 'vue-router'
import { isAuthenticated } from '../auth/session'
import LoginView from '../views/LoginView.vue'
import DashboardView from '../views/DashboardView.vue'
import RecommendationsView from '../views/RecommendationsView.vue'
import CoursesView from '../views/CoursesView.vue'
import CourseDetailView from '../views/CourseDetailView.vue'
import ScheduleView from '../views/ScheduleView.vue'
import EnrollmentsView from '../views/EnrollmentsView.vue'
import AuditLogsView from '../views/AuditLogsView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/login', component: LoginView, meta: { public: true } },
    { path: '/dashboard', component: DashboardView },
    { path: '/recommendations', component: RecommendationsView },
    { path: '/courses', component: CoursesView },
    { path: '/courses/:id', component: CourseDetailView },
    { path: '/schedule', component: ScheduleView },
    { path: '/my-enrollments', component: EnrollmentsView },
    { path: '/my-audit-logs', component: AuditLogsView },
    { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
  ],
})

router.beforeEach((to) => {
  if (!to.meta.public && !isAuthenticated()) return '/login'
  if (to.path === '/login' && isAuthenticated()) return '/dashboard'
})

export default router
