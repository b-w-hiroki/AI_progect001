/**
 * レビュー表示まわりのロジック。
 *
 * 型は @repo/contracts から取る。ここで独自に型を定義し直さないこと。
 */

import { MAX_RATING, MIN_RATING, type ReviewSummary, type Sentiment } from "@repo/contracts";

const SENTIMENT_LABELS: Record<Sentiment, string> = {
  positive: "好評",
  neutral: "普通",
  negative: "要改善",
};

export function sentimentLabel(sentiment: Sentiment): string {
  return SENTIMENT_LABELS[sentiment];
}

export function isValidRating(rating: number): boolean {
  return Number.isInteger(rating) && rating >= MIN_RATING && rating <= MAX_RATING;
}

/** 集計結果を1行のサマリ文字列にする。 */
export function formatSummary(summary: ReviewSummary): string {
  const label = sentimentLabel(summary.sentiment);
  return `${summary.productId}: ${summary.averageRating.toFixed(1)}点 (${summary.count}件) — ${label}`;
}
