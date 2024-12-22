/**
 * @author 小九九
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

const jsonSchema = BncrCreateSchema.object({
    rabbit: BncrCreateSchema.object({
        base: BncrCreateSchema.string().setTitle("地址").setDescription(`最后不要带/`).setDefault("http://172.0.0.1:1234"),
        name: BncrCreateSchema.string().setTitle("用户名").setDescription(`登录后台用的那个用户名`).setDefault("admin"),
        passwd: BncrCreateSchema.string().setTitle("密码").setDescription(`登录后台用的那个密码`).setDefault("password"),
    }).setTitle("兔子面板"),
    rlist: BncrCreateSchema.array(BncrCreateSchema.string().setTitle("地址").setDescription(`前面不要http(s)://，最后不要带/`).setDefault("mr-orgin.1888866.xyz"))
        .setTitle("反代地址")
        .setDescription(`点击右下角+增加更多地址`)
        .setDefault([
            "rabbit.cfyes.tech",
            "mr-orgin.1888866.xyz",
            "jd-orgin.1888866.xyz",
            "mr.118918.xyz",
            "host.257999.xyz",
            "log.madrabbit.eu.org",
            "fd.gp.mba:6379",
        ]),
});
const ConfigDB = new BncrPluginConfig(jsonSchema);

const db = new BncrDB("rabbit");

module.exports = async (s) => {
    await ConfigDB.get();
    if (!Object.keys(ConfigDB.userConfig).length) {
        return await s.reply('请先发送"修改无界配置",或者前往前端web"插件配置"来完成插件首次配置');
    }
    const baseUrl = ConfigDB.rabbit.base;
    const name = ConfigDB.rabbit.name;
    const passwd = ConfigDB.rabbit.passwd;
    const urlArr = ConfigDB.rlist;
    if (!global.crbfd_lock) {
        global.crbfd_lock = true;
        try {
            const axios = require("axios");
            const regBaseUrl = regHttpUrl(baseUrl);
            const authToken = await auth(name, passwd);
            if (!authToken) throw new Error("兔子后台鉴权失败");
            let config = await getConfig(authToken);
            let oldAuthUrl = config.ServerHost;
            let n = urlArr.indexOf(oldAuthUrl) ?? 0;
            if (!config) throw new Error("network problem");
            const availUrl = await testAvailUrl(authToken, urlArr, n);
            if (!availUrl) throw new Error("no url available");
            await db.set("auth_url", `http://${availUrl}`);
            config.ServerHost = availUrl;
            await saveConfig(authToken, config);

            await sysMethod.sleep(5);
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
                        msg: "更换rabbitpro反代auth：" + result.msg,
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
                        msg: "更换rabbitpro反代：" + result.msg + "\n现在使用的是：" + config.ServerHost,
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

            async function testAvailUrl(authToken, urlArr, n) {
                //urlArr = shuffleArray(urlArr);
                //for (let url of urlArr) {
                for (let i = 1; i < urlArr.length; i++) {
                    url = urlArr[(n + i) % urlArr.length];
                    const regUrl = regHttpUrl(url);
                    console.log("正在测试：" + regUrl);

                    let result = false;
                    try {
                        await axios({
                            method: "get",
                            timeout: 5000,
                            url: regUrl + "/enc/M",
                        })
                            .then((response) => {
                                result = response.data;
                            })
                            .catch((response) => {
                                //if (!response?.response) console.log(response);
                                result = response.response.data;
                            });
                    } catch (e) {
                        console.log("crbfd testAvail:", e);
                    }
                    //if (result.toString().includes("message")) return url;
                    console.log(result);
                    if (result && result?.message?.data == "no data") return url;

                    /* await axios({
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
                    } */
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
            sysMethod.pushAdmin({
                platform: [],
                msg: "更换rabbitpro反代err：" + err,
            });
            await sysMethod.sleep(5);
            global.crbfd_lock = false;
            throw err;
        }
    } else {
        console.log("更换rabbitpro反代：另一个自动更换反代正在运行中");
    }
};
