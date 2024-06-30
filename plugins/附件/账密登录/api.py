# -*- coding: utf-8 -*-
# api.py
# author: 小九九 t.me/gdot0
run_port = 12345 #修改运行端口

from quart import Quart, request, jsonify
import hashlib, asyncio
import login as backend
import ddddocr

ocr = ddddocr.DdddOcr(show_ad=False, beta=True)


class account:
    status = ""
    uid = ""
    account = ""
    password = ""
    isAuto = False
    cookie = ""
    SMS_CODE = ""
    msg = ""

    def __init__(self, data):
        try:
            self.status = "pending"
            self.account = data.get("id", None)
            self.password = data.get("pw", None)
            self.isAuto = data.get("isAuto", False)
            if not self.account or not self.password:
                raise ValueError("账号和密码不能为空")

            c = str(self.account) + str(self.password)
            self.uid = hashlib.sha256(c.encode("utf-8")).hexdigest()
        except:
            raise ValueError("账号密码错误：" + str(data))


# 正在处理的账号列表
workList = {}
"""
workList ={
    uid: {
        status: pending,
        account: 123xxxxxxxx, 
        password: test123,
        isAuto: False
        cookie: ""
        SMS_CODE: None,
        msg: "Error Info"
    },
    ...
}
"""
app = Quart(__name__)

# 制作响应
def mr(status, **kwargs):
    r_data = {}
    r_data["status"] = status
    for key, value in kwargs.items():
        r_data[str(key)] = value
    r_data = jsonify(r_data)
    r_data.headers["Content-Type"] = "application/json; charset=utf-8"
    return r_data


# -----router-----
# 传入账号密码，启动登录线程
@app.route("/login", methods=["POST"])
async def login():
    data = await request.get_json()
    try:
        u = account(data)
    except Exception as e:
        r = mr("error", msg=str(e))
        return r
    # 检测重复提交
    if workList.get(u.uid):
        workList[u.uid].SMS_CODE = ""
        r = mr("pass", uid=u.uid, msg=f"{u.account}已经在处理了，请稍后再试")
        return r

    # 开始登录
    workList[u.uid] = u
    asyncio.create_task(THREAD_DO_LOGIN(workList, u.uid, ocr))
    # 更新信息，响应api请求
    workList[u.uid].status = "pending"
    r = mr("pass", uid=u.uid, msg=f"{u.account}处理中, 到/check查询处理进度")
    return r


# 登录过程
async def THREAD_DO_LOGIN(workList, uid, ocr):
    try:
        await backend.main(workList, uid, ocr)
    except Exception as e:
        print(e)
        workList[uid].msg = str(e)

    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(backend.start(workList, uid))
    except Exception as e:
        print(e)
        workList[uid].msg = str(e)
    """


# 检查后端进度
@app.route("/check", methods=["POST"])
async def check():
    data = await request.get_json()
    uid = data.get("uid", None)
    r = None
    # 有记录
    if workList.get(uid, ""):
        status = workList[uid].status
        if status == "pass":
            cookie = workList[uid].cookie
            r = mr(status, cookie=cookie, msg="成功")
        elif status == "pending":
            r = mr(status, msg="正在处理中，请等待")
        elif status == "error":
            r = mr(status, msg="登录失败，请在十秒后重试：" + workList[uid].msg)
        elif status == "SMS":
            r = mr(status, msg="需要短信验证")
        elif status == "wrongSMS":
            r = mr(status, msg="短信验证错误，请重新输入")
        else:
            r = mr("error", msg="笨蛋开发者，忘记适配新状态啦：" + status)
    # 无记录
    else:
        r = mr("error", msg="未找到该账号记录，请重新登录")
    return r


# 传入短信验证码
@app.route("/sms", methods=["POST"])
async def sms():
    data = await request.get_json()
    uid = data.get("uid", None)
    code = data.get("code", None)
    # 检查传入验证码合规
    if len(code) != 6 and not code.isdigit():
        r = mr("wrongSMS", msg="验证码错误")
        return r
    try:
        THREAD_SMS(uid, code)
        r = mr("pass", msg="成功提交验证码")
        return r
    except Exception as e:
        r = mr("error", msg=str(e))
        return r


def THREAD_SMS(uid, code):
    print("phase THREAD_SMS: " + str(code))
    u = workList.get(uid, "")
    if not u:
        raise ValueError("账号不在记录中")
    if u.status == "SMS" or u.status == "wrongSMS":
        u.SMS_CODE = code
    else:
        raise ValueError("账号不在SMS过程中")


# -----regular functions-----
# 删除成功或失败的账号记录
async def deleteSession(uid):
    await asyncio.sleep(5)
    del workList[uid]


"""
@app.route("/delck", methods=["POST"])
def delck():
    data = request.get_json()
    uid = data.get("uid", None)
    if not exist(uid):
        r = mr(False, msg="not exist")
        return r

    THREAD_DELCK(uid)
"""
asyncio.new_event_loop().run_until_complete(app.run(host="0.0.0.0", port=run_port))
