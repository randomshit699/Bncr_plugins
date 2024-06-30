# -*- coding: utf-8 -*-
# login.py
# author: github/svjdck & github.com/icepage/AutoUpdateJdCookie & 小九九 t.me/gdot0

import os  # 读取配置文件
from pyppeteer import launch  # pyppeteer库，用于自动化控制浏览器
import aiohttp  # 用于请求青龙
from urllib import request  # 用于网络请求，这里主要用来下载图片
from PIL import Image  # 用于图像处理
import platform  # 判断系统类型
import zipfile  # 用于解压文件

import datetime  # 获取时间
import asyncio  # 异步I/O操作库
import random  # 用于模拟延迟输入
import cv2  # OpenCV库，用于图像处理
import numpy as np
import base64
import io
import re

# 传参获得已初始化的ddddocr实例
ocr = None

# 支持的形状类型
supported_types = [
    "三角形",
    "正方形",
    "长方形",
    "五角星",
    "六边形",
    "圆形",
    "梯形",
    "圆环",
]
# 定义了支持的每种颜色的 HSV 范围
supported_colors = {
    "紫色": ([125, 50, 50], [145, 255, 255]),
    "灰色": ([0, 0, 50], [180, 50, 255]),
    "粉色": ([160, 50, 50], [180, 255, 255]),
    "蓝色": ([100, 50, 50], [130, 255, 255]),
    "绿色": ([40, 50, 50], [80, 255, 255]),
    "橙色": ([10, 50, 50], [25, 255, 255]),
    "黄色": ([25, 50, 50], [35, 255, 255]),
    "红色": ([0, 50, 50], [10, 255, 255]),
}


async def deleteSession(workList, uid):
    s = workList.get(uid, "")
    if s:
        await asyncio.sleep(60)
        del workList[uid]


