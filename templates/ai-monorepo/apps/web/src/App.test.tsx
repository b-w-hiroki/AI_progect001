import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { ApiError, createReview, fetchSummary } from "./api";

// ネットワークを叩かないようモジュールごと差し替える。
// `vi.spyOn(namespace, ...)` はESMのバインディングに効かない場合があるため vi.mock を使う。
vi.mock("./api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./api")>();
  return { ...actual, createReview: vi.fn(), fetchSummary: vi.fn() };
});

const mockCreateReview = vi.mocked(createReview);
const mockFetchSummary = vi.mocked(fetchSummary);

beforeEach(() => {
  vi.clearAllMocks();
});

describe("App", () => {
  it("投稿に成功すると集計が表示される", async () => {
    mockCreateReview.mockResolvedValue({ productId: "SKU-001", rating: 5, text: "" });
    mockFetchSummary.mockResolvedValue({
      productId: "SKU-001",
      count: 1,
      averageRating: 5,
      sentiment: "positive",
    });

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "送信" }));

    await waitFor(() => {
      expect(screen.getByTestId("summary")).toHaveTextContent("SKU-001: 5.0点 (1件) — 好評");
    });
    expect(mockCreateReview).toHaveBeenCalledWith({
      productId: "SKU-001",
      rating: 5,
      text: "",
    });
  });

  it("APIが失敗するとエラーを表示する", async () => {
    mockCreateReview.mockRejectedValue(new ApiError("boom", 500));

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "送信" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("送信に失敗しました (500)");
    expect(mockFetchSummary).not.toHaveBeenCalled();
  });
});
