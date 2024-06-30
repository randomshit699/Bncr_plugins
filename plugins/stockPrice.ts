/**
 * @author 小九九 t.me/gdot0
 * @description 查大A与美股股价，持仓，盈利(浮) 
 * @origin 小九九
 * @team 小九九
 * @version v1.0.0
 * @name stockPrice
 * @rule ^(stk) ?(help)?$
 * @rule ^(add) ([shzbjk]{0,2}[0-9]{5,6}) ?(-?\d+(\.\d+)? \d+)?$
 * @rule ^(add) ([_a-zA-Z]{1,9}) ?(-?\d+(\.\d+)? \d+)?$
 * @rule ^(buy) ([shzbjk]{0,2}[0-9]{5,6}) (-?\d+(\.\d+)? \d+)$
 * @rule ^(buy) ([_a-zA-Z]{1,9}) (-?\d+(\.\d+)? \d+)$
 * @rule ^(sell) ([shzbjk]{0,2}[0-9]{5,6}) (-?\d+(\.\d+)? \d+)$
 * @rule ^(sell) ([_a-zA-Z]{1,9}) (-?\d+(\.\d+)? \d+)$
 * @rule ^(del) ([shzbjk]{0,2}[0-9]{5,6})$
 * @rule ^(del) ([_a-zA-Z]{1,9})$
 * @rule ^(edit) ([shzbjk]{0,2}[0-9]{5,6}) (-?\d+(\.\d+)? \d+)$
 * @rule ^(edit) ([_a-zA-Z]{1,9}) (-?\d+(\.\d+)? \d+)$
 * @priority 10000
 * @admin false
 * @disable false
 */
/*
功能：
    0.stk help 显示帮助词
    1.stk 展示自选股与盈利
    2.add uid cost? hold? 添加一支票到自选股，uid是代码（例：600066，aapl或sh600066，gb_aapl） cost是成本价，hold是持仓（整数）
    3.buy|sell uid cost share|hold 买入|卖出一支票
    4.del uid 在自选股中删除一支票
    5.edit uid cost hold 修改持仓记录
    TODO:
    1. 根据股票名查询代码 //没找到接口
    2. 个股、账户总盈亏统计（现在是清仓时利润归零）
    3. 计算手续费
    5. convert text to picture for better view  //原意是想用canvas画一个的，但是docker环境内部不支持，有实力的自己实体机搭个接口吧
    6. 一次添加多支股票到自选股 add uid,uid,uid...
*/
const stkInPic = false;
const HELP = `stk 展示自选股与盈利
add uid cost? hold? 添加一支票到自选股
buy|sell uid cost share|hold 买入|卖出一支票
del uid 在自选股中删除一支票
edit uid cost hold 修改持仓记录
注：uid=股票代码（例：600066，aapl或sh600066，gb_aapl）
cost=成本价
hold|share=持仓（整数）`;

const got = require("got");
const iconv = require("iconv-lite");
//const { v4: uuidv4 } = require("uuid");
/*
import { Canvas } from "canvas";
import Table2canvas from "table2canvas";
import fs from "fs";
*/
//import { CanvasTable, CTConfig } from "canvas-table";
//import { createCanvas, registerFont } from "canvas";
//registerFont("/bncr/BncrData/public/simsunb.ttf", { family: "simsun" });

const stkdb = new BncrDB("stockDB");
class stk {
    name = "";
    currSign = "";
    uid = "";
    id = "";
    cost = 0;
    hold = 0;
    price = 0;
    profit = 0;
    profitPercent = 0;
    constructor(id = "", cost = 0, hold = 0, dbopt = {}) {
        if (Object.keys(dbopt).length === 0) {
            this.name = "";
            const market = this.deciMarketSign(id);
            this.currSign = market[0] ? market[2] : "";
            this.uid = market[0] ? market[0] : "";
            this.id = market[0] ? market[1] : "";
            this.cost = cost;
            this.hold = hold;
            this.price = 0;
            this.profit = 0;
            this.profitPercent = 0;
        } else {
            this.name = dbopt.name;
            this.currSign = dbopt.currSign;
            this.uid = dbopt.uid;
            this.id = dbopt.id;
            this.cost = dbopt.cost;
            this.hold = dbopt.hold;
            this.price = dbopt.price;
            this.profit = dbopt.profit;
            this.profitPercent = dbopt.profitPercent;
        }
    }