async def logon_main(chromium_path, workList, uid):
    # 判断账号密码错误
    async def isWrongAccountOrPassword(page, verify=False):
        try:
            element = await page.xpath('//*[@id="app"]/div/div[5]')
            """
            text = await page.evaluate_on_element(
                element[0], "(element) => element.textContent"
            )
            """
            if element:
                text = await page.evaluate(
                    "(element) => element.textContent", element[0]
                )
                if text == "账号或密码不正确":
                    if verify == True:
                        return True
                    await asyncio.sleep(2)
                    return await isWrongAccountOrPassword(page, verify=True)
            return False
        except Exception as e:
            print("isWrongAccountOrPassword " + str(e))
            return False

    # 判断验证码超时
    async def isStillInSMSCodeSentPage(page):
        try:
            if await page.xpath('//*[@id="header"]/span[2]'):
                element = await page.xpath('//*[@id="header"]/span[2]')
                """
                text = await page.evaluate_on_element(
                    element[0], "(element) => element.textContent"
                )
                """
                if element:
                    text = await page.evaluate(
                        "(element) => element.textContent", element[0]
                    )
                    if text == "手机短信验证":
                        return True
            return False
        except Exception as e:
            print("isStillInSMSCodeSentPage " + str(e))
            return False

    # 判断验证码错误
    async def needResendSMSCode(page):
        try:
            if await page.xpath('//*[@id="app"]/div/div[2]/div[2]/button'):
                element = await page.xpath('//*[@id="app"]/div/div[2]/div[2]/button')
                """
                text = await page.evaluate_on_element(
                    element[0], "(element) => element.textContent"
                )
                """
                if element:
                    text = await page.evaluate(
                        "(element) => element.textContent", element[0]
                    )
                    if text == "获取验证码":
                        return True
            return False
        except Exception as e:
            print("needResendSMSCode " + str(e))
            return False
        
    async def isSendSMSDirectly(page):
        try:
            title = await page.title()
            if title in ['手机语音验证', '手机短信验证']:
                print('需要' + title)
                return True  
            return False
        except Exception as e:
            print("isSendSMSDirectly " + str(e))
            return False

    # 前期操作
    usernum = workList[uid].account
    passwd = workList[uid].password
    sms_sent = False
    print(f"正在登录 {usernum} 的账号")
    browser = await launch(
        {
            "executablePath": chromium_path,  # 定义chromium路径
            "headless": False,  # 设置为非无头模式，即可视化浏览器界面
            "args": (
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ),
        }
    )
    page = await browser.newPage()  # 打开新页面
    await page.setViewport({"width": 360, "height": 640})  # 设置视窗大小
    await page.goto(
        "https://plogin.m.jd.com/login/login?appid=300&returnurl=https%3A%2F%2Fm.jd.com%2F&source=wq_passport"
    )  # 访问京东登录页面
    await typeuser(page, usernum, passwd)  # 进行账号密码登录

    IN_SMS_TIMES = 0
    start_time = datetime.datetime.now()

    """
    page.on("response", lambda rep: asyncio.ensure_future(intercept_response(rep)))
    acpwWrong = False

    async def intercept_response(interceptedResponse):
        if "domlogin" in interceptedResponse.url:
            response = await interceptedResponse.text()
            if "账号或密码不正确" in response:
                print('账号或密码不正确')
                global acpwWrong
                acpwWrong = True
    """

    # 登录状态检查循环
    while True:
        try:
            # -----常规状态-----
            # 登录过程超时
            now_time = datetime.datetime.now()
            print("循环检测中...")
            if (now_time - start_time).total_seconds() > 120:
                print("进入超时分支")
                workList[uid].status = "error"
                workList[uid].msg = "登录超时"
                break

            # 成功获取ck
            elif await page.J("#searchWrapper"):
                print("进入成功获取cookie分支")
                workList[uid].cookie = await getCookie(page)  # 提取ck
                workList[uid].status = "pass"
                break

            # 账号或密码不正确
            elif await isWrongAccountOrPassword(page):
                print("进入账号密码不正确分支")

                workList[uid].status = "error"
                workList[uid].msg = "账号或密码不正确"
                break

            # 过滑块验证
            elif await page.xpath('//*[@id="small_img"]'):
                print("进入过滑块分支")

                workList[uid].status = "pending"
                workList[uid].msg = "正在过滑块检测"
                await verification(page)
                await page.waitFor(3000)  # 等待3秒，等待滑块验证结果

            # 点击图片验证
            elif await page.xpath('//*[@id="captcha_modal"]/div/div[3]/button'):
                print("进入点形状、颜色验证分支")

                workList[uid].status = "pending"
                workList[uid].msg = "正在过形状、颜色检测"
                await verification_shape(page)
                await page.waitFor(3000)  # 等待3秒，等待滑块验证结果

                """
                await page.waitFor(3000)  # 等待3秒
                print("验证出错，正在重试……")
                await page.reload()  # 刷新浏览器
                await typeuser(page, usernum, passwd)  # 进行账号密码登录
                """

            # -----短信验证状态-----
            # <p data-v-4c407d20="" class="sub-title">选择认证方式</p>
            if not sms_sent:
                if await page.J(".sub-title"):
                    print("进入选择短信验证分支")
                    # 用户登录，运行进入短信验证过程
                    if not workList[uid].isAuto:
                        """
                        if SMS_TIMES > 1:
                            if SMS_TIMES > 3:
                                await browser.close()
                                return
                            workList[uid].status = "wrongSMS"
                        else:
                        """
                        workList[uid].status = "SMS"
                        workList[uid].msg = "需要短信验证"

                        # 选择发送短信验证码，获取并输入短信验证码
                        await sendSMS(page)
                        await page.waitFor(3000)
                        await typeSMScode(page, workList, uid)
                        sms_sent = True

                    # 自动续期，不允许进入短信验证过程，亦不会触发下面的验证码错误与超时分支
                    else:
                        workList[uid].status = "error"
                        workList[uid].msg = "自动续期时不能使用短信验证"
                        print("自动续期时不能使用短信验证")
                        break
                elif await isSendSMSDirectly(page):
                    print("进入直接发短信分支")
                
                    if not workList[uid].isAuto:
                        workList[uid].status = "SMS"
                        workList[uid].msg = "需要短信验证"
                        await sendSMSDirectly(page)
                        await page.waitFor(3000)
                        await typeSMScode(page, workList, uid)
                        sms_sent = True

                    else:
                        workList[uid].status = "error"
                        workList[uid].msg = "自动续期时不能使用短信验证"
                        print("自动续期时不能使用短信验证")
                        break
            else:
                # 验证码错误，超时
                if await isStillInSMSCodeSentPage(page):
                    print("进入验证码错误分支")
                    IN_SMS_TIMES += 1
                    if IN_SMS_TIMES % 3 == 0:
                        workList[uid].SMS_CODE = None
                        workList[uid].status = "wrongSMS"
                        workList[uid].msg = "短信验证码错误，请重新输入"
                        await typeSMScode(page, workList, uid)

                elif await needResendSMSCode(page):
                    print("进入验证码超时分支")
                    workList[uid].status = "error"
                    workList[uid].msg = "验证码超时，请重新开始"
                    break

            await asyncio.sleep(1)
        except Exception as e:
            continue
            print("异常退出")
            print (e)
            await browser.close()
            raise e
        
    print("任务完成退出")

    await browser.close()
    await deleteSession(workList, uid)
    return

