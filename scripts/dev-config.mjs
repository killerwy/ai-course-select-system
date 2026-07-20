import { fileURLToPath } from 'node:url'
import path from 'node:path'

const workspaceRoot = path.resolve(fileURLToPath(new URL('..', import.meta.url)))

export function createDevApps(env = process.env) {
  const host = env.DEV_HOST || '127.0.0.1'
  const studentPort = Number(env.STUDENT_WEB_PORT || 5173)
  const adminPort = Number(env.ADMIN_WEB_PORT || 5174)
  if (!Number.isInteger(studentPort) || !Number.isInteger(adminPort) || studentPort <= 0 || adminPort <= 0 || studentPort === adminPort) {
    throw new Error('INVALID_WEB_PORTS')
  }
  const portalUrl = `http://${host}:${studentPort}`
  const adminUrl = `http://${host}:${adminPort}`
  return [
    {
      name: '学生端/统一登录',
      cwd: path.join(workspaceRoot, 'student-web'),
      host,
      port: studentPort,
      url: portalUrl,
      env: { VITE_USE_MOCK: 'false', VITE_ADMIN_WEB_URL: adminUrl },
    },
    {
      name: '教师端',
      cwd: path.join(workspaceRoot, 'admin-web'),
      host,
      port: adminPort,
      url: adminUrl,
      env: { VITE_USE_MOCK: 'false', VITE_PORTAL_URL: `${portalUrl}/login` },
    },
  ]
}
