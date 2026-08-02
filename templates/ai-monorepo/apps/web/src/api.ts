/**
 * バックエンドAPIのクライアント。
 *
 * fetch をここに閉じ込め、コンポーネントからは型の付いた関数だけを呼ぶ。
 * URLやエラー処理が散らばらないので、変更時に直す場所が1箇所で済む。
 *
 * パスは相対の /api で書く。vite.config.ts の proxy がバックエンドに転送する。
 */

import type { Review, ReviewSummary } from "@repo/contracts";

const BASE = "/api";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!response.ok) {
    throw new ApiError(`${init?.method ?? "GET"} ${path} failed`, response.status);
  }

  return (await response.json()) as T;
}

export function createReview(review: Review): Promise<Review> {
  return request<Review>("/reviews", {
    method: "POST",
    body: JSON.stringify(review),
  });
}

export function fetchSummary(productId: string): Promise<ReviewSummary> {
  return request<ReviewSummary>(`/reviews/${encodeURIComponent(productId)}/summary`);
}
