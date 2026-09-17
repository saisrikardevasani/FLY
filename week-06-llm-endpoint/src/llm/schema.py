"""The contract. Both ends of the endpoint are defined here and nowhere else.

The input schema is what a caller may send. The output schema is what this API promises
to return, and it is also what the model's answer is checked against before anything
leaves the building.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

# The closed list from JOB-CARD.md. A value outside it is a failure, not a new category.
Genre = Literal[
    "fiction",
    "mystery-thriller",
    "romance",
    "science-fiction-fantasy",
    "historical",
    "biography-memoir",
    "history-politics",
    "science-nature",
    "food-drink",
    "art-design",
    "self-help",
    "childrens",
    "poetry",
    "other",
]

Audience = Literal["adult", "young-adult", "children"]

Trimmed = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ClassifyIn(BaseModel):
    """What a caller may send. Checked before a model is ever called."""

    title: Annotated[Trimmed, StringConstraints(max_length=200)]
    description: Annotated[Trimmed, StringConstraints(max_length=4000)]


class Classification(BaseModel):
    """What this API returns, and what the model's answer must survive.

    extra="forbid" matters here: a model that invents a field fails validation rather
    than quietly widening the contract.
    """

    model_config = {"extra": "forbid"}

    genre: Genre
    audience: Audience
    confidence: float = Field(ge=0.0, le=1.0)
    one_line: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1,
                                               max_length=160)]


# Returned when LLM_STUB=1. It satisfies the schema, so every path through the endpoint
# returns the same shape and the tests never need a model.
STUB = Classification(
    genre="other",
    audience="adult",
    confidence=0.0,
    one_line="Stub response. No model was called.",
)

# Returned when LLM_ENABLED is not true. Deterministic, schema valid, and honest about
# being a fallback rather than a classification.
FALLBACK = Classification(
    genre="other",
    audience="adult",
    confidence=0.0,
    one_line="Classification is switched off, so this book was not classified.",
)
