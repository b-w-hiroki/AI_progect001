# PRコードレビューの導入

ClaudeにPRのコードレビューをさせる設定。方式が2つあり、プランで選択が変わる。

## どちらを使うか

| | A. マネージド Code Review | B. GitHub Actions |
|---|---|---|
| 実体 | Anthropic側のインフラで実行 | 自分のGitHub Actions上で実行 |
| プラン | **Team / Enterprise 限定**（research preview） | 制限なし |
| 設定 | 管理画面でリポジトリを選ぶだけ | ワークフローファイル + シークレット |
| APIキー | 不要 | `ANTHROPIC_API_KEY` が必要（またはBedrock） |
| 出力 | 該当行へのインラインコメント + `Claude Code Review` チェックラン + 重要度別の一覧 | PRコメント |
| 重要度 | 🔴 Important / 🟡 Nit / 🟣 Pre-existing のタグ付き | プロンプト次第 |
| 費用 | 1レビュー **$15〜25**。usage credits から別建てで請求 | APIトークン + Actions実行時間 |
| ZDR組織 | 利用不可 | 利用可 |

**このリポジトリでは B を設定済み**（個人プランのため）。
Team/Enterprise なら A のほうが設定が楽で、出力も構造化されている。

---

## B（GitHub Actions）のセットアップ手順

導入済みのファイル:

| ファイル | 役割 |
|---|---|
| `.github/workflows/code-review.yml` | PR作成時・ドラフト解除時に自動レビュー |
| `.github/workflows/claude.yml` | コメントで `@claude` と書くと応答・修正 |
| `REVIEW.md` | レビューの基準（重要度、指摘しないもの） |
| `CLAUDE.md` | プロジェクト全体の前提。レビューもこれを読む |

**動かすには以下の2つが必要。まだ未設定なら実施すること。**

### 1. Claude GitHub App をインストール

https://github.com/apps/claude から対象リポジトリにインストールする。

必要な権限:
- Contents: Read & write
- Issues: Read & write
- Pull requests: Read & write

### 2. `ANTHROPIC_API_KEY` をリポジトリシークレットに登録

1. https://console.anthropic.com でAPIキーを発行
2. リポジトリの Settings → Secrets and variables → Actions → New repository secret
3. 名前を `ANTHROPIC_API_KEY` にして値を貼る

> APIキーをワークフローファイルに直接書かないこと。必ずシークレット経由にする。

これで次のPRからレビューが動く。

---

## 費用を抑える設定

ソロ開発ではプッシュ回数が多くなりがちなので、既定は控えめにしてある。

**現在の設定**: `types: [opened, ready_for_review]` — PR作成時とドラフト解除時のみ。

毎プッシュでレビューさせたい場合は `synchronize` を足す:

```yaml
on:
  pull_request:
    types: [opened, ready_for_review, synchronize]   # ← 費用は増える
```

その他、入れてある抑制策:

- `concurrency` + `cancel-in-progress` — 連続プッシュ時に古い実行を止める
- `if: github.event.pull_request.draft == false` — ドラフトPRはレビューしない
- `--max-turns 20` — 暴走時の上限
- `timeout-minutes: 30` — ジョブ全体の上限
- `claude.yml` の `if` 条件 — `@claude` を含むコメントのときだけジョブを起動する

手動で再レビューしたいときは、Actions タブから `Code Review` ワークフローを
`workflow_dispatch` で実行する。

---

## レビュー内容の調整

**`REVIEW.md`** と **`CLAUDE.md`** の2つで制御する。読まれる範囲が違うので使い分ける。

| ファイル | マネージド Code Review | ローカル `/code-review` | GitHub Actions |
|---|---|---|---|
| `CLAUDE.md` | 読む（違反は Nit 扱い） | 読む | 読む |
| `REVIEW.md` | 読む（最優先で注入） | **読まない** | 保証なし |

つまり **確実に効かせたい規約は `CLAUDE.md`**、レビューだけに効かせたい調整を `REVIEW.md` に書く。

調整して効果が大きいのは以下。

**重要度の再定義** — 既定は本番コード向けの較正なので、教材リポジトリやプロトタイプでは
広すぎる。何を Important とするかを明示的に書く。

**Nitの上限** — 「1レビューあたり最大5件、残りは件数だけサマリに書く」。
これが無いとスタイル指摘で埋まって本題が見えなくなる。

**指摘しないもの** — CIが既に見ている範囲（lint、フォーマット、型）を除外する。
二重に指摘されても直す場所は同じで、ノイズになるだけ。

**再レビュー時の収束** — 「2回目以降は新規Nitを出さず Important のみ」。
一行の修正が些細な指摘で何往復もするのを防ぐ。

---

## ローカルでの事前レビュー

PRを出す前に手元で確認したい場合、Claude Code のセッションで:

```
/code-review
```

現在のブランチの差分（未コミット分を含む）をレビューする。
`--fix` で修正の適用、`--comment` でPRへのインラインコメント投稿もできる。

GitHub App のインストールもAPIキーも不要なので、まず試すならここから。

---

## A（マネージド）に切り替える場合

Team/Enterprise プランになったら、こちらのほうが手間が少ない。

1. https://claude.ai/admin-settings/claude-code の Code Review セクションで **Setup**
2. Claude GitHub App をインストール
3. 対象リポジトリを選択
4. リポジトリごとに **Review Behavior** を選ぶ
   - Once after PR creation（PR作成時のみ / 費用が読みやすい）
   - After every push（毎プッシュ / 最も高い）
   - Manual（`@claude review` コメント時のみ）

PRでのコマンド:

| コマンド | 動作 |
|---|---|
| `@claude review` | 1回だけレビュー。以降のプッシュは購読しない |
| `@claude review always` | レビューし、以降のプッシュでも自動実行するよう購読 |

月額の上限は https://claude.ai/admin-settings/usage で設定できる。

切り替えたら B のワークフロー（`code-review.yml`）は削除するか無効化すること。
両方動くと二重にレビューされ、二重に課金される。

---

## 未検証事項

`.github/workflows/*.yml` は、この環境からGitHub Actionsを起動できないため
**実行しての検証はしていない**（YAML構文の妥当性のみ確認済み）。

初回PRで以下を確認すること:

- [ ] `Code Review` ワークフローが起動する
- [ ] レビューコメントがPRに投稿される
- [ ] `@claude` コメントに `Claude` ワークフローが反応する
- [ ] 指摘の粒度が `REVIEW.md` の意図と合っている（合わなければ調整）

うまく動かない場合の確認順:

1. Actions タブでジョブが起動しているか（起動していない → `on:` の条件かApp未インストール）
2. ジョブのログに認証エラーが出ていないか（→ `ANTHROPIC_API_KEY` 未設定・無効）
3. `permissions` が足りているか（→ コメント投稿には `pull-requests: write` が必要）
