# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot


snapshots = Snapshot()

snapshots["test_confirm_signup_invalid_verification_code 1"] = {
    "body": {"data": None, "message": "Invalid confirmation code."},
    "statusCode": 400,
}

snapshots["test_confirm_signup[not_found-400] 1"] = {
    "body": {
        "data": None,
        "message": "Username test.user.foo@pogam-estate.com doesn't exist.",
    },
    "statusCode": 400,
}

snapshots["test_confirm_signup[unconfirmed-400] 1"] = {
    "body": {"data": None, "message": "Invalid confirmation code."},
    "statusCode": 400,
}

snapshots[
    "test_signup[hi-invitation code-400] 1"
] = """{
  "data": null,
  "message": "Invalid invitation code. Please contact an administrator."
}"""

snapshots[
    "test_signup[H3l!o W-invitation code-400] 1"
] = """{
  "data": null,
  "message": "Invalid invitation code. Please contact an administrator."
}"""

snapshots[
    "test_signup[h3llo world!-invitation code-400] 1"
] = """{
  "data": null,
  "message": "Invalid invitation code. Please contact an administrator."
}"""

snapshots[
    "test_signup[H3LLO WORLD!-invitation code-400] 1"
] = """{
  "data": null,
  "message": "Invalid invitation code. Please contact an administrator."
}"""

snapshots[
    "test_signup[H3llo World-invitation code-400] 1"
] = """{
  "data": null,
  "message": "Invalid invitation code. Please contact an administrator."
}"""

snapshots[
    "test_signup[H3llo World!-wrong invitation code-400] 1"
] = """{
  "data": null,
  "message": "Invalid invitation code. Please contact an administrator."
}"""

snapshots[
    "test_signup[hi-True-400] 1"
] = """{
  "data": null,
  "message": "Parameter validation failed:\\nInvalid length for parameter Password, value: 2, valid range: 6-inf"
}"""

snapshots[
    "test_signup[H3l!o W-True-400] 1"
] = """{
  "data": null,
  "message": "The password must be at least 8 characters long, have both upper and lower case letters, and at least one special character."
}"""

snapshots[
    "test_signup[h3llo world!-True-400] 1"
] = """{
  "data": null,
  "message": "The password must be at least 8 characters long, have both upper and lower case letters, and at least one special character."
}"""

snapshots[
    "test_signup[H3LLO WORLD!-True-400] 1"
] = """{
  "data": null,
  "message": "The password must be at least 8 characters long, have both upper and lower case letters, and at least one special character."
}"""

snapshots[
    "test_signup[H3llo World-True-400] 1"
] = """{
  "data": null,
  "message": "The password must be at least 8 characters long, have both upper and lower case letters, and at least one special character."
}"""

snapshots[
    "test_signup[H3llo World!-False-400] 1"
] = """{
  "data": null,
  "message": "Invalid invitation code. Please contact an administrator."
}"""

snapshots[
    "test_signup[H3llo World!-True-200] 1"
] = """{
  "data": null,
  "message": "Your account has been created. Please check your email for the confirmation code."
}"""

snapshots[
    "test_resend_verification_code[not_found-400] 1"
] = """{
  "data": null,
  "message": "Username test.user.foo@pogam-estate.com doesn\'t exist."
}"""

snapshots[
    "test_resend_verification_code[unconfirmed-200] 1"
] = """{
  "data": null,
  "message": "The confirmation code has been resent. Please check your email."
}"""

snapshots[
    "test_resend_verification_code[confirmed-200] 1"
] = """{
  "data": null,
  "message": "User is already confirmed."
}"""

snapshots[
    "test_confirm_signup[not_found-True-400] 1"
] = """{
  "data": null,
  "message": "Username test.user.foo@pogam-estate.com doesn\'t exist."
}"""

snapshots[
    "test_confirm_signup[confirmed-True-200] 1"
] = """{
  "data": null,
  "message": "User is already confirmed."
}"""

snapshots[
    "test_confirm_signup[confirmed-False-200] 1"
] = """{
  "data": null,
  "message": "User is already confirmed."
}"""

snapshots[
    "test_confirm_signup[unconfirmed-False-400] 1"
] = """{
  "data": null,
  "message": "Invalid confirmation code."
}"""

snapshots[
    "test_forgot_password[not_found-400] 1"
] = """{
  "data": null,
  "message": "Username test.user.foo@pogam-estate.com doesn\'t exist."
}"""

snapshots[
    "test_forgot_password[unconfirmed-400] 1"
] = """{
  "data": null,
  "message": "Username test.user.unconfirmed@pogam-estate.com is not yet confirmed."
}"""

snapshots[
    "test_forgot_password[confirmed-200] 1"
] = """{
  "data": null,
  "message": "Please check your registered email for the password reset code."
}"""

snapshots[
    "test_reset_password[not_found-True-400] 1"
] = """{
  "data": null,
  "message": "Username test.user.foo@pogam-estate.com doesn\'t exist."
}"""

snapshots[
    "test_reset_password[unconfirmed-True-400] 1"
] = """{
  "data": null,
  "message": "Verification code has expired. Please request a new verification code from the forgot password page."
}"""

snapshots[
    "test_reset_password[confirmed-True-400] 1"
] = """{
  "data": null,
  "message": "Verification code has expired. Please request a new verification code from the forgot password page."
}"""

snapshots[
    "test_reset_password[forgot_password-False-400] 1"
] = """{
  "data": null,
  "message": "Invalid confirmation code."
}"""

snapshots["test_authenticate[not_found-False-401] 1"] = {
    "data": None,
    "message": "The username or password is incorrect.",
}

snapshots["test_authenticate[unconfirmed-False-400] 1"] = {
    "data": None,
    "message": "User is not confirmed.",
}

snapshots["test_authenticate[confirmed-False-401] 1"] = {
    "data": None,
    "message": "The username or password is incorrect.",
}

snapshots["test_authenticate[confirmed-True-200] 1"] = {
    "data": {
        "expires_in": 3600,
        "refresh_token": "****hidden-secret****",
        "token": "****hidden-secret****",
    },
    "message": "Authentication successful.",
}

snapshots["test_profile[False-401] 1"] = {"message": "Unauthorized"}

snapshots["test_profile[True-200] 1"] = {
    "data": [
        {"Name": "sub", "Value": "****hidden-secret****"},
        {"Name": "email_verified", "Value": "True"},
        {"Name": "name", "Value": "Test User"},
        {"Name": "email", "Value": "test.user@pogam-estate.com"},
    ],
    "message": None,
}