# 输入账户密码到账户密码输入框
async def typeuser(page, usernum, passwd):
    print("开始输入账号密码")
    await page.waitForSelector(".J_ping.planBLogin")  # 等待元素出现
    await page.click(".J_ping.planBLogin")  # 点击密码登录
    await page.type(
        "#username", usernum, {"delay": random.randint(60, 121)}
    )  # 输入用户名，模拟键盘输入延迟
    await page.type(
        "#pwd", passwd, {"delay": random.randint(100, 151)}
    )  # 输入密码，模拟键盘输入延迟
    await page.waitFor(random.randint(100, 2000))  # 随机等待1-2秒
    await page.click(".policy_tip-checkbox")  # 点击同意
    await page.waitFor(random.randint(100, 2000))  # 随机等待1-2秒
    await page.click(".btn.J_ping.btn-active")  # 点击登录按钮
    await page.waitFor(random.randint(100, 2000))  # 随机等待1-2秒

async def sendSMSDirectly(page):  # 短信验证函数
    async def preSendSMS(page):
        await page.waitForXPath(
            '//*[@id="app"]/div/div[2]/div[2]/button'
        )  # 等获取验证码元素
        await page.waitFor(random.randint(1, 3) * 1000)  # 随机等待1-3秒
        elements = await page.xpath(
            '//*[@id="app"]/div/div[2]/div[2]/button'
        )  # 选择元素
        await elements[0].click()  # 点击元素
        await page.waitFor(7000)  # 等待7秒，等待是否要滑块

    await preSendSMS(page)
    print("开始发送验证码")

    try:
        # 过滑块
        while True:
            if await page.xpath('//*[@id="captcha_modal"]/div/div[3]/div'):
                await verification(page)  # 过滑块

            # 点击图片验证
            elif await page.xpath('//*[@id="captcha_modal"]/div/div[3]/button'):
                await verification_shape(page)

            else:
                break
            
            """elif 其他验证
                await page.waitFor(5000)  # 等待3秒
                print("验证出错，正在重试……")
                await page.reload()  # 刷新浏览器
                await typeuser(page, usernum, passwd)  # 进行账号密码登录
                return
            """
            await page.waitFor(3000)

    except Exception as e:
        raise e
# 选择发送短信验证码
async def sendSMS(page):  # 短信验证函数
    async def preSendSMS(page):
        print("进行发送验证码前置操作")
        await page.waitForXPath(
            '//*[@id="app"]/div/div[2]/div[2]/span/a'
        )  # 等手机短信认证元素  //*[@id="app"]/div/div[2]
        await page.waitFor(random.randint(1, 3) * 1000)  # 随机等待1-3秒
        elements = await page.xpath(
            '//*[@id="app"]/div/div[2]/div[2]/span/a'
        )  # 选择元素
        await elements[0].click()  # 点击元素
        await page.waitForXPath(
            '//*[@id="app"]/div/div[2]/div[2]/button'
        )  # 等获取验证码元素
        await page.waitFor(random.randint(1, 3) * 1000)  # 随机等待1-3秒
        elements = await page.xpath(
            '//*[@id="app"]/div/div[2]/div[2]/button'
        )  # 选择元素
        await elements[0].click()  # 点击元素
        await page.waitFor(3000)  # 等待3秒，等待是否要滑块

    await preSendSMS(page)
    print("开始发送验证码")

    try:
        # 过滑块
        while True:
            if await page.xpath('//*[@id="captcha_modal"]/div/div[3]/div'):
                await verification(page)  # 过滑块

            # 点击图片验证
            elif await page.xpath('//*[@id="captcha_modal"]/div/div[3]/button'):
                await verification_shape(page)

            else:
                break
            
            """elif 其他验证
                await page.waitFor(5000)  # 等待3秒
                print("验证出错，正在重试……")
                await page.reload()  # 刷新浏览器
                await typeuser(page, usernum, passwd)  # 进行账号密码登录
                return
            """
            await page.waitFor(3000)

    except Exception as e:
        raise e