    deciMarketSign(id) {
        if (/^((sh)|(sz)|(bj))\d{6}$/.test(id) || /^hk\d{6}$/.test(id)) return [id, id.slice(2), "￥"];
        else if (/^gb_.*?$/.test(id)) return [id, id.slice(3), "＄"];
        else if (/^\d+$/.test(id)) return [this.signChinaMarket(id), id, "￥"];
        else return [this.signUSMarket(id), id, "$"];
    }
    signChinaMarket(id) {
        if (/^\d{5}$/.test(id)) return "hk" + id;
        else if (/^6\d{5}$/.test(id) || /^90\d{4}$/.test(id)) return "sh" + id;
        else if (/^[03]\d{5}$/.test(id)) return "sz" + id;
        else if (/^92\d{4}$/.test(id)) return "bj" + id;
        else return;
    }
    signUSMarket(id) {
        const vid = id.toLowerCase();
        return "gb_" + vid;
    }

    buy(cost, share) {
        if (this.hold == 0) this.profit = 0;
        this.cost = (this.cost * this.hold + cost * share) / (this.hold + share);
        this.hold += share;
        getProfit(this);
    }
    sell(cost, share) {
        if (this.hold == share) {
            this.profit = this.cost * this.hold;
            this.cost = 0;
            this.hold = 0;
        } else if (this.hold > share) {
            this.cost = (this.cost * this.hold - cost * share) / (this.hold - share);
            this.hold -= share;
            getProfit(this);
        } else {
            throw new Error("持仓不足");
        }
    }
}

/**
 *
 * @param {string} stk.uid
 * @returns [名字,今开盘,昨收盘,现价,今最高,今最低,买一价,卖一价,成交量,成交额,买一量,买一价,买二量,买二价,买三量,买三价,买四量,买四价,买五量,买五价,卖一量,卖一价,卖二量,卖二价,卖三量,卖三价,卖四量,卖四价,卖五量,卖五价,日期,时间,00]
 * @returns i.e. [航天科技,8.310,8.250,8.640,8.740,8.240,8.640,8.650,37090241,316262549.770,216190,8.640,120000,8.630,109345,8.620,142990,8.610,57500,8.600,306400,8.650,99000,8.660,50901,8.670,209904,8.680,83600,8.690,2024-05-31,15:00:00,00]
 */
async function callAPI(uid) {
    const url = "https://hq.sinajs.cn/list=" + uid;
    const opt = {
        retry: {
            limit: 3,
            statusCodes: [408, 500, 502, 503, 504],
            delay: ({ attemptCount }) => {
                // 自定义延迟函数，这里简单实现了一个指数退避策略
                return Math.pow(2, attemptCount) * 1000; // 每次重试间隔翻倍，单位是毫秒
            },
        },
        timeout: 5000,
        responseType: "buffer",
        headers: {
            Referer: "https://finance.sina.com.cn",
            "Content-Type": "text/html; charset=utf-8",
        },
    };
    const oreq = await got.get(url, opt);
    const req = iconv.decode(oreq.body, "gbk");
    let data = req.match(/"([^"]*)"/)[0];
    data = data.slice(1, -1).split(",");
    return data;
}
/**
 * init a new stock instance
 * @param {string} id
 * @param {int} cost
 * @param {int} hold
 * @returns class stk || throw Error(string)
 */
