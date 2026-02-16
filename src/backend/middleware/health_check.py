import logging
from typing import Awaitable, Callable, Dict

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware


class HealthCheckResult:
    def __init__(self, status: bool, message: str):
        self.status = status
        self.message = message


class HealthCheckSummary:
    def __init__(self):
        self.status = True
        self.results = {}

    def Add(self, name: str, result: HealthCheckResult):
        self.results[name] = result
        self.status = self.status and result.status

    def AddDefault(self):
        self.Add(
            "Default",
            HealthCheckResult(
                True, "This is the default check, it always returns True"
            ),
        )

    def AddException(self, name: str, exception: Exception):
        self.Add(name, HealthCheckResult(False, str(exception)))


class HealthCheckMiddleware(BaseHTTPMiddleware):
    __healthz_path = "/healthz"

    def __init__(
        self,
        app,
        checks: Dict[str, Callable[..., Awaitable[HealthCheckResult]]],
        password: str = None,
    ):
        super().__init__(app)
        self.checks = checks
        self.password = password

    async def check(self) -> HealthCheckSummary:
        results = HealthCheckSummary()
        results.AddDefault()

        for name, check in self.checks.items():
            if not name or not check:
                continue
            try:
                if not callable(check) or not hasattr(check, "__await__"):
                    logging.error(f"Check {name} is not a coroutine function")
                    raise ValueError(f"Check {name} is not a coroutine function")
                results.Add(name, await check())
            except Exception as e:
                logging.error(f"Check {name} failed: {e}")
                results.AddException(name, e)

        return results

    async def dispatch(self, request: Request, call_next):
        if request.url.path == self.__healthz_path:
            status = await self.check()

            status_code = 200 if status.status else 503
            status_message = "OK" if status.status else "Service Unavailable"

            if (
                self.password is not None
                and request.query_params.get("code") == self.password
            ):
                return JSONResponse(jsonable_encoder(status), status_code=status_code)

            return PlainTextResponse(status_message, status_code=status_code)

        response = await call_next(request)
        return response
