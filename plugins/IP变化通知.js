/**
 * @author IP变化通知
 * @name IP变化通知
 * @team 小寒寒-小九九二改
 * @origin 小寒寒-小九九二改
 * @version 1.0.2
 * @rule ^IP变化通知$
 * @description IP变化通知，变化后自动执行代理“更换白名单”命令，多线路的请勿使用，增加更换dynv6 ddns功能
 * @admin true
 * @public true
 * @priority 1000
 * @cron 0 *\/3 * * * *
 * @classification ["Server"]
 */
const log4js = require("log4js");
const log = log4js.getLogger("ipChange.js");
log.level = "info";

const urls = ["https://4.ipw.cn/", "https://ip.3322.net/", "https://cdid.c-ctrip.com/model-poc2/h"]; //多个api避免某一个失效导致脚本失败
const urlv6 = "http://"; //自备查ipv6地址的接口
const domains = [""]; //你的ddns域名，仅支持dynv6

const got = require("got");

module.exports = async (s) => {
    let sL = [];
    const djunDB = new BncrDB("djunDB");
    let ip = await djunDB.get("local_ip");
    let newip;
    for (let url of urls) {
        try {
            const req = await got.get(url);
            //todo: if json/multiLine
            const ipPattern = /(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})/g;
            newip = req.body.match(ipPattern)[0];
        } catch (e) {
            log.error("api:" + url + "failed, try next one");
        }
        if (newip) break;
    }
    if (!newip) log.error(`failed to fetch ipv4 on all sites`);
    if (newip.split(".").length != 4) {
        return;
    }
    if (ip) {
        if (newip && newip != ip) {
            console.log(newip);
            await djunDB.set("local_ip", newip);
            await sysMethod.pushAdmin({
                platform: ["tgBot", "qq"],
                type: "text",
                msg: "【IP变更通知】\n上次IP：" + ip + "\n当前IP：" + newip + "\n开始执行【更换白名单】命令",
            });
            await sysMethod.inline("更换白名单"); //Doraemon的
            //await sysMethod.inline("chwlst"); //我的
        } else {
            await djunDB.set("local_ip", newip);
        }
    }

    let ipv6 = await djunDB.get("local_ipv6", "");
    let newipv6;
    try {
        const req = await got.get(urlv6);
        if (req) newipv6 = req.body;
    } catch {
        log.error("get ipv6 addr failed");
    }
    if (newipv6 && newipv6 != ipv6) {
        log.info(newipv6);
        await djunDB.set("local_ipv6", newipv6);
        await sysMethod.pushAdmin({
            platform: ["tgBot", "qq"],
            type: "text",
            msg: "【IPv6变更通知】\n上次IP：" + ipv6 + "\n当前IP：" + newipv6 + "\n开始更换ddns",
        });
        await dynv6(newipv6, domains, 5);
        let msg = `以下域名成功更换ddns(${sL.length}/${domains.length})：`;
        for (s of sL) {
            msg += `\n${s}`;
        }
        await sysMethod.pushAdmin({
            platform: ["tgBot", "qq"],
            type: "text",
            msg: msg,
        });
    }

    async function dynv6(newipv6, domains, retry = 5) {
        retry -= 1;
        if (retry < 0) return log.error(`${domains[0]}更换ipv6解析失败`);
        for (domain of domains) {
            const url = "https://dynv6.com/api/update?zone=" + domain + "&token=xxx&ipv6=" + newipv6; //填token

            try {
                const req = await got.get(url, { timeout: 60000 });
                if (req.body == "addresses updated") {
                    log.info(`${domain}更换ipv6解析成功`);
                    sL.push(domain);
                }
            } catch {
                log.error(`${domain}更换ipv6解析失败，重试第${5 - retry}次`);
                await dynv6(newipv6, [domain], retry);
            }
        }
    }
};