# 输入验证码到验证码输入框
async def typeSMScode(page, workList, uid):
    # 输入验证码，等待输入框元素出现
    print("开始输入验证码")

    async def get_verification_code(workList, uid):  # 获取验证码
        print("开始从全局变量获取验证码")
        retry = 60
        while not workList[uid].SMS_CODE and not retry < 0:
            await asyncio.sleep(1)
            retry -= 1
        if retry < 0:
            workList[uid].status = "error"
            workList[uid].msg = "输入短信验证码超时"
            return

        workList[uid].status = "pending"
        return workList[uid].SMS_CODE

    await page.waitForXPath('//*[@id="app"]/div/div[2]/div[2]/div/input')
    code = await get_verification_code(workList, uid)  # 获取验证码
    # print("获取到验证码：" + str(code))
    if not code:
        return

    workList[uid].status = "pending"
    workList[uid].msg = "正在通过短信验证"
    # 选择输入框元素
    input_elements = await page.xpath('//*[@id="app"]/div/div[2]/div[2]/div/input')

    # 清除验证码输入框中已有的验证码
    try:
        if input_elements:
            input_value = await input_elements[0].getProperty("value")
            if input_value:
                print("清除验证码输入框中已有的验证码")
                """
                await page.evaluate_on_element(
                    input_elements[0],
                    '(element) => element.value = ""',
                )
                """
                await page.evaluate(
                    '(element) => element.value = ""', input_elements[0]
                )
                # await input_elements[0].evaluate('(element) => element.value = ""')
    except Exception as e:
        print("typeSMScode" + str(e))

    await input_elements[0].type(code)  # 输入验证码
    await page.waitForXPath('//*[@id="app"]/div/div[2]/a[1]')  # 等登录按钮元素
    await page.waitFor(random.randint(1, 3) * 1000)  # 随机等待1-3秒
    elements = await page.xpath('//*[@id="app"]/div/div[2]/a[1]')  # 选择元素
    await elements[0].click()  # 点击元素
    await page.waitFor(random.randint(2, 3) * 1000)  # 随机等待2-3秒


