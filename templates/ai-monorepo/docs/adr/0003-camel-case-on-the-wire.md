# ADR 0003: JSONは camelCase で統一し、Python側で自動変換する

- ステータス: 承認
- 日付: YYYY-MM-DD

## 背景

Python は snake_case、TypeScript は camelCase が慣習で、境界のどこかで変換が必要になる。
人手で対応付けると、片側だけ変更されたときに**型チェックでは検出できず、実行時まで気づけない**。

AIに両側を実装させる場合これが増幅する。フロントとバックを別のターンで書くと、
微妙に形の違うオブジェクトができ、しかも両方の型チェックは通ってしまう。

## 決定

- **通信するJSONは camelCase に統一する。**
- Python側は pydantic の `alias_generator=to_camel` で自動変換する。
  アプリケーションコードは snake_case のまま書ける（`populate_by_name=True`）。
- `extra="forbid"` を付け、想定外のキーが黙って捨てられないようにする。
- 出力形状をテストで固定する（`test_serializes_to_camel_case`）。
  ここが落ちたら、TS側の型と食い違ったということ。

## 結果

- 命名規約の差を人間が吸収しなくてよくなった
- 型定義の変更漏れが、実行時ではなくテストで検出される
- 入力については camelCase / snake_case の両方を受け付ける（`populate_by_name` の副作用）。
  これは互換性の観点では利点だが、「snake_caseで送ると弾かれる」ことは期待できない
- pydantic への依存が入る。バリデーションが実行時の検証信号として働くので、
  この依存は許容する
