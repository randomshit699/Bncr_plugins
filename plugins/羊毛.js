/**
 * @author 小九九 t.me/gdot0
 * @name 羊毛
 * @origin 小九九
 * @team 小九九
 * @version 1.0.2
 * @description 借助QLTools api上传ck，QLTools项目：https://t.me/qltools
 * @rule ^(羊毛|refwool)$
 * @priority 1
 * @public true
 * @disable false
 * @admin false
 * @cron 0 0 7 *\/7 * *
 * @classification ["Server"]
 */

/*
命令解释：
refwool: （管理员）刷新文字缓存，因为QLTools的api还挺慢的
羊毛：（用户）开始上传ck
update history:
1.0.0 [initial]:
    get configs from QLTools
    cache texts
    upload CK
1.0.1 [add]:
    cache/show simpleGuide
    extract simpleGuide from html
    parse markdown to html
1.0.2 [fix]
    fix when simpleGuide is in the smae section of woolName

next plan: 

*/

// --configuration--
const QLToolsURL = "http://"; //青龙Tools前端地址
const appendGuidanceURL = true; //是否附加教程文章地址
const guidanceURL = 'https://example.site/dir/page/#${wool.envRemark}' //教程文章地址，wool.envRemark==羊毛名，wool.envName==ck名
const loglevel = "info"; //debug,info,warn 
const simpleGuide = true; //是否启用附加简化教程
const simpleGuideFilePath = 'https://example.site/dir/page'; //简化教程文件地址(网络地址(http(s))或本地地址(/)，html或markdown，markdown会自动解析为html)
const articleFrame = 'body > article > div'; //简化教程在所在页面的哪个等级（以edge浏览器为例，f12 > 元素 > 选中元素后右键 > 复制 > 复制selector）
const whereIsWoolName = 'h1'; //羊毛名称在Frame内的哪个等级（h1,h2,div,blockquote,p...)
const whereIsSimpleGuide = 'div > p'; //简化教程在Frame的哪个等级(只支持查找同级第一个)
async function changeWoolName(wool) { //自定义wool变量，供guidanceURL调用，如果你的教程网址用得上羊毛名且教程中的名字和羊毛名不一样
    //for example
    wool.envRemark = wool.envRemark //+'Customed' //修改原有值
    wool.envNameCustom = 'Topic:' + wool.envName //新增值
    //any other Values/Rules you need
    return wool;
}

// --coding--
const axios = require('axios');
const fs = require('fs');
//const he = require('he');  
//const path = require('path');  
const winston = require('winston');
const QLToolsDB = new BncrDB("qltools");
const cacheDB = new BncrDB('qltoolsTextCache');
const logger = winston.createLogger({
    level: loglevel, // 设置日志级别为 info，这将记录 info、warn 和 error 级别的日志  
    format: winston.format.combine(
        winston.format.timestamp(), // 添加时间戳  
        winston.format.printf(({
            timestamp,
            level,
            message
        }) => {
            return `${timestamp} ${level}: ${message}`;
        })
    ),
    transports: [
        new winston.transports.Console()
    ]
});

