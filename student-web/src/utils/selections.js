export function mergeSelections(enrollments, waitlists) {
  return [
    ...enrollments.filter(item => ['ENROLLED', 'CONFLICT_REVIEW'].includes(item.status)).map(item => ({ ...item, display_status: '已选' })),
    ...waitlists.filter(item => item.status === 'WAITING').map(item => ({ ...item, display_status: '候补' })),
  ]
}
