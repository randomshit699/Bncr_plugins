/**
 * @author 小九九 t.me/gdot0
 * @name 更换rabbitpro反代
 * @origin 小九九
 * @team 小九九
 * @version 1.0
 * @rule ^crbfd$
 * @description 检查反代列表，更换可用的rabbitpro反代
 * @admin true
 * @public false
 * @priority 1000
 */
//@rule触发词可自行更换

const baseUrl = "http://"; //rabbitpro前台地址
const name = ""; //后台用户名
const passwd = ""; //后台密码
const urlArr = [
    "rabbit.cfyes.tech",
    "mr-orgin.1888866.xyz",
    "jd-orgin.1888866.xyz",
    "mr.yanyuwangluo.cn",
    "mr.118918.xyz",
    "mr.5gyh.com",
    "host.257999.xyz",
    "log.madrabbit.eu.org",
    "62.204.54.137:4566",
    "fd.gp.mba:6379",
    "mr.108168.xyz:10188",
    "rabbit.gushao.club",
]; //反代列表

module.exports = async (s) => {
    if (!global.crbfd_lock) {
        global.crbfd_lock = true;
        try {
            const axios = require("axios");
            const regBaseUrl = regHttpUrl(baseUrl);
            const authToken = await auth(name, passwd);
            if (!authToken) return;
            let config = await getConfig(authToken);
            if (!config) return;
            const availUrl = await testAvailUrl(authToken, urlArr);
            if (!availUrl) return;
            config.ServerHost = availUrl;
            await saveConfig(authToken, config);
            global.crbfd_lock = false;

            async function auth(name, passwd) {
                await axios({
                    method: "post",
                    url: regBaseUrl + "/admin/auth",
                    data: { username: name, password: passwd },
                })
                    .then((response) => {
                        result = response.data;
                    })
                    .catch((error) => {
                        console.log(error);
                        sysMethod.pushAdmin({
                            platform: [],
                            msg: "连接rabbitpro后台失败",
                        });
                    });
                if (!result) {
                    return;
                } else if (result.code == 401) {
                    sysMethod.pushAdmin({
                        platform: [],
                        msg: "更换rabbitpro反代：" + result.msg,
                    });
                    return;
                }
                return result.access_token;
            }

            async function getConfig(authToken) {
                await axios({
                    method: "get",
                    url: regBaseUrl + "/admin/GetConfig",
                    headers: {
                        authorization: "Bearer " + authToken,
                    },
                })
                    .then((response) => {
                        result = response.data;
                    })
                    .catch();
                if (!result) {
                    return;
                }
                return result;
            }

            async function saveConfig(authToken, config) {
                await axios({
                    method: "post",
                    url: regBaseUrl + "/admin/SaveConfig",
                    headers: {
                        authorization: "Bearer " + authToken,
                    },
                    data: config,
                })
                    .then((response) => {
                        result = response.data;
                    })
                    .catch();
                if (result?.code == 0) {
                    sysMethod.pushAdmin({
                        platform: [],
                        msg:
                            "更换rabbitpro反代：" +
                            result.msg +
                            "\n现在使用的是：" +
                            config.ServerHost,
                    });
                    return;
                } else {
                    sysMethod.pushAdmin({
                        platform: [],
                        msg: "更换rabbitpro反代：保存设置失败",
                    });
                }
                return;
            }

            async function testAvailUrl(authToken, urlArr) {
                urlArr = shuffleArray(urlArr);
                for (let url of urlArr) {
                    const regUrl = regHttpUrl(url);
                    console.log("正在测试：" + regUrl);
                    await axios({
                        method: "post",
                        url: regBaseUrl + "/admin/TestServerHost",
                        headers: {
                            authorization: "Bearer " + authToken,
                        },
                        data: {
                            ServerHost: regUrl,
                        },
                    })
                        .then((response) => {
                            result = response.data;
                        })
                        .catch();
                    if (result.success == true) {
                        return url;
                    }
                }
                sysMethod.pushAdmin({
                    platform: [],
                    msg: "更换rabbitpro反代：全都不能用",
                });
                function shuffleArray(array) {
                    for (let i = array.length - 1; i > 0; i--) {
                        const j = Math.floor(Math.random() * (i + 1));
                        [array[i], array[j]] = [array[j], array[i]]; // 使用ES6的解构赋值进行交换
                    }
                    return array;
                }
            }

            function regHttpUrl(url) {
                const httpReg = /^https?:\/\//;
                if (!httpReg.test(url)) {
                    url = "http://" + url;
                }
                if (baseUrl.endsWith("/")) {
                    url = url.slice(0, -1);
                }
                return url;
            }
        } catch (err) {
            global.crbfd_lock = false;
            sysMethod.pushAdmin({
                platform: [],
                msg: "更换rabbitpro反代：" + err,
            });
        }
    } else {
        console.log("更换rabbitpro反代：另一个自动更换反代正在运行中");
    }
};