async function newStock(id, cost = 0, hold = 0) {
    cost = Number(cost);
    hold = Number(hold);
    let stock = new stk(id, cost, hold);
    stock = await initStock(stock);
    return stock;
}
async function initStock(stk) {
    const data = await callAPI(stk.uid);
    if (data && data != "") {
        stk.name = data[0];
        await getCurrProfit(stk, data);
        return stk;
    } else {
        throw new Error("错误的股票代码");
    }
}
async function getCurrPrice(stkIns, oData = "") {
    const data = oData ? oData : await callAPI(stkIns.uid);
    if (data && data != "") {
        if (stkIns.currSign == "￥") {
            stkIns.price = parseFloat(data[3]);
            return parseFloat(data[3]);
        } else {
            stkIns.price = parseFloat(data[1]);
            return parseFloat(data[1]);
        }
    }
    throw new Error("没有获取到现价");
}
function getProfit(stkIns) {
    if (stkIns.hold && stkIns.cost) {
        stkIns.profit = (stkIns.price - stkIns.cost) * stkIns.hold;
        stkIns.profitPercent = (stkIns.price / stkIns.cost - 1) * 100;
    } else {
        stkIns.profit = 0;
        stkIns.profitPercent = 0;
    }
}
async function getCurrProfit(stkIns, oData = "") {
    await getCurrPrice(stkIns, oData);
    getProfit(stkIns);
    return stkIns.profit;
}
async function updateStockArr(stkArr) {
    let uidArr = [];
    for (const stk of stkArr) {
        uidArr.push(stk.uid);
    }
    const resArr = await callAPIArr(uidArr);
    for (let i = 0; i < stkArr.length; i++) {
        if (resArr[i][0].length > 4) resArr[i][0] = resArr[i][0].slice(0, 4);
        stkArr[i].name = resArr[i][0];
        await getCurrProfit(stkArr[i], resArr[i]);
    }
    /**
     *
     * @param {stringArr} uidArr ["sz000001","sh600001","bj920001","hk10000","gb_appl"]
     * @returns [[stock1],[stock2],[stock3],[stock4],[stock5]]
     */
    async function callAPIArr(uidArr) {
        const uid = uidArr.join(",");
        const url = "https://hq.sinajs.cn/list=" + uid;
        const opt = {
            retry: {
                limit: 3,
                statusCodes: [408, 500, 502, 503, 504],
                delay: ({ attemptCount }) => {
                    // 自定义延迟函数，这里简单实现了一个指数退避策略
                    return Math.pow(2, attemptCount) * 1000; // 每次重试间隔翻倍，单位是毫秒
                },
            },
            timeout: 5000,
            responseType: "buffer",
            headers: {
                Referer: "https://finance.sina.com.cn",
                "Content-Type": "text/html; charset=utf-8",
            },
        };
        const oreq = await got.get(url, opt);
        const req = iconv.decode(oreq.body, "gbk");
        let dataArr = req.match(/"([^"]*)"/g);
        dataArr = dataArr.map((v, i) => {
            v = v.slice(1, -1);
            v = v.split(",");
            return v;
        });
        return dataArr;
    }
}

