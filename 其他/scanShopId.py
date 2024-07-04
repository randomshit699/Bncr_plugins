import json, time, threading, queue, os, random, string, traceback
from requests.exceptions import SSLError, ProxyError
from fake_useragent import UserAgent  # type: ignore
from typing import List

# import requests
from curl_cffi import requests  # type: ignore 
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.ssl_ import create_urllib3_context  # type: ignore


# configuration
startId = 10000
# 从哪个id开始扫描
path = (
    "/home/shopid.txt"  # 扫描结果存储到哪个文件 
)
noCookieMode = True  # 一般不需要cookie，当风控严重时需要cookie，风控时改为False
ck_path = ""  # ck列表文件位置，一行一个ck
proxy_pool_url = "http://"  # 代理池地址 ## TODO: api代理 ##支持ipv6代理池 https://zu1k.com/posts/tutorials/http-proxy-ipv6-pool/
thread_num = 3  # 并发线程数
writeToFileEveryXRecords = 1000  # 每x个扫描结果写入一次文件
sleepBase = 10  # 异常情况休息时间（秒）
lcDumpPath = "/home/lc_dump.txt"

# constants
impersonates = [
    "chrome99",
    "chrome107",
    "chrome99_android",
    "edge101",
    "safari15_3",
    "safari15_5",
]
## tls指纹
ORIGIN_CIPHERS = (
    "ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:ECDH+HIGH:"
    "DH+HIGH:ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+HIGH:RSA+3DES"
)
## 初始化ck列表
if not noCookieMode:
    cookies = []
    with open(ck_path, "r") as ckFile:
        for ck in ckFile:
            ck = ck.strip()
            cookies.append(ck)


## 自定义异常类
class TooManyRetry(Exception):
    def __init__(self, message, shopId):
        super().__init__(message)
        self.shopId = int(shopId)


## 请求参数
baseURL = "https://api.m.jd.com/client.action?t="
headers = {
    "accept": "*/*",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "cache-control": "no-cache",
    "content-type": "application/x-www-form-urlencoded",
    "cookie": "",  
    "origin": "https://shop.m.jd.com",
    "pragma": "no-cache",
    "priority": "u=1, i",
    "referer": "https://jd.com/",
    "sec-ch-ua": '"Chromium";v="124", "Microsoft Edge";v="124", "Not-A.Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "x-referer-page": "https://shop.m.jd.com/shop/home",
    "x-rp-client": "h5_1.0.0",
}
proxies = {
    "http": proxy_pool_url,
    "https": proxy_pool_url,
}
## 记录本次扫描最后一次成功的进度
lastId = str(startId)
## 停止标志
scanStop = False


# functions
## 更新ck列表
def updateCookies(ck_path, cookies):
    while True:
        with open(ck_path, "r") as ckFile:
            for ck in ckFile:
                ck = ck.strip()
                cookies.append(ck)
        time.sleep(3600)


def removeCookieFromHeaders(headers):
    del headers["cookie"]
    return headers


## 更换tls指纹
class DESAdapter(HTTPAdapter):
    def __init__(self, *args, **kwargs):
        """
        A TransportAdapter that re-enables 3DES support in Requests.
        """
        CIPHERS = ORIGIN_CIPHERS.split(":")
        random.shuffle(CIPHERS)
        CIPHERS = ":".join(CIPHERS)
        self.CIPHERS = CIPHERS + ":!aNULL:!eNULL:!MD5"
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context(ciphers=self.CIPHERS)
        kwargs["ssl_context"] = context
        return super(DESAdapter, self).init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        context = create_urllib3_context(ciphers=self.CIPHERS)
        kwargs["ssl_context"] = context
        return super(DESAdapter, self).proxy_manager_for(*args, **kwargs)


## 更换session
def generate_random_sec_ch_ua_token():  # 随机sec_ch_ua_token
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=16))


def generate_random_sec_ch_ua():  # 随机sec_ch_ua
    brand1 = generate_random_sec_ch_ua_token()
    version1 = str(random.randint(1, 99))
    brand2 = generate_random_sec_ch_ua_token()
    version2 = str(random.randint(1, 99))
    return f'"{brand1}";v="{version1}", "{brand2}";v="{version2}", "Not A Brand";v="99"'


def generate_random_sec_ch_ua_mobile():  # 随机sec_ch_ua_mobile
    return "?" + str(random.randint(0, 1))


def generate_random_sec_ch_ua_platform() -> str:  # 随机sec_ch_ua_platform
    platforms: List[str] = ["Windows", "macOS", "Android", "iOS", "Linux", "Unknown"]
    return random.choice(platforms)


def changeCookie(headers):  # 更换headers中的cookie
    headers["cookie"] = random.choice(cookies)
    return headers


def changeHeaders(headers):  # 更换headers
    if not noCookieMode:
        headers["cookie"] = random.choice(cookies)
    headers["user-agent"] = UserAgent().random
    headers["sec-ch-ua"] = generate_random_sec_ch_ua()
    headers["sec-ch-ua-mobile"] = generate_random_sec_ch_ua_mobile()
    headers["sec-ch-ua-platform"] = generate_random_sec_ch_ua_platform()
    return headers


