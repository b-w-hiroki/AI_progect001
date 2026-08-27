"""レビュー投稿・取得API。

Lab 1 の handler.py を拡張し、保存後に classify Lambda 向けのメッセージを
SQSへ送る。LLM呼び出しはここではしない — POSTの応答をLLM待ちにしないための分離。
外部依存なし（boto3 は Lambda ランタイムに同梱）。
"""

import json
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

TABLE_NAME = os.environ["TABLE_NAME"]
QUEUE_URL = os.environ["QUEUE_URL"]
VALID_RATINGS = range(1, 6)

table = boto3.resource("dynamodb").Table(TABLE_NAME)
sqs = boto3.client("sqs")


def respond(status, body):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "body": json.dumps(body, ensure_ascii=False, default=_json_default),
    }


def _json_default(value):
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    raise TypeError(f"not JSON serializable: {type(value)}")


def handler(event, context):
    route = event.get("routeKey", "")

    try:
        if route == "POST /reviews":
            return create_review(event)
        if route == "GET /reviews":
            return list_reviews(event)
        return respond(404, {"error": f"unknown route: {route}"})
    except Exception as exc:
        print(f"unhandled error: {exc!r}")
        return respond(500, {"error": "internal server error"})


def create_review(event):
    try:
        payload = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return respond(400, {"error": "body must be valid JSON"})

    product_id = payload.get("product_id")
    rating = payload.get("rating")
    text = payload.get("text", "")

    if not isinstance(product_id, str) or not product_id.strip():
        return respond(400, {"error": "product_id is required (non-empty string)"})
    if not isinstance(rating, int) or rating not in VALID_RATINGS:
        return respond(400, {"error": "rating must be an integer between 1 and 5"})
    if not isinstance(text, str):
        return respond(400, {"error": "text must be a string"})

    item = {
        "product_id": product_id.strip(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "review_id": str(uuid.uuid4()),
        "rating": rating,
        "text": text,
        # classify Lambda が書き戻すまでは未分類。GETした側が「まだ分類中」を
        # 区別できるよう、保存した時点で明示的にnullを入れておく。
        "sentiment": None,
    }
    table.put_item(Item=item)

    # レビューの保存自体は成功しているので、キュー投入の失敗で500にはしない。
    # 分類はあくまで付加価値であり、投稿の可否を左右してはいけない。
    try:
        sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(
                {
                    "product_id": item["product_id"],
                    "created_at": item["created_at"],
                    "text": item["text"],
                },
                ensure_ascii=False,
            ),
        )
    except Exception as exc:
        print(f"failed to enqueue classify job: {exc!r}")

    print(f"stored review product_id={item['product_id']} rating={rating}")
    return respond(201, item)


def list_reviews(event):
    params = event.get("queryStringParameters") or {}
    product_id = params.get("product_id")

    if not product_id:
        return respond(400, {"error": "query parameter product_id is required"})

    result = table.query(
        KeyConditionExpression=Key("product_id").eq(product_id),
        ScanIndexForward=False,
        Limit=50,
    )

    items = result.get("Items", [])
    return respond(200, {"product_id": product_id, "count": len(items), "items": items})
