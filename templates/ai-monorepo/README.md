# AI開発向け モノレポテンプレート（Python + TypeScript）

AIに実装させる前提で初期設定を最適化した雛形。**ブラウザで動く状態**で配布している。

```bash
cp -r templates/ai-monorepo ../my-project && cd ../my-project
git init
./scripts/bootstrap.sh my-project        # 名前置換・フック有効化・依存導入
make dev                                 # API :8000 / Web :5173
```

サンプル実装を消して骨組みだけ欲しい場合:

```bash
./scripts/bootstrap.sh my-project --strip-samples
```

### GitHubに置いたあと（PRレビューを使う場合）

`.github/workflows/code-review.yml` と `claude.yml` が入っているが、
**動かすには2つの初期設定が要る**。不要ならこの2ファイルを削除する。

1. [Claude GitHub App](https://github.com/apps/claude) をリポジトリにインストール
2. リポジトリシークレットに `ANTHROPIC_API_KEY` を登録
   （Settings → Secrets and variables → Actions）

レビューの基準は `REVIEW.md` で調整する。

---

## 何が入っているか

| スタック | 構成 |
|---|---|
| バックエンド | FastAPI + uvicorn / pydantic / pytest |
| フロントエンド | Vite + React 19 / Vitest + Testing Library |
| 共通 | uv（Pythonパッケージ管理）、pnpm workspace、ruff、mypy strict、biome、tsc strict |
| 自動化 | `make` の各ターゲット、pre-commitフック、GitHub Actions、Claude Code の SessionStart フック |

`make dev` でAPIとフロントが同時に立ち上がり、レビュー投稿→集計が**ブラウザで動く**ところから始められる。

---

## なぜこの構成なのか

AIコーディングの精度は、モデルの賢さより**「AIが自分で間違いに気づける環境か」**に強く依存する。
人間なら「なんか変だな」で気づくところを、AIはツールの出力でしか判断できない。
初期設定の効きが通常開発より大きいのはこのため。

効く順に5つ。

### 1. 検証ループを速く・単一にする（最重要）

AIは「実行 → エラーを読む → 直す」を回して収束する。このループの質がすべてを決める。

| コマンド | 用途 | 実測 |
|---|---|---|
| `make watch` | 反復中。変更した分だけ再実行 | 即時 |
| `make check-fast` | 反復中。lintを飛ばす | 約5秒 |
| `make check` | コミット前。全部 | 約6秒 |

`make check` は Python と TypeScript を並列実行する（直列7.4秒→並列6.2秒）。
劇的には縮まない — jsdom環境の起動が支配的なため。日常の反復には `make watch` のほうが効く。

CIも**同じ `make check`** を呼ぶ。分岐させると「ローカルは通るがCIで落ちる」が生まれ、AIには原因が見えない。

### 2. 型と実行時検証の二重化＝無料の教師信号

mypy strict / tsc strict に加えて、**pydantic が実行時にも検証する**。
型エラーもバリデーションエラーも、人間のレビューを介さずAIに届く検証信号なので、
ここを緩めると効果が丸ごと消える。`Any` / `as any` での握りつぶしを禁止しているのも同じ理由。

### 3. 境界の型を機械的に一致させる

フロントとバックを別々に実装させると、AIは両側で微妙に形の違うオブジェクトを作る。
型が合っていないことに実行時まで誰も気づかない。

対策は3段構え:

- `packages/contracts/src/index.ts` と `apps/api/src/api/contracts.py` を1対1で対応させる
- **JSONは camelCase に統一**。Python側は pydantic の `alias_generator` が自動変換するので、命名規約の差を人間が吸収しなくてよい
- `test_serializes_to_camel_case` が出力形状を固定する。崩れたらテストが落ちる

### 4. テンプレ→プロジェクトの手作業をなくす

`cp -r` した後に「名前を6箇所書き換えてサンプルを消して…」をやると、
その手作業自体がミスの温床になり、着手が遅れる。

`./scripts/bootstrap.sh <name>` が以下をまとめて行う:

1. `package.json` / `pyproject.toml` のプロジェクト名置換
2. `CLAUDE.md` のプレースホルダを、埋めるべきTODOに差し替え
3. `--strip-samples` ならサンプル実装を削除し、動く最小構成（`/health` のみ）に縮小
4. git hooks を有効化（`core.hooksPath .githooks`）
5. `.env.example` → `.env`
6. `make setup`

### 5. ガードレール

AIは速く動ける分、壊すのも速い。

- `.claude/settings.json` の `deny` で `.env`・鍵ファイルの読み取り、`terraform apply/destroy` を禁止
- `allow` に安全なコマンドを列挙し、許可プロンプトを減らす（中断が減るほど作業が進む）
- pre-commit フックが lint と型チェックを実行し、CIに行く前に止める
- PRテンプレートのチェックリストが、漏れやすい項目（contracts の同時更新、`.env.example`）を機械的に拾う

---

## ファイル構成

| パス | 役割 |
|---|---|
| `CLAUDE.md` | **最重要。** AIが毎ターン読む前提情報 |
| `REVIEW.md` | PRレビューの基準（重要度、指摘しないもの） |
| `Makefile` | すべての入口。`setup` / `dev` / `watch` / `check` / `check-fast` / `fmt` |
| `scripts/bootstrap.sh` | テンプレート→プロジェクト変換 |
| `.githooks/pre-commit` | コミット前に lint + 型チェック |
| `.claude/settings.json` | 権限のallow/denyとフック登録 |
| `.claude/hooks/session-start.sh` | Web版セッション起動時に依存を導入 |
| `pyproject.toml` | Python側の全設定（uv workspace / ruff / mypy / pytest） |
| `package.json` / `tsconfig.json` / `biome.json` / `vitest.config.ts` | TypeScript側の全設定 |
| `packages/contracts/` | API入出力型。境界の唯一の正 |
| `apps/api/` | FastAPI バックエンド |
| `apps/web/` | Vite + React フロントエンド |
| `docs/adr/` | 設計判断の記録 |
| `.github/workflows/ci.yml` | `make check` と同じものを回す |
| `.github/workflows/code-review.yml` | PR作成時にClaudeがコードレビュー |
| `.github/workflows/claude.yml` | コメントの `@claude` に応答・修正 |

## CLAUDE.md の書き方

**短く保つこと。** 毎ターン読み込まれるので、長いと毎回コンテキストを消費し、重要な指示が埋もれる。

| 書く | 書かない |
|---|---|
| 検証コマンド | コードを読めば分かること |
| ディレクトリの意味 | 一般的なコーディング作法 |
| コードから推測できない規約 | 長い設計背景（→ `docs/adr/`） |
| 禁止事項 | 変わりやすい実装詳細 |

## ADR（設計判断の記録）

AIはセッションをまたぐと文脈を失い、決定済みの議論を蒸し返す。`docs/adr/` に残せば防げる。
1件5分で書ける粒度に留め、些細な判断は記録しない。

---

## 検証済みの内容

2026-08-02 時点で、以下を実際に実行して確認している。

| 項目 | 結果 |
|---|---|
| `make setup` | ✅ |
| `make check`（並列） | ✅ 警告ゼロ / 約6秒 |
| pytest（ドメイン + API） | ✅ 25件 |
| vitest（純粋関数 + コンポーネント） | ✅ 12件 |
| mypy strict / tsc strict | ✅ |
| ruff / biome | ✅ |
| `make dev` → API `/health`・投稿・集計 | ✅ camelCaseで応答 |
| `make dev` → Vite (:5173) と `/api` proxy | ✅ HTTP 200 |
| `bootstrap.sh`（通常 / `--strip-samples`） | ✅ 別ディレクトリで実行して確認 |
| pre-commit フック（通過 / 型エラーで阻止） | ✅ |
| SessionStart フック（remote / local 分岐） | ✅ |

**未検証**: `.github/workflows/ci.yml` はこの環境からGitHub Actionsを起動できないため未実行。
テンプレート利用時の初回PRで確認すること。

構築中に見つけて直した不具合:
- `uv sync` が FastAPI を入れない（root の依存に workspace member が無かった）
- `--strip-samples` 後に vitest が「テストなし」で失敗 → `passWithNoTests`
- Testing Library の自動クリーンアップが効かず要素が重複 → setup で明示 `cleanup`
- `bootstrap.sh --help` がコード部分まで出力（行番号べた書き）→ コメント走査方式に変更

## サンプルコードについて

レビュー集計の実装は、**ツールチェーンが実際に動くことを示すための最小構成**。
`--strip-samples` で消せる。構造（エンドポイントを薄く保つ、fetchを`api.ts`に閉じ込める、
テストの置き方、contractsとの対応）は流用する価値がある。

## カスタマイズの起点

| やりたいこと | 触る場所 |
|---|---|
| DBを繋ぐ | `apps/api/pyproject.toml` に依存追加、`main.py` の `_store` を差し替え |
| ルーティングを増やす | `apps/web/package.json` に react-router 追加 |
| lintルールの追加・除外 | `pyproject.toml` の `[tool.ruff.lint]`、`biome.json` |
| Terraformを足す | `infra/` を作る。`.claude/settings.json` の deny を確認 |
| フックを非同期化 | `.claude/hooks/session-start.sh` の先頭に `echo '{"async": true, "asyncTimeout": 300000}'` |

> SessionStart フックは既定で同期実行。セッション開始は遅くなるが、AIが初手で
> テストを走らせたときに依存が未インストール、という競合を防げる。
> 起動速度を優先するなら非同期に変更する。
