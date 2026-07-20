export const STUDENT_ROLE = 'STUDENT'
export const ACADEMIC_ROLE = 'ACADEMIC'

export function assertSelectedRole(user, selectedRole) {
  if (user?.role !== selectedRole) {
    const error = new Error('ROLE_MISMATCH')
    error.code = 'ROLE_MISMATCH'
    error.message = selectedRole === ACADEMIC_ROLE ? '该账号不是教师/教务账号' : '该账号不是学生账号'
    throw error
  }
  return user
}

export function buildAcademicHandoffUrl(baseUrl, accessToken) {
  if (!accessToken) throw new Error('ACADEMIC_TOKEN_REQUIRED')
  const target = new URL(baseUrl)
  target.hash = new URLSearchParams({ access_token: accessToken, role: ACADEMIC_ROLE }).toString()
  return target.toString()
}
