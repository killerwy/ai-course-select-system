import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const root = path.resolve(fileURLToPath(new URL('..', import.meta.url)))
const npmCli = path.join(path.dirname(process.execPath), 'node_modules', 'npm', 'bin', 'npm-cli.js')

function run(command, args, cwd) {
  const result = spawnSync(command, args, { cwd, stdio: 'inherit', env: process.env, shell: false })
  if (result.error) throw result.error
  if (result.status !== 0) process.exit(result.status ?? 1)
}

run(process.execPath, ['--test', 'scripts/dev-config.test.mjs'], root)
run(process.execPath, [npmCli, 'test', '--', '--run'], path.join(root, 'student-web'))
run(process.execPath, [npmCli, 'test'], path.join(root, 'admin-web'))
