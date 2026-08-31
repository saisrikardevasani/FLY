"""The shape of a finished book record, and the cleaning that gets a raw one there.

Anything scraped is untrusted input. A record is only allowed into books.json after it
has been through this file.
"""

import re
from typing import Literal

from pydantic import BaseModel, field_validator

# The site shows a star count as a word. Anything outside this list is a page change
# we should hear about, not a value we should quietly store.
Rating = Literal["One", "Two", "Three", "Four", "Five"]


class Book(BaseModel):
    """One validated book. The raw text and the clean value live side by side."""

    title: str
    product_url: str
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: Rating
    description: str | None
    source_page: str
    fetched_at: str

    @field_validator("title")
    @classmethod
    def title_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("title is empty")
        return value

    @field_validator("product_url", "source_page")
    @classmethod
    def url_is_absolute(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError(f"not an absolute https URL: {value!r}")
        return value

    @field_validator("price_gbp")
    @classmethod
    def price_is_sane(cls, value: float) -> float:
        if value < 0:
            raise ValueError(f"negative price: {value}")
        return value


def to_gbp(price_text: str) -> float:
    """'£51.77' becomes 51.77, a number a program can sort and compare."""
    match = re.search(r"\d+(?:\.\d+)?", price_text)
    if match is None:
        raise ValueError(f"no number in price text: {price_text!r}")
    return float(match.group())


def normalise(raw: dict) -> dict:
    """Add the clean fields to a raw record without throwing the raw ones away."""
    return {**raw, "price_gbp": to_gbp(raw["price_text"])}
