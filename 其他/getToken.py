# 这是青龙脚本
# 基于t.me/InteTU 二改，增加并发功能
# author: t.me/InteTU & 小九九 t.me/gdot0
thread_num = 5 #并发数

import json
import os
import random
import re
import sys
import time
from urllib import parse
import threading

import redis
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

"""
必装依赖
requests
redis
不报错不安装
PySocks
"""
"""
实现规律UA  还是久佬提供建议 还没实现
支持库有 KR本地 慈善家redis和本地 环境redis 麦积本地 超人库redis
2023/11/26
添加 ProxyHttpOverHttps 开关针对go代理进行的修改，极大避免的脚本使用的403,如果使用的go版本并且是今天或者最新请开启，默认关闭
2023/11/16
协议使用http
2023/11/10 15:00
修复了一大堆问题
2023/11/10
作者太菜了，异步换成非异步
2023/11/9 19:50
添加代理监测，监测不通过切换 (超人队久佬 https://github.com/Jejz168/BoredPlay.git 库作者提供建议)
获取成功添加 1-4秒随机等待 (超人队久佬提供建议)
取消 Complete_Pause完成后等待时间
2023/11/9 19:00
修复不使用代理aiohttp-socks报错
2023/11/9 18:00
修复不能使用socks5 代理问题
需要安装依赖 aiohttp-socks
2023/11/9 2:40
修复几个报错
2023 /11/8 22:45
支持隧道代理 Tunnel_url
支持完成后等待时间 默认2秒  Complete_Pause
支持隧道代理403等待时间 默认30秒 Tunnel_Pause
支持是否启用代理默认启用 (感觉秒什么用给一些号特别少的人准备的开关) JD_PROXY_OPEN
隧道代理优先级低于api,设置隧道后不会调用api 
2023/11/7 21:30
修复kr 慈善家的过期时间key错误的值不同问题
pin正则表达式问题
2023/11/6 23:00
必安装依赖 aioredis aiohttp
可安装可不安装依赖 aiodns
依赖版本限制 Python 3.10 > cchardet
依赖版本限制 Python 3.10 <=  charset-normalizer
修复慈善家路径错误问题

2023/11/6 5:30
本地存储支持 M系列 KR 慈善家
远程redis普通模式支持 慈善家 环境
如果有其他库需要添加可以自己添加也可以 https://t.me/InteTU/184 留言 如果是本地存储提供本地存储路径和存储格式 如果是远程存储配合获取格式
慈善家
    不支持 JD_ISV_TOKEN_REDIS_CACHE_KEY 如果需要支持 https://t.me/InteTU/184 留言
    支持 获取JD_ISV_TOKEN_CUSTOM_CACHE 但是仅支持 .json文件
"""
# 获取 token的域名 默认是 https://lzkj-isv.isvjcloud.com
Token_url = "https://lzkj-isv.isvjcloud.com"
ProxyHttpOverHttps = False  # 针对代理优化如果你使用的是go代理并且版本是2023/11/26或者更新版本请设置为 True
# 代理相关 不填写默认获取隧道代理
proxyUrl = None  # 代理API 使用http \n分割 只能提取一个
user_pass = None  # 账户:密码 如果不能自动白名单建议填写

Tunnel_url = "http:/"  # 隧道代理, 如果填写隧道代理将会不获取代理api

Tunnel_Pause = 3  # 隧道代理如果403停止秒数

JD_PROXY_OPEN = 0  # 是否启动代理默认启动 非0都不启用 给家宽小白准备的

# M系列缓存Token路径 如果使用就 MCacheToken = "walle1798_EVE/tokens/"
MCacheToken = "walle1798_EVE/tokens/"

# KR系列缓存Token路径 如果使用就 KRCacheToken = "KingRan_KR/function/cache/token.json"
KRCacheToken = "KingRan_KR/function/cache/token.json"
# 慈善家 SuperManito/cishanjia库 默认读取 JD_ISV_TOKEN_REDIS_CACHE_URL
CiShanJiaToken = "SuperManito_cishanjia_main/function/cache/token.json"
# 环境redis换成
redis_url = "redis://"  # "redis://:Redis密码@127.0.0.1:6379" 默认读取 PRO_REDIS_URL 变量的

# 慈善家 SuperManito/cishanjia库 支持格式 优先慈善家变量后环境变量
if redis_url is None:
    redis_url = os.environ.get("JD_ISV_TOKEN_REDIS_CACHE_URL", None)
    if redis_url is None:
        redis_url = os.environ.get("PRO_REDIS_URL", None)

