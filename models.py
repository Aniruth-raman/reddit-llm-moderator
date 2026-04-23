from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    number: int
    title: str
    explanation: str


@dataclass(frozen=True)
class ModerationItem:
    item_id: str
    item_type: str
    title: str
    body: str
    author: str
    permalink: str


@dataclass(frozen=True)
class ModerationDecision:
    violates: bool
    confidence: int
    rule_number: int | None = None
    explanation: str = ""
