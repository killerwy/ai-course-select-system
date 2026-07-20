import { existsSync } from 'node:fs'
import path from 'node:path'
import { spawn } from 'node:child_process'
import { createDevApps } from './dev-config.mjs'

const smoke = process.argv.includes('--smoke')
const apps = createDevApps()
const children = []
let stopping = false

function stopAll(exitCode = 0) {
  if (stopping) return
  stopping = true
  for (const child of children) {
    if (!child.killed) child.kill('SIGTERM')
  }
  process.exitCode = exitCode
}

async function waitFor(url, timeoutMs = 20000) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url)
      if (response.ok) return response.status
    } catch {}
    await new Promise(resolve => setTimeout(resolve, 250))
  }
  throw new Error(`DEV_SERVER_TIMEOUT: ${url}`)
}

for (const app of apps) {
  const viteBin = path.join(app.cwd, 'node_modules', 'vite', 'bin', 'vite.js')
  if (!existsSync(viteBin)) {
    throw new Error(`${app.name} 缺少依赖，请先在 ${app.cwd} 执行 npm install`)
  }
  const child = spawn(process.execPath, [viteBin, '--host', app.host, '--port', String(app.port), '--strictPort'], {
    cwd: app.cwd,
    env: { ...process.env, ...app.env },
    stdio: 'inherit',
    windowsHide: true,
  })
  child.on('exit', (code) => {
    if (!stopping) {
      console.error(`${app.name} 意外退出，code=${code}`)
      stopAll(code || 1)
    }
  })
  children.push(child)
  console.log(`${app.name}: ${app.url}`)
}

process.on('SIGINT', () => stopAll(0))
process.on('SIGTERM', () => stopAll(0))

if (smoke) {
  try {
    const statuses = await Promise.all(apps.map(app => waitFor(app.url)))
    console.log(`DEV_SMOKE_OK ${apps.map((app, index) => `${app.name}=${statuses[index]}`).join(' ')}`)
    stopAll(0)
  } catch (error) {
    console.error(error.message)
    stopAll(1)
  }
}
