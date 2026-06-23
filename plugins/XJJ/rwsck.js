/**
 * @author 小九九 t.me/gdot0
 * @name rwsck
 * @origin 小九九
 * @team 小九九
 * @version 1.0
 * @description 调用青龙rwsck转换脚本（见附件文件夹）
 * @rule ^(rwsck转换)$
 * @admin true
 * @public true
 * @priority 1000
 * @classification ["Qinglong"]
 */

const QlMod = require("../红灯区/mod/AmQlMod")

//要执行的容器序号
let i = 0
 //插件入口
module.exports = async s => {
    
    let qlDb = await QlMod.GetQlDataBase()
    let qlDbArr = qlDb["data"] || []

    QlMod.PutQlCrons(s,qlDbArr, i, 'rwsck.py', 'run', true)

}
