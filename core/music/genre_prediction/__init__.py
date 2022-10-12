import time
import typing
import asyncio

import aiohttp

FAST_BEST = typing.Literal["fast", "best"]


class GenrePrediction:
    URL = "https://api.yodabot.xyz/v/{}/music/predict-genre"  # Use Yoda API

    def __init__(self, *, session: aiohttp.ClientSession = None, api_version='1'):
        self.session: aiohttp.ClientSession = session or aiohttp.ClientSession()

        self.url = self.URL.format(api_version)  # Yoda API v1

    async def __call__(self, file: bytes | str, *,
                       mode: FAST_BEST = "fast") -> tuple[dict[str, int | float], float, float, int | float]:
        return await self.run(file, mode=mode)

    async def read_url(self, url) -> bytes:
        async with self.session.get(url) as resp:
            return await resp.read()

    async def call_api(self, file: bytes, *, mode: FAST_BEST = "fast") -> dict:
        params = {'mode': mode}

        data = aiohttp.FormData()
        data.add_field("file", file)

        async with self.session.post(self.url, data=data, params=params) as resp:
            d = await resp.json()

        return d

    async def get_result_from_job_id(self, job_id: str) -> dict:
        data = {'status': 'pending'}

        url = self.url + f"/{job_id}"

        while data['status'] in ['pending', 'running']:
            async with self.session.get(url) as resp:
                data = await resp.json()

            await asyncio.sleep(.3)

        return data

    async def run_fast(self, file: bytes) -> tuple[dict[str, int | float], float, float, int | float]:
        mode: FAST_BEST = "fast"

        start = time.perf_counter()
        res = await self.call_api(file, mode=mode)
        end = time.perf_counter()

        return res, start, end, end-start

    async def run_best(self, file: bytes) -> tuple[dict[str, int | float], float, float, int | float]:
        mode: FAST_BEST = "best"

        start = time.perf_counter()
        job = await self.call_api(file, mode=mode)

        job_id = job['job_id']

        js = await self.get_result_from_job_id(job_id)
        end = time.perf_counter()

        res = js['result']

        return res, start, end, end-start

    async def run(self, file: bytes | str, *,
                  mode: FAST_BEST = "fast") -> tuple[dict[str, int | float], float, float, int | float]:
        if isinstance(file, str):
            file = await self.read_url(file)

        match mode:
            case "fast":
                return await self.run_fast(file)
            case "best":
                return await self.run_best(file)
