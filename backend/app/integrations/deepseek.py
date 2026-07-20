from __future__ import annotations

import json
import os
from typing import Any

from pydantic import ValidationError

from ..contracts import RecommendationRequest
from ..schemas.recommendation import GeneratedRecommendationResponse


class DeepSeekUnavailable(RuntimeError):
    """The external recommendation service is unavailable or returned unsafe data."""


class DeepSeekAdapter:
    def __init__(self, client: Any | None = None) -> None:
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").strip()
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip()
        self.timeout = float(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "5"))
        self._client = client

    def _get_client(self):
        if self._client is not None:
            return self._client
        if not self.api_key:
            raise DeepSeekUnavailable("DeepSeek 配置不完整")
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise DeepSeekUnavailable("openai 依赖未安装") from exc
        self._client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url, timeout=self.timeout)
        return self._client

    async def recommend(self, payload: RecommendationRequest, snapshot: dict, retrieved_context: str | None = None):
        client = self._get_client()
        safe_courses = [
            {
                "id": course["id"],
                "code": course["code"],
                "name": course["name"],
                "credits": course.get("credits"),
                "schedules": course.get("schedules", []),
                "prerequisites": course.get("prerequisites", []),
            }
            for course in snapshot.get("catalog", [])
        ]
        prompt_input = {
            "goals": payload.goals,
            "preferences": payload.preferences,
            "candidate_courses": safe_courses,
            "selected_courses_and_timetable": snapshot.get("selected_courses", []),
        }
        if retrieved_context:
            prompt_input["local_rag_evidence"] = retrieved_context
        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是课程推荐解释器。只能从候选课程中选择课程。"
                            "只返回 json 对象，不要 Markdown。格式："
                            '{"items":[{"course_id":"course-001","reasons":["理由"],'
                            '"uncertainties":["不确定点"]}]}。每项至少一条理由和一条不确定点。'
                            "必须读取学生已选课程时间与候选课程时间；时间冲突课程可以继续推荐，"
                            "但不要判断最终选课资格。"
                        ),
                    },
                    {"role": "user", "content": json.dumps(prompt_input, ensure_ascii=False)},
                ],
                response_format={"type": "json_object"},
                max_tokens=2000,
            )
            parsed = json.loads(response.choices[0].message.content)
            generated = GeneratedRecommendationResponse.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError, AttributeError, IndexError, TypeError, ValueError) as exc:
            raise DeepSeekUnavailable("DeepSeek 返回结构非法") from exc
        except Exception as exc:
            raise DeepSeekUnavailable("DeepSeek 调用失败") from exc

        candidate_ids = {course["id"] for course in snapshot.get("catalog", [])}
        result_ids = [item.course_id for item in generated.items]
        if any(course_id not in candidate_ids for course_id in result_ids) or len(result_ids) != len(set(result_ids)):
            raise DeepSeekUnavailable("DeepSeek 返回未知或重复课程")
        if any(not all(text.strip() for text in item.reasons + item.uncertainties) for item in generated.items):
            raise DeepSeekUnavailable("DeepSeek 返回空理由或不确定点")
        return generated.items
