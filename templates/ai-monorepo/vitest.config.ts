import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    include: ["apps/**/src/**/*.test.{ts,tsx}"],
    setupFiles: ["./vitest.setup.ts"],
    // 失敗を早く返すほど検証ループが速く回る
    reporters: "dot",
    // テストが1件も無い状態を失敗にしない。
    // これが false だと、サンプルを消した直後のプロジェクトで make check が
    // 「テストが無い」だけの理由で落ち、原因を誤認させる。
    passWithNoTests: true,
  },
});
