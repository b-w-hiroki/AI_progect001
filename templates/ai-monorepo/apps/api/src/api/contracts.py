"""APIの入出力型。

**`packages/contracts/src/index.ts` と1対1で対応させること。**
片方だけ変更すると型チェックでは検出できず、実行時に初めて壊れる。
"""

from dataclasses import dataclass
from typing import Literal

Sentiment = Literal["positive", "neutral", "negative"]

MIN_RATING = 1
MAX_RATING = 5


@dataclass(frozen=True)
class Review:
    """1件のレビュー。"""

    product_id: str
    rating: int
    text: str


@dataclass(frozen=True)
class ReviewSummary:
    """商品単位の集計結果。"""

    product_id: str
    count: int
    average_rating: float
    sentiment: Sentiment
