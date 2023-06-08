import aiohttp

from core.music.spotify.config import *

# from exceptions import SpotifyClientException


class SpotifyClient:
    # _proxy = PROXY
    _client_token = ""
    _access_token = ""
    _client_id = ""
    __USER_AGENT = USER_AGENT
    _verify_ssl = VERIFY_SSL

    user_data = None

    def __init__(self, sp_dc=None, sp_key=None, session: aiohttp.ClientSession = None):
        self.dc = sp_dc
        self.key = sp_key
        self.__HEADERS = {
            "User-Agent": self.__USER_AGENT,
            "Accept": "application/json",
            "Origin": "https://open.spotify.com",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Referer": "https://open.spotify.com/",
            "Te": "trailers",
            "App-Platform": "WebPlayer",
        }

        self.session = session

    async def get_tokens(self, sp_dc=None, sp_key=None):
        self._access_token, self._client_id = await self.get_access_token(sp_dc=sp_dc, sp_key=sp_key)
        self._client_token = await self.get_client_token(self._client_id)

    async def refresh_tokens(self):
        await self.get_tokens(self.dc, self.key)

    async def get_client_token(self, client_id: str):
        headers = self.__HEADERS
        # session.proxies = self._proxy
        # session.headers = self.__HEADERS

        # # Clear old tokens, otherwise we will get 400 Bad Request
        # if 'client_token' in session.headers:
        #     session.headers.pop('client_token')
        # if 'Authorization' in session.headers:
        #     session.headers.pop('Authorization')

        data = {
            "client_data": {
                "client_version": "1.2.13.477.ga4363038",
                "client_id": client_id,
                "js_sdk_data": {
                    "device_brand": "",
                    "device_id": "",
                    "device_model": "",
                    "device_type": "",
                    "os": "",
                    "os_version": "",
                },
            }
        }

        # response = session.post('https://clienttoken.spotify.com/v1/clienttoken', json=data, verify=self._verify_ssl)
        # try:
        #     rj = response.json()
        # except Exception as ex:
        #     raise SpotifyClientException('Failed to parse client token response as json!', ex)

        async with self.session.post(
            "https://clienttoken.spotify.com/v1/clienttoken", json=data, verify_ssl=self._verify_ssl, headers=headers
        ) as response:
            try:
                rj = await response.json()
            except Exception as ex:
                # raise SpotifyClientException('Failed to parse client token response as json!', ex)
                raise ex

        return rj["granted_token"]["token"]

    async def get_access_token(self, keys=None, sp_dc=None, sp_key=None):
        # session.proxies = self._proxy
        # session.headers = self.__HEADERS
        headers = self.__HEADERS
        cookie = {}
        if keys is not None:
            cookie = keys
        if sp_dc is not None:
            cookie["sp_dc"] = sp_dc
        if sp_key is not None:
            cookie["sp_key"] = sp_key
        # response = session.get('https://open.spotify.com/get_access_token', verify=self._verify_ssl, cookies=cookie)
        # try:
        #     rj = response.json()
        # except Exception as ex:
        #     raise SpotifyClientException('An error occured when generating an access token!', ex)

        async with self.session.get(
            "https://open.spotify.com/get_access_token", verify_ssl=self._verify_ssl, cookies=cookie, headers=headers
        ) as response:
            try:
                rj = await response.json()
            except Exception as ex:
                # raise SpotifyClientException('An error occured when generating an access token!', ex)
                raise ex

        self.is_anonymous = rj["isAnonymous"]
        return rj["accessToken"], rj["clientId"] if rj["clientId"].lower() != "unknown" else self._client_id

    async def get(self, url: str) -> dict:
        # with requests.session() as session:
        #     session.proxies = self._proxy
        #     session.headers = self.__HEADERS
        #     session.headers.update({
        #                             'Client-Token': self._client_token,
        #                             'Authorization': f'Bearer {self._access_token}'
        #                             })

        #     response = session.get(url, verify=self._verify_ssl)
        #     return response

        await self.refresh_tokens()

        headers = self.__HEADERS.copy()
        headers.update({"Client-Token": self._client_token, "Authorization": f"Bearer {self._access_token}"})
        async with self.session.get(url, verify_ssl=self._verify_ssl, headers=headers) as resp:
            return await resp.json()

    # def post(self, url: str, payload=None) -> Response:
    #     with requests.session() as session:
    #         session.proxies = self._proxy
    #         session.headers = self.__HEADERS
    #         session.headers.update({
    #                                 'Client-Token': self._client_token,
    #                                 'Authorization': f'Bearer {self._access_token}'
    #                                 })

    #         response = session.post(url, verify=self._verify_ssl, data=payload)
    #         return response
