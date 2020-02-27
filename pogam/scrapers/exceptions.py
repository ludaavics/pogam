import requests


class Captcha(requests.exceptions.RequestException):
    pass


class ListingParsingError(RuntimeError):
    pass
