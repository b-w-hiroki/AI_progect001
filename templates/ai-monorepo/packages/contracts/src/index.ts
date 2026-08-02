/**
 * フロントエンドとバックエンドが共有するAPIの入出力型。
 *
 * **`apps/api/src/api/contracts.py` と1対1で対応させること。**
 * 片方だけ変更しても型チェックでは検出できず、実行時に初めて壊れる。
 *
 * ここを「唯一の正」にしておくと、AIが両側を実装するときに
 * 形の違うオブジェクトを勝手に作ってしまう事故を防げる。
 */

export type Sentiment = "positive" | "neutral" | "negative";

export const MIN_RATING = 1;
export const MAX_RATING = 5;

/** 1件のレビュー。 */
export interface Review {
  productId: string;
  rating: number;
  text: string;
}

/** 商品単位の集計結果。 */
export interface ReviewSummary {
  productId: string;
  count: number;
  averageRating: number;
  sentiment: Sentiment;
}