def makeNewSession():  # 新session
    session = requests.Session()
    session.proxies = proxies
    global headers
    headers = changeHeaders(headers)
    session.headers.update(headers)
    return session


## 生成器获取跨越数值范围内的下一个数
def getShopId(
    start_id,
):
    d = start_id
    while d > 0:
        if d < 10000:
            raise ValueError("at least 10000")
        elif d < 218900:
            for i in range(d, 218900):
                yield i
            d = 529000
        elif (
            d >= 529000 and d < 559000
        ):  
            for i in range(d, 559000):  
                yield i  
            d = 564000  
        elif d >= 564000 and d < 1000000:
            for i in range(d, 1000000):
                yield i
            d = 10000000
        elif d >= 10000000 and d < 12280000:
            for i in range(d, 12280000):
                yield i
            d = 1000000000
        elif d >= 1000000000 and d < 1000600000:
            for i in range(d, 1000600000):
                yield i
            d = -1  # 跳出循环，会raise StopIteration
        else:
            raise ValueError("end")


## 合成请求体
def makeBody(shopid):
    timestamp = int(time.time() * 1000)
    data = {
        "functionId": "whx_getMShopOutlineInfo",
        "body": json.dumps({"shopId": shopid, "source": "m-shop"}),
        "t": timestamp,
        "appid": "shop_m_jd_com",
        "clientVersion": "11.0.0",
        "client": "wh5",
    }
    # print("正在扫描shopid=" + shopid)
    return data


## 进行请求


def requestJD(session, shopId, t_dict, tryNum):
    tn = t_dict["name"]
    availUA = True 
    while tryNum < 2:
        time.sleep(0.5)
        data = makeBody(shopId)
        url = (
            baseURL  
        )
        response = session.post(
            url, data=data, verify=True, impersonate=random.choice(impersonates)
        )  
        if response.status_code == 200:
            json = response.json()
            if json["code"] == "200":  # 请求成功 & 店铺存在
                shopInfo = json["data"]["shopInfo"]
                venderId = str(shopInfo["venderId"])
                closed = shopInfo["closed"]
                t_closed = "closed" if closed else "online"
                shopName = str(shopInfo["shopName"])
                """if not closed:
                    if shopInfo["followerCount"]:
                        followerCount = str(shopInfo["followerCount"])
                    else:
                        followerCount = "no_data"
                    if shopInfo["grade"]:
                        if shopInfo["grade"]["scoreRankRateGrade"]:
                            scoreRankRateGrade = str(
                                shopInfo["grade"]["scoreRankRateGrade"]
                            )
                    else:
                        scoreRankRateGrade = "no_data"
                else:
                    followerCount = "no_data"
                    scoreRankRateGrade = "no_data"
                """
                res = {
                    "shopId": shopId,
                    "venderId": venderId,
                    "closed": t_closed,
                    "shopName": shopName,
                    # "followerCount": followerCount,
                    # "scoreRankRateGrade": scoreRankRateGrade,
                }
                print(
                    tn
                    + " | 扫描结果： "
                    + shopId
                    + ","
                    + venderId
                    + ","
                    + t_closed
                    + ","
                    + shopName
                    # + ",关注量："
                    # + followerCount
                    # + ",评分："
                    # + scoreRankRateGrade
                )
                return res
            else:  # 请求成功 & 店铺不存在
                if json["msg"]:
                    print(tn + " | " + "扫描结果： " + shopId + " " + str(json["msg"]))
                else:
                    print(tn + " | " + "扫描结果： " + shopId + " 其他错误")
                return "No shop"
        elif response.status_code == 403:
            if not availUA:  
                sleepTime = sleepBase
                print(
                    tn
                    + " | "
                    + shopId
                    + "的请求403了，歇"
                    + str(sleepTime)
                    + "s后再试一次"
                )
                time.sleep(sleepTime)
            else: 
                availUA = False
                print(tn + " | " + shopId + "的请求403了，换套ua再试一次")
                session = makeNewSession()
            tryNum += 1  
        else:  
            msg = tn + " | " + shopId + "其他错误，code：" + str(response.status_code)
            raise RuntimeError(msg)

    raise TooManyRetry( 
        tn
        + " | "
        + shopId
        + "请求失败的次数太多了",
        int(shopId),
    )


## 将各扫描线程的扫描结果队列queue写入文件
def writeQueueToFileThread(queue, path):
    time.sleep(30)  
    while True:
        with open(path, "a", encoding="utf-8") as file:
            i = 0
            while i <= writeToFileEveryXRecords and i >= 0:  
                if not queue.empty():
                    data = queue.get()
                    r = (
                        data["shopId"]
                        + ","
                        + data["venderId"]
                        + ","
                        + data["closed"]
                        + ","
                        + data["shopName"]
                        # + ","
                        # + data["followerCount"]
                        # + ","
                        # + data["scoreRankRateGrade"]
                        + "\n"
                    )
                    file.write(r)
                    global lastId
                    lastId = data["shopId"]
                    i += 1
                else:  
                    i = -1
                    print("wqtf | 开始写入一次缓存")
                    file.close()
                    break
            if i != -1:  
                print(
                    "已缓存"
                    + str(writeToFileEveryXRecords)
                    + "条数据，开始写入一次文件"
                )
            else:
                time.sleep(30)  
        if scanStop and queue.empty():
            break  


