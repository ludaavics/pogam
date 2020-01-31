import base64
import os
import hashlib
import hmac
import json
import logging
import secrets

import boto3

logger = logging.getLogger("pogam")


USER_POOL_ID = os.getenv("USER_POOL_ID")
CLIENT_ID = os.getenv("USER_POOL_CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
STAGE = os.environ["STAGE"]


def _get_secret_hash(username):
    if CLIENT_SECRET is None:
        return ""

    msg = username + CLIENT_ID
    dig = hmac.new(
        str(CLIENT_SECRET).encode("utf-8"),
        msg=str(msg).encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    d2 = base64.b64encode(dig).decode()
    return d2


def _jsonify(status_code, data, message):
    body = {"data": data, "message": message}
    return {"statusCode": status_code, "body": json.dumps(body, indent=2)}


def signup(event, context):
    print(USER_POOL_ID)
    print(CLIENT_ID)
    # input validation
    data = json.loads(event["body"])
    for field in ["username", "email", "password", "name", "invitation_code"]:
        if not data.get(field):
            status_code = 400
            data = None
            msg = f"Field '{field}' is missing."
            return _jsonify(status_code, data, msg)
    username = data["username"]
    email = data["email"]
    password = data["password"]
    name = data["name"]
    invitation_code = data["invitation_code"]

    # invitation code
    ssm = boto3.client("ssm")
    try:
        current_invitation_code = ssm.get_parameter(
            Name=f"/pogam/{STAGE}/users/invitation-code", WithDecryption=False
        )["Parameter"]["Value"]
    except ssm.exceptions.ParameterNotFound:
        new_invitation_code = secrets.token_urlsafe()
        ssm.put_parameter(
            Name=f"/pogam/{STAGE}/users/invitation-code",
            Description="Invitation code for user sign up.",
            Value=new_invitation_code,
            Type="String",
            Tier="Standard",
        )
        status_code = 400
        data = None
        msg = f"Invalid invitation code. Please contact an administrator."
        return _jsonify(status_code, data, msg)

    if invitation_code != current_invitation_code:
        status_code = 400
        data = None
        msg = f"Invalid invitation code. Please contact an administrator."
        return _jsonify(status_code, data, msg)

    cognito = boto3.client("cognito-idp")
    try:
        cognito.sign_up(
            ClientId=CLIENT_ID,
            Username=username,
            Password=password,
            UserAttributes=[
                {"Name": "name", "Value": name},
                {"Name": "email", "Value": email},
            ],
            ValidationData=[
                {"Name": "email", "Value": email},
                {"Name": "custom:username", "Value": username},
            ],
        )
    except cognito.exceptions.UsernameExistsException:
        status_code = 400
        data = None
        msg = "This username already exists."
        return _jsonify(status_code, data, msg)
    except cognito.exceptions.InvalidPasswordException:
        status_code = 400
        data = None
        msg = (
            "The password must have both upper and lower case letters, "
            "special characeters and numbers."
        )
        return _jsonify(status_code, data, msg)
    except cognito.exceptions.UserLambdaValidationException:
        status_code = 400
        data = None
        msg = "This email already exists."
        return _jsonify(status_code, data, msg)
    except Exception as e:
        # we dont want client to see an unexpected error, but we wanna log it
        logger.error(e)
        status_code = 500
        data = str(e)
        msg = "Unexpected server error."
        return _jsonify(status_code, data, msg)

    status_code = 200
    data = None
    msg = (
        "Your account has been created. "
        "Please check your email for the validation code."
    )
    return _jsonify(status_code, data, msg)
