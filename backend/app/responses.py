from fastapi.responses import JSONResponse


def ok(data=None, message="Operation completed successfully.", status_code=200):
    return JSONResponse(
        status_code=status_code,
        content={"success": True, "message": message, "data": data if data is not None else {}},
    )


def fail(message: str, error_code: str, status_code: int = 400):
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "message": message, "error_code": error_code},
    )
