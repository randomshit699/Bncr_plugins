/**
 * @author 小九九 t.me/gdot0
 * @description 账号密码登录
 * @origin 小九九
 * @team 小九九
 * @version v1.0.0
 * @name 账密登录
 * @rule ^账密登录$
 * @rule ^(账密登录) ([^\s]+)$
 * @rule ^(账密登录) ([^\s]+) ([^\s]+)$
 * @priority 10000
 * @admin false
 * @public true
 * @disable false
 * @cron 30 30 *\/2 * * *
 * @classification ["Server"]
 */
/*
说明：
1.用户通过触发词登录，可选携带账号或账号和密码为参数，例： 账密登录 13312341234 qwe114515
2.定时检查cookie失效，自动重登
3.在其他插件中通过sysMethod.inline('账密登录 pt_pin')调用，重登指定pin账号

后端使用说明：
0.基于github/svjdck以及github.com/icepage/AutoUpdateJdCookie二改，感谢原作者
1.需要python3.12
2.依赖 pyppeteer Pillow asyncio aiohttp opencv-python ddddocr quart
3.python ./api.py 启动
4.仅Windows环境下测试，理论上linux也可以
*/
//配置
const apiBackend = "http://"; //后台地址，后台代码见附件文件夹，do not end with '/'
const waitTime = 60; //等待用户输入的时间，秒
let smsRetry = 3; //短信验证允许错几次
const ReplyMsgs = {
    //自定义回复词
    serverDown: "服务器失联啦，过会再试",
    timeout: "超时啦，下次动作快一点哦",
    quit: "已退出",
    formatError: "密码可以有空格吗？请检查",
    tooManyFail: "怎么总输错呢，再捣乱要拉黑了哦",
    wrongCode: "验证码错误，请检查后再输入：",
    notifyMsg:
        "账密登录以及自动续登已基本稳定，如遇到bug和报错请反馈\n目前和wx的掉线通知尚未适配，请忽略wx通知，以机器人的通知为准\n为避免滥用，每个账号每天只能使用2次（无论成功与否）",
};


declare const sysMethod: any;
declare const BncrDB: any;
const log4js = require("log4js");
const log = log4js.getLogger("botApi.js");
log.level = "debug";
const got = require("got");
const db = new BncrDB("AccPw");

