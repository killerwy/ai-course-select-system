import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'

import {
  ACADEMIC_HOME,
  LOGIN_PAGE,
  STUDENT_HOME,
  homeForRole,
  navigationForRole,
  routeAllowed,
} from '../miniprogram/domain/navigation.ts'

const root = resolve(import.meta.dirname, '..', 'miniprogram')

test('MP-05 app manifest registers all P0 pages and removes sample routes', () => {
  const manifest = JSON.parse(readFileSync(resolve(root, 'app.json'), 'utf8'))
  assert.equal(manifest.pages[0], LOGIN_PAGE.slice(1))
  assert.equal(manifest.pages.includes('pages/index/index'), false)
  assert.equal(manifest.pages.includes('pages/logs/logs'), false)
  assert.equal(manifest.pages.length, 12)
  for (const page of manifest.pages) {
    for (const extension of ['.ts', '.json', '.wxml', '.scss']) {
      assert.equal(existsSync(resolve(root, page + extension)), true, page + extension)
    }
  }
})

test('MP-05 role navigation is isolated and home routes are deterministic', () => {
  assert.equal(homeForRole('STUDENT'), STUDENT_HOME)
  assert.equal(homeForRole('ACADEMIC'), ACADEMIC_HOME)
  assert.equal(navigationForRole('STUDENT').every(item => item.roles.includes('STUDENT')), true)
  assert.equal(navigationForRole('ACADEMIC').every(item => item.roles.includes('ACADEMIC')), true)
  assert.equal(routeAllowed('/pages/academic/approvals/approvals', 'STUDENT'), false)
  assert.equal(routeAllowed('/pages/student/courses/courses', 'ACADEMIC'), false)
})

test('MP-27 student navigation removes the redundant learning overview button', () => {
  const studentNavigation = navigationForRole('STUDENT')
  assert.equal(studentNavigation.some(item => item.url === STUDENT_HOME), false)
  assert.equal(studentNavigation.some(item => item.label === '学习概览'), false)
})

test('MP-05 common async/status components exist and app has no sample login logging', () => {
  for (const component of ['async-state', 'status-tag']) {
    for (const extension of ['.ts', '.json', '.wxml', '.scss']) {
      assert.equal(existsSync(resolve(root, 'components', component, component + extension)), true)
    }
  }
  const appSource = readFileSync(resolve(root, 'app.ts'), 'utf8')
  assert.equal(appSource.includes('wx.login'), false)
  assert.equal(appSource.includes('console.log'), false)
  assert.equal(appSource.includes('authService.restore'), true)
})

test('MP-27 schedule page renders selected-course identity with unique lesson keys', () => {
  const source = readFileSync(resolve(root, 'pages/student/schedule/schedule.wxml'), 'utf8')

  assert.equal(source.includes('schedule-day-header'), true)
  assert.equal(source.includes('{{day.label}}'), true)
  assert.equal(source.includes('lesson.display_name'), true)
  assert.equal(source.includes('lesson.course_id'), false)
  assert.equal(source.includes('当前没有已选课程'), true)
})

test('MP-28 enrollment page renders course names rather than course IDs', () => {
  const source = readFileSync(resolve(root, 'pages/student/enrollments/enrollments.wxml'), 'utf8')

  assert.equal(source.includes('item.course_name'), true)
  assert.equal(source.includes('item.course_id}}</text>'), false)
})
