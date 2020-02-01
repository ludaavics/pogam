import json
import logging
import os
import secrets

import boto3

logger = logging.getLogger("pogam")


USER_POOL_ID = os.getenv("USER_POOL_ID")
CLIENT_ID = os.getenv("USER_POOL_CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
STAGE = os.environ["STAGE"]


def _jsonify(status_code, data, message):
    body = {"data": data, "message": message}
    return {
        "statusCode": status_code,
        "body": json.dumps(body, indent=2),
    }


def _raise(message, status_code=400):
    data = None
    return _jsonify(status_code, data, message)


def _validate(data, fields):
    for field in fields:
        if not data.get(field):
            msg = f"Field '{field}' is missing."
            return _raise(msg)


def signup(event, context):
    # input validation
    data = json.loads(event["body"])
    _validate(data, ["username", "email", "password", "name", "invitation_code"])
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
        msg = f"Invalid invitation code. Please contact an administrator."
        return _raise(msg)

    if invitation_code != current_invitation_code:
        msg = f"Invalid invitation code. Please contact an administrator."
        return _raise(msg)

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
        msg = "This username already exists."
        return _raise(msg)
    except cognito.exceptions.InvalidPasswordException:
        msg = (
            "The password must have both upper and lower case letters, "
            "special characeters and numbers."
        )
        return _raise(msg)
    except cognito.exceptions.UserLambdaValidationException:
        msg = "This email already exists."
        return _raise(msg)
    except Exception as e:
        # we dont want client to see an unexpected error, but we wanna log it
        logger.error(e)
        status_code = 500
        msg = (
            "Unexpected server error. "
            "If this persists, please contact an administrator."
        )
        return _raise(msg, status_code=status_code)

    status_code = 200
    data = None
    msg = (
        "Your account has been created. "
        "Please check your email for the confirmation code."
    )
    return _jsonify(status_code, data, msg)


def resend_confirmation(event, context):
    data = json.loads(event["body"])
    _validate(data, ["username"])
    username = data.get("username")

    client = boto3.client("cognito-idp")
    try:
        client.resend_confirmation_code(
            ClientId=CLIENT_ID, Username=username,
        )
    except client.exceptions.UserNotFoundException:
        msg = f"Username {username} doesn't exist."
        return _raise(msg)
    except client.exceptions.InvalidParameterException:
        msg = f"User is already confirmed."
        status_code = 200
        data = None
        return _jsonify(status_code, data, msg)
    except Exception as e:
        logger.error(e)
        status_code = 500
        msg = (
            "Unexpected server error. "
            "If this persists, please contact an administrator."
        )
        return _raise(msg, status_code=status_code)

    status_code = 200
    data = None
    msg = "The confirmation code has been resent. Please check your email."
    return _jsonify(status_code, data, msg)


def confirm(event, context):
    data = json.loads(event["body"])
    _validate(data, ["username", "confirmation_code"])
    username = data["username"]
    confirmation_code = data["confirmation_code"]

    client = boto3.client("cognito-idp")
    try:
        client.confirm_sign_up(
            ClientId=CLIENT_ID,
            Username=username,
            ConfirmationCode=confirmation_code,
            ForceAliasCreation=False,
        )
    except client.exceptions.UserNotFoundException:
        msg = f"Username {username} doesn't exist."
        return _raise(msg)
    except client.exceptions.CodeMismatchException:
        msg = "Invalid confirmation code."
        return _raise(msg)
    except client.exceptions.NotAuthorizedException:
        msg = f"User is already confirmed."
        status_code = 200
        data = None
        return _jsonify(status_code, data, msg)
    except Exception as e:
        logger.error(e)
        status_code = 500
        msg = (
            "Unexpected server error. "
            "If this persists, please contact an administrator."
        )
        return _raise(msg, status_code=status_code)

    status_code = 200
    data = None
    msg = "Your account has been confirmed. You can now log in."
    return _jsonify(status_code, data, msg)


def forgot_password(event, context):
    data = json.loads(event["body"])
    _validate(data, ["username"])
    username = data["username"]

    client = boto3.client("cognito-idp")
    try:
        client.forgot_password(
            ClientId=CLIENT_ID, Username=username,
        )
    except client.exceptions.UserNotFoundException:
        msg = f"Username {username} doesn't exist."
        return _raise(msg)
    except client.exceptions.InvalidParameterException:
        msg = f"Username {username} is not yet confirmed."
        return _raise(msg)
    except Exception as e:
        logger.error(e)
        status_code = 500
        msg = (
            "Unexpected server error. "
            "If this persists, please contact an administrator."
        )
        return _raise(msg, status_code=status_code)

    status_code = 200
    data = None
    msg = "Please check your registered email for the password reset code."
    return _jsonify(status_code, data, msg)


def reset_password(event, context):
    data = json.loads(event["body"])
    _validate(data, ["username", "password", "confirmation_code"])
    username = data["username"]
    password = data["password"]
    confirmation_code = data["confirmation_code"]

    client = boto3.client("cognito-idp")
    try:
        client.confirm_forgot_password(
            ClientId=CLIENT_ID,
            Username=username,
            ConfirmationCode=confirmation_code,
            Password=password,
        )
    except client.exceptions.UserNotFoundException:
        msg = f"Username {username} doesn't exist."
        return _raise(msg)
    except client.exceptions.CodeMismatchException:
        msg = "Invalid confirmation code."
        return _raise(msg)
    except client.exceptions.NotAuthorizedException:
        msg = f"User is already confirmed."
        status_code = 200
        data = None
        return _jsonify(status_code, data, msg)
    except Exception as e:
        logger.error(e)
        status_code = 500
        msg = (
            "Unexpected server error. "
            "If this persists, please contact an administrator."
        )
        return _raise(msg, status_code=status_code)

    status_code = 200
    data = None
    msg = "Your password has been reset. You can now log in."
    return _jsonify(status_code, data, msg)
