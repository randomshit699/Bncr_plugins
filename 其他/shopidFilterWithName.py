import re

sour = "/home/shopid.txt" //输入文件
fin = "/home/filtered_shopid.txt" //输出文件

with open(sour, "r", encoding="utf-8") as file:
    text = file.read()


pattern_digital_shop = re.compile(r"^\d+的?店铺?$")
pattern_ofSomeOne_shop = re.compile(r".+的店铺?$")
pattern_pureDigitAndAlpha_shop = re.compile(r"^[\da-zA-Z]+$")
pattern_endInNum_shop = re.compile(r'.+\d$')

filtered_results = []

lines = text.strip().split("\n")

for line in lines:
    columns = line.split(",") 
    if len(columns) == 4:
        status, name = columns[2], columns[3].strip() 
        if (
            status == "online"
            and name
            and not pattern_endInNum_shop.match(name)
            and not pattern_digital_shop.match(name)
            and not pattern_pureDigitAndAlpha_shop.match(name)
            and not pattern_ofSomeOne_shop.match(name)
            and "拼购" not in name
            and "京喜拼拼" not in name
            and "有限公司" not in name
            and "本地生活" not in name
            and "测试" not in name
            and "充值" not in name
            and "TEST" not in name
            and "test" not in name
            and "法院" not in name
            and "eqeq" not in name
            and "无界" not in name
            and "京东便利店" not in name
            and "京采汇" not in name
            and "合作联社" not in name
            and "停用" not in name
            and "jd_" not in name
            and "京东企业自营店" not in name
            and "退店" not in name
            and "买手店" not in name
            and "卖场店" not in name
            and "生活服务专营店" not in name
        ):
            filtered_results.append(",".join(columns[:2]) + "," + columns[3] + "\n")


with open(fin, "w", encoding="utf-8") as file:
    file.writelines(filtered_results)
