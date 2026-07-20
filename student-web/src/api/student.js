import { client, unwrapResponse } from './client'

export const login = async payload => unwrapResponse(await client.post('/auth/login', payload))
export const register = async payload => unwrapResponse(await client.post('/auth/register', payload))
export const getMe = async () => unwrapResponse(await client.get('/me'))
export const listCourses = async () => unwrapResponse(await client.get('/courses'))
export const getCourse = async id => unwrapResponse(await client.get(`/courses/${id}`))
export const createRecommendation = async payload => unwrapResponse(await client.post('/students/me/recommendations', payload))
export const getRecommendation = async id => unwrapResponse(await client.get(`/students/me/recommendations/${id}`))
export const requestEnrollment = async (courseId, type) => unwrapResponse(await client.post('/students/me/enrollment-requests', { course_id: courseId, type }))
export const listEnrollments = async () => unwrapResponse(await client.get('/students/me/enrollments'))
export const listWaitlists = async () => unwrapResponse(await client.get('/students/me/waitlists'))
export const getSchedule = async () => unwrapResponse(await client.get('/students/me/schedule'))
export const listAuditLogs = async () => unwrapResponse(await client.get('/students/me/audit-logs'))
