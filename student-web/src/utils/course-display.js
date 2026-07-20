export function prerequisiteCourseNames(prerequisites, courseCatalog) {
  const courses = Array.isArray(courseCatalog) ? courseCatalog : []
  return (Array.isArray(prerequisites) ? prerequisites : []).map((identifier) => {
    const matched = courses.find(course => course.id === identifier || course.code === identifier)
    return matched?.name || identifier
  })
}
