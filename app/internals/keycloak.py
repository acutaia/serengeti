#!/usr/bin/env python3
"""
Keycloack package

:author: Angelo Cutaia
:copyright: Copyright 2021, Angelo Cutaia
:version: 1.0.0

..

    Copyright 2021 Angelo Cutaia

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""

# Standard Library
from asyncio import Lock, Semaphore
from functools import lru_cache
import time

# Third Party
from fastapi import status, HTTPException
from aiohttp import ClientSession, ClientResponseError, ClientTimeout, ServerTimeoutError
import orjson

# Internal
from .logger import get_logger
from ..config import get_keycloack_settings
from ..models.model import orjson_dumps
from ..models.security import Token

# --------------------------------------------------------------------------------------------


class _Keycloak:
    """Class that handles the communication with keycloack"""

    last_token_reception_time: float
    """UTC timestamp"""

    last_token: str
    """Token"""

    async_lock: Lock
    """Asynchronous lock """

    async_semaphore: Semaphore
    """Asynchronous semaphore"""

    async def setup(self):
        """
        Setup keycloack, call this method only inside the startup event
        """
        self.async_lock = Lock()
        self.async_semaphore = Semaphore(30)
        self.last_token = await self._get_token()
        self.last_token_reception_time = time.time()

    @classmethod
    async def _get_token(cls):
        """
        Private method used to make the http request to keycloack
        in order to obtain a valid token
        """
        # Get Logger
        logger = get_logger()
        # Get settings
        settings = get_keycloack_settings()

        # timeout to obtain  token
        timeout = ClientTimeout(total=30)
        try:
            async with ClientSession(raise_for_status=True, json_serialize=orjson_dumps, timeout=timeout) as session:
                async with session.post(
                    url=settings.token_request_url,
                    data={
                        "client_id": settings.client_id,
                        "username": settings.username_keycloak,
                        "password": settings.password,
                        "grant_type": settings.grant_type,
                        "client_secret": settings.client_secret
                    }
                ) as resp:
                    return Token.parse_obj(
                        await resp.json(
                            encoding="utf-8",
                            loads=orjson.loads,
                            content_type=None
                        )
                    ).access_token

        except ClientResponseError as exc:
            await logger.error(
                {
                    "method": exc.request_info.method,
                    "url": exc.request_info.url,
                    "client_id": settings.client_id,
                    "username": settings.username_keycloak,
                    "password": settings.password,
                    "grant_type": settings.grant_type,
                    "client_secret": settings.client_secret,
                    "status_code": exc.status,
                    "error": exc.message
                }
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Wrong credentials"
            )
        except ServerTimeoutError as exc:
            # Can't contact keycloack
            await logger.warning(
                {
                    "url": settings.token_request_url,
                    "error": exc
                }
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Can't contact Keycloack service"
            )

    async def get_ublox_token(self):
        """
        Obtain a token from keycloack. If 150 seconds are passed since the last token was obtained,
        it will obtain a fresh one and adjust it's timestamp
        """

        # Use an a semaphore to let pass 100 coroutines
        async with self.async_semaphore:
            # timestamp of this moment
            now = time.time()

            # Check if it's been at least 50 seconds since last token was obtained
            if now - self.last_token_reception_time > 50:

                # Check if the lock is already acquired by a coroutine
                if self.async_lock.locked():

                    # Await until the lock is released by the other coroutine
                    # and after that release it
                    await self.async_lock.acquire()
                    self.async_lock.release()

                    # Here we are sure that the token was updated
                    return self.last_token

                # Only one coroutine has to update the token
                async with self.async_lock:
                    # Update token and timestamp
                    self.last_token = await self._get_token()
                    self.last_token_reception_time = time.time()

            # return the stored token
            return self.last_token

# --------------------------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _get_keycloack() -> _Keycloak:
    """Instantiate a singleton  Keycloack"""
    return _Keycloak()

# --------------------------------------------------------------------------------------------


KEYCLOACK = _get_keycloack()
"""Keycloack Singleton"""
