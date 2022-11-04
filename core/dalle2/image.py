import io
import typing
import datetime


class Image:
    def __init__(self, gen: "GeneratedImages", data: dict):
        self._gen = gen

        self.url: str = data["url"]

    def __eq__(self, other):
        return isinstance(other, Image) and self.url == other.url

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
            with open(fp, 'wb') as f:
                return f.write(img)


class GeneratedImages:
    def __init__(self, client, data):
        self._client = client
        self._data = data

        self._created = data["created"]
        self.created = datetime.datetime.utcfromtimestamp(self._created)

        self._images = data["data"]
        self.images = [Image(self, d) for d in self._images]

        # print(data)

    def __getitem__(self, item):
        return self._data[item]

    def __eq__(self, other):
        return isinstance(other, GeneratedImages) and self._data == other._data

    def get_urls(self):
        return [img.url for img in self.images]

    async def read_all(self, *, io_type=None) -> list[bytes | typing.Any]:
        io_type = io_type or bytes

        urls = self.get_urls()

        imgs = []

        for url in urls:
            async with self._client.session.get(url) as resp:
                imgs.append(io_type(await resp.read()))

        return imgs
