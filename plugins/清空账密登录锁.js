/**
 * @author 小九九 t.me/gdot0
 * @description 清空账密登录锁
 * @origin 小九九 t.me/gdot0
 * @version v1.0.0
 * @name 清空账密登录锁
 * @rule ^清空账密登录锁$
 * @priority 1
 * @admin true
 * @disable false
 * @cron 0 0 3 * * *
 */
//清空账密登录.ts的每日登录数量限制

const db = new BncrDB("AccPw");
const pindb = new BncrDB("pinDB");

module.exports = async s => {
    await db.del('usage_lock');
    await pindb.del('system:bncr');
}
