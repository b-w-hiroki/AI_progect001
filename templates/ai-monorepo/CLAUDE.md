# CLAUDE.md

> このファイルは毎ターン読み込まれる。**短く・事実だけ**を保つこと。
> 長い背景説明は `docs/` に置き、ここからリンクする。

## このプロジェクトについて

<!-- 1〜2行で。何を作っているか、誰のためか。 -->
（例）EC事業者向けのレビュー分析SaaS。レビューを収集・分類し、月次で改善レポートを出す。

## 変更したら必ず実行する

```bash
make check
```

lint・型チェック・テストをまとめて実行する（Python/TS を並列、約6秒）。
**これが通らない状態でコミットしない。**

| コマンド | 内容 |
|---|---|
| `make dev` | API(:8000) と フロント(:5173) を同時起動 |
| `make watch` | テストを監視実行。変更した分だけ再実行される |
| `make check-fast` | 型チェックとテストのみ（lintを飛ばす。作業中の反復用） |
| `make check` | lint + 型 + テスト。コミット前に必ず |
| `make fmt` | フォーマット自動修正 |

反復中は `make watch` か `make check-fast`、コミット前に `make check` が速い。

## ディレクトリ構造

```
apps/api/           FastAPI。src/api/ に実装、tests/ にテスト
  src/api/main.py     エンドポイント定義。薄く保つ
  src/api/reviews.py  ドメインロジック。純粋関数。外部I/Oを書かない
  src/api/contracts.py 入出力型（pydantic）
apps/web/           Vite + React
  src/api.ts          fetchはここに閉じ込める
  src/App.tsx         画面
packages/contracts/ API入出力型のTS版。フロント・バックの境界
docs/adr/           設計判断の記録。なぜそうしたかはここ
scripts/            開発用スクリプト
```

## 規約

- **API の入出力型を変えるときは `packages/contracts/src/index.ts` と `apps/api/src/api/contracts.py` を同時に変える。** 片方だけだと実行時まで気づけない
- **JSONは camelCase で統一。** Python側は pydantic の `alias_generator` が変換する。`test_serializes_to_camel_case` がこれを守る
- エンドポイント（`main.py`）は薄く。判断は `reviews.py` 側の純粋関数に置く。テストが速くなり検証ループが回る
- フロントの fetch は `apps/web/src/api.ts` にだけ書く。コンポーネントから直接叩かない
- テストは実装と同じ階層に置く（`reviews.py` → `test_reviews.py`、`App.tsx` → `App.test.tsx`）
- 型は `Any` / `as any` を使わない。mypy strict / tsc strict が通る形で書く
- 秘密情報は `.env` に置く。新しい環境変数を足したら `.env.example` にも追記する
- 設計判断をしたら `docs/adr/` に1ファイル追加する

## やらないこと

- `make check` を通さずにコミットしない
- 型エラーを `# type: ignore` / `as any` で黙らせない。直せない理由があるならコメントで書く
- 依頼されていないリファクタ・抽象化を追加しない
- `.env`、認証情報、実データを含むファイルを読み書きしない
- 開発サーバー（`make dev`）を起動したまま放置しない

## 環境構築

```bash
make setup   # uv sync + pnpm install
```
