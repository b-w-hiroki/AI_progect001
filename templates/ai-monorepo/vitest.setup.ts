// toHaveTextContent などのDOM向けマッチャを有効にする
import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// globals: true を使わない構成では自動クリーンアップが働かないため明示する。
// これが無いと前のテストのDOMが残り、「要素が複数見つかる」で落ちる。
afterEach(cleanup);
