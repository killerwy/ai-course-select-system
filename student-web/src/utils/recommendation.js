export function buildRecommendationPayload(goals, preferencesText, useRag = false) {
  return {
    goals: String(goals || '').trim(),
    preferences: String(preferencesText || '').split(/[,，\n]/).map(item => item.trim()).filter(Boolean),
    use_rag: Boolean(useRag),
  }
}

const RAG_MESSAGES = {
  RAG_DEPENDENCY_MISSING: 'RAG 依赖尚未安装',
  RAG_EMBEDDING_MODEL_NOT_FOUND: '本地 embedding 模型目录不存在',
  RAG_EMBEDDING_LOAD_FAILED: '本地 embedding 模型加载失败',
  RAG_CATALOG_EMPTY: '当前课程目录为空',
  RAG_INDEX_BUILD_FAILED: '课程向量索引建立失败',
  RAG_RETRIEVE_FAILED: '课程知识库检索失败',
  RAG_NO_MATCH: '课程知识库没有检索到匹配结果',
  RAG_LLM_UNAVAILABLE: 'RAG 检索成功，但 DeepSeek 当前不可用',
}

export function ragStatusMessage(code) {
  return RAG_MESSAGES[code] || 'RAG 服务暂时不可用'
}
