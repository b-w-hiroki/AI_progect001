"""レビューのドメインロジック。

外部I/O（DB・HTTP・LLM）をここに書かないこと。
純粋関数にしておくとテストが速く、AIが変更した際の検証ループも速くなる。
入力の形式的な検証は contracts.py の pydantic モデルが担う。
"""

from collections.abc import Sequence

from api.contracts import Review, ReviewSummary, Sentiment

# この境界を動かすときは apps/web 側の表示ロジックも合わせて確認する
POSITIVE_THRESHOLD = 4.0
NEGATIVE_THRESHOLD = 2.5


class EmptyReviewsError(ValueError):
    """集計対象のレビューが1件も無いときに送出する。"""


def classify(average_rating: float) -> Sentiment:
    """平均評点から感情ラベルを決める。"""
    if average_rating >= POSITIVE_THRESHOLD:
        return "positive"
    if average_rating < NEGATIVE_THRESHOLD:
        return "negative"
    return "neutral"


def summarize(product_id: str, reviews: Sequence[Review]) -> ReviewSummary:
    """商品単位でレビューを集計する。

    Raises:
        EmptyReviewsError: reviews が空の場合。
    """
    if not reviews:
        raise EmptyReviewsError("reviews must not be empty")

    average = sum(review.rating for review in reviews) / len(reviews)
    return ReviewSummary(
        product_id=product_id,
        count=len(reviews),
        average_rating=round(average, 2),
        sentiment=classify(average),
    )
