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

lint・フォーマット・型チェック・テストをまとめて実行する。**これが通らない状態でコミットしない。**

個別に回したいとき:

| コマンド | 内容 |
|---|---|
| `make fmt` | フォーマット自動修正（Python: ruff / TS: biome） |
| `make lint` | 静的解析 |
| `make types` | 型チェック（Python: mypy strict / TS: tsc） |
| `make test` | テスト（pytest / vitest） |
| `make check` | 上記すべて |

## ディレクトリ構造

```
apps/api/          Python バックエンド。src/api/ 配下に実装、tests/ にテスト
apps/web/          TypeScript フロントエンド
packages/contracts/ API の入出力型。フロント・バックの境界はここが唯一の正
infra/             Terraform。環境ごとに分ける
docs/adr/          アーキテクチャ決定記録。なぜそうしたかはここ
scripts/           開発用スクリプト
```

## 規約

- **API の入出力型を変えるときは `packages/contracts/` と `apps/api/src/api/contracts.py` を同時に変える。** 片方だけ変えると実行時まで気づけない
- テストは実装と同じ階層構造に置く（`src/api/reviews.py` → `tests/test_reviews.py`）
- 型は `Any` を使わない。mypy strict / tsc strict が通る形で書く
- 秘密情報は `.env` に置き、コミットしない。新しい環境変数を足したら `.env.example` にも追記する
- 設計上の判断をしたら `docs/adr/` に1ファイル追加する。次に読む人（と次のセッションのAI）が同じ議論を繰り返さないため

## やらないこと

- `make check` を通さずにコミットしない
- 型エラーを `# type: ignore` / `as any` で黙らせない。直せない理由があるならコメントで書く
- 依頼されていないリファクタ・抽象化を追加しない
- `.env`、認証情報、実データを含むファイルを読み書きしない

## 環境構築

```bash
make setup   # uv sync + pnpm install
```

初回のみ。`.env.example` を `.env` にコピーして値を埋める。
