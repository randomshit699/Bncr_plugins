from __future__ import annotations

__META_INFO__ = {"author": "XJJ",
                 "name": "登录",
                 "team": "XJJ",
                 "version": "1.0.0",
                 "platform": None, # or None
                 "rule": [r'^(登录)$', r'^(登陆)$', r'^(上车)$'], # or []
                 "description": '登录插件，支持多种登录方式，登录成功后会自动更新/添加青龙环境变量，支持通知管理员和执行后续命令',
                 "admin": False, # or False
                 "disable": False, 
                 "classification": ["Jingdong", "Chat"], 
                 "service": False,
                 "priority": 99999,
                 "cron": None, # or None
                 }

import asyncio
import base64
import hashlib
import json
import logging
import os
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from type.python import (  # type: ignore
        BncrDB,
        BncrPluginConfig,
        MethodClass,
        Sender,
        router,
        sysMethod,
    )

PLUGIN_NAME = "登录"
log = logging.getLogger("login.py")
logging.basicConfig(level=logging.INFO)

LOGIN_METHODS = [
    {"index": 1, "tip": "pro扫码登录", "enable": True, "adminEnable": True},
    {"index": 2, "tip": "pro口令登录", "enable": True, "adminEnable": True},
    {"index": 3, "tip": "pro短信登录", "enable": True, "adminEnable": True},
    {"index": 4, "tip": "rabbit扫码登录", "enable": True, "adminEnable": True},
    {"index": 5, "tip": "rabbit口令登录", "enable": True, "adminEnable": True},
    {"index": 6, "tip": "rabbit短信登录", "enable": True, "adminEnable": True},
    {"index": 7, "tip": "账号密码登录", "enable": False, "adminEnable": True},
    {
        "index": 8,
        "tip": "无头浏览器短信登录[小九九版]",
        "enable": True,
        "adminEnable": True,
    },
    {
        "index": 9,
        "tip": "无头浏览器短信登录[Dsmggm版]",
        "enable": True,
        "adminEnable": True,
    },
]

jsonSchema = {
    "type": "object",
    "properties": {
        "logLevel": {
            "type": "string",
            "title": "日志级别",
            "enum": ["DEBUG", "INFO", "WARNING", "ERROR"],
            "default": "INFO",
        },
        "whiteList": {
            "type": "array",
            "title": "群组白名单",
            "description": "留空表示不限制群聊；私聊不受限制。",
            "items": {"type": "string"},
            "default": [],
        },
        "login_reply_array": {
            "type": "array",
            "title": "登录方式",
            "items": {
                "type": "object",
                "properties": {
                    "index": {
                        "type": "integer",
                        "title": "方式序号",
                        "enum": [1, 2, 3, 4, 5, 6, 7, 8, 9],
                        "enumNames": [
                            "pro扫码登录",
                            "pro口令登录",
                            "pro短信登录",
                            "rabbit扫码登录",
                            "rabbit口令登录",
                            "rabbit短信登录",
                            "账号密码登录",
                            "无头浏览器短信登录 [小九九版]",
                            "无头浏览器短信登录 [Dsmggm版]",
                        ],
                    },
                    "tip": {"type": "string", "title": "提示语"},
                    "enable": {"type": "boolean", "title": "是否启用", "default": True},
                    "adminEnable": {
                        "type": "boolean",
                        "title": "管理员是否可见",
                        "default": True,
                    },
                },
            },
            "default": [],
        },
        "login_reply_more": {
            "type": "string",
            "title": "登录方式补充说明",
            "default": "",
        },
        "phoneInputTip": {
            "type": "string",
            "title": "输入手机号提示",
            "default": "请输入11位手机号：",
        },
        "phoneInputErrTip": {
            "type": "string",
            "title": "手机号输入错误提示",
            "default": "手机号格式错误，请重新输入：",
        },
        "codeTip": {
            "type": "string",
            "title": "输入验证码提示",
            "default": "请输入收到的6位验证码：",
        },
        "codeInputErrTip": {
            "type": "string",
            "title": "验证码输入错误提示",
            "default": "验证码格式错误，请重新输入：",
        },
        "overTimeTip": {
            "type": "string",
            "title": "超时提示",
            "default": "超时，已退出",
        },
        "quitTip": {"type": "string", "title": "退出提示", "default": "已退出"},
        "newLoginOkTip": {
            "type": "string",
            "title": "新用户登录成功提示",
            "default": "",
        },
        "oldLoginOkTip": {
            "type": "string",
            "title": "老用户更新成功提示",
            "default": "",
        },
        "noWhiteListTip": {
            "type": "string",
            "title": "非白名单群提示",
            "default": "当前群未开启登录",
        },
        "remarksOpen": {
            "type": "boolean",
            "title": "新用户登录后询问备注",
            "default": False,
        },
        "waitTime": {"type": "integer", "title": "交互等待时间", "default": 60},
        "qrCodeBaseUrl": {
            "type": "string",
            "title": "二维码生成地址",
            "default": "https://api.qqsuu.cn/api/dm-qrcode?frame=1&e=L&text=",
        },
        "qrCookieType": {
            "type": "integer",
            "title": "扫码/口令写入方式",
            "enum": [1, 2],
            "default": 2,
            "description": "1 表示由服务管理后台接收，2 表示写入青龙。",
        },
        "rabbitProContainerId": {
            "type": "integer",
            "title": "rabbitPro容器id",
            "default": 0,
        },
        "pushAdminOn": {
            "type": "boolean",
            "title": "登录结果通知管理员",
            "default": False,
        },
        "pushPlatform": {
            "type": "string",
            "title": "管理员通知平台，多个用&分隔",
            "default": "",
        },
        "inlineCommand": {
            "type": "array",
            "title": "登录成功后执行命令",
            "items": {"type": "string"},
            "default": [],
        },
        "proUrl": {"type": "string", "title": "Pro服务地址", "default": ""},
        "proBotApiToken": {"type": "string", "title": "Pro机器人Token", "default": ""},
        "rabbitProUrl": {"type": "string", "title": "rabbitPro服务地址", "default": ""},
        "rabbitBotApiToken": {
            "type": "string",
            "title": "rabbitPro机器人Token",
            "default": "",
        },
        "browserUrl": {"type": "string", "title": "无头浏览器服务地址", "default": ""},
        "passwdLoginOn": {
            "type": "boolean",
            "title": "是否开启账号密码登录",
            "default": False,
        },
        "passwdLoginApi": {
            "type": "integer",
            "title": "账号密码登录接口",
            "enum": [1, 2],
            "enumNames": [
                "rabbit",
                "pro",
            ],
            "default": 1,
            "description": "选择账密接口",
        },
        "passwdLoginQl": {
            "type": "integer",
            "title": "账密变量面板索引",
            "description": "-1 表示默认上车面板。",
            "default": -1,
        },
        "savePwdOnLogin": {
            "type": "boolean",
            "title": "账密登录成功后保存JD_AUTO_PWD",
            "default": True,
        },
        "ql_data_arr": {
            "type": "array",
            "title": "青龙面板",
            "description": "若为空则读取 AmingScriptQl.qlDataBase。",
            "items": {
                "type": "object",
                "properties": {
                    "Name": {"type": "string", "title": "面板名称"},
                    "Host": {"type": "string", "title": "面板地址"},
                    "ClientID": {"type": "string", "title": "客户端ID"},
                    "ClientSecret": {"type": "string", "title": "客户端密钥"},
                    "Version": {"type": "string", "default": "2.17.0", "title": "青龙版本号"},
                },
            },
            "default": [],
        },
        "ql_default_index": {
            "type": "integer",
            "title": "默认上车青龙面板索引",
            "description": "从0开始；为空时读取 AmingScriptQl.qlDataBase.LoginDefault。",
            "default": -1,
        },
    },
    "required": [
        "phoneInputTip",
        "phoneInputErrTip",
        "codeTip",
        "codeInputErrTip",
        "overTimeTip",
        "quitTip",
    ],
}