# 过滑块
async def verification(page):
    print("开始过滑块")

    async def get_distance():  # 图形处理函数
        img = cv2.imread("image.png", 0)  # 读取全屏截图，灰度模式
        template = cv2.imread("template.png", 0)  # 读取滑块图片，灰度模式
        img = cv2.GaussianBlur(img, (5, 5), 0)  # 图像高斯模糊处理
        template = cv2.GaussianBlur(template, (5, 5), 0)  # 图像高斯模糊处理
        bg_edge = cv2.Canny(img, 100, 200)  # 识别边缘
        cut_edge = cv2.Canny(template, 100, 200)  # 识别边缘
        img = cv2.cvtColor(bg_edge, cv2.COLOR_GRAY2RGB)  # 转换图片格式，不知道是啥
        template = cv2.cvtColor(
            cut_edge, cv2.COLOR_GRAY2RGB
        )  # 转换图片格式，不知道是啥
        res = cv2.matchTemplate(
            img, template, cv2.TM_CCOEFF_NORMED
        )  # 使用模板匹配寻找最佳匹配位置
        value = cv2.minMaxLoc(res)[3][0]  # 获取匹配结果的最小值位置，即为滑块起始位置
        distance = (
            value + 10
        )  # 计算实际滑动距离，这里根据实际页面比例进行调整，+10像素校准算法这傻逼玩意
        return distance

    await page.waitForSelector("#cpc_img")
    image_src = await page.Jeval(
        "#cpc_img", 'el => el.getAttribute("src")'
    )  # 获取滑块背景图的地址
    request.urlretrieve(image_src, "image.png")  # 下载滑块背景图
    width = await page.evaluate(
        '() => { return document.getElementById("cpc_img").clientWidth; }'
    )  # 获取网页的图片尺寸
    height = await page.evaluate(
        '() => { return document.getElementById("cpc_img").clientHeight; }'
    )  # 获取网页的图片尺寸
    image = Image.open("image.png")  # 打开图像
    resized_image = image.resize((width, height))  # 调整图像尺寸
    resized_image.save("image.png")  # 保存调整后的图像
    template_src = await page.Jeval(
        "#small_img", 'el => el.getAttribute("src")'
    )  # 获取滑块图片的地址
    request.urlretrieve(template_src, "template.png")  # 下载滑块图片
    width = await page.evaluate(
        '() => { return document.getElementById("small_img").clientWidth; }'
    )  # 获取网页的图片尺寸
    height = await page.evaluate(
        '() => { return document.getElementById("small_img").clientHeight; }'
    )  # 获取网页的图片尺寸
    image = Image.open("template.png")  # 打开图像
    resized_image = image.resize((width, height))  # 调整图像尺寸
    resized_image.save("template.png")  # 保存调整后的图像
    await page.waitFor(100)  # 等待1秒，确保图片处理完成
    el = await page.querySelector(
        "#captcha_modal > div > div.captcha_footer > div > img"
    )  # 定位到滑块按钮
    box = await el.boundingBox()  # 获取滑块按钮信息
    distance = await get_distance()  # 调用前面定义的get_distance函数计算滑块移动距离
    await page.mouse.move(box["x"] + 10, box["y"] + 10)
    await page.mouse.down()  # 模拟鼠标按下
    await page.mouse.move(
        box["x"] + distance + random.uniform(3, 15), box["y"], {"steps": 10}
    )  # 模拟鼠标拖动，考虑到实际操作中可能存在的轻微误差和波动，加入随机偏移量
    await page.waitFor(
        random.randint(100, 500)
    )  # 随机等待一段时间，模仿人类操作的不确定性
    await page.mouse.move(
        box["x"] + distance, box["y"], {"steps": 10}
    )  # 继续拖动滑块到目标位置
    await page.mouse.up()  # 模拟鼠标释放，完成滑块拖动
    # await page.waitFor(3000)  # 等待3秒，等待滑块验证结果
    print ("过滑块结束")

