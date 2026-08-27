"""レビューをBedrock経由のClaudeで分類し、DynamoDBへ書き戻す。

SQS（batch_size=1）からトリガーされる。1メッセージ = 1レビュー。
失敗した場合は例外をそのまま送出する。SQSが自動的に再試行し、
`main.tf` の redrive_policy に従って一定回数失敗したメッセージはDLQへ移る
（このLambda側でリトライ処理を書く必要はない）。
"""

import json
import os

import boto3
from anthropic import AnthropicBedrockMantle

TABLE_NAME = os.environ["TABLE_NAME"]
BEDROCK_MODEL_ID = os.environ["BEDROCK_MODEL_ID"]
# AWS_REGION はLambdaランタイムが自動的に設定する予約済み環境変数。
# 自前で変数を用意する必要はない。
AWS_REGION = os.environ["AWS_REGION"]

VALID_SENTIMENTS = {"positive", "negative", "neutral"}

SYSTEM_PROMPT = (
    "あなたはECサイトのレビューを分類する担当者です。"
    "レビュー本文を読み、positive / negative / neutral のいずれか1語だけで回答してください。"
    "説明や句読点、前置きは一切不要です。"
)

table = boto3.resource("dynamodb").Table(TABLE_NAME)
bedrock = AnthropicBedrockMantle(aws_region=AWS_REGION)


def handler(event, context):
    for record in event["Records"]:
        process_record(record)


def process_record(record):
    payload = json.loads(record["body"])
    product_id = payload["product_id"]
    created_at = payload["created_at"]
    text = payload["text"]

    sentiment = classify(text) if text.strip() else "neutral"

    table.update_item(
        Key={"product_id": product_id, "created_at": created_at},
        # 属性名を式に直接書かず ExpressionAttributeNames を経由する。
        # DynamoDBは予約語が多く、直書きすると属性名によっては ValidationException になる。
        UpdateExpression="SET #sentiment = :s",
        ExpressionAttributeNames={"#sentiment": "sentiment"},
        ExpressionAttributeValues={":s": sentiment},
    )
    print(f"classified product_id={product_id} created_at={created_at} sentiment={sentiment}")


def classify(text):
    message = bedrock.messages.create(
        model=BEDROCK_MODEL_ID,
        max_tokens=16,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
    )

    raw = ""
    for block in message.content:
        if block.type == "text":
            raw += block.text

    answer = raw.strip().lower()
    if answer in VALID_SENTIMENTS:
        return answer

    # モデルが指示に従わず余計な語を返すことがある。決め打ちで揃えず、
    # 判定不能を明示する値を返す — 沈黙して positive 扱いにする方が危険。
    print(f"unrecognized sentiment output: {raw!r}")
    return "unknown"
