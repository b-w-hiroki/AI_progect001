import type { ReviewSummary } from "@repo/contracts";
import { describe, expect, it } from "vitest";
import { formatSummary, isValidRating, sentimentLabel } from "./reviews.js";

describe("sentimentLabel", () => {
  it("maps every sentiment to a label", () => {
    expect(sentimentLabel("positive")).toBe("好評");
    expect(sentimentLabel("neutral")).toBe("普通");
    expect(sentimentLabel("negative")).toBe("要改善");
  });
});

describe("isValidRating", () => {
  it.each([1, 3, 5])("accepts %i", (rating) => {
    expect(isValidRating(rating)).toBe(true);
  });

  it.each([0, 6, -1, 3.5, Number.NaN])("rejects %s", (rating) => {
    expect(isValidRating(rating)).toBe(false);
  });
});

describe("formatSummary", () => {
  it("formats a summary line", () => {
    const summary: ReviewSummary = {
      productId: "SKU-001",
      count: 3,
      averageRating: 4.33,
      sentiment: "positive",
    };

    expect(formatSummary(summary)).toBe("SKU-001: 4.3点 (3件) — 好評");
  });
});