# 过形状、颜色
async def verification_shape(page):
    print("开始过颜色、形状验证")

    def get_shape_location_by_type(img_path, type: str):
        """
        获取指定形状在图片中的坐标
        """

        def sort_rectangle_vertices(vertices):
            """
            获取左上、右上、右下、左下顺序的坐标
            """
            # 根据 y 坐标对顶点排序
            vertices = sorted(vertices, key=lambda x: x[1])

            # 根据 x 坐标对前两个和后两个顶点分别排序
            top_left, top_right = sorted(vertices[:2], key=lambda x: x[0])
            bottom_left, bottom_right = sorted(vertices[2:], key=lambda x: x[0])

            return [top_left, top_right, bottom_right, bottom_left]

        def is_trapezoid(vertices):
            """
            判断四边形是否为梯形。
            vertices: 四个顶点按顺序排列的列表。
            返回值: 如果是梯形返回 True，否则返回 False。
            """
            top_width = abs(vertices[1][0] - vertices[0][0])
            bottom_width = abs(vertices[2][0] - vertices[3][0])
            return top_width < bottom_width

        img = cv2.imread(img_path)
        imgGray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)  # 转灰度图
        imgBlur = cv2.GaussianBlur(imgGray, (5, 5), 1)  # 高斯模糊
        imgCanny = cv2.Canny(imgBlur, 60, 60)  # Canny算子边缘检测
        contours, hierarchy = cv2.findContours(
            imgCanny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
        )  # 寻找轮廓点
        for obj in contours:
            perimeter = cv2.arcLength(obj, True)  # 计算轮廓周长
            approx = cv2.approxPolyDP(obj, 0.02 * perimeter, True)  # 获取轮廓角点坐标
            CornerNum = len(approx)  # 轮廓角点的数量
            x, y, w, h = cv2.boundingRect(approx)  # 获取坐标值和宽度、高度

            # 轮廓对象分类
            if CornerNum == 3:
                obj_type = "三角形"
            elif CornerNum == 4:
                if w == h:
                    obj_type = "正方形"
                else:
                    approx = sort_rectangle_vertices([vertex[0] for vertex in approx])
                    if is_trapezoid(approx):
                        obj_type = "梯形"
                    else:
                        obj_type = "长方形"
            elif CornerNum == 6:
                obj_type = "六边形"
            elif CornerNum == 8:
                obj_type = "圆形"
            elif CornerNum == 20:
                obj_type = "五角星"
            else:
                obj_type = "未知"

            if obj_type == type:
                # 获取中心点
                center_x, center_y = x + w // 2, y + h // 2
                return center_x, center_y

        # 如果获取不到,则返回空
        return None, None

    def get_shape_location_by_color(img_path, target_color):
        """
        根据颜色获取指定形状在图片中的坐标
        """

        # 读取图像
        image = cv2.imread(img_path)
        # 读取图像并转换为 HSV 色彩空间。
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # 获取目标颜色的范围
        lower, upper = supported_colors[target_color]
        lower = np.array(lower, dtype="uint8")
        upper = np.array(upper, dtype="uint8")

        # 创建掩码并找到轮廓
        mask = cv2.inRange(hsv_image, lower, upper)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # 遍历轮廓并在中心点画点
        for contour in contours:
            # 过滤掉太小的区域
            if cv2.contourArea(contour) > 100:
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    cX = int(M["m10"] / M["m00"])
                    cY = int(M["m01"] / M["m00"])
                    return cX, cY

        return None, None

    def get_word(ocr, img_path):
        image_bytes = open(img_path, "rb").read()
        result = ocr.classification(image_bytes, png_fix=True)
        return result

    def rgba2rgb(rgb_image_path, rgba_img_path):
        """
        rgba图片转rgb
        """
        # 打开一个带透明度的RGBA图像
        rgba_image = Image.open(rgba_img_path)
        # 创建一个白色背景图像
        rgb_image = Image.new("RGB", rgba_image.size, (255, 255, 255))
        # 将RGBA图像粘贴到背景图像上，使用透明度作为蒙版
        rgb_image.paste(rgba_image, (0, 0), rgba_image)
        rgb_image.save(rgb_image_path)

    def save_img(img_path, img_bytes):
        # with open(img_path, 'wb') as file:
        #     file.write(img_bytes)
        # 使用 Pillow 打开图像
        with Image.open(io.BytesIO(img_bytes)) as img:
            # 保存图像到文件
            img.save(img_path)

    def get_img_bytes(img_src: str) -> bytes:
        """
        获取图片的bytes
        """
        img_base64 = re.search(r"base64,(.*)", img_src)
        if img_base64:
            base64_code = img_base64.group(1)
            # print("提取的Base64编码:", base64_code)
            # 解码Base64字符串
            img_bytes = base64.b64decode(base64_code)
            return img_bytes
        else:
            raise "image is empty"

    for i in range(5):
        await page.waitForSelector("div.captcha_footer img")
        image_src = await page.Jeval(
            "#cpc_img", 'el => el.getAttribute("src")'
        )  # 获取大图的地址
        request.urlretrieve(image_src, "shape_image.png")  # 下载大图
        width = await page.evaluate(
            '() => { return document.getElementById("cpc_img").clientWidth; }'
        )  # 获取网页的图片尺寸
        height = await page.evaluate(
            '() => { return document.getElementById("cpc_img").clientHeight; }'
        )  # 获取网页的图片尺寸
        image = Image.open("shape_image.png")  # 打开图像
        resized_image = image.resize((width, height))  # 调整图像尺寸
        resized_image.save("shape_image.png")  # 保存调整后的图像

        # 获取网页的图片位置
        b_image = await page.querySelector("#cpc_img")
        b_image_box = await b_image.boundingBox()
        image_top_left_x = b_image_box["x"]
        image_top_left_y = b_image_box["y"]

        # 获取文字
        word_src = await page.Jeval(
            "div.captcha_footer img", 'el => el.getAttribute("src")'
        )
        # 获取文字图并保存
        word_bytes = get_img_bytes(word_src)
        save_img("rgba_word_img.png", word_bytes)
        # 文字图是RGBA的，有蒙板识别不了，需要转成RGB
        rgba2rgb("rgb_word_img.png", "rgba_word_img.png")
        word = get_word(ocr, "rgb_word_img.png")

        # 获取确定按钮
        button = await page.querySelector("div.captcha_footer button.sure_btn")
        # 获取刷新按钮
        refresh_button = await page.querySelector("div.captcha_header img.jcap_refresh")

        # 判断找颜色
        if word.find("色") > 0:
            target_color = word.split("请选出图中")[1].split("的图形")[0]
            if target_color in supported_colors:
                print(f"正在找{target_color}")
                # 获取点的中心点
                center_x, center_y = get_shape_location_by_color(
                    "shape_image.png", target_color
                )
                if center_x is None and center_y is None:
                    print("识别失败，刷新")
                    await refresh_button.click()
                    await asyncio.sleep(random.uniform(2, 4))
                    continue
                x, y = image_top_left_x + center_x, image_top_left_y + center_y
                await page.mouse.click(x, y)
                await asyncio.sleep(random.uniform(0.5, 2))
                await button.click()
                await asyncio.sleep(random.uniform(0.3, 1))
                # await page.waitFor(3000)  # 等待3秒，等待滑块验证结果
                break
            else:
                print(f"不支持{target_color}，重试")
                await refresh_button.click()
                await asyncio.sleep(random.uniform(2, 4))
                continue

        # 或是找形状
        else:
            shape_type = word.split("请选出图中的")[1]
            if shape_type in supported_types:
                print(f"正在找{shape_type}")
                if shape_type == "圆环":
                    shape_type = shape_type.replace("圆环", "圆形")
                # 获取点的中心点
                center_x, center_y = get_shape_location_by_type(
                    "shape_image.png", shape_type
                )
                if center_x is None and center_y is None:
                    print(f"识别失败,刷新")
                    await refresh_button.click()
                    await asyncio.sleep(random.uniform(2, 4))
                    continue
                # 得到网页上的中心点
                x, y = image_top_left_x + center_x, image_top_left_y + center_y
                # 点击图片
                await page.mouse.click(x, y)
                await asyncio.sleep(random.uniform(0.5, 2))
                # 点击确定
                await button.click()
                await asyncio.sleep(random.uniform(0.3, 1))
                # await page.waitFor(3000)  # 等待3秒，等待滑块验证结果
                break
            else:
                print(f"不支持{shape_type},刷新中......")
                # 刷新
                await refresh_button.click()
                await asyncio.sleep(random.uniform(2, 4))
                continue
    print ("过图形结束")