# 如果是 0 = JD_SIGN_API 1 =  JD_SIGN_KRAPI 2 = M_API_SIGN_URL
state = 0
# 获取Sign
JD_SIGN = os.environ.get("JD_SIGN_API", None)
if JD_SIGN is None:
    JD_SIGN = os.environ.get("JD_SIGN_KRAPI", None)
    state = 1
    if JD_SIGN is None:
        JD_SIGN = os.environ.get("M_API_SIGN_URL", None)
        state = 2
        if JD_SIGN is None:
            print(
                "没有请填写 sign获取地址 JD_SIGN_API | JD_SIGN_KRAPI | M_API_SIGN_URL"
            )
            sys.exit()

Father_path = re.findall(f"(.*?/scripts/)", os.path.abspath(__file__))[0]
# 自动识别
dirlist = os.listdir(Father_path)
if "walle1798_EVE" in dirlist:
    MCacheToken = Father_path + MCacheToken
    print("识别到M系列Token 存放目录是: ", MCacheToken)
else:
    MCacheToken = None
if "KingRan_KR" in dirlist:
    KRCacheToken = Father_path + KRCacheToken
    print("识别到KR Token 存放文件是: ", KRCacheToken)
else:
    KRCacheToken = None
if "SuperManito_cishanjia_main" in dirlist:
    CiShanJiaToken = Father_path + CiShanJiaToken
    print("识别到慈善家 Token 存放文件是: ", CiShanJiaToken)
else:
    CiShanJiaToken = None
# 获取慈善家是否设置了 JD_ISV_TOKEN_CUSTOM_CACHE
if os.environ.get("JD_ISV_TOKEN_CUSTOM_CACHE", None) is not None:
    CiShanJiaToken = os.environ.get("JD_ISV_TOKEN_CUSTOM_CACHE", None)
    # 判断是否可RK一样
    if CiShanJiaToken == KRCacheToken:
        CiShanJiaToken = None


#


class Proxy:
    def __init__(self, url=None, user_pass=None, redis_url=None, Tunnel_url=None):
        self.proxies = None
        self.url = url
        self.user_pass = user_pass
        self.new_time: int = 0
        self.headers = {
            "Connection": "keep-alive",
            "User-Agent": f"okhttp/3.{random.uniform(7, 16)}.{random.uniform(1, 16)};jdmall;android;version/12.0.{random.uniform(1, 16)};build/{random.uniform(1, 100000)};",
            "Charset": "UTF-8",
            "Cache-Control": "no-cache",
        }
        self.redisConn = None
        self.redis_url = redis_url
        self.Tunnel_url = {"https": Tunnel_url}
        self.http_url_402 = "http://wifi.vivo.com.cn/generate_204"

    def getproxy(self):
        for i in range(0, 3):
            resp = fetch_url_with_proxy(url=self.url, headers=self.headers)
            if resp is None:
                continue
            if resp["status"] != 200:
                print(
                    f"获取代理状态码: {resp['status']} 原因 {resp['data']} 延迟一秒等待"
                )
                # 延迟一秒
                time.sleep(1)
            elif len(resp["data"]) > 30:
                print("获取api长度超过限制", resp["data"])
                self.proxies = None
                return
            else:
                ip = str(resp["data"]).rstrip("\n")
                if self.user_pass:
                    self.proxies = {"https": f"http://{self.user_pass}@{ip}"}
                else:
                    self.proxies = {"https": f"http://{ip}"}
                self.new_time = int(time.time()) + 40
                resp = self.http402()
                if resp != 204:
                    print(f"检测 {self.proxies} 不通过等待两秒切换新的")
                    time.sleep(2)
                    continue
                print(f"获取新代理: {self.proxies}")
                return

    def redis(self):
        if self.redis_url is None:
            print("没有配置获取到redis不尝试重新连接")
            return
        try:
            self.redisConn = redis.Redis.from_url(self.redis_url)
        except redis.exceptions.ConnectionError as e:
            print("redis链接地址不通")

    def use_proxy(self):
        """
        获取使用的代理
        :return:
        :rtype:
        """
        if JD_PROXY_OPEN != 0:
            return None
        if self.url is not None:
            if self.new_time < int(time.time()):
                print("代理超过40秒主动切换")
                self.getproxy()
                return self.proxies
            else:
                return self.proxies
        else:
            return self.Tunnel_url

    def http402(self):
        headers = {
            "Connection": "keep-alive",
            "User-Agent": f"okhttp/3.{random.uniform(7, 16)}.{random.uniform(1, 16)};jdmall;android;version/12.0.{random.uniform(1, 16)};build/{random.uniform(1, 100000)};",
            "Charset": "UTF-8",
            "Accept-Encoding": "br,gzip,deflate",
            "Cache-Control": "no-cache",
        }
        resp = fetch_url_with_proxy(
            url=self.http_url_402, headers=headers, proxy=self.proxies, method="get"
        )
        if resp is None:
            return -1
        if resp["status"] == 204:
            return 204
        else:
            return -1


