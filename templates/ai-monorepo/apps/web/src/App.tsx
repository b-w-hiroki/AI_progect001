import type { ReviewSummary } from "@repo/contracts";
import { type FormEvent, useState } from "react";
import { ApiError, createReview, fetchSummary } from "./api";
import { formatSummary, isValidRating } from "./reviews";

const PRODUCT_ID = "SKU-001";

export function App() {
  const [rating, setRating] = useState(5);
  const [text, setText] = useState("");
  const [summary, setSummary] = useState<ReviewSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    if (!isValidRating(rating)) {
      setError("評点は1〜5の整数で入力してください");
      return;
    }

    try {
      await createReview({ productId: PRODUCT_ID, rating, text });
      setSummary(await fetchSummary(PRODUCT_ID));
      setText("");
    } catch (cause) {
      setError(
        cause instanceof ApiError ? `送信に失敗しました (${cause.status})` : "送信に失敗しました",
      );
    }
  }

  return (
    <main>
      <h1>レビュー投稿</h1>

      <form onSubmit={handleSubmit}>
        <label htmlFor="rating">評点</label>
        <input
          id="rating"
          type="number"
          min={1}
          max={5}
          value={rating}
          onChange={(e) => setRating(Number(e.target.value))}
        />

        <label htmlFor="text">コメント</label>
        <textarea id="text" value={text} onChange={(e) => setText(e.target.value)} />

        <button type="submit">送信</button>
      </form>

      {error && <p role="alert">{error}</p>}
      {summary && <p data-testid="summary">{formatSummary(summary)}</p>}
    </main>
  );
}
