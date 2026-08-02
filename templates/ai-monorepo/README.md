# AI開発向け モノレポテンプレート（Python + TypeScript）

AIに実装させる前提で初期設定を最適化した雛形。`make check` が通る状態で配布している。

```bash
cp -r templates/ai-monorepo ../my-new-project
cd ../my-new-project
make setup
make check      # ✅ all checks passed
```

---

## なぜこの構成なのか

AIコーディングの精度は、モデルの賢さより**「AIが自分で間違いに気づける環境か」**に強く依存する。
人間なら「なんか変だな」で気づくところを、AIはツールの出力でしか判断できない。
初期設定の効きが通常開発より大きいのはこのため。

効く順に4つ。

### 1. 検証ループを1コマンドに集約する（最重要）

AIは「実行 → エラーを読む → 直す」を回して収束する。このループの質がすべてを決める。

```bash
make check      # lint + 型チェック + テスト
```

- **単一** — 何を実行すべきか迷わせない。`CLAUDE.md` の指示が1行で済む
- **速い** — 遅いと実行回数が減り、まとめて修正して失敗しやすくなる。ruff / biome という単一バイナリを選んでいるのはこのため（このテンプレートでの実測値は `make check` 全体で約4秒）
- **機械可読** — ファイル名・行番号・エラーコードが出る

CIも**同じコマンド**を呼ぶ（`make setup && make check`）。分岐させると「ローカルは通るがCIで落ちる」が生まれ、AIには原因が見えない。

### 2. 型を厳しくする＝無料の教師信号

mypy strict / tsconfig strict。型エラーは**人間のレビューを介さずAIに届く唯一の検証信号**なので、ここを緩めると効果が丸ごと消える。

`Any` / `as any` での握りつぶしを禁止しているのも同じ理由。黙らせた瞬間に信号が消える。

### 3. 探索コストを下げる

AIは毎回コードベースを探索し直す。構造が予測可能なら探索が短く済み、そのぶん本題に使える。

- テストは実装と同じ階層構造（`src/api/reviews.py` → `tests/test_reviews.py`）
- ドメインロジックは純粋関数に寄せ、外部I/Oと分離する（テストが速く、変更の影響範囲が読める）
- `packages/contracts/` を境界の唯一の正にする

**contracts が効く理由**: フロントとバックを別々に実装させると、AIは両側で微妙に形の違うオブジェクトを作る。型が合っていないことに実行時まで誰も気づかない。型定義を1箇所に集約し、「両方を同時に変える」と `CLAUDE.md` とPRテンプレートの両方に書いてある。

### 4. ガードレールを置く

AIは速く動ける分、壊すのも速い。

- `.claude/settings.json` の `deny` で `.env` や鍵ファイルの読み取り、`terraform apply/destroy` を禁止
- `allow` に安全な読み取り系コマンドを列挙し、許可プロンプトを減らす（中断が減るほど作業が進む）
- `.gitignore` で `.env` を除外し、`.env.example` だけをコミット
- PRテンプレートのチェックリストで、漏れやすい項目（contracts の同時更新、`.env.example` への追記）を機械的に拾う

---

## ファイル構成と役割

| パス | 役割 |
|---|---|
| `CLAUDE.md` | **最重要。** AIが毎ターン読む前提情報。検証コマンド・構造・規約・禁止事項 |
| `Makefile` | 検証ループの入口。`setup` / `fmt` / `lint` / `types` / `test` / `check` |
| `.claude/settings.json` | 権限のallow/denyとフック登録 |
| `.claude/hooks/session-start.sh` | Web版セッション起動時に依存関係を入れる。無いと初手でテストが動かない |
| `pyproject.toml` | Python側の全設定（uv workspace / ruff / mypy / pytest） |
| `package.json` / `tsconfig.json` / `biome.json` | TypeScript側の全設定 |
| `packages/contracts/` | API入出力型。フロント・バックの境界 |
| `apps/api/` | Pythonバックエンド |
| `apps/web/` | TypeScriptフロントエンド |
| `docs/adr/` | 設計判断の記録 |
| `.github/workflows/ci.yml` | `make check` と同じものを回す |
| `.github/pull_request_template.md` | レビュー観点のチェックリスト |

## CLAUDE.md の書き方

**短く保つこと。** 毎ターン読み込まれるので、長いと毎回コンテキストを消費し、かつ重要な指示が埋もれる。

| 書く | 書かない |
|---|---|
| 検証コマンド | コードを読めば分かること |
| ディレクトリの意味 | 一般的なコーディング作法 |
| コードから推測できない規約 | 長い設計背景（→ `docs/adr/`） |
| 禁止事項 | 変わりやすい実装詳細 |

肥大化したら `docs/` に切り出してリンクする。

## ADR（設計判断の記録）

AIはセッションをまたぐと文脈を失う。一度決めたことを次のセッションで蒸し返したり、逆の判断をしたりする。
`docs/adr/` に残しておけばそれを防げる。1件5分で書ける粒度に留め、些細な判断は記録しない。

同梱の2件が書き方の例:
- `0001-record-architecture-decisions.md`
- `0002-single-verification-command.md`

---

## 検証済みの内容

このテンプレートは以下を実行して確認している（2026-07-31時点）。

| 項目 | 結果 |
|---|---|
| `make setup`（uv sync + pnpm install） | ✅ |
| `make check` 全体 | ✅ 警告ゼロ |
| ruff format / check | ✅ |
| mypy strict | ✅ 4ファイル |
| pytest | ✅ 18件 |
| biome check | ✅ |
| tsc strict | ✅ |
| vitest | ✅ 10件 |
| `.claude/settings.json` のJSON妥当性 | ✅ |
| SessionStart フック（remote / local 両方） | ✅ |

**未検証**: `.github/workflows/ci.yml` はこの環境からGitHub Actionsを起動できないため未実行。
初回PRで実際に回して確認すること。

## サンプルコードについて

`apps/api` と `apps/web` に入っているレビュー集計のコードは、**ツールチェーンが実際に動くことを示すための最小実装**。
新規プロジェクトで使うときは中身を差し替える。構造（テストの置き方、contractsとの対応、純粋関数への寄せ方）は流用する価値がある。

## カスタマイズの起点

| やりたいこと | 触る場所 |
|---|---|
| Webフレームワークを入れる | `apps/api/pyproject.toml` の `dependencies` |
| React等を入れる | `apps/web/package.json`、`tsconfig.json` の `lib`/`jsx` |
| lintルールの追加・除外 | `pyproject.toml` の `[tool.ruff.lint]`、`biome.json` |
| Terraformを足す | `infra/` を作り、`.claude/settings.json` の deny を確認 |
| フックを非同期化 | `.claude/hooks/session-start.sh` の先頭に `echo '{"async": true, "asyncTimeout": 300000}'` |

> フックは既定で同期実行にしている。セッション開始は遅くなるが、AIが初手で
> テストやlintを走らせたときに依存関係が未インストール、という競合状態を防げる。
> 起動速度を優先するなら非同期に変更する。
