from fastapi import Request
from fastapi.responses import JSONResponse

def openai_error(message: str, code: str, type: str = "invalid_request_error", status_code: int = 400):
    """
    Return an OpenAI-formatted error response.
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "message": message,
                "type": type,
                "param": None,
                "code": code
            }
        }
    )

# Common Errors
def error_invalid_api_key():
    return openai_error(
        "Incorrect API key provided.",
        "invalid_api_key",
        "authentication_error",
        401
    )

def error_quota_exceeded():
    return openai_error(
        "You have exceeded your current quota, please check your plan and billing details.",
        "insufficient_quota",
        "insufficient_quota",
        429
    )

def error_model_not_found(model_name: str):
    return openai_error(
        f"The model '{model_name}' does not exist",
        "model_not_found",
        "invalid_request_error",
        404
    )

def error_server(message: str):
    return openai_error(
        message,
        "internal_server_error",
        "server_error",
        500
    )