proxy = Proxy(
    url=proxyUrl, user_pass=user_pass, redis_url=redis_url, Tunnel_url=Tunnel_url
)


def fetch_url_with_proxy(url, headers=None, data=None, proxy=None, method="post"):
    try:
        if method == "post":
            response = requests.post(
                url=url,
                headers=headers,
                data=data,
                verify=False,
                timeout=30000,
                proxies=proxy,
            )
            return {"status": response.status_code, "data": response.text}
        elif method == "get":
            response = requests.post(
                url=url,
                headers=headers,
                data=data,
                verify=False,
                timeout=30000,
                proxies=proxy,
            )
            return {"status": response.status_code, "data": response.text}
    except Exception as e:
        print("请求发生异常: ")
        # print("请求发生异常: ", e)
        return None


def get_cookies():
    """
    获取CK
    :return:
    :rtype:
    """
    return os.environ["JD_COOKIE"].split("&")


def get_sign(functionId, body):
    global headers, data
    if state == 0 or state == 2:
        headers = {"Content-Type": "application/json"}
        data = json.dumps({"fn": functionId, "functionId": functionId, "body": body})
    elif state == 1:
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        # 将 JSON 对象转换为 JSON 字符串
        data = {
            "fn": functionId,
            "functionId": functionId,
            "body": json.dumps(body),
        }
    resp = fetch_url_with_proxy(url=JD_SIGN, headers=headers, data=data)
    if resp is None:
        return None
    if resp["status"] != 200:
        print("sign出现异常", resp["status"])
        return None
    resp_json = json.loads(resp["data"])
    if "body" in resp_json:
        return resp_json["body"]
    elif "data" in resp_json:
        return resp_json["data"]["body"]
    return None


def gettoken(ck, times, tid="1"):
    for i in range(0, times):
        try:
            if i != 0:
                txt = str(tid) + ": 获取错误，正在重试第{}次"
                print(txt.format(i))
                # url403=f"https://api403.m.jd.com/client.action?functionId=try_SpecFeedList&appid=newtry"
                # fetch_url_with_proxy(url403, proxy=ip, method="get")
            headers = {
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "zh-cn",
                "Connection": "keep-alive",
                "Content-Type": "application/x-www-form-urlencoded",
                "Host": "api.m.jd.com",
                "Cookie": ck,
                "User-Agent": "JD4iPhone/168069 (iPhone; iOS 13.7; Scale/3.00)",
            }
            """headers = {
                "X-Rp-Client": "android_3.0.0",
                "Connection": "keep-alive",
                "User-Agent": f"okhttp/3.{random.uniform(7, 16)}.{random.uniform(1, 16)};jdmall;android;version/12.0.{random.uniform(1, 16)};build/{random.uniform(1, 100000)};",
                "X-Referer-Package": "com.jingdong.app.mall",
                "Charset": "UTF-8",
                "X-Referer-Page": "com.jingdong.app.mall.WebActivity",
                "Accept-Encoding": "br,gzip,deflate",
                "Cache-Control": "no-cache",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Host": "api.m.jd.com",
                "Cookie": ck
            }"""
            if ProxyHttpOverHttps:
                headers["Proxy-Http-Over-Https"] = True
            functionId = "isvObfuscator"
            data = {"id": "", "url": Token_url}
            sign = get_sign(functionId, data)
            if sign is None:
                continue

            ip = proxy.use_proxy()
            url = f"https://api.m.jd.com/client.action?functionId={functionId}&{sign}"
            resp = fetch_url_with_proxy(
                url, headers, f"body={parse.quote(json.dumps(data))}", proxy=ip
            )
            if resp is None:
                print(str(tid) + ": resp为空")
                continue
            if resp["status"] != 200:
                if resp["status"] == 403:
                    print(str(tid) + ": resp=403")
                    if proxy.Tunnel_url["https"] is None:
                        print(str(tid) + ": 代理超过403了切换代理")
                        proxy.getproxy()
                    else:
                        # 隧道代理停止秒
                        time.sleep(Tunnel_Pause)
                time.sleep(1)
                continue
            resp_json = json.loads(resp["data"])
            if resp_json["code"] == "0" and resp_json["errcode"] == 0:
                return resp_json["token"]
            print(str(tid) + ": isvObfuscator 接口发生异常: ", resp_json)
        except Exception as e:
            print(str(tid) + ": isvObfuscator 接口发生异常: ", e)
    return None