# 获取并返回ck
async def getCookie(page):
    cookies = await page.cookies()  # 设置cookeis变量，用于下面的搜索
    pt_key = ""  # 初始化变量
    pt_pin = ""  # 初始化变量
    for cookie in cookies:  # 找所有网页所有的cookie数据
        if cookie["name"] == "pt_key":  # 找到pt_key的值
            pt_key = cookie["value"]  # 把值设置到变量pt_key
        elif cookie["name"] == "pt_pin":  # 找到pt_pin的值
            pt_pin = cookie["value"]  # 把值设置到变量pt_pin
    ck = f"pt_key={pt_key};pt_pin={pt_pin};"
    print(f"登录成功 {ck}")
    return ck


# 下载文件
async def download_file(url, file_path):
    timeout = aiohttp.ClientTimeout(total=60000)  # 设置超时时间
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as response:
            with open(file_path, "wb") as file:
                file_size = int(response.headers.get("Content-Length", 0))
                downloaded_size = 0
                chunk_size = 1024
                while True:
                    chunk = await response.content.read(chunk_size)
                    if not chunk:
                        break
                    file.write(chunk)
                    downloaded_size += len(chunk)
                    progress = (downloaded_size / file_size) * 100
                    print(f"已下载{progress:.2f}%...", end="\r")
    print("下载完成，进行解压安装....")