## Lost-Catch，捕获扫描线程扫描失败的条目
def lc(lc_queue, lc_dict):
    time.sleep(3)  
    try:
        if lc_queue.empty():
            time.sleep(10)
        while not lc_queue.empty():
            shopId = str(lc_queue.get())
            session = makeNewSession()
            if scanStop:
                with open(lcDumpPath, "a", encoding="utf-8") as file:
                    while not lc_queue.empty():
                        r = str(lc_queue.get()) + "\n"
                        file.write(r)
                    print("lc1 | lc_queue DUMPED")
                break
            res = None
            while not res and not scanStop:
                try:
                    tryNum = 1
                    res = requestJD(session, shopId, lc_dict, tryNum)
                    if res and res != "No shop":
                        t_queue.put(res)
                except (
                    Exception
                ) as e:  
                    lc_queue.put(shopId)
                    print(str(e))
                    raise RuntimeError
        raise RuntimeError
    except RuntimeError:  # 在结束本线程后，启动另一条lc线程
        lc_t = threading.Thread(target=lc, args=(lc_queue, lc_dict))
        lc_t.daemon = True
        lc_t.start()


# main
gen = getShopId(startId)  
t_queue = queue.Queue()  # 扫描结果queue
lc_queue = queue.Queue()  # Lost-Catch queue


def main(t_dict):
    global scanStop
    session = makeNewSession()
    try:
        threadName = t_dict["name"]
        while True:  
            if scanStop:
                break
            shopId = str(next(gen)) 
            res = None
            tryNum = 0
            while not res and not scanStop:
                try:
                    tryNum += 1  
                    res = requestJD(session, shopId, t_dict, tryNum)
                    if not noCookieMode:
                        headers = changeCookie(session.headers)  # 每次请求换一个ck
                        session.headers.update(headers)
                    if res and res != "No shop":
                        t_queue.put(res)
                except SSLError as e:
                    print(threadName + " | SSLError: " + str(e))
                    slp = random.randint(sleepBase / 3, sleepBase)
                    time.sleep(slp)
                except ProxyError as e:
                    print(threadName + " | PROXYError: " + str(e))
                    slp = random.randint(sleepBase, sleepBase * 3)
                    time.sleep(slp)
                except (
                    RuntimeError,
                    TooManyRetry,
                ) as e:  
                    lc_queue.put(shopId)
                    print(e)
                    time.sleep(3)
                    break
                except (
                    Exception,
                    requests.errors.RequestsError,
                ) as e:  # debug
                    """
                    print(
                        t_dict["name"]
                        + " on "
                        + shopId
                        + " | "
                        + traceback.format_exc()
                    )
                    print(e)
                    """
                    time.sleep(sleepBase)
    except ValueError:
        print("ShopId不在合理范围内")
        scanStop = True
    except StopIteration:
        print("Generator exhausted")
        raise StopIteration


# multiTreading
# 创建运行时更新cookie线程
if not noCookieMode:
    updc = threading.Thread(target=updateCookies, args=(ck_path, cookies))
    updc.daemon = True
    updc.start()
# 创建将queue写入文件的线程
wqtf = threading.Thread(target=writeQueueToFileThread, args=(t_queue, path))
wqtf.daemon = True
wqtf.start()


try:
    lc_dict = {  
        "id": 1,
        "name": "lc1",
    }
    lc_t = threading.Thread(target=lc, args=(lc_queue, lc_dict))
    lc_t.daemon = True
    lc_t.start()
    print("lc1 booting")

    t_pool = []
    for t_id in range(1, thread_num + 1):
        t_name = "t" + str(t_id)
        t_dict = {
            "id": t_id,
            "name": t_name,
        }
        t = threading.Thread(target=main, args=(t_dict,))
        t.daemon = True
        t_pool.append(t)
        print(t_name + " booting")
        t.t_dict = t_dict
        t.start()
        time.sleep(3)

    while True:  
        if not wqtf.is_alive():
            print("写入文件线程已死，可能丢失数据，即将停止")
            scanStop = True
        if scanStop:
            # TODO: 将所有正在扫描的shopId put到 lc_queue，然后转储lc_queue
            break
        time.sleep(3)
    os._exit()
except KeyboardInterrupt:
    print("手动停止，正在停止线程...")
    scanStop = True
except StopIteration:
    while not lc_queue.empty():
        print("Lost & Catch 收尾中...")
        time.sleep(30)
finally:
    # 写入文件
    while not t_queue.empty():
        time.sleep(3)
        print("将缓存写入文件中...")
    print("写入完成，即将退出")
    print("本次扫描到shopId=" + lastId)
    exit()
