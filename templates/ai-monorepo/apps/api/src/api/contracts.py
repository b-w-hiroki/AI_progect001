"""APIの入出力型。

**`packages/contracts/src/index.ts` と1対1で対応させること。**

Pythonは snake_case、TypeScriptは camelCase が慣習なので、
pydantic の alias_generator で **JSON上は camelCase に統一**している。
これにより「Python側を直したがTS側の型と合っていない」を機械的に防げる。

pydantic を使う副次効果として、不正な入力は実行時に弾かれる。
型チェックに加えて実行時の検証信号が増えるぶん、AIが誤りに気づきやすくなる。
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

Sentiment = Literal["positive", "neutral", "negative"]

MIN_RATING = 1
MAX_RATING = 5


class _Base(BaseModel):
    """全モデル共通の設定。"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Python側は snake_case のまま構築できる
        frozen=True,
        extra="forbid",  # 想定外のフィールドは黙って捨てずにエラーにする
    )


class Review(_Base):
    """1件のレビュー。"""

    product_id: str = Field(min_length=1)
    rating: int = Field(ge=MIN_RATING, le=MAX_RATING)
    text: str = ""


class ReviewSummary(_Base):
    """商品単位の集計結果。"""

    product_id: str
    count: int
    average_rating: float
    sentiment: Sentiment