async def main(workList, uid, oocr):
    global ocr
    ocr = oocr

    async def init_chrome():  # 判断chrome是否存在，不存在则下载，仅针对windows
        if platform.system() == "Windows":
            chrome_dir = os.path.join(
                os.environ["USERPROFILE"],
                "AppData",
                "Local",
                "pyppeteer",
                "pyppeteer",
                "local-chromium",
                "588429",
                "chrome-win32",
            )
            chrome_exe = os.path.join(chrome_dir, "chrome.exe")
            chmod_dir = os.path.join(
                os.environ["USERPROFILE"],
                "AppData",
                "Local",
                "pyppeteer",
                "pyppeteer",
                "local-chromium",
                "588429",
                "chrome-win32",
                "chrome-win32",
            )
            if os.path.exists(chrome_exe):
                return chrome_exe
            else:
                print("貌似第一次使用，未找到chrome，正在下载chrome浏览器....")

                # chromeurl = 'http://npm.taobao.org/mirrors/chromium-browser-snapshots/Win_x64/588429/chrome-win32.zip'        #定义下载地址
                chromeurl = "https://mirrors.huaweicloud.com/chromium-browser-snapshots/Win_x64/588429/chrome-win32.zip"  # 定义下载地址
                target_file = "chrome-win.zip"  # 定义下载文件名
                await download_file(chromeurl, target_file)  # 下载
                with zipfile.ZipFile(target_file, "r") as zip_ref:
                    zip_ref.extractall(chrome_dir)
                os.remove(target_file)
                for item in os.listdir(chmod_dir):  # 移动所有文件
                    source_item = os.path.join(chmod_dir, item)
                    destination_item = os.path.join(chrome_dir, item)
                    os.rename(source_item, destination_item)
                print("解压安装完成")
                await asyncio.sleep(1)  # 等待1秒，等待
                return chrome_exe

        elif platform.system() == "Linux":
            chrome_path = os.path.expanduser(
                "~/.local/share/pyppeteer/local-chromium/1181205/chrome-linux/chrome"
            )
            download_path = os.path.expanduser(
                "~/.local/share/pyppeteer/local-chromium/1181205/"
            )
            if os.path.isfile(chrome_path):
                return chrome_path
            else:
                print("貌似第一次使用，未找到chrome，正在下载chrome浏览器....")
                print("文件位于github，请耐心等待，如遇到网络问题可到项目地址手动下载")
                download_url = "https://mirrors.huaweicloud.com/chromium-browser-snapshots/Linux_x64/884014/chrome-linux.zip"
                if not os.path.exists(download_path):  # 如果没有路径就创建路径
                    os.makedirs(download_path, exist_ok=True)  # 创建下载路径
                target_file = os.path.join(
                    download_path, "chrome-linux.zip"
                )  # 定义下载文件路径跟文件名
                await download_file(download_url, target_file)  # 下载
                with zipfile.ZipFile(target_file, "r") as zip_ref:
                    zip_ref.extractall(download_path)
                os.remove(target_file)
                os.chmod(chrome_path, 0o755)
                return chrome_path
        elif platform.system() == "Darwin":
            return "mac"
        else:
            return "unknown"

    chromium_path = await init_chrome()  # 检测初始化chrome
    await logon_main(chromium_path, workList, uid)  # 登录操作，写入ck到文件
    # 删除缓存照片
    os.remove("image.png") if os.path.exists("image.png") else None
    os.remove("template.png") if os.path.exists("template.png") else None
    os.remove("shape_image.png") if os.path.exists("shape_image.png") else None
    os.remove("rgba_word_img.png") if os.path.exists("rgba_word_img.png") else None
    os.remove("rgb_word_img.png") if os.path.exists("rgb_word_img.png") else None
    print("登录完成")
    await asyncio.sleep(10)  # 等待10秒，等待


"""
def start(workList, uid):  # 传入用户信息u
    asyncio.get_event_loop().run_until_complete(
        main(workList, uid)
    )  # 使用异步I/O循环运行main()函数，启动整个自动登录和滑块验证流程。
"""
