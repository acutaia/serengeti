#!/usr/bin/env python3
"""
Position Authentication concurrency

:author: Angelo Cutaia
:copyright: Copyright 2021, LINKS Foundation
:version: 1.0.0

..

    Copyright 2021 LINKS Foundation

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        https://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""

# Standard Library
from asyncio import Lock, Semaphore
from functools import lru_cache

# --------------------------------------------------------------------------------------------


@lru_cache(maxsize=1)
def store_semaphore() -> Semaphore:
    """Synchronize the position to store in order to avoid starvation"""
    return Semaphore(25)


# --------------------------------------------------------------------------------------------


@lru_cache(maxsize=1)
def position_auth() -> Semaphore:
    """Synchronize position authorization requests to prevent starvation"""
    return Semaphore(10)


# --------------------------------------------------------------------------------------------


@lru_cache(maxsize=1)
def position_test_lock() -> Lock:
    """Lock to prevent more than one test on the position authentication"""
    return Lock()
