import json

from . import service  # auth.service


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _get_payload(event: dict) -> dict:
    if "body" in event:
        body = event["body"]
        if isinstance(body, str):
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                return {}
        if isinstance(body, dict):
            return body
    return event


def _get_path(event: dict) -> str:
    ctx = event.get("requestContext", {})
    http = ctx.get("http", {})
    return http.get("path") or event.get("rawPath", "")


def lambda_handler(event, context):
    data = _get_payload(event)
    path = _get_path(event)

    if path.endswith("/signup"):
        email = data.get("email")
        password = data.get("password")
        if not email or not password:
            return _response(400, {"error": "email and password are required"})
        try:
            result = service.signup(email, password)
        except service.cognito.exceptions.UsernameExistsException:
            return _response(409, {"error": "User already exists"})
        except Exception as exc:
            return _response(500, {"error": str(exc)})
        return _response(200, {"message": "User created", **result})

    if path.endswith("/login"):
        email = data.get("email")
        password = data.get("password")
        if not email or not password:
            return _response(400, {"error": "email and password are required"})
        try:
            auth_result = service.login(email, password)
        except service.cognito.exceptions.NotAuthorizedException:
            return _response(401, {"error": "Invalid username or password"})
        except service.cognito.exceptions.UserNotConfirmedException:
            return _response(403, {"error": "User is not confirmed"})
        except Exception as exc:
            return _response(500, {"error": str(exc)})
        return _response(200, auth_result)

    if path.endswith("/confirm"):
        email = data.get("email")
        code = data.get("code")
        if not email or not code:
            return _response(400, {"error": "email and code are required"})
        try:
            service.confirm(email, code)
        except service.cognito.exceptions.CodeMismatchException:
            return _response(400, {"error": "Invalid confirmation code"})
        except service.cognito.exceptions.ExpiredCodeException:
            return _response(400, {"error": "Confirmation code expired"})
        except Exception as exc:
            return _response(500, {"error": str(exc)})
        return _response(200, {"message": "User confirmed"})

    return _response(400, {"error": "Unknown path"})