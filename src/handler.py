import json
import os

import boto3

cognito = boto3.client("cognito-idp")

USER_POOL_ID = os.environ["USER_POOL_ID"]
CLIENT_ID = os.environ["CLIENT_ID"]


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _get_payload(event: dict) -> dict:
    """
    Support both:
    - direct aws lambda invoke (event is already a dict)
    - API Gateway HTTP API (JSON string in event["body"])
    """
    if "body" in event:
        body = event["body"]
        if isinstance(body, str):
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                return {}
        if isinstance(body, dict):
            return body
    # fallback: assume event itself is the payload
    return event


def lambda_handler(event, context):
    """
    Simple auth backend:

    - action = "signup": create user in Cognito
    - action = "login":  start USER_PASSWORD_AUTH flow and return tokens
    """

    data = _get_payload(event)
    action = data.get("action")

    if action == "signup":
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return _response(400, {"error": "email and password are required"})

        try:
            resp = cognito.sign_up(
                ClientId=CLIENT_ID,
                Username=email,
                Password=password,
                UserAttributes=[{"Name": "email", "Value": email}],
            )
        except cognito.exceptions.UsernameExistsException:
            return _response(409, {"error": "User already exists"})
        except Exception as exc:  # simplified for demo
            return _response(500, {"error": str(exc)})

        return _response(
            200,
            {
                "message": "User created",
                "userSub": resp.get("UserSub"),
                "userConfirmed": resp.get("UserConfirmed"),
            },
        )

    if action == "login":
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return _response(400, {"error": "email and password are required"})

        try:
            resp = cognito.initiate_auth(
                AuthFlow="USER_PASSWORD_AUTH",
                ClientId=CLIENT_ID,
                AuthParameters={"USERNAME": email, "PASSWORD": password},
            )
        except cognito.exceptions.NotAuthorizedException:
            return _response(401, {"error": "Invalid username or password"})
        except cognito.exceptions.UserNotConfirmedException:
            return _response(403, {"error": "User is not confirmed"})
        except Exception as exc:
            return _response(500, {"error": str(exc)})

        auth_result = resp.get("AuthenticationResult", {})

        return _response(
            200,
            {
                "accessToken": auth_result.get("AccessToken"),
                "idToken": auth_result.get("IdToken"),
                "refreshToken": auth_result.get("RefreshToken"),
                "expiresIn": auth_result.get("ExpiresIn"),
                "tokenType": auth_result.get("TokenType"),
            },
        )

    return _response(400, {"error": "Unknown action"})