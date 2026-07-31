"""レビュー投稿・取得API。

API Gateway HTTP API (payload format 2.0) から呼ばれる。
外部依存なし — boto3 は Lambda ランタイムに同梱されている。
"""

import json
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

TABLE_NAME = os.environ["TABLE_NAME"]
VALID_RATINGS = range(1, 6)

table = boto3.resource("dynamodb").Table(TABLE_NAME)


def respond(status, body):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "body": json.dumps(body, ensure_ascii=False, default=_json_default),
    }


def _json_default(value):
    # DynamoDB は数値を Decimal で返すため、json.dumps がそのままでは失敗する
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
        # スタックトレースは CloudWatch Logs に出し、クライアントには詳細を返さない
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
        # ISO8601のUTC。文字列としてソートすると時系列順になるのでSKに適している
        "created_at": datetime.now(timezone.utc).isoformat(),
        "review_id": str(uuid.uuid4()),
        "rating": rating,
        "text": text,
    }
    table.put_item(Item=item)

    print(f"stored review product_id={item['product_id']} rating={rating}")
    return respond(201, item)


def list_reviews(event):
    params = event.get("queryStringParameters") or {}
    product_id = params.get("product_id")

    if not product_id:
        return respond(400, {"error": "query parameter product_id is required"})

    # Query は必ず PK 指定が要る。PK なしで全件取るのは Scan で、
    # テーブル全体を読むため遅く高い。実運用では基本的に使わない。
    result = table.query(
        KeyConditionExpression=Key("product_id").eq(product_id),
        ScanIndexForward=False,  # SK の降順 = 新しい順
        Limit=50,
    )

    items = result.get("Items", [])
    return respond(200, {"product_id": product_id, "count": len(items), "items": items})
