from pydantic import BaseModel, ConfigDict, Field


class GeneratedRecommendationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    course_id: str = Field(min_length=1)
    reasons: list[str] = Field(min_length=1)
    uncertainties: list[str] = Field(min_length=1)


class GeneratedRecommendationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[GeneratedRecommendationItem] = Field(default_factory=list)