ConfigDB = BncrPluginConfig(jsonSchema)  # type: ignore[name-defined]

@dataclass
class HttpResponse:
    status: int
    body: Any
    headers: dict[str, str]
    raw: bytes

@dataclass
class LoginResult:
    value: str
    env_name: str
    key: str
    pin: str
    pin_name: str
    phone: str = ""

def normalize_base_url(url: str) -> str:
    return (url or "").strip().rstrip("/")

def mask_phone(phone: str) -> str:
    return re.sub(r"(\d{3})\d*(\d{4})", r"\1****\2", phone or "")

def now_ms() -> int:
    return int(time.time()) * 1000

def get_env_id_key(panel: dict[str, Any]) -> str:
    version = str(panel.get("Version") or "2.17.0").split(".")
    try:
        minor = int(version[1]) if len(version) > 1 else 17
    except ValueError:
        minor = 17
    return "_id" if minor < 11 else "id"

def get_cookie_part(cookie: str, name: str) -> str:
    match = re.search(rf"{re.escape(name)}=([^;\s]+);?", cookie or "")
    if not match:
        raise ValueError(f"未找到 {name}")
    return match.group(1)

def build_cookie_result(ck: str, phone: str = "") -> LoginResult:
    key = get_cookie_part(ck, "pt_key")
    pin = get_cookie_part(ck, "pt_pin")
    return LoginResult(
        value=f"pt_key={key};pt_pin={pin};",
        key=f"pt_key={key};",
        pin=f"pt_pin={pin};",
        pin_name=urllib.parse.quote(urllib.parse.unquote(pin), safe=""),
        env_name="JD_COOKIE",
        phone=phone,
    )

def build_wskey_result(wskey: str, env_name: str = "JD_R_WSCK") -> LoginResult:
    key = get_cookie_part(wskey, "wskey")
    pin = get_cookie_part(wskey, "pin")
    return LoginResult(
        value=f"pin={pin};wskey={key};",
        key=f"wskey={key};",
        pin=f"pin={pin};",
        pin_name=urllib.parse.quote(urllib.parse.unquote(pin), safe=""),
        env_name=env_name,
    )

def rabbit_pro_encrypt_pwd(account: str, pwd: str) -> str:
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except Exception as exc:  # pragma: no cover - depends on runtime env
        raise RuntimeError("rabbitPro账密登录需要安装 cryptography") from exc

    digest = hashlib.sha512(
        f"#(*():dfgjn^%&89$%#{account}#(*():dfgjn^%&89$%#".encode()
    ).digest()
    key = digest[:32]
    nonce = os.urandom(12)
    padded = os.urandom(16) + pwd.encode() + os.urandom(16)
    encrypted = AESGCM(key).encrypt(nonce, padded, None)
    ciphertext, tag = encrypted[:-16], encrypted[-16:]
    return base64.b64encode(tag + ciphertext + nonce).decode()