class NotAutoRenewError extends Error {
    constructor(message) {
        super(message);
        this.name = "AutoRenewError";
    }
}
module.exports = async (s) => {
    const from = s.getFrom();
    const userId = s.getUserId();
    const group = s.getGroupId();

    let pin;
    let isAuto = false;
    let isUser = true;

    if (from == "system") { //由其他插件调用
        isAuto = true;
        pin = s.param(2);
        log.info(`由其他插件调用，开始登录${pin}`);
        for (const pinInDB of await db.keys()) {
            if (pin != pinInDB) continue;
            const rec = await db.get(pinInDB);
            const { account, password, user, platform } = rec;
            try {
                await doLogin(account, password);
            } catch (e) {
                if (e instanceof NotAutoRenewError) {
                    return;
                }
                await sysMethod.push({
                    platform: platform,
                    userId: user,
                    msg: `${pin}账密登录失败了，请重新登录\n失败原因：${e}`,
                    type: "text",
                });
                log.error(`${pin}账密登录失败了，原因${e}`);
                await db.del(pin);
            }
            break;
        }
    } else if (from == "cron") { //定时检查cookie失效
        isAuto = true;
        isUser = false;
        //数据库取出每一条记录
        for (const pin of await db.keys()) {
            if (pin == "usage_lock") continue;
            log.info(`开始检索${pin}是否过期`);

            const rec = await db.get(pin);
            const { account, password, cookie, user, platform } = rec;
            //检查cookie是否过期
            const isLogin = await isLoginByX1a0He(cookie);
            await sysMethod.sleep(3);
            if (isLogin) continue;
            try {
                log.info(`${pin}过期了，开始登录`);
                await doLogin(account, password);
            } catch (e) {
                if (e instanceof NotAutoRenewError) {
                    log.warn(e);
                } else {
                    await sysMethod.push({
                        platform: platform,
                        userId: user,
                        msg: `${pin}账密登录失败了，请重新登录\n失败原因：${e}`,
                        type: "text",
                    });
                    log.error(`${pin}账密登录失败了，原因${e}`);
                    await db.del(pin);
                }
            }

            async function isLoginByX1a0He(cookie) {
                const url = "https://plogin.m.jd.com/cgi-bin/ml/islogin";
                const options = {
                    headers: {
                        Cookie: cookie,
                        referer: "https://h5.m.jd.com/",
                        "User-Agent":
                            "jdapp;iPhone;10.1.2;15.0;network/wifi;Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148;supportJDSHWK/1",
                    },
                    timeout: 10000,
                };
                const data = await got.get(url, options).json();
                if (data) {
                    if (data.islogin === "1") {
                        log.debug(`使用X1a0He写的接口加强检测: Cookie有效\n`);
                        return true;
                    } else if (data.islogin === "0") {
                        log.error(`使用X1a0He写的接口加强检测: Cookie无效`);
                        return false;
                    } else {
                        log.info(data);
                        log.info(`使用X1a0He写的接口加强检测: 未知返回，假设有效\n`);
                        return true;
                    }
                }
            }
        }
    } else { //用户主动登录，可选带一个或两个参数：账号 密码
        await s.reply(ReplyMsgs.notifyMsg);
        if (group != "0") {
            const m = s.getMsgId();
            await s.delMsg(m);
            return s.reply("为了您的账户安全，请私聊机器人使用");
        }
        let lock = await db.get("usage_lock", {});
        lock[userId] = (lock[userId] || 0) + 1;
        await db.set("usage_lock", lock);
        if (lock[userId] > 4) return s.reply("不要捣蛋，再瞎玩就全面拉黑了哦"); //限制单日使用次数
        if (lock[userId] > 2) return s.reply("您今日可用次数已经用完了，请明日再试");
        let account, password;
        if (s.param(3)) {
            account = s.param(2);
            password = s.param(3);
        } else if (s.param(2)) {
            account = s.param(2);
            await s.reply("请输入密码：");
            const pMsg = await s.waitInput(() => {}, waitTime);
            if (!pMsg) return s.reply(ReplyMsgs.timeout);
            password = pMsg.getMsg();
            await s.delMsg(pMsg.getMsgId());
            if (password == "q") return s.reply(ReplyMsgs.quit);
        } else {
            await s.reply("请输入账号：");
            const aMsg = await s.waitInput(() => {}, waitTime);
            if (!aMsg) return s.reply(ReplyMsgs.timeout);
            account = aMsg.getMsg();
            await s.delMsg(aMsg.getMsgId());
            if (account == "q") return s.reply(ReplyMsgs.quit);
            await s.reply("请输入密码：");
            const pMsg = await s.waitInput(() => {}, waitTime);
            if (!pMsg) return s.reply(ReplyMsgs.timeout);
            password = pMsg.getMsg();
            await s.delMsg(pMsg.getMsgId());
            if (password == "q") return s.reply(ReplyMsgs.quit);
        }
        if (password.includes(" ")) return s.reply(ReplyMsgs.formatError);
        try {
            pin = await doLogin(account, password);
        } catch (e) {
            log.error(e);
            await s.reply(e);
        }
    }
    //回复用户登录成功
    if (pin) {
        const maskPin = mask(pin);
        await s.reply(`${maskPin}账密登录成功`);
    }
    /**
     * 登录账号，返回pin
     * @param account
     * @param password
     * @returns pin | false
     */
    async function doLogin(account, password) {
        //主要登录过程
        //提交账号密码
        let res = await callAPI("/login", { id: account, pw: password, isAuto: isAuto });
        if (res?.status != "pass") throw new NotAutoRenewError(ReplyMsgs.serverDown);
        log.debug("phase login:" + res.status);
        const uid = res.uid;

        await s.reply("登录中，请稍等，请勿重复操作...");
        //检查登录结果，获取cookie
        let ckReq = await check(uid);
        log.debug("phase login:" + ckReq);
        const cookie = ckReq.cookie;
        const pin = getPinByCk(cookie);

        //存储到数据库
        let dbStruct = {
            account: account,
            password: password,
            user: userId,
            platform: from,
            cookie: cookie,
        };
        if (!isAuto) {
            await db.set(pin, dbStruct);
        } else {
            const oldStruct = await db.get(pin, {
                user: "debug",
                platform: "debug",
            });
            dbStruct.user = oldStruct.user;
            dbStruct.platform = oldStruct.platform;
            await db.set(pin, dbStruct);
        }

        //调用老登录
        if (isUser) {
            await s.inlineSugar(cookie);
        } else {
            await sysMethod.inline(cookie);
        }
        return pin;
    }
    async function SMS(uid, smsCode) {
        //发送验证码
        let res = await callAPI("/sms", { uid: uid, code: smsCode });
        if (res.status == "error") throw new Error("短信验证失败：" + res.msg);
    }
    //获取后台处理的最终状态，处理短信验证与验证码错误的情况，成功=返回响应包，失败=throw Error
    async function check(uid, retry = 3) {
        await sysMethod.sleep(5);
        log.debug("phase check:" + uid);
        retry -= 1;
        let ret;
        if (retry < 0) throw new Error(ReplyMsgs.tooManyFail);
        const checkResult = await checkActualStatus(uid);
        switch (checkResult.status) {
            case "SMS":
                if (isAuto) throw new Error("自动续期失败，需要短信验证");
                await s.reply("需要短信验证，请输入短信验证码：");
                break;
            case "wrongSMS":
                await s.reply(ReplyMsgs.wrongCode);
                break;
            case "pass":
                ret = checkResult;
                return ret;
        }
        //验证码输入
        const smsMsg = await s.waitInput((m) => {
            const msg = m.getMsg();
            //if (msg == "q") return;
            if (msg.length != 6) return m.again(ReplyMsgs.wrongCode);
        }, waitTime);
        if (!smsMsg) throw new Error(ReplyMsgs.timeout);
        const smsCode = smsMsg.getMsg();
        if (smsCode == "q") throw new Error(ReplyMsgs.quit);
        await SMS(uid, smsCode);

        ret = await check(uid, retry);
        return ret;
    }
    //检查后台处理状态，排除error和pending状态获取有效结果
    async function checkActualStatus(uid) {
        //log.debug("phase checkActualStatus:" + uid);
        let retry = 18;
        while (retry) {
            let checkr = await callAPI("/check", { uid: uid });
            log.debug("phase checkActualStatus retry:" + retry + " result:" + JSON.stringify(checkr, null, 2));
            if (checkr.status == "error") {
                throw new Error(checkr.msg);
            }
            if (checkr.status != "pending") {
                return checkr;
            }
            retry -= 1;
            await sysMethod.sleep(7);
        }
        throw new Error("处理账号超时，可能无法通过此方法登录");
    }
    //调用api，排除异常请求的情况
    async function callAPI(uri = "/", params = {}) {
        log.debug("phase callAPI:" + JSON.stringify(params));

        const url = apiBackend + uri;
        const opt = {
            json: params,
            timeout: 10000,
        };
        try {
            const res = await got.post(url, opt).json();
            //const req = await got.post(url, opt);
            //const res = req.json();
            if (res) {
                return res;
            } else {
                throw new Error();
            }
        } catch (e) {
            log.info(e);
            throw new NotAutoRenewError(ReplyMsgs.serverDown);
        }
    }
    /**
     * 获取ck的pin
     * @param {*} ck
     * @returns
     */
    function getPinByCk(ck) {
        if (!ck) throw new NotAutoRenewError(`未获取到ck`);

        const match = ck.match(/(?<=(pt_pin|pin)=).*?(?=;|$)/);
        if (match) {
            return match[0];
        }
        throw new NotAutoRenewError(`未获取到pin ${ck}`);
    }
    function mask(text) {
        if (text.length <= 4) {
            return text;
        }
        const start = text.slice(0, 2);
        const end = text.slice(-2);
        return start + "***" + end;
    }
};
