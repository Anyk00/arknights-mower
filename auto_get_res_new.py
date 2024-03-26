import json
import shutil
import os

import cv2
import numpy as np
import pickle
import lzma

from datetime import datetime

from sklearn.neighbors import KNeighborsClassifier
from skimage.feature import hog

from PIL import Image, ImageDraw, ImageFont
from arknights_mower.data import agent_list
from arknights_mower.utils.image import thres2


class Arknights数据处理器:
    def __init__(self):
        self.当前时间戳 = datetime.now().timestamp()
        self.物品表 = self.加载json(
            "./ArknightsGameResource/gamedata/excel/item_table.json"
        )
        self.干员表 = self.加载json(
            "./ArknightsGameResource/gamedata/excel/character_table.json"
        )
        self.抽卡表 = self.加载json(
            "./ArknightsGameResource/gamedata/excel/gacha_table.json"
        )
        self.关卡表 = self.加载json(
            "./ArknightsGameResource/gamedata/excel/stage_table.json"
        )
        self.活动表 = self.加载json(
            "./ArknightsGameResource/gamedata/excel/activity_table.json"
        )
        self.装仓库物品的字典 = {"NORMAL": [], "CONSUME": [], "MATERIAL": []}

    def 加载json(self, file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def 添加物品(self):
        def 检查图标代码匹配(目标图标代码):
            限定十连 = self.抽卡表["limitTenGachaItem"]
            联动十连 = self.抽卡表["linkageTenGachaItem"]
            匹配结果 = False
            for 限定池子 in 限定十连:
                if 限定池子["itemId"] == 目标图标代码:
                    if self.当前时间戳 > 限定池子["endTime"]:
                        匹配结果 = True
                    break

            for 联动池子 in 联动十连:
                if 联动池子["itemId"] == 目标图标代码:
                    if self.当前时间戳 > 联动池子["endTime"]:
                        匹配结果 = True
                    break

            分割部分 = 目标图标代码.split("_")
            if len(分割部分) == 2 and 分割部分[0].endswith("recruitment10"):
                匹配结果 = True

            if len(分割部分) == 6 and int(分割部分[5]) < 2023:
                匹配结果 = True

            if 目标图标代码 == "ap_supply_lt_60":
                匹配结果 = True

            抽卡 = self.抽卡表.get("gachaPoolClient", [])
            for 卡池 in 抽卡:
                if 卡池["LMTGSID"] == 目标图标代码 and self.当前时间戳 > int(
                    卡池["endTime"]
                ):
                    匹配结果 = True
            return 匹配结果

        物品_名称对 = {}

        for 物品代码, 物品数据 in self.物品表["items"].items():
            图标代码 = 物品数据["iconId"]
            排序代码 = 物品数据["sortId"]
            中文名称 = 物品数据["name"]
            分类类型 = 物品数据["classifyType"]
            源文件路径 = f"./ArknightsGameResource/item/{图标代码}.png"
            os.makedirs(f"./ui/public/depot/{分类类型}", exist_ok=True)
            if 分类类型 != "NONE" and 排序代码 > 0:
                排除开关 = False
                排除开关 = 检查图标代码匹配(图标代码)
                if os.path.exists(源文件路径) and not 排除开关:
                    目标文件路径 = f"./ui/public/depot/{图标代码}.png"
                    self.装仓库物品的字典[分类类型].append(目标文件路径)

                    if not os.path.exists(目标文件路径):
                        shutil.copy(源文件路径, 目标文件路径)
                    物品_名称对[图标代码] = [
                        物品代码,
                        中文名称,
                        分类类型,
                        排序代码,
                    ]
                    print(f"复制 {源文件路径} 到 {目标文件路径}")
                else:
                    print(f"可以复制，但是未找到: {源文件路径}")
        with open(
            "./arknights_mower/data/key_mapping.json", "w", encoding="utf8"
        ) as json_file:
            json.dump(物品_名称对, json_file, ensure_ascii=False)
        with open("./ui/src/pages/key_mapping.json", "w", encoding="utf8") as json_file:
            json.dump(物品_名称对, json_file, ensure_ascii=False)
        print()

    def 添加干员(self):
        干员_名称列表 = []

        for 干员代码, 干员数据 in self.干员表.items():
            if not 干员数据["itemObtainApproach"]:
                continue

            干员名 = 干员数据["name"]
            干员_名称列表.append(干员名)
            干员头像路径 = f"./ArknightsGameResource/avatar/{干员代码}.png"
            目标路径 = f"./ui/public/avatar/{干员数据['name']}.png"
            print(f"{干员名}: {干员代码}")

            shutil.copy(干员头像路径, 目标路径)

        干员_名称列表.sort(key=len)
        with open("./arknights_mower/data/agent.json", "w", encoding="utf-8") as f:
            json.dump(干员_名称列表, f, ensure_ascii=False)
        print()

    def 读取卡池(self):

        抽卡 = self.抽卡表.get("gachaPoolClient", [])
        卡池类型映射 = {
            "SINGLE": "单人池",
            "LIMITED": "限定池",
            "NORM": "普通池",
            "CLASSIC": "中坚池",
            "CLASSIC_ATTAIN": "跨年中坚池",
            "LINKAGE": "联动池",
            "ATTAIN": "跨年池",
            "FESCLASSIC": "中坚甄选",
        }

        for 项 in 抽卡:
            卡池名称 = 项.get("gachaPoolName")
            开始时间戳 = 项.get("openTime")
            结束时间戳 = 项.get("endTime")
            卡池类型代码 = 项.get("gachaPoolId")
            卡池出人 = 项.get("dynMeta")

            if self.当前时间戳 < 结束时间戳:
                卡池类型 = 卡池类型映射.get(卡池类型代码.split("_")[0], 卡池类型代码)
                if 卡池类型代码.split("_")[1] == "ATTAIN":
                    卡池类型 = "跨年中坚池"
                if 卡池名称 == "适合多种场合的强力干员":
                    卡池名称 = 卡池类型
                开始时间 = datetime.fromtimestamp(开始时间戳)
                结束时间 = datetime.fromtimestamp(结束时间戳 + 1)
                print("卡池名称:", 卡池名称)
                print("卡池类型:", 卡池类型)
                if 卡池类型 == "中坚池":
                    print(
                        卡池出人["main6RarityCharId"],
                        卡池出人["sub6RarityCharId"],
                        卡池出人["rare5CharList"],
                    )
                if self.当前时间戳 > 开始时间戳:
                    print("正在进行")
                    print("卡池结束时间:", 结束时间)
                else:
                    print("卡池开始时间:", 开始时间)
                    print("卡池结束时间:", 结束时间)
                print(卡池类型代码)
                print()

    def 读取活动关卡(self):
        可以刷的活动关卡 = []
        关卡 = self.关卡表["stageValidInfo"]
        还未结束的非常驻关卡 = {
            键: 值
            for 键, 值 in 关卡.items()
            if 值["endTs"] != -1 and 值["endTs"] > self.当前时间戳
        }
        还未结束的非常驻关卡 = dict(sorted(还未结束的非常驻关卡.items()))
        for 键, _ in 还未结束的非常驻关卡.items():
            关卡代码 = self.关卡表["stages"][键]["code"]
            if 键.endswith("#f#"):
                关卡代码 += " 突袭"
            关卡名称 = self.关卡表["stages"][键]["name"]
            关卡结束时间戳 = 还未结束的非常驻关卡[键]["endTs"]
            关卡结束时间 = datetime.fromtimestamp(还未结束的非常驻关卡[键]["endTs"] + 1)
            关卡掉落表 = self.关卡表["stages"][键]["stageDropInfo"]["displayRewards"]
            关卡掉落 = {"普通掉落": []}
            for item in 关卡掉落表:
                if not "side_token" in self.物品表["items"][item["id"]]["iconId"]:
                    if not item["dropType"] == 8:

                        关卡掉落["普通掉落"].append(
                            self.物品表["items"][item["id"]]["iconId"]
                        )
            if 关卡掉落["普通掉落"] != []:
                可以刷的活动关卡.append(
                    {
                        "id": 关卡代码,
                        "name": 关卡名称,
                        "drop": 关卡掉落,
                        "end": 关卡结束时间戳,
                    }
                )
            # print(关卡代码, 关卡名称, 关卡掉落, 关卡结束时间)

        with open(
            "./ui/src/pages/stage_data/event_data.json", "w", encoding="utf-8"
        ) as f:
            json.dump(可以刷的活动关卡, f, ensure_ascii=False)
        print(可以刷的活动关卡)

    def 训练仓库的knn模型(self, 模板文件夹, 模型保存路径):
        def 提取特征点(模板):
            模板 = 模板[40:173, 40:173]
            hog_features = hog(
                模板,
                orientations=18,
                pixels_per_cell=(8, 8),
                cells_per_block=(2, 2),
                block_norm="L2-Hys",
                transform_sqrt=True,
                multichannel=True,
            )
            return hog_features

        def 加载图片特征点_标签(模板类型):
            特征点列表 = []
            标签列表 = []
            for 文件名 in (self.装仓库物品的字典[模板类型]):
                模板 = cv2.imread(文件名)
                模板 = cv2.resize(模板, (213, 213))
                特征点 = 提取特征点(模板)
                特征点列表.append(特征点)
                标签列表.append(文件名[18:-4])
            return 特征点列表, 标签列表

        def 训练knn模型(images, labels):
            knn_classifier = KNeighborsClassifier(
                weights="distance", n_neighbors=1, n_jobs=-1
            )
            knn_classifier.fit(images, labels)
            return knn_classifier

        def 保存knn模型(classifier, filename):
            with lzma.open(filename, "wb") as f:
                pickle.dump(classifier, f)

        模板特征点, 模板标签 = 加载图片特征点_标签(模板文件夹)
        knn模型 = 训练knn模型(模板特征点, 模板标签)
        保存knn模型(knn模型, 模型保存路径)

    def 批量训练并保存扫仓库模型(self):
        self.训练仓库的knn模型(
            "NORMAL", "./arknights_mower/models/NORMAL.pkl"
        )
        self.训练仓库的knn模型(
            "CONSUME", "./arknights_mower/models/CONSUME.pkl"
        )
        self.训练仓库的knn模型(
            "MATERIAL", "./arknights_mower/models/MATERIAL.pkl"
        )

    def 训练在房间内的干员名的模型(self):

        font = ImageFont.truetype(
            "arknights_mower/fonts/SourceHanSansCN-Medium.otf", 37)

        data = {}

        kernel = np.ones((12, 12), np.uint8)

        for operator in sorted(agent_list, key=lambda x: len(x), reverse=True):
            img = Image.new(mode="L", size=(400, 100))
            draw = ImageDraw.Draw(img)
            draw.text((50, 20), operator, fill=(255,), font=font)
            img = np.array(img, dtype=np.uint8)
            img = thres2(img, 200)
            dilation = cv2.dilate(img, kernel, iterations=1)
            contours, _ = cv2.findContours(
                dilation, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            rect = map(lambda c: cv2.boundingRect(c), contours)
            x, y, w, h = sorted(rect, key=lambda c: c[0])[0]
            img = img[y: y + h, x: x + w]
            tpl = np.zeros((46, 265), dtype=np.uint8)
            tpl[: img.shape[0], : img.shape[1]] = img
            # cv2.imwrite(f"/home/zhao/Desktop/data/{operator}.png", tpl)
            data[operator] = tpl

        with lzma.open("arknights_mower/models/operator_room.model", "wb") as f:
            pickle.dump(data, f)

    def 训练选中的干员名的模型(self):
        font31 = ImageFont.truetype(
            "arknights_mower/fonts/SourceHanSansCN-Medium.otf", 31)
        font30 = ImageFont.truetype(
            "arknights_mower/fonts/SourceHanSansCN-Medium.otf", 30)
        font25 = ImageFont.truetype(
            "arknights_mower/fonts/SourceHanSansCN-Medium.otf", 25)

        data = {}

        kernel = np.ones((10, 10), np.uint8)

        for idx, operator in enumerate(agent_list):
            font = font31
            if not operator[0].encode().isalpha():
                if len(operator) == 7:
                    font = font25
                elif len(operator) == 6:
                    font = font30
            img = Image.new(mode="L", size=(400, 100))
            draw = ImageDraw.Draw(img)
            draw.text((50, 20), operator, fill=(255,), font=font)
            img = np.array(img, dtype=np.uint8)
            img = thres2(img, 140)
            dilation = cv2.dilate(img, kernel, iterations=1)
            contours, _ = cv2.findContours(
                dilation, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            rect = map(lambda c: cv2.boundingRect(c), contours)
            x, y, w, h = sorted(rect, key=lambda c: c[0])[0]
            img = img[y: y + h, x: x + w]
            tpl = np.zeros((42, 200), dtype=np.uint8)
            tpl[: img.shape[0], : img.shape[1]] = img
            # cv2.imwrite(f"/home/zhao/Desktop/data/{operator}.png", tpl)
            data[operator] = tpl

        with lzma.open("arknights_mower/models/operator_select.model", "wb") as f:
            pickle.dump(data, f)


数据处理器 = Arknights数据处理器()

数据处理器.添加物品()
# 希望可以运行一下 npm run format json在后端和前端存了两份一样的
# 权宜之计

数据处理器.添加干员()

数据处理器.读取卡池()
数据处理器.读取活动关卡()

数据处理器.批量训练并保存扫仓库模型()
# 批量训练并保存扫仓库模型 和 添加物品 有联动 ， 添加物品提供了分类的图片位置

数据处理器.训练在房间内的干员名的模型()
数据处理器.训练选中的干员名的模型()
