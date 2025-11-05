import datetime
import json


def lambda_handler(event, context):
    """
    Basic example Lambda handler.
    """
    name = event.get("name", "world")
    now = datetime.datetime.utcnow().isoformat()

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "message": f"Hello, {name}!",
            "timestamp": now,
        }),
    }