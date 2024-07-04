/**
 * @author 小九九
 * @description 解析关注有礼线报中的奖品内容，执行有豆线报
 * @origin 小九九
 * @version v1.0.0
 * @name 关注有礼解析奖品
 * @rule ^活动名称: 关注有礼[\s\S]+$
 * @priority 10000
 * @admin false
 * @disable false
 */
module.exports = async s => {
    const content = s.getMsg();
    let url = content.match(/https:\/\/shop\.m\.jd\.com\/\?shopId=\d{5,11}&venderId=\d{5,11}/g)[0];
    let prize = content.match(/奖品: (.*?)\n/)[1];
    if (prize.search(/京豆/) !== -1) {
        await sysMethod.inline(`spy插队 export BEAN_FOLLOW="${url}"`)
    }


}
