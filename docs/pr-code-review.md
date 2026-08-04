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

**ファイルを置いただけでは動かない。以下を上から順に実施する。**
所要時間は10〜15分。ブラウザだけで完結する（ターミナル不要）。

---

### Step 0. `main` のワークフローに `id-token: write` があるか確認

https://github.com/b-w-hiroki/AI_progect001/blob/main/.github/workflows/code-review.yml
を開き、`permissions:` に `id-token: write` が含まれているか見る。

**無い場合は、それを追加するPR（#4）を先にマージすること。**
初版にはこれが欠けており、そのままでは以降の設定をしても必ず失敗する。

あれば何もせず Step 1 へ。

---

### Step 1. Claude GitHub App をインストール

1. https://github.com/apps/claude を開く
2. **Install** → 対象アカウント（`b-w-hiroki`）を選択
3. **Only select repositories** を選び、`AI_progect001` を指定
4. **Install** で確定

要求される権限（いずれも必要）:

| 権限 | 用途 |
|---|---|
| Contents: Read & write | コードの読み取り、`@claude` での修正コミット |
| Issues: Read & write | Issueへの応答 |
| Pull requests: Read & write | レビューコメントの投稿 |

> **All repositories は選ばないこと。** 個人の全リポジトリに書き込み権限を渡すことになる。

---

### Step 2. APIキーを発行し、使用量の上限を設定

1. https://console.anthropic.com にログイン
2. **API Keys** → **Create Key**
   - 名前は用途が分かるものにする（例: `github-actions-AI_progect001`）
   - **表示は1回きり。この画面を閉じる前にコピーする**
3. **Limits**（または Usage）から**月額の上限を設定する**

> 上限設定は飛ばさないこと。ワークフローの設定ミスでループした場合、
> これが唯一のストッパーになる。学習用途なら月 $20〜30 程度から始めれば十分。

キーを一時保存する場合は、メモアプリではなくパスワードマネージャに入れる。
使い終わったら消す。

---

### Step 3. `ANTHROPIC_API_KEY` をリポジトリシークレットに登録

1. https://github.com/b-w-hiroki/AI_progect001/settings/secrets/actions を開く
   （リポジトリ → **Settings** → **Secrets and variables** → **Actions**）
2. **New repository secret**
3. Name: `ANTHROPIC_API_KEY` ← **この名前ちょうど**。前後の空白やスペル違いに注意
4. Secret: Step 2 でコピーした値を貼る
5. **Add secret**

> - APIキーをワークフローファイルや `.env` に直接書かないこと
> - 登録後は値を再表示できない。間違えたら **Update** で入れ直す
> - Environment secrets ではなく **Repository secrets** に入れる（ワークフローが参照するのはこちら）

---

### Step 4. 動作確認

適当な変更でPRを作る（このリポジトリなら README に1行足すだけでよい）。
**ドラフトではなく通常のPRとして作成する** — ドラフトはレビュー対象外の設定にしてあるため。

確認する場所:

1. PRの **Checks** タブ、または Actions タブの `Code Review` ワークフロー
2. 成功なら数分後にPRへレビューコメントが付く

期待される結果:

| 状態 | 意味 |
|---|---|
| `success` + PRにコメント | ✅ 完了 |
| `skipped` | ドラフトPRのため。ドラフトを解除する |
| 約20秒で `failure` | `id-token: write` が無い → Step 0 に戻る |
| 認証エラーで `failure` | シークレットの名前か値が違う → Step 3 をやり直す |
| そもそも起動しない | App未インストール → Step 1 に戻る |

ログは Actions タブ → 該当の run → `review` ジョブで読める。
ログ中に `ANTHROPIC_API_KEY:` が**空**で出ていたら、シークレットが読めていない。

---

### Step 5.（任意）レビューの粒度を調整

数回動かしてみて、指摘が細かすぎる・的外れだと感じたら `REVIEW.md` を編集する。
調整の勘所は後述の「レビュー内容の調整」を参照。

---

### 参考: なぜ `id-token: write` が要るのか

（設定済みなので対応不要。テンプレートを他所で使い回すときのための記録）

`claude-code-action` は GitHub トークンの取得に OIDC を使う。
そのため以下が**両方のワークフローで必須**。

```yaml
permissions:
  contents: read        # claude.yml は write（修正をコミットするため）
  pull-requests: write
  issues: write
  id-token: write       # ← これが無いと即座に失敗する
```

AWS/GCP 連携用の権限だと誤解しやすいが、**APIキー方式でも必要**。
欠けていると起動から約20秒で以下のエラーで落ちる。

```
Could not fetch an OIDC token.
Did you remember to add `id-token: write` to your workflow permissions?
```

APIキーの検証より前の段階で失敗するので、
「シークレットは設定したのに動かない」ときは、まずここを疑う。

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

## 検証状況

PR #3・#4 で実際に起動し、以下まで確認できている。

| 項目 | 結果 |
|---|---|
| ドラフトPRでジョブが `skipped` になる | ✅ ガードは正常動作 |
| ドラフト解除で `ready_for_review` が発火する | ✅ 起動条件は正常 |
| OIDC → GitHub App トークンの交換 | ✅ `id-token: write` 追加後に成功 |
| Claude Code のインストール | ✅ v2.1.220 |
| アクションが最後まで完走する | ❌ **未確認** |
| レビューコメントの投稿 | ❌ **未確認** |
| `@claude` への応答 | ❌ **未確認** |

PR #4 の実行ログで、Claude GitHub App が**インストール済みであることも確認できた**
（OIDC からアプリトークンへの交換が成功しているため）。
残るのは `ANTHROPIC_API_KEY` の登録のみだった。

次のPRで以下を確認すること:

- [ ] `Code Review` ワークフローが完走する（`conclusion: success`）
- [ ] レビューコメントがPRに投稿される
- [ ] `@claude` コメントに `Claude` ワークフローが反応する
- [ ] 指摘の粒度が `REVIEW.md` の意図と合っている（合わなければ調整）

### 失敗時の切り分け

**ジョブが起動しない**
`on:` の条件、ドラフト状態、またはApp未インストール。

**`skipped` で終わる**
ドラフトPRのため。意図した挙動なので、ドラフトを解除する。

**約20秒で `failure`。ログに以下:**

```
Could not fetch an OIDC token.
Did you remember to add `id-token: write` to your workflow permissions?
```

→ `permissions` に `id-token: write` が無い。

**約10秒で `failure`。ログに以下:**

```
Environment variable validation failed:
  - Either ANTHROPIC_API_KEY, CLAUDE_CODE_OAUTH_TOKEN, or workload identity
    federation (ANTHROPIC_FEDERATION_RULE_ID and ANTHROPIC_ORGANIZATION_ID)
    is required when using direct Anthropic API.
```

→ シークレットが読めていない。同じログの `ANTHROPIC_API_KEY:` が空になっている。
Repository secrets に `ANTHROPIC_API_KEY` という名前ちょうどで登録されているか確認する
（Variables タブや Environment secrets に入れた場合もこれになる）。

**コメントが投稿されない**
`pull-requests: write` の欠落。

> どこまで進んだかは、ログの以下の行で判断できる。
> `OIDC token successfully obtained` → `App token successfully obtained`
> → `Claude Code successfully installed!` の順に出る。
> どこで止まったかが、そのまま原因の切り分けになる。