module.exports = async (s) => {
    // --main--
    if (s.getFrom() == "cron") {
        logger.info('定时自动刷新缓存');
        doCache();
    } else if (s.param(1) === 'refwool') {
        if (!(await s.isAdmin())) return;
        logger.info('管理员手动刷新缓存');
        doCache();
    } else {
        logger.info('用户开始提交ck');

        const woolKeys = await cacheDB.get('woolKeys');
        await s.reply(await cacheDB.get('woolListText'));
        let selection = await s.waitInput(async (s) => {
            const msg = s.getMsg();
            if (await checkInput(s)) {
                //logger.debug(typeof(msg));
                if (woolKeys.includes(msg)) {
                    const wool = await QLToolsDB.get(msg);
                    await s.reply('请输入“' + wool.envRemark + '”的CK值' + (appendGuidanceURL ? '\n抓包教程参看：' + eval('`' + guidanceURL + '`') : '') + (simpleGuide ? '\n简要教程：' + await makeSimpleGuide(wool.envRemark) : ''));
                    await s.waitInput(async (s) => {
                        s.delMsg(s.getMsgId());
                        if (await checkInput(s)) {
                            await uploadCK(wool.serverId, wool.envName, await s.getMsg());
                        }
                    }, 60);

                } else {
                    return await s.again(`序号有误，请重新输入正确的序号`);
                }
            }
        }, 60);
    }
    // --functions--
    async function makeSimpleGuide(woolName) { //提取简化教程缓存，生成文字
        const msg = await cacheDB.get(woolName);
        return msg
    }
    async function cacheSimpleGuide() { //缓存简化教程
        let filepath = '';
        if (isURL(simpleGuideFilePath)) {
            const downloadPath = '/bncr/BncrData/public/qltoolsSimpleGuide'
            await axios({
                method: 'get',
                url: simpleGuideFilePath,
                responseType: 'stream' // 以流的形式获取响应数据  
            }).then(response => {
                const writer = fs.createWriteStream(downloadPath); // 创建写入流  
                response.data.pipe(writer); // 将响应流数据写入到文件  
                writer.on('finish', () => {
                    logger.debug(`文件已成功下载到 ${downloadPath}`);
                });

                writer.on('error', err => {
                    logger.error('写入文件时发生错误:', err);
                });
            }).catch(error => {
                logger.error('下载文件时发生错误:', error);
            });
            filepath = downloadPath;
        } else {
            filepath = simpleGuideFilePath;
        }
        let html;
        if (!isHTML(filepath)) {
            html = await parseMarkdownToHTML(filepath);
        } else {
            html = fs.readFileSync(filepath, 'utf8');
        }
        if (html) {
            let pair = [];
            const finder = whereIsSimpleGuide.split(' > ');
            const htmlLoad = require('cheerio').load(html);
            const found = htmlLoad(articleFrame + ' ' + whereIsWoolName);
            found.each((index, element) => {
                const ckName = htmlLoad(element).text();
                //let blk = htmlLoad(element).next(finder[0]);
                let blk;
                if (finder[0] == whereIsWoolName) {
                    blk = htmlLoad(element);
                } else {
                    blk = htmlLoad(element).nextAll().filter(finder[0]).first();
                }
                if (blk.length > 0 && finder[1]) {
                    for (let i = 1; i < finder.length; i++) {
                        blk = blk.find(finder[i]).first();
                    }
                }
                const guidance = blk.html().replace(/<br\s*\/?>/gi, '\n').trim();
                //const guidance = blk.text();
                pair.push([ckName.trim(), guidance]);
            })
            for (p of pair) {
                logger.debug('p0=' + p[0]);
                logger.debug('p1=' + p[1]);
                await cacheDB.set(p[0], p[1]);
            }
        }

    }
    async function isURL(path) {
        var pattern = new RegExp('^(https?:\\/\\/)?');
        return pattern.test(path);
    }
    async function isHTML(path) {
        try {
            // 读取文件的第一行  
            const firstLine = fs.readFileSync(path, 'utf8').split('\n')[0];
            // 去除首尾的空白字符，并比较是否为'<!DOCTYPE html>'  
            return firstLine.trim() === '<!DOCTYPE html>';
        } catch (err) {
            // 如果读取文件时出错，则返回false  
            logger.error('读取文件时出错:', err);
            return false;
        }
    }
    async function parseMarkdownToHTML(markdownFilePath) {
        let html;
        fs.readFile(markdownFilePath, 'utf8', (err, markdownContent) => {
            if (err) {
                logger.error('读取Markdown文件时出错:', err);
                return;
            }
            // 使用marked解析Markdown内容  
            html = require('marked')(markdownContent);
        });
        return html;
    }
    async function checkInput(msg) {
        if (msg === null) {
            await s.reply("回复超时，已退出");
            return false;
        } else if (msg.getMsg() === 'q') {
            await s.reply("已退出");
            logger.info('用户退出')
            return false;
        } else {
            return true;
        }
    }
    async function doCache() { //缓存
        let keys = await cacheDB.keys();
        if (keys) {
            for (let key of keys) {
                await cacheDB.del(key);
            } // 删除旧缓存
        }
        let keys2 = await QLToolsDB.keys();
        if (keys2) {
            for (let key of keys2) {
                await QLToolsDB.del(key);
            } // 删除旧数据库，不会搞动态更新，先全删掉吧:)
        }
        logger.info('删除旧缓存完成')
        await cacheWoolList();
        logger.info('缓存woolList完成')
        const i = await QLToolsDB.keys();
        await cacheDB.set('woolNumbers', i.length);
        logger.info('缓存woolNumbers完成')
        await cacheDB.set('woolKeys', i);
        logger.info('缓存woolKeys完成')
        const woolListText = await makeWoolList();
        await cacheDB.set('woolListText', woolListText);
        logger.info('缓存woolListText完成')
        await cacheSimpleGuide();
        logger.info('缓存SimpleGuide完成')
        return;
    }
    async function cacheWoolList() { //缓存
        let woolList;
        let woolIndex = 1;
        await axios.get(QLToolsURL + '/v1/api/index/data')
            .then(response => {
                woolList = response.data;
            })
            .catch(error => {
                // 如果请求失败，处理错误  
                logger.error('Error fetching data:', error);
            });
        if (woolList.code == 2000) {
            logger.debug(woolList.data.serverData);
            let woolNames = [],
                woolCKNames = [];
            for (const server of woolList.data.serverData) {
                for (const env of server.envData) {
                    if (env) {
                        let envJSON = {
                            'serverId': server.ID,
                            'envName': env.name,
                            'envRemark': env.nameRemarks
                        }
                        woolNames.push(env.nameRemarks);
                        woolCKNames.push(env.name);
                        envJSON = await changeWoolName(envJSON);
                        await QLToolsDB.set(woolIndex, envJSON); //写入新数据库
                        woolIndex += 1;
                    }
                }
            }
            await cacheDB.set('woolNames', woolNames);
            await cacheDB.set('woolCKNames', woolCKNames);
            logger.info('缓存成功');
        } else {
            logger.error(woolList.code + woolList.msg);
        }
    }
    async function makeWoolList() {
        let woolList = [];
        //const woolIndices = await QLToolsDB.keys();
        for (woolIndex = 1; woolIndex <= await cacheDB.get('woolNumbers'); woolIndex++) {
            woolName = await QLToolsDB.get(woolIndex);
            woolList.push(woolIndex + '.' + woolName.envRemark);
        }
        let msg = '羊毛列表：\n';
        for (wool of woolList) {
            msg += wool + '\n';
        }
        msg += '请回复【数字序号】，退出回复q';
        return msg;
    }
    async function uploadCK(serverId, ckName, ck) { //通过api上传ck
        let result;
        const data = {
            "serverID": serverId,
            "envName": ckName,
            "envData": ck
        }
        const config = {
            method: 'post',
            url: QLToolsURL + '/v1/api/env/add',
            headers: {
                'Content-Type': 'application/json'
            },
            data: data
        }
        await axios(config)
            .then(response => {
                result = response.data;
            })
            .catch(error => {
                // 如果请求失败，处理错误  
                logger.error('Error fetching data:', error);
            });
        switch (result.code) {
            case 2000:
                s.reply('提交成功');
                break;
            case 5003:
                s.reply('服务器繁忙，请重试或通知管理员检查')
                break;
            case 5016:
                s.reply('发生一点小意外，请重新提交');
                break;
            case 5019:
                s.reply('ck不符合规定, 请检查后再提交');
                break;
            case 5020:
                s.reply('限额已满，提交失败');
                break;
            case 5021:
                s.reply('ck内容不能为空')
                break;
            case 5024:
                s.reply('库中已有相同ck，请勿重复提交');
                break;
            case 5028:
                s.reply('其他错误，错误内容：' + result.msg);
                break;
            default:
                s.reply('未知错误，错误内容已记录在管理员后台');
                logger.error(result.code + result.msg + result.data);
        }
    }
    /*const woolList = []*/
}
