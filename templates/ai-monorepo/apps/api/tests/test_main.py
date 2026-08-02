"""APIエンドポイントのテスト。

TestClient は実サーバーを起動しないので高速。
`make dev` で手動確認する前に、まずここに1件足すほうが速く回る。
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from api.main import _store, app


@pytest.fixture
def client() -> Iterator[TestClient]:
    _store.clear()  # テスト間で状態を持ち越さない
    yield TestClient(app)
    _store.clear()


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


class TestCreateReview:
    def test_creates_review(self, client: TestClient) -> None:
        response = client.post(
            "/reviews",
            json={"productId": "SKU-001", "rating": 5, "text": "良かった"},
        )

        assert response.status_code == 201
        # レスポンスは camelCase。TS側の Review 型とそのまま合う
        assert response.json() == {"productId": "SKU-001", "rating": 5, "text": "良かった"}

    @pytest.mark.parametrize("rating", [0, 6])
    def test_rejects_out_of_range_rating(self, client: TestClient, rating: int) -> None:
        response = client.post("/reviews", json={"productId": "SKU-001", "rating": rating})
        assert response.status_code == 422

    def test_accepts_snake_case_but_always_responds_camel_case(self, client: TestClient) -> None:
        """入力は camelCase / snake_case の両方を受け付ける（populate_by_name=True）。

        重要なのは**出力が常に camelCase であること**。ここが崩れるとTS側と食い違う。
        """
        response = client.post("/reviews", json={"product_id": "SKU-001", "rating": 5})

        assert response.status_code == 201
        assert response.json() == {"productId": "SKU-001", "rating": 5, "text": ""}

    def test_rejects_unknown_field(self, client: TestClient) -> None:
        """extra="forbid" により、想定外のキーは黙って無視されずエラーになる。"""
        response = client.post(
            "/reviews",
            json={"productId": "SKU-001", "rating": 5, "sentiment": "positive"},
        )
        assert response.status_code == 422


class TestGetSummary:
    def test_returns_summary(self, client: TestClient) -> None:
        for rating in (5, 4, 3):
            client.post("/reviews", json={"productId": "SKU-001", "rating": rating})

        response = client.get("/reviews/SKU-001/summary")

        assert response.status_code == 200
        assert response.json() == {
            "productId": "SKU-001",
            "count": 3,
            "averageRating": 4.0,
            "sentiment": "positive",
        }

    def test_returns_404_when_no_reviews(self, client: TestClient) -> None:
        response = client.get("/reviews/UNKNOWN/summary")
        assert response.status_code == 404
