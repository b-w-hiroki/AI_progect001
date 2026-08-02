"""バックエンドAPI。

構成:
    contracts.py  フロントエンドと共有する入出力型（packages/contracts と対応）
    reviews.py    レビューまわりのドメインロジック（純粋関数）
    main.py       FastAPI のエンドポイント定義（薄く保つ）
"""

__all__ = ["contracts", "main", "reviews"]
