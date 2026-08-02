"""レビューのドメインロジック。

外部I/O（DB・HTTP・LLM）をここに書かないこと。
純粋関数にしておくとテストが速く、AIが変更した際の検証ループも速くなる。
"""

from collections.abc import Sequence

from api.contracts import MAX_RATING, MIN_RATING, Review, ReviewSummary, Sentiment

# この境界を動かすときは apps/web 側の表示ロジックも合わせて確認する
POSITIVE_THRESHOLD = 4.0
NEGATIVE_THRESHOLD = 2.5


class InvalidReviewError(ValueError):
    """レビューの内容が不正なときに送出する。"""


def validate(review: Review) -> None:
    """レビュー1件を検証する。不正なら InvalidReviewError を送出する。"""
    if not review.product_id.strip():
        raise InvalidReviewError("product_id must not be empty")
    if not MIN_RATING <= review.rating <= MAX_RATING:
        raise InvalidReviewError(
            f"rating must be between {MIN_RATING} and {MAX_RATING}, got {review.rating}"
        )


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
        InvalidReviewError: reviews が空、または不正なレビューを含む場合。
    """
    if not reviews:
        raise InvalidReviewError("reviews must not be empty")

    for review in reviews:
        validate(review)

    average = sum(review.rating for review in reviews) / len(reviews)
    return ReviewSummary(
        product_id=product_id,
        count=len(reviews),
        average_rating=round(average, 2),
        sentiment=classify(average),
    )
