"""Minimal Zabbix JSON-RPC helper for lab scripts."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_LAB_JSON = Path('/home/ubuntu/zabbix-docker/lab.json')


def load_lab(path: Path | None = None) -> dict:
    p = path or DEFAULT_LAB_JSON
    if not p.exists():
        return {'url': 'http://127.0.0.1:8080', 'token': None, 'user': 'Admin', 'password': 'zabbix'}
    return json.loads(p.read_text())


class ZabbixAPI:
    def __init__(self, url: str, token: str | None = None, user: str | None = None, password: str | None = None):
        self.url = url.rstrip('/') + '/api_jsonrpc.php' if not url.endswith('api_jsonrpc.php') else url
        if '/api_jsonrpc.php' not in self.url:
            base = url.rstrip('/')
            self.url = f'{base}/api_jsonrpc.php'
        self.auth = token
        self._user = user
        self._password = password

    def login_if_needed(self) -> None:
        if self.auth:
            return
        if not self._user:
            raise RuntimeError('No Zabbix token or user/password')
        self.auth = self.call('user.login', {'username': self._user, 'password': self._password}, auth=False)

    def call(self, method: str, params: Any = None, *, auth: bool | None = None) -> Any:
        body: dict[str, Any] = {'jsonrpc': '2.0', 'method': method, 'params': params if params is not None else {}, 'id': 1}
        use_auth = self.auth if auth is None else (False if auth is False else self.auth)
        if use_auth:
            body['auth'] = use_auth
        req = urllib.request.Request(
            self.url,
            data=json.dumps(body).encode(),
            headers={'Content-Type': 'application/json-rpc'},
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                payload = json.load(resp)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f'HTTP {e.code} for {method}: {e.read()[:400]!r}') from e
        if 'error' in payload:
            err = payload['error']
            raise RuntimeError(f'{method}: {err.get("data") or err.get("message") or err}')
        return payload['result']

    @classmethod
    def from_lab(cls, path: Path | None = None) -> 'ZabbixAPI':
        lab = load_lab(path)
        url = lab.get('url', 'http://127.0.0.1:8080')
        api = cls(url, token=lab.get('token'), user=lab.get('user', 'Admin'), password=lab.get('password', 'zabbix'))
        api.login_if_needed()
        return api