def m_token(pin, token):
    """
    M系列缓存
    :param pin:
    :type pin:
    :param token:
    :type token:
    :return:
    :rtype:
    """
    if MCacheToken is None:
        return
    var = {"expireTime": int(time.time() * 1000) + 1500000, "token": token}
    with open(f"{MCacheToken}{pin}.json", "w", encoding="utf-8") as f:
        json.dump(var, f)
    print(f"M系列缓存 {pin} 的token 成功")


def kr_token(path_token, KR):
    if path_token is None:
        return
    try:
        with open(path_token, "w", encoding="utf-8") as f:
            json.dump(KR, f)
        print(f"{path_token} 路径缓存 的token 成功")
    except Exception as e:
        print(f"{path_token} 路径缓存 的token 发生异常: ", e)


def recToken(pt_pin_match, token):
    # 写入开始
    m_token(pt_pin_match, token)
    # 记录KR
    global KR
    KR[f"{pt_pin_match}"] = {"expires": int(time.time() * 1000) + 2500000, "val": token}
    # 环境的开始实现
    if proxy.redisConn is not None:
        try:
            proxy.redisConn.set(pt_pin_match, token)
            proxy.redisConn.expire(pt_pin_match, 2500)
            print(f"redis {pt_pin_match}缓存 {token} 成功")
        except Exception as e:
            print("写入redis失败: ", e)
    # 完成任务等待时间
    # time.sleep(random.randint(3, 5))


def makeGenFromArr(arr):
    return (x for x in arr)


def thread_gettoken(id, generator):
    try:
        while True:
            ck = next(generator)
            if not ck:
                print("没有获取到ck，线程退出")
                break
            token = gettoken(ck, 3, id)
            if token is None:
                print(str(id) + ": 获取次数过多跳过获取, " + str(ck))
                global fail
                fail += 1
                continue
            global succ
            succ += 1
            pt_pin_match = re.search(r"pin=(.*?);", ck).group(1)
            print(str(id), end=": ")
            recToken(pt_pin_match, token)
    except StopIteration:
        print(str(id) + ": thread completed")


KR = {}
succ = 0
fail = 0


def main_async():
    token_Path = [KRCacheToken, CiShanJiaToken]
    if proxy.Tunnel_url["https"] is None and proxy.url is None and JD_PROXY_OPEN == 0:
        print("你设置的使用代理但是没有设置隧道代理或者api")
        return
    # 如果用户使用api或者隧道
    proxy.use_proxy()

    # 链接redis
    proxy.redis()
    cks = get_cookies()
    if cks is None:
        return

    # 多线程处理其余ck
    ck_gen = makeGenFromArr(cks)
    tnum = thread_num  
    tnum = 1 if not tnum else tnum
    t_pool = []
    for tid in range(1, tnum + 1):
        t = threading.Thread(target=thread_gettoken, args=(tid, ck_gen))
        t.daemon = True
        t_pool.append(t)
        t.start()
        time.sleep(3)
    for t in t_pool:
        t.join()
    global succ
    global fail
    print("成功：" + str(succ))
    print("失败：" + str(fail))

    """ 原单线程处理
    for ck in cks[1:]:
        token = gettoken(ck,3)
        if token is None:
            print("获取次数过多跳过获取, ", ck)
            continue
        pt_pin_match = re.search(r'pin=(.*?);', ck).group(1)
        recToken(pt_pin_match, token)
        # 以下过程打包到recToken(pt_pin_match, token): 中了
        # 写入开始
        m_token(pt_pin_match, token)
        # 记录KR
        KR[f"{pt_pin_match}"] = {"expires": int(time.time() * 1000) + 2500000,
                                 "val": token}
        # 环境的开始实现
        if proxy.redisConn is not None:
            try:
                proxy.redisConn.set(pt_pin_match, token)
                proxy.redisConn.expire(pt_pin_match, 2500)
                print(f"redis {pt_pin_match}缓存 {token} 成功")
            except Exception as e:
                print("写入redis失败: ", e)
        # 完成任务等待时间
        #time.sleep(random.randint(3, 5))
    """
    if KR != {}:
        for path_token in token_Path:
            kr_token(path_token, KR)
    if proxy.redisConn is not None:
        proxy.redisConn.close()


if __name__ == "__main__":
    main_async()
