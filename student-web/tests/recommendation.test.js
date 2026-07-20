import { describe, expect, it } from 'vitest'
import { buildRecommendationPayload, ragStatusMessage } from '../src/utils/recommendation'

describe('RAG 推荐', () => {
  it('请求只扩展 use_rag 并保留目标与偏好', () => {
    expect(buildRecommendationPayload(' 人工智能 ', '实践课程，软件工程', true)).toEqual({
      goals: '人工智能',
      preferences: ['实践课程', '软件工程'],
      use_rag: true,
    })
    expect(ragStatusMessage('RAG_EMBEDDING_MODEL_NOT_FOUND')).toContain('模型目录不存在')
    expect(ragStatusMessage('UNKNOWN_RAG_ERROR')).toContain('暂时不可用')
  })
})
