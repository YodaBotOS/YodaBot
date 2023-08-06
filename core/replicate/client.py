import asyncio
import json
import re
from typing import Any

import aiohttp
import yarl

from .dataclass import ReplicateResult, create_dataclass


# Keeping it simple cause this is only used to make predictions only, only sole purpose is to make it asynchronous.
class Replicate:
    BASE_URL = yarl.URL("https://api.replicate.com/v1/")

    def __init__(self, api_token: str, *, session: aiohttp.ClientSession = None) -> None:
        self.api_token = api_token
        self.session = session or aiohttp.ClientSession()

    def _get_headers(self):
        return {"Authorization": f"Token {self.api_token}"}

    async def get_latest_version(self, owner: str, model: str) -> str:
        """
        Get the latest version of a model.
        """
        async with self.session.get(
            self.BASE_URL / "models" / owner / model / "versions", headers=self._get_headers()
        ) as resp:
            data = await resp.json()

        return data["results"][0]["id"]

    async def run(self, model_version: str, *, wait: bool = True, **inputs) -> ReplicateResult:
        """
        Run a prediction in Replicate asynchronously.
        """
        # Similar code with the Official Replicate Python SDK
        # Split model_version into owner, name, version in format owner/name:version
        m = re.match(r"^(?P<owner>[^\/]+)\/(?P<model>[^:]+):(?P<version>.+)$", model_version)
        if not m:
            raise ValueError(f"Invalid model_version: {model_version}. Expected format: owner/name:version")

        owner = m.group("owner")
        model = m.group("model")
        version = m.group("version")

        if version == "latest":
            version = await self.get_latest_version(owner, model)

        data = {"version": version, "input": inputs}
        h = self._get_headers()
        h["Content-Type"] = "application/json"

        async with self.session.post(self.BASE_URL / "predictions", data=json.dumps(data), headers=h) as resp:
            js = await resp.json()
            prediction = create_dataclass(js, resp.status)

        if wait:
            done, pending = await asyncio.wait(
                [self._create_wait_task(model, version, prediction)], return_when=asyncio.FIRST_COMPLETED
            )

            if done:
                prediction = done.pop().result()

        return prediction

    async def get(self, prediction: ReplicateResult) -> ReplicateResult:
        """
        Get a prediction from Replicate asynchronously.
        """
        async with self.session.get(self.BASE_URL / "predictions" / prediction.id, headers=self._get_headers()) as resp:
            return create_dataclass(await resp.json(), resp.status)

    async def _create_wait_task(self, model: str, version: str, prediction: ReplicateResult) -> ReplicateResult:
        """
        Create a task that waits for the prediction to finish. For `wait=True` in `run()` method.
        """
        while True:
            response = await self.get(prediction)

            if response.status in ("succeeded", "failed", "canceled"):
                return response

            await asyncio.sleep(1.5)

    async def __call__(self, model_version: str, *, wait: bool = True, **inputs) -> ReplicateResult:
        return await self.run(model_version, wait=wait, **inputs)
