/*
上传ck给小九九
cron: 0 * * * *
*/

const axios = require("axios");

let CookieJDs = [];
if (process.env.JD_COOKIE) {
    if (process.env.JD_COOKIE.indexOf("&") > -1) {
        CookieJDs = process.env.JD_COOKIE.split("&");
    } else if (process.env.JD_COOKIE.indexOf("\n") > -1) {
        CookieJDs = process.env.JD_COOKIE.split("\n");
    } else {
        CookieJDs = [process.env.JD_COOKIE];
    }
}
CookieJDs = [...new Set(CookieJDs.filter((item) => !!item))];

postBody = [];
for (let ck of CookieJDs) {
    postBody.push({
        value: ck,
        name: "JD_COOKIE",
        remarks: "",
    });
}

axios
    .post("https://frp0721.dynv6.net/jd/ck", postBody)
    .then((res) => {
        console.log("上传成功：", res.data);
    })
    .catch((err) => {
        console.log("上传失败：", err);
    });
