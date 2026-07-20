export function matchesCourse(course, query) {
  const keyword = query.trim().toLocaleLowerCase()
  if (!keyword) return true
  return `${course.code} ${course.name} ${course.teacher_name || ''}`.toLocaleLowerCase().includes(keyword)
}
