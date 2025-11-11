import os

import boto3

cognito = boto3.client("cognito-idp")

USER_POOL_ID = os.environ["USER_POOL_ID"]
CLIENT_ID = os.environ["CLIENT_ID"]


def signup(email: str, password: str) -> dict:
    resp = cognito.sign_up(
        ClientId=CLIENT_ID,
        Username=email,
        Password=password,
        UserAttributes=[{"Name": "email", "Value": email}],
    )
    return {
        "userSub": resp.get("UserSub"),
        "userConfirmed": resp.get("UserConfirmed"),
    }


def login(email: str, password: str) -> dict:
    resp = cognito.initiate_auth(
        AuthFlow="USER_PASSWORD_AUTH",
        ClientId=CLIENT_ID,
        AuthParameters={"USERNAME": email, "PASSWORD": password},
    )
    return resp.get("AuthenticationResult", {})


def confirm(email: str, code: str) -> None:
    cognito.confirm_sign_up(
        ClientId=CLIENT_ID,
        Username=email,
        ConfirmationCode=code,
    )