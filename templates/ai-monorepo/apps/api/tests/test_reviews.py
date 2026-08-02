"""ドメインロジックのテスト。

テストは実装と同じ階層構造に置く（src/api/reviews.py -> tests/test_reviews.py）。
境界値と異常系を必ず含めること — AIが実装を書き換えたときに壊れたと分かるのはここだけ。
"""

import pytest
from pydantic import ValidationError

from api.contracts import Review
from api.reviews import EmptyReviewsError, classify, summarize


def review(rating: int, product_id: str = "SKU-001", text: str = "") -> Review:
    return Review(product_id=product_id, rating=rating, text=text)


class TestReviewValidation:
    """入力検証は pydantic モデルが担う。"""

    @pytest.mark.parametrize("rating", [1, 5])
    def test_accepts_boundary_ratings(self, rating: int) -> None:
        assert review(rating).rating == rating

    @pytest.mark.parametrize("rating", [0, 6, -1])
    def test_rejects_out_of_range_rating(self, rating: int) -> None:
        with pytest.raises(ValidationError):
            review(rating)

    def test_rejects_empty_product_id(self) -> None:
        with pytest.raises(ValidationError):
            review(3, product_id="")

    def test_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError):
            Review(product_id="SKU-001", rating=3, sentiment="positive")  # type: ignore[call-arg]

    def test_serializes_to_camel_case(self) -> None:
        """TS側の型と一致することの検証。ここが崩れると実行時まで気づけない。"""
        assert review(4).model_dump(by_alias=True) == {
            "productId": "SKU-001",
            "rating": 4,
            "text": "",
        }


class TestClassify:
    @pytest.mark.parametrize(
        ("average", "expected"),
        [
            (5.0, "positive"),
            (4.0, "positive"),  # 境界: 以上
            (3.9, "neutral"),
            (2.5, "neutral"),  # 境界: 未満で negative
            (2.49, "negative"),
            (1.0, "negative"),
        ],
    )
    def test_boundaries(self, average: float, expected: str) -> None:
        assert classify(average) == expected


class TestSummarize:
    def test_aggregates_ratings(self) -> None:
        result = summarize("SKU-001", [review(5), review(4), review(3)])

        assert result.product_id == "SKU-001"
        assert result.count == 3
        assert result.average_rating == 4.0
        assert result.sentiment == "positive"

    def test_rounds_average_to_two_places(self) -> None:
        result = summarize("SKU-001", [review(5), review(4), review(4)])
        assert result.average_rating == 4.33

    def test_rejects_empty_input(self) -> None:
        with pytest.raises(EmptyReviewsError, match="must not be empty"):
            summarize("SKU-001", [])