async def http_request(
    method: str,
    url: str,
    *,
    json_body: Any | None = None,
    form_body: dict[str, Any] | str | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 60,
) -> HttpResponse:
    def do_request() -> HttpResponse:
        data = None
        req_headers = dict(headers or {})
        if json_body is not None:
            data = json.dumps(json_body, ensure_ascii=False).encode()
            req_headers.setdefault("Content-Type", "application/json")
        elif form_body is not None:
            if isinstance(form_body, str):
                data = form_body.encode()
            else:
                data = urllib.parse.urlencode(form_body).encode()
            req_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")

        request = urllib.request.Request(
            url, data=data, headers=req_headers, method=method.upper()
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as resp:
                raw = resp.read()
                resp_headers = {k.lower(): v for k, v in resp.headers.items()}
                status = resp.status
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            resp_headers = {k.lower(): v for k, v in exc.headers.items()}
            status = exc.code

        text = raw.decode("utf-8", errors="replace")
        try:
            body = json.loads(text) if text else None
        except json.JSONDecodeError:
            body = text
        return HttpResponse(status=status, body=body, headers=resp_headers, raw=raw)

    return await asyncio.to_thread(do_request)

class QingLongClient:
    def __init__(self, panel: dict[str, Any], index: int):
        self.panel = panel
        self.index = index
        self.host = normalize_base_url(str(panel.get("Host") or ""))
        self.client_id = str(panel.get("ClientID") or "")
        self.client_secret = str(panel.get("ClientSecret") or "")
        self.db = BncrDB("AmingScriptQl")  # type: ignore[name-defined]

    async def token(self, force: bool = False) -> dict[str, Any]:
        cache_key = f"{self.client_id}_token"
        if not force:
            cached = await self.db.get(cache_key, None)
            if isinstance(cached, dict) and int(
                cached.get("expiration", 0)
            ) * 1000 > int(time.time() * 1000):
                return cached

        if not self.host or not self.client_id or not self.client_secret:
            raise RuntimeError(f"面板【{self.index + 1}】配置不完整")

        query = urllib.parse.urlencode(
            {"client_id": self.client_id, "client_secret": self.client_secret}
        )
        resp = await http_request(
            "GET", f"{self.host}/open/auth/token?{query}", timeout=30
        )
        if (
            resp.status != 200
            or not isinstance(resp.body, dict)
            or resp.body.get("code") != 200
        ):
            raise RuntimeError(f"面板【{self.index + 1}】获取token失败：{resp.body}")

        data = resp.body.get("data")
        if not isinstance(data, dict):
            raise RuntimeError(f"面板【{self.index + 1}】token响应异常")
        await self.db.set(cache_key, data)
        return data

    async def request(
        self, method: str, path: str, body: Any | None = None, retry: bool = True
    ) -> Any:
        token = await self.token()
        headers = {
            "Authorization": f"{token.get('token_type', 'Bearer')} {token.get('token')}"
        }
        resp = await http_request(
            method, f"{self.host}{path}", json_body=body, headers=headers, timeout=60
        )
        if resp.status == 401 and retry:
            token = await self.token(force=True)
            headers = {
                "Authorization": f"{token.get('token_type', 'Bearer')} {token.get('token')}"
            }
            resp = await http_request(
                method,
                f"{self.host}{path}",
                json_body=body,
                headers=headers,
                timeout=60,
            )

        if not isinstance(resp.body, dict) or resp.body.get("code") != 200:
            raise RuntimeError(f"面板【{self.index + 1}】请求失败：{resp.body}")
        return resp.body.get("data")

    async def all_envs(self) -> list[dict[str, Any]]:
        data = await self.request("GET", "/open/envs")
        return data if isinstance(data, list) else []

    async def search_envs(self, keyword: str) -> list[dict[str, Any]]:
        query = urllib.parse.urlencode({"searchValue": keyword})
        data = await self.request("GET", f"/open/envs?{query}")
        return data if isinstance(data, list) else []

    async def add_envs(self, envs: list[dict[str, Any]]) -> None:
        await self.request("POST", "/open/envs", envs)

    async def edit_env(self, env: dict[str, Any]) -> None:
        await self.request("PUT", "/open/envs", env)

    async def enable_env(self, env_id: Any) -> None:
        await self.request("PUT", "/open/envs/enable", [env_id])

class LoginPlugin:
    def __init__(self, s: "Sender", config: dict[str, Any], ql_db: dict[str, Any]):
        self.s = s
        self.config = config
        self.ql_db = ql_db
        self.pin_db = BncrDB("pinDB")  # type: ignore[name-defined]
        self.form = s.getFrom()
        self.user_id = s.getUserId()
        self.user_name = s.getUserName()
        self.chat_id = s.getGroupId()
        self.wait_time = int(config.get("waitTime") or 60)
        self.pro_url = normalize_base_url(config.get("proUrl", ""))
        self.pro_token = str(config.get("proBotApiToken") or "")
        self.rabbit_url = normalize_base_url(config.get("rabbitProUrl", ""))
        self.rabbit_token = str(config.get("rabbitBotApiToken") or "")
        self.browser_url = normalize_base_url(config.get("browserUrl", ""))
        self.cookie_type = int(config.get("qrCookieType") or 2)
        self.ql_panels = self._load_ql_panels()
        self.ql_index = self._load_ql_default_index()
        self.ql = QingLongClient(self.ql_panels[self.ql_index], self.ql_index)
        passwd_index = int(config.get("passwdLoginQl", -1))
        self.passwd_index = self.ql_index if passwd_index < 0 else passwd_index
        self.passwd_ql = QingLongClient(
            self.ql_panels[self.passwd_index], self.passwd_index
        )

    def _load_ql_panels(self) -> list[dict[str, Any]]:
        panels = self.config.get("ql_data_arr") or self.ql_db.get("data") or []
        if not isinstance(panels, list) or not panels:
            raise RuntimeError("请先配置青龙面板")
        return panels

    def _load_ql_default_index(self) -> int:
        configured = int(self.config.get("ql_default_index", -1))
        index = configured if configured >= 0 else self.ql_db.get("LoginDefault")
        if not isinstance(index, int):
            raise RuntimeError("请先设置默认上车面板")
        if index < 0 or index >= len(self.ql_panels):
            raise RuntimeError("默认上车面板索引无效")
        return index

    async def reply(self, msg: Any) -> None:
        await self.s.reply(msg)

    async def wait_text(
        self, prompt: str, validator: Any | None = None, timeout: int | None = None
    ) -> str:
        await self.reply(prompt)

        async def cb(sender: "Sender") -> Any:
            text = sender.getMsg().strip()
            if text == "q":
                return None
            if validator and not validator(text):
                return await sender.again(prompt)
            return None

        sender = await self.s.waitInput(cb, timeout or self.wait_time)
        if sender is None:
            raise RuntimeError(self.config.get("overTimeTip") or "超时，已退出")
        text = sender.getMsg().strip()
        if text == "q":
            raise RuntimeError(self.config.get("quitTip") or "已退出")
        return text

    async def input_phone(self) -> str:
        return await self.wait_text(
            str(self.config.get("phoneInputTip") or "请输入手机号："),
            lambda text: bool(re.fullmatch(r"\d{11}", text)),
        )

    async def input_code(self, phone: str = "") -> str:
        prefix = f"[{mask_phone(phone)}] " if phone else ""
        return await self.wait_text(
            prefix + str(self.config.get("codeTip") or "请输入验证码："),
            lambda text: bool(re.fullmatch(r"\d{6}", text)),
        )

    async def confirm(self, prompt: str, timeout: int = 120) -> None:
        text = await self.wait_text(prompt, lambda value: value == "1", timeout)
        if text != "1":
            raise RuntimeError(self.config.get("quitTip") or "已退出")

    def build_tip(self, is_admin: bool) -> tuple[str, list[dict[str, Any]]]:
        source = self.config.get("login_reply_array") or LOGIN_METHODS
        enabled: list[dict[str, Any]] = []
        lines = ["选择一个渠道:"]
        for item in source:
            if not isinstance(item, dict):
                continue
            if not item.get("enable") and not (is_admin and item.get("adminEnable")):
                continue
            enabled.append(item)
            lines.append(
                f"{len(enabled)}. {item.get('tip') or self.method_name(int(item.get('index', 0)))}"
            )
        more = str(self.config.get("login_reply_more") or "").replace("\\n", "\n")
        if more:
            lines.extend(["", more])
        lines.append("(q退出)")
        return "\n".join(lines), enabled

    @staticmethod
    def method_name(index: int) -> str:
        for item in LOGIN_METHODS:
            if item["index"] == index:
                return str(item["tip"])
        return f"登录方式{index}"

    async def run(self) -> None:
        msg = self.s.getMsg()
        if re.search(r"pt_key=[\w-]{15,};", msg):
            result = build_cookie_result(msg)
            await self.commit_to_ql(result)
            return

        is_admin = await self.s.isAdmin()
        whitelist = [str(x) for x in self.config.get("whiteList") or []]
        if (
            not is_admin
            and self.chat_id
            and str(self.chat_id) != "0"
            and whitelist
            and str(self.chat_id) not in whitelist
        ):
            await self.reply(
                str(self.config.get("noWhiteListTip") or "当前群未开启登录")
            )
            return

        if self.s.param(1) not in ["登录", "登陆", "上车"]:
            return

        tip, methods = self.build_tip(is_admin)
        if not methods:
            raise RuntimeError("未启用任何登录方式")

        if len(methods) == 1 and not is_admin:
            choice = 1
        else:
            await self.reply(tip)

            async def choose_cb(ss: "Sender") -> Any:
                text = ss.getMsg().strip()
                if text == "q":
                    return None
                if text.isdigit():
                    return None
                return await ss.again(tip)

            chosen = await self.s.waitInput(choose_cb, self.wait_time)
            if chosen is None:
                raise RuntimeError(self.config.get("overTimeTip") or "超时，已退出")
            if chosen.getMsg() == "q":
                raise RuntimeError(self.config.get("quitTip") or "已退出")
            choice = int(chosen.getMsg())
            if choice < 1 or choice > len(methods):
                raise RuntimeError("无效的登录方式")

        selected = int(methods[choice - 1].get("index", 0))
        result = await self.dispatch(selected)
        if result:
            await self.commit_to_ql(result)

    async def dispatch(self, index: int) -> LoginResult | None:
        mapping = {
            1: self.pro_qr_login,
            2: self.pro_short_login,
            3: self.pro_sms_login,
            4: self.rabbit_qr_login,
            5: self.rabbit_short_login,
            6: self.rabbit_sms_login,
            7: self.password_login,
            8: self.browser_sms_login,
            9: self.browser_dsmggm_sms_login,
        }
        method = mapping.get(index)
        if not method:
            raise RuntimeError("未找到登录方式")
        log.info("login method: %s", self.method_name(index))
        return await method()

    async def commit_to_ql(self, result: LoginResult) -> None:
        env_id_key = get_env_id_key(self.ql.panel)
        envs = await self.ql.all_envs()
        matched = next(
            (
                env
                for env in envs
                if env.get("name") == result.env_name
                and result.pin in str(env.get("value", ""))
            ),
            None,
        )
        if matched:
            remarks = self._update_phone_in_remarks(
                str(matched.get("remarks") or ""), result.phone
            )
            env = {
                "name": result.env_name,
                "value": result.value,
                "remarks": remarks,
                env_id_key: matched.get(env_id_key),
            }
            await self.ql.edit_env(env)
            await self.ql.enable_env(matched.get(env_id_key))
            await self.bind_pin(result.pin_name)
            await self.reply(
                f"【{result.env_name}】\n{urllib.parse.unquote(result.pin_name)} 更新成功"
            )
            extra = str(self.config.get("oldLoginOkTip") or "").replace("\\n", "\n")
        else:
            remarks = f"@@{now_ms()}@@"
            if self.config.get("remarksOpen"):
                name = await self.wait_text(
                    f"OK，收到【{result.env_name}】。\n请回复此号的备注信息（q退出）：",
                    None,
                )
                remarks = f"{name}@@{now_ms()}@@"
            if result.phone:
                remarks = self._update_phone_in_remarks(remarks, result.phone)
            await self.ql.add_envs(
                [{"name": result.env_name, "value": result.value, "remarks": remarks}]
            )
            await self.bind_pin(result.pin_name)
            await self.reply(
                f"【{result.env_name}】\n{urllib.parse.unquote(result.pin_name)} 登录成功"
            )
            extra = str(self.config.get("newLoginOkTip") or "").replace("\\n", "\n")

        if extra:
            await self.reply(extra)
        await self.notify_admin(
            f"【{result.env_name}】\n{urllib.parse.unquote(result.pin_name)} 登录/更新成功"
        )
        for command in self.config.get("inlineCommand") or []:
            if command:
                await sysMethod.inline(str(command))  # type: ignore[name-defined]

    @staticmethod
    def _update_phone_in_remarks(remarks: str, phone: str) -> str:
        if not phone:
            return remarks
        parts = (remarks or "").split("@@")
        if len(parts) >= 4:
            parts[3] = phone
            return "@@".join(parts)
        return (remarks or "") + "@@" * (4 - len(parts)) + phone

    async def bind_pin(self, pin: str) -> None:
        key = f"{self.form}:{self.user_id}"
        user_db = await self.pin_db.get(key, None)
        if not isinstance(user_db, dict):
            user_db = {
                "Pin": [],
                "Form": self.form,
                "ID": self.user_id,
                "Name": self.user_name,
            }
        pins = user_db.setdefault("Pin", [])
        if pin not in pins:
            pins.append(pin)
        await self.pin_db.set(key, user_db)

    async def notify_admin(self, message: str) -> None:
        if not self.config.get("pushAdminOn"):
            return
        platforms = [
            x for x in str(self.config.get("pushPlatform") or "").split("&") if x
        ]
        if not platforms:
            return
        await sysMethod.pushAdmin(  # type: ignore[name-defined]
            platforms,
            f"平台：{self.form}\n用户名：{self.user_name}\n用户ID：{self.user_id}\n-\n{message}",
        )

    async def pro_qr_login(self) -> LoginResult | None:
        self.require_service(self.pro_url, self.pro_token, "Pro")
        resp = await http_request(
            "POST",
            f"{self.pro_url}/qr/GetQRKey",
            json_body={"botApitoken": self.pro_token},
        )
        body = resp.body if isinstance(resp.body, dict) else {}
        qrkey = body.get("data", {}).get("key")
        if not qrkey:
            raise RuntimeError(
                f"扫码服务器异常：{body.get('message') or body.get('msg') or body}"
            )
        await self.reply({"type": "image", "path": self.qr_code_url(qrkey)})
        await self.confirm("扫码完成后发送1确认，退出发送q")
        check_body: dict[str, Any] = {"qrkey": qrkey}
        if self.cookie_type == 2:
            check_body["botApitoken"] = self.pro_token
        resp = await http_request(
            "POST", f"{self.pro_url}/qr/CheckQRKey", json_body=check_body
        )
        data = resp.body if isinstance(resp.body, dict) else {}
        if not data.get("success"):
            raise RuntimeError(data.get("message") or "扫码登录失败")
        if self.cookie_type != 2:
            username = data.get("data", {}).get("username")
            if username:
                await self.bind_pin(username)
                await self.reply(f"{username} 登录成功")
            return None
        return build_wskey_result(data.get("data", {}).get("rwskey", ""), "JD_R_WSCK")

    async def pro_short_login(self) -> LoginResult | None:
        self.require_service(self.pro_url, self.pro_token, "Pro")
        resp = await http_request(
            "POST",
            f"{self.pro_url}/qr/GetQRKey",
            json_body={"botApitoken": self.pro_token},
        )
        body = resp.body if isinstance(resp.body, dict) else {}
        qrkey = body.get("data", {}).get("key")
        if not qrkey:
            raise RuntimeError(
                f"扫码服务器异常：{body.get('message') or body.get('msg') or body}"
            )
        command_url = self.jd_scan_command_url(qrkey)
        await self.reply({"msg": command_url, "dontEdit": True})
        await self.confirm("60秒内复制口令打开京东确认登录，完成后发送1确认，退出发送q")
        check_body: dict[str, Any] = {"qrkey": qrkey}
        if self.cookie_type == 2:
            check_body["botApitoken"] = self.pro_token
        resp = await http_request(
            "POST", f"{self.pro_url}/qr/CheckQRKey", json_body=check_body
        )
        data = resp.body if isinstance(resp.body, dict) else {}
        if not data.get("success"):
            raise RuntimeError(data.get("message") or "口令登录失败")
        if self.cookie_type != 2:
            username = data.get("data", {}).get("username")
            if username:
                await self.bind_pin(username)
                await self.reply(f"{username} 登录成功")
            return None
        return build_wskey_result(data.get("data", {}).get("rwskey", ""), "JD_R_WSCK")

    async def pro_sms_login(self) -> LoginResult:
        self.require_service(self.pro_url, self.pro_token, "Pro")
        phone = await self.input_phone()
        send = await self.pro_post(
            "/sms/SendSMS", {"phone": phone, "botApitoken": self.pro_token}
        )
        if send != "ok":
            raise RuntimeError(str(send))
        code = await self.input_code(phone)
        data = await self.pro_post(
            "/sms/VerifyCode",
            {"phone": phone, "botApitoken": self.pro_token, "code": code},
            transform=False,
        )
        return await self.handle_pro_sms_result(data, phone)

    async def handle_pro_sms_result(
        self, data: dict[str, Any], phone: str
    ) -> LoginResult:
        if data.get("success"):
            return build_cookie_result(data.get("data", {}).get("ck", ""), phone)
        sub = data.get("data") or {}
        status = sub.get("status")
        mode = sub.get("mode") or data.get("mode")
        if status == 555 and mode == "USER_ID":
            code = await self.wait_text(
                str(self.config.get("userIdTip") or "请输入身份证前2后4："),
                lambda text: len(text) == 6,
            )
            res = await self.pro_post(
                "/sms/VerifyCardCode",
                {"phone": phone, "botApitoken": self.pro_token, "code": code},
                transform=False,
            )
            if res.get("success"):
                return build_cookie_result(res.get("data", {}).get("ck", ""), phone)
            raise RuntimeError(res.get("message") or "身份验证失败")
        if status == 555 and mode == "HISTORY_DEVICE":
            await self.wait_text(
                str(
                    self.config.get("deviceTip")
                    or "请在京东APP确认新设备登录，完成后回复 已确认"
                ),
                lambda t: t == "已确认",
            )
            res = await self.pro_post(
                "/sms/VerifyCardCode",
                {"phone": phone, "botApitoken": self.pro_token, "code": ""},
                transform=False,
            )
            if res.get("success"):
                return build_cookie_result(res.get("data", {}).get("ck", ""), phone)
            raise RuntimeError(res.get("message") or "新设备验证失败")
        raise RuntimeError(data.get("message") or "登录失败")

    async def pro_post(
        self, path: str, body: dict[str, Any], transform: bool = True
    ) -> Any:
        resp = await http_request(
            "POST", f"{self.pro_url}{path}", json_body=body, timeout=90
        )
        data = resp.body if isinstance(resp.body, dict) else {}
        if transform:
            if data.get("success"):
                return "ok"
            return data.get("message") or json.dumps(data, ensure_ascii=False)
        return data

    async def rabbit_qr_login(self) -> LoginResult | None:
        return await self.rabbit_qr_common(short=False)

    async def rabbit_short_login(self) -> LoginResult | None:
        return await self.rabbit_qr_common(short=True)

    async def rabbit_qr_common(self, short: bool) -> LoginResult | None:
        self.require_service(self.rabbit_url, self.rabbit_token, "rabbitPro")
        if self.cookie_type == 1:
            gen_url = f"{self.rabbit_url}/api/GenQrCode"
            check_url = f"{self.rabbit_url}/api/QrCheck"
        else:
            gen_url = f"{self.rabbit_url}/bot/GenQrCode?BotApiToken={urllib.parse.quote(self.rabbit_token)}"
            check_url = f"{self.rabbit_url}/bot/QrCheck?BotApiToken={urllib.parse.quote(self.rabbit_token)}"
        resp = await http_request("POST", gen_url)
        body = resp.body if isinstance(resp.body, dict) else {}
        if resp.status != 200 or body.get("code") != 0 or not body.get("QRCodeKey"):
            raise RuntimeError(f"rabbit扫码服务器异常：{body.get('msg') or body}")
        qrkey = body["QRCodeKey"]
        if short:
            await self.reply(
                {
                    "msg": body.get("jcommond") or self.jd_scan_command_url(qrkey),
                    "dontEdit": True,
                }
            )
            prompt = "60秒内复制口令打开京东确认登录，完成后发送1确认，退出发送q"
        else:
            await self.reply({"type": "image", "path": self.qr_code_url(qrkey)})
            prompt = "扫码完成后发送1确认，退出发送q"
        await self.confirm(prompt)
        body = {"QRCodeKey": qrkey}
        if self.cookie_type == 1:
            body = {
                "QRCodeKey": qrkey,
                "container_id": self.config.get("rabbitProContainerId") or 0,
                "token": "",
            }
        resp = await http_request("POST", check_url, json_body=body)
        data = resp.body if isinstance(resp.body, dict) else {}
        if resp.status != 200 or data.get("code") != 200:
            raise RuntimeError(data.get("msg") or "rabbitPro登录失败")
        if self.cookie_type == 1:
            pin = data.get("pin")
            if pin:
                await self.bind_pin(pin)
                await self.reply(f"{pin} 登录成功")
            return None
        return LoginResult(
            value=f"pin={data.get('pin')};wskey={data.get('wskey')};",
            key=f"wskey={data.get('wskey')};",
            pin=f"pin={data.get('pin')};",
            pin_name=str(data.get("pin") or ""),
            env_name="JD_R_WSCK",
        )

    async def rabbit_sms_login(self) -> LoginResult:
        self.require_service(self.rabbit_url, self.rabbit_token, "rabbitPro")
        phone = await self.input_phone()
        ok = await self.rabbit_send_sms(phone)
        if not ok:
            raise RuntimeError("获取验证码失败，请重新登录使用其他方式")
        while True:
            code = await self.input_code(phone)
            data = await self.rabbit_api(
                "/bot/mck/VerifyCode", {"Phone": phone, "Code": code}
            )
            if data.get("success") and data.get("code") == 200:
                return build_cookie_result(
                    data.get("ck") or data.get("data", {}).get("ck", ""), phone
                )
            message = data.get("message") or data.get("msg") or "验证码错误"
            if data.get("code") in [503, 505]:
                await self.reply(message)
                continue
            raise RuntimeError(message)

    async def rabbit_send_sms(self, phone: str) -> bool:
        data = await self.rabbit_api("/bot/mck/sendSMS", {"Phone": phone})
        if data.get("success"):
            return True
        if data.get("code") == 666 or (data.get("data") or {}).get("status") == 666:
            return await self.rabbit_auto_captcha("mck", {"Phone": phone})
        if data.get("code") == 503:
            raise RuntimeError(
                data.get("message") or data.get("msg") or "rabbitPro授权异常"
            )
        return False

    async def rabbit_auto_captcha(
        self, name: str, body: dict[str, Any], retry: int = 7
    ) -> bool:
        data = await self.rabbit_api(f"/bot/{name}/AutoCaptcha", body)
        if data.get("success"):
            return True
        if retry > 0 and (
            (data.get("data") or {}).get("status") == 666
            or data.get("message") == "Expecting value: line 1 column 1 (char 0)"
        ):
            await sysMethod.sleep(1)  # type: ignore[name-defined]
            return await self.rabbit_auto_captcha(name, body, retry - 1)
        raise RuntimeError(data.get("message") or data.get("msg") or "图形验证失败")

    async def rabbit_api(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.rabbit_url}{path}?BotApiToken={urllib.parse.quote(self.rabbit_token)}"
        resp = await http_request("POST", url, json_body=body, timeout=90)
        if not isinstance(resp.body, dict):
            raise RuntimeError("rabbitPro服务响应异常")
        return resp.body

    async def browser_sms_login(self) -> LoginResult:
        self.require_url(self.browser_url, "无头浏览器服务")
        phone = await self.input_phone()
        ck = await self.browser_login_flow(phone)
        return build_cookie_result(ck, phone)

    async def browser_login_flow(
        self, account: str, login_type: str = "phone"
    ) -> str:
        body = {"account": account, "type": login_type}
        data = await self.browser_api("/login", body)
        if data.get("status") != "pass":
            raise RuntimeError("服务器失联啦，过会再试")
        uid = data.get("uid", "")
        await self.reply(f"{mask_phone(account)}正在登录中，请稍等...")
        result = await self.browser_check(uid)
        return result.get("cookie", "")

    async def browser_check(self, uid: str, retry: int = 3) -> dict[str, Any]:
        await sysMethod.sleep(5)  # type: ignore[name-defined]
        status = await self.browser_status(uid)
        if status.get("status") == "SMS":
            await self.reply("需要短信或语音验证，请输入验证码：")
            await self.browser_api(
                "/sms", {"uid": uid, "code": await self.input_code()}
            )
        elif status.get("status") == "wrongSMS":
            await self.reply("验证码错误，请检查后再输入：")
            await self.browser_api(
                "/sms", {"uid": uid, "code": await self.input_code()}
            )
        elif status.get("status") in ["IDCard", "wrongIDCard"]:
            await self.reply("需要身份证验证，请输入身份证前2后4：")
            id_card = await self.wait_text(
                "请输入身份证前2后4：", lambda text: len(text) == 6
            )
            await self.browser_api("/idcard", {"uid": uid, "idcard": id_card})
        elif status.get("status") == "pass":
            return status
        else:
            raise RuntimeError(status.get("msg") or "处理账号超时")
        if retry <= 0:
            raise RuntimeError("错误次数过多，已退出")
        return await self.browser_check(uid, retry - 1)

    async def browser_status(self, uid: str) -> dict[str, Any]:
        for _ in range(18):
            data = await self.browser_api("/check", {"uid": uid})
            if data.get("status") == "error":
                raise RuntimeError(data.get("msg") or "登录失败")
            if data.get("status") != "pending":
                return data
            await sysMethod.sleep(7)  # type: ignore[name-defined]
        raise RuntimeError("处理账号超时，可能无法通过此方法登录")

    async def browser_api(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        resp = await http_request(
            "POST", f"{self.browser_url}{path}", json_body=body, timeout=180
        )
        if not isinstance(resp.body, dict):
            raise RuntimeError("无头浏览器服务异常")
        if resp.body.get("status") == "error":
            raise RuntimeError(resp.body.get("msg") or "无头浏览器服务异常")
        return resp.body

    async def browser_dsmggm_sms_login(self) -> LoginResult:
        self.require_url(self.browser_url, "无头浏览器服务")
        phone = await self.input_phone()
        send = await http_request(
            "POST",
            f"{self.browser_url}/sendcode",
            json_body={"username": phone},
            timeout=120,
        )
        send_body = send.body if isinstance(send.body, dict) else {}
        if send_body.get("msg") != "验证码发送成功":
            raise RuntimeError(f"发送验证码失败：{send_body.get('msg') or send_body}")
        while True:
            code = await self.input_code(phone)
            verify = await http_request(
                "POST",
                f"{self.browser_url}/verifycode",
                json_body={"username": phone, "code": code},
                timeout=120,
            )
            data = verify.body if isinstance(verify.body, dict) else {}
            if data.get("msg") == "登录成功":
                ck = f"pt_key={data.get('pt_key')};pt_pin={data.get('pt_pin')};"
                return build_cookie_result(ck, phone)
            if data.get("msg") == "验证码错误，请重新输入":
                await self.reply("验证码错误，请重新输入")
                continue
            raise RuntimeError(f"验证码失败：{data.get('msg') or data}")

    async def password_login(self) -> LoginResult:
        if not self.config.get("passwdLoginOn"):
            raise RuntimeError("未开启账号密码登录功能")
        phone = await self.wait_text(
            "请输入账号或11位手机号码：",
            lambda text: bool(re.fullmatch(r"[a-zA-Z0-9_-]{4,16}|\d{11}", text)),
        )
        pwd = await self.wait_text(
            "请输入8到20位的京东密码：",
            lambda text: bool(re.fullmatch(r"\S{8,20}", text)),
        )
        login_type = int(self.config.get("passwdLoginApi") or 1)
        if login_type == 1:
            ck = await self.rabbit_password_login(phone, pwd)
        elif login_type == 2:
            ck = await self.pro_password_login(phone, pwd)
        else:
            raise RuntimeError("不支持的账号密码登录接口")
        result = build_cookie_result(ck, phone)
        if self.config.get("savePwdOnLogin", True):
            await self.save_password_env(result.pin_name, phone, pwd)
        return result

    async def rabbit_password_login(self, phone: str, pwd: str) -> str:
        self.require_service(self.rabbit_url, self.rabbit_token, "rabbitPro")
        init = await self.rabbit_api("/bot/pwd/init", {"account": phone})
        if not init.get("success") and init.get("code") == 666:
            await self.rabbit_auto_captcha("pwd", {"account": phone})
        elif not init.get("success"):
            raise RuntimeError(
                init.get("message") or init.get("msg") or "rabbitPro初始化失败"
            )
        data = await self.rabbit_api(
            "/bot/pwd/login",
            {"account": phone, "pwd": rabbit_pro_encrypt_pwd(phone, pwd)},
        )
        if data.get("success") and data.get("ck"):
            return data["ck"]
        if data.get("code") in [601, 602]:
            await self.rabbit_api("/bot/risk/risk_send", {"account": phone})
            code = await self.input_code(phone)
            verify = await self.rabbit_api(
                "/bot/risk/risk_verify_code", {"account": phone, "code": code}
            )
            if verify.get("ck"):
                return verify["ck"]
        raise RuntimeError(
            data.get("message") or data.get("msg") or "rabbitPro账密登录失败"
        )

    async def pro_password_login(self, phone: str, pwd: str) -> str:
        self.require_service(self.pro_url, self.pro_token, "Pro")
        payload = {"username": phone, "password": pwd, "BotApitoken": self.pro_token}
        data = await self.pro_password_request("/Pwd/Login", payload)
        if data.get("ck"):
            return data["ck"]
        raise RuntimeError("Pro账密登录未返回Cookie")

    async def pro_password_request(
        self, path: str, payload: dict[str, Any], retry: int = 3
    ) -> dict[str, Any]:
        resp = await http_request(
            "POST", f"{self.pro_url}{path}", json_body=payload, timeout=30
        )
        data = resp.body if isinstance(resp.body, dict) else {}
        if data.get("success"):
            return data.get("data") or {}
        sub = data.get("data") or {}
        if data.get("message") == "未找到用户" and path != "/Pwd/Login":
            return await self.pro_password_request("/Pwd/Login", payload, retry)
        if retry > 0 and re.search(
            r"哦豁|获取im失败|加载异常", str(data.get("message") or "")
        ):
            return await self.pro_password_request(path, payload, retry - 1)
        if sub.get("status") == 555:
            raise RuntimeError(
                f"{data.get('message') or '需要安全验证'}\n{sub.get('jmp_url') or sub.get('RiskUrl') or ''}"
            )
        raise RuntimeError(data.get("message") or "Pro账密登录失败")

    async def save_password_env(self, pin: str, phone: str, pwd: str) -> None:
        remark = f"{self.user_id}@{pin}"
        value = f"{phone}#{pwd}"
        found = [
            env
            for env in await self.passwd_ql.search_envs(remark)
            if env.get("name") == "JD_AUTO_PWD"
        ]
        env_id_key = get_env_id_key(self.passwd_ql.panel)
        if found:
            env = dict(found[0])
            await self.passwd_ql.edit_env(
                {
                    "name": "JD_AUTO_PWD",
                    "value": value,
                    "remarks": remark,
                    env_id_key: env.get(env_id_key),
                }
            )
            if env.get("status") == 1:
                await self.passwd_ql.enable_env(env.get(env_id_key))
        else:
            await self.passwd_ql.add_envs(
                [{"name": "JD_AUTO_PWD", "value": value, "remarks": remark}]
            )

    def qr_code_url(self, qrkey: str) -> str:
        base = str(self.config.get("qrCodeBaseUrl") or "")
        raw = f"https://qr.m.jd.com/p?k={urllib.parse.quote(qrkey)}&size=150"
        return base + raw if base else raw

    @staticmethod
    def jd_scan_command_url(qrkey: str) -> str:
        params = {
            "category": "jump",
            "des": "scanLogin",
            "key": qrkey,
            "sourceType": "JSHOP_SOURCE_TYPE",
            "sourceValue": "JSHOP_SOURCE_VALUE",
            "M_sourceFrom": "mxz",
            "msf_type": "auto",
        }
        encoded = urllib.parse.quote(json.dumps(params, separators=(",", ":")))
        return f"https://lzkj-isv.isvjcloud.com/lzclient/cjwx/common/openJDApp.html?actlink=openapp.jdmobile://virtual?params={encoded}"

    @staticmethod
    def ua() -> str:
        return (
            "jdapp;iPhone;12.2.0;;;M/5.0;appBuild/168392;jdSupportDarkMode/0;"
            "ef/1;ep/%7B%7D;Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)"
        )

    @staticmethod
    def require_url(url: str, name: str) -> None:
        if not url:
            raise RuntimeError(f"请先配置{name}地址")

    def require_service(self, url: str, token: str, name: str) -> None:
        if not url or not token:
            raise RuntimeError(f"请先配置{name}服务地址和Token")

async def load_ql_database(config: dict[str, Any]) -> dict[str, Any]:
    if config.get("ql_data_arr"):
        default = int(config.get("ql_default_index", -1))
        return {
            "data": config["ql_data_arr"],
            "LoginDefault": default if default >= 0 else 0,
        }
    db = BncrDB("AmingScriptQl")  # type: ignore[name-defined]
    data = await db.get("qlDataBase", {})
    return data if isinstance(data, dict) else {}

async def main(s: "Sender") -> None:
    await ConfigDB.get()
    config = ConfigDB.userConfig
    if not config:
        raise RuntimeError("请先在web【插件配置】对插件进行首次保存")

    log.setLevel(
        getattr(logging, str(config.get("logLevel") or "INFO").upper(), logging.INFO)
    )
    ql_db = await load_ql_database(config)
    try:
        plugin = LoginPlugin(s, config, ql_db)
        await plugin.run()
    except Exception as exc:
        log.exception("login failed")
        await s.reply(str(exc))
