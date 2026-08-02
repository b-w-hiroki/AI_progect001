"""FastAPI アプリケーション。

起動: make dev  (実体は uvicorn api.main:app --reload)
ドキュメント: http://localhost:8000/docs

エンドポイントは薄く保ち、判断はすべて reviews.py 側に置くこと。
ここが厚くなるとテストが遅くなり、検証ループが鈍る。
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from api.contracts import Review, ReviewSummary
from api.reviews import EmptyReviewsError, summarize

app = FastAPI(title="Reviews API", version="0.1.0")

# 開発用。本番ドメインは環境変数から読むこと
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 学習・雛形用のインメモリ保存。実装時はDBに差し替える
_store: dict[str, list[Review]] = {}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/reviews", status_code=status.HTTP_201_CREATED)
def create_review(review: Review) -> Review:
    """レビューを1件登録する。入力検証は Review モデルが行う。"""
    _store.setdefault(review.product_id, []).append(review)
    return review


@app.get("/reviews/{product_id}/summary")
def get_summary(product_id: str) -> ReviewSummary:
    """商品単位の集計を返す。"""
    try:
        return summarize(product_id, _store.get(product_id, []))
    except EmptyReviewsError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"no reviews for product {product_id}",
        ) from exc
