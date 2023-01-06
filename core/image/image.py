import datetime
import io
import typing


class GeneratedImage:
    def __init__(self, gen: "GeneratedImages", data: dict):
        self._gen = gen

        self.url: str = data["url"]

    def __eq__(self, other):
        return isinstance(other, GeneratedImage) and self.url == other.url

    async def read(self, *, io_type=None) -> bytes | typing.Any:
        io_type = io_type or bytes

        async with self._gen._client.session.get(self.url) as resp:
            return io_type(await resp.read())

    async def save(self, fp, *, seek=True):
        img = await self.read()

        if isinstance(fp, io.IOBase) and fp.writable():
            written = fp.write(img)

            if seek:
                fp.seek(0)

            return written
        else:
            with open(fp, "wb") as f:
                return f.write(img)


class GeneratedImages:
    def __init__(self, client, data):
        self._client = client
        self._data = data

        self._created = data["created"]
        self.created = datetime.datetime.utcfromtimestamp(self._created)

        self._images = data["data"]
        self.images = [GeneratedImage(self, d) for d in self._images]

    def __getitem__(self, item):
        return self._data[item]

    def __eq__(self, other):
        return isinstance(other, GeneratedImages) and self._data == other._data

    def get_urls(self):
        return [img.url for img in self.images]

    async def read_all(self, *, io_type=None) -> list[bytes | typing.Any]:
        io_type = io_type or bytes

        imgs = []

        for img in self.images:
            imgs.append(await img.read(io_type=io_type))

        return imgs