module.exports = async (s) => {
    const from = s.getFrom();
    const userId = s.getUserId();
    const userKey = `${from}:${userId}`;
    /**
     *
     * @param {string} operator stk || add || buy || sell || del || edit
     * @param {int} id id || uid
     * @param {int} cost_hold cost(space)hold
     * @returns
     */
    if (s.param(3)) {
        const stkid = s.param(2);
        let [cost, hold] = s.param(3).split(" ");
        cost = Number(cost);
        hold = Number(hold);
        //if (hold != parseInt(hold)) return s.reply('股份数必须是整数')
        if (s.param(1) == "buy") {
            await buystk(stkid, cost, hold); // hold=share
        } else if (s.param(1) == "sell") {
            await sellstk(stkid, cost, hold);
        } else if (s.param(1) == "edit") {
            await editstk(stkid, cost, hold);
        } else await addstk(stkid, cost, hold);
    } else if (s.param(2)) {
        const stkid = s.param(2);
        if (s.param(1) == "del") {
            await delstk(stkid);
        } else if (s.param(2) == "help") {
            await s.reply(HELP);
        } else await addstk(stkid);
    } else await showstk();

    async function showstk() {
        const db = await stkdb.get(userKey);
        if (!db || !Array.isArray(db)) {
            return s.reply(`请先'add id'`);
        }
        let stkInsArr = [];
        for (const db_stkIns of db) {
            let stkIns = new stk("", 0, 0, db_stkIns);
            stkInsArr.push(stkIns);
        }
        await updateStockArr(stkInsArr);
        await stkdb.set(userKey, stkInsArr);

        if (!stkInPic) {
            //msg = `代码\t名称\t现价\t盈亏`;
            //let msg = `代码\t名称\t现价\t持仓\t盈亏`;
            let msg = `名称\t      现价\t       盈亏`;
            for (const stk of stkInsArr) {
                const op = stk.profit > 0 ? "+" : "";
                //msg += `\n${stk.id}\t${stk.name}\t${stk.price}${stk.currSign}\t${op}${stk.profit.toFixed(2)}[${op}${stk.profitPercent.toFixed(2)}%]`;
                //msg += `\n${stk.id}\t${stk.name}\t${stk.price}${stk.currSign}\t${stk.hold}\t${op}${stk.profit.toFixed(2)}[${op}${stk.profitPercent.toFixed(2)}%]`;
                const _3price = parseInt(stk.price) >= 100 ? stk.price.toFixed(1) : stk.price.toFixed(2);
                const _kprofit = Math.abs(parseInt(stk.profit)) >= 1000 ? `${(stk.profit / 1000).toFixed(2)}k ` : stk.profit.toFixed(2);
                msg += `\n${stk.name}\t${" ".repeat(12 - 3 * stk.name.length)} ${_3price}${stk.currSign}\t ${" ".repeat(8 - 2 * (_3price.length - 1))}${op}${_kprofit}[${op}${stk.profitPercent.toFixed(0)}%]`;
                //msg = await convText2Pic(msg)
            }
            return s.reply(msg);
        } /*else {
            let data = [];
            for (const stk of stkInsArr) {
                const op = stk.profit > 0 ? "+" : "";
                const d = [stk.id, stk.name, stk.price + stk.currSign, stk.hold.toFixed(0), op + stk.profit.toFixed(2) + "[" + stk.profitPercent.toFixed(2) + "%]", stk.profit];
                //const d = [stk.id, stk.name, stk.price + stk.currSign, stk.hold, op + stk.profit + "[" + stk.profitPercent + "%]", stk.profit];
                data.push(d);
            }
            const opic: String = await render(data);
            const pic = opic.replace("/bncr/BncrData", "http://192.168.0.106:9096");
            return s.reply({
                type: "image", // video
                path: pic,
            });
        }*/
        /*
        async function render(data): Promise<String> {
            const canvas = createCanvas(400, 200);
            let cdata: CTData = [];
            for (let stkIns of data) {
                if (stkIns[5] >= 0) {
                    stkIns[4] = { value: stkIns[4], color: "#c85862" };
                } else {
                    stkIns[4] = { value: stkIns[4], color: "#a0c69d" };
                }
                stkIns.splice(5, 1);
                cdata.push(stkIns);
            }
            const ccolumns: CTColumns[] = [
                { title: "代码", options: { textAlign: "center", fontFamily: "simsun" } },
                { title: "名称", options: { textAlign: "center", fontFamily: "simsun" } },
                { title: "现价", options: { textAlign: "center", fontFamily: "simsun" } },
                { title: "持仓", options: { textAlign: "center", fontFamily: "simsun" } },
                { title: "盈亏", options: { textAlign: "center", fontFamily: "simsun" } },
            ];
            const coptions: CTOptions = {
                borders: {
                    column: undefined,
                    header: undefined,
                    table: { width: 1, color: "#aaa" },
                },
                fit: true,
                header: {
                    fontFamily: "simsun",
                }, // set to false to hide the header
                cell: {
                    fontFamily: "simsun",
                },
                subtitle: {
                    fontFamily: "simsun",
                },
                title: {
                    fontFamily: "simsun",
                },
            };
            const config: CTConfig = {
                data: cdata,
                columns: ccolumns,
                options: coptions,
            };
            const ct = new CanvasTable(canvas, config);
            await ct.generateTable();
            const path = "/bncr/BncrData/public/" + userKey.replace(":", "-") + uuidv4() + ".png";
            await ct.renderToFile(path);
            return path;
        }*/
        /*
        function render(data) {
            const columns = [
                { title: "代码", dataIndex: "uid", textAlign: "center", textColor: "black" },
                { title: "名称", dataIndex: "name", textAlign: "center", textColor: "black" },
                { title: "现价", dataIndex: "price", textAlign: "center", textColor: "black" },
                { title: "持仓", dataIndex: "hold", textAlign: "center", textColor: "black" },
                { title: "盈亏", dataIndex: "profit", textAlign: "center", textColor: "black" },
            ];
            let dataSource: any[] = [];
            for (const stkIns of data) {
                const s = {
                    uid: stkIns[0],
                    name: stkIns[1],
                    price: stkIns[2],
                    hold: stkIns[3],
                    profit: stkIns[4],
                };
                dataSource.push(s);
            }
            const table = new Table2canvas({
                canvas: new Canvas(2, 2),
                columns: columns,
                dataSource: dataSource,
                bgColor: "#fff",
            });
            const buffer = table.canvas.toBuffer();
            const path = "/bncr/BncrData/public/" + userKey + ".png";
            fs.writeFileSync(path, buffer);
            return path;
        }*/
    }

    async function editstk(stkid, cost, hold) {
        let db: Array<any> = await stkdb.get(userKey);
        if (!db || !Array.isArray(db)) {
            db = [];
        }
        for (const key in db) {
            if (db[key].id == stkid || db[key].uid == stkid) {
                const name = db[key].name;
                db[key].cost = cost;
                db[key].hold = hold;
                await stkdb.set(userKey, db);
                return s.reply(`已修改${name}的持仓数据`);
            }
        }
        return s.reply("不能修改未添加的股票");
    }
    async function delstk(stkid) {
        let db: Array<any> = await stkdb.get(userKey);
        if (!db || !Array.isArray(db)) {
            db = [];
        }
        for (const key in db) {
            if (db[key].id == stkid || db[key].uid == stkid) {
                const name = db[key].name;
                if (db[key].hold != 0) {
                    await s.reply(`${name}当前仍有持仓，确定要删除吗？y/n`);
                    let yn = await s.waitInput(() => {}, 60);
                    yn = yn.getMsg();
                    if (yn != "y") return s.reply("已取消");
                }
                db.splice(Number(key), 1);
                await stkdb.set(userKey, db);
                return s.reply(`已删除${name}`);
            }
        }
        return s.reply("不能删除未添加的股票");
    }
    async function buystk(stkid, cost = 0, share = 0) {
        let db: Array<any> = await stkdb.get(userKey);
        if (!db || !Array.isArray(db)) {
            db = [];
        }
        let stkIns;
        for (const key in db) {
            if (db[key].id == stkid || db[key].uid == stkid) {
                stkIns = new stk("", 0, 0, db[key]);
                stkIns.buy(cost, share);
                db[key] = stkIns;
                await stkdb.set(userKey, db);
                return s.reply(`已购买${stkIns.name}${share}股，现在以${stkIns.cost.toFixed(2)}${stkIns.currSign}成本持有${stkIns.hold}股`);
            }
        }
        await addstk(stkid, cost, share);
    }
    async function sellstk(stkid, cost = 0, hold = 0) {
        let db: Array<any> = await stkdb.get(userKey);
        if (!db || !Array.isArray(db)) {
            db = [];
        }
        for (const key in db) {
            if (db[key].id == stkid || db[key].uid == stkid) {
                let stkIns = new stk("", 0, 0, db[key]);
                try {
                    stkIns.sell(cost, hold);
                } catch (e) {
                    return s.reply(e);
                }
                db[key] = stkIns;
                await stkdb.set(userKey, db);
                return s.reply(`已出售${stkIns.name}${hold}股，现在以${stkIns.cost.toFixed(2)}${stkIns.currSign}成本持有${stkIns.hold}股`);
            }
        }
        return s.reply("不能出售未持有的股票");
    }
    async function addstk(stkid, cost = 0, hold = 0) {
        try {
            const stock = await newStock(stkid, cost, hold);
            let db: Array<any> = await stkdb.get(userKey);
            if (!Array.isArray(db)) {
                db = [];
            } else {
                for (const rec of db) {
                    if (rec.uid == stock.uid) return s.reply(`已经添加过${stock.name}了`);
                }
            }
            let profitMsg;
            if (cost != 0) {
                profitMsg = stock.profit >= 0 ? "，您盈利" : "，您亏损";
                profitMsg += `${Math.abs(stock.profit).toFixed(2)}${stock.currSign}`;
            }
            await s.reply(`成功添加${stock.name}，现价${stock.price}${stock.currSign}${profitMsg ? profitMsg : ""}`);
            delete stock.price;
            delete stock.profit;
            delete stock.profitPercent;
            db.push(stock);
            await stkdb.set(userKey, db);
        } catch (e) {
            await s.reply(e);
        }
    }
};
