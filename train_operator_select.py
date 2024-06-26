import lzma
import pickle

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from sklearn.neighbors import KNeighborsClassifier

from arknights_mower.data import agent_list
from arknights_mower.utils.image import thres2

mh = 42
mw = 200

font31 = ImageFont.truetype("arknights_mower/fonts/SourceHanSansCN-Medium.otf", 31)
font30 = ImageFont.truetype("arknights_mower/fonts/SourceHanSansCN-Medium.otf", 30)
font25 = ImageFont.truetype("arknights_mower/fonts/SourceHanSansCN-Medium.otf", 25)

X = []
Y = []

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
    contours, _ = cv2.findContours(dilation, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    rect = map(lambda c: cv2.boundingRect(c), contours)
    x, y, w, h = sorted(rect, key=lambda c: c[0])[0]
    img = img[y : y + h, x : x + w]
    tpl = np.zeros((mh, mw))
    tpl[: img.shape[0], : img.shape[1]] = img
    # cv2.imwrite(f"/home/zhao/Desktop/data/{operator}.png", tpl)
    tpl /= 255
    tpl = tpl.reshape(mh * mw)
    X.append(tpl)
    Y.append(idx)

model = KNeighborsClassifier(n_neighbors=1)
model.fit(X, Y)

with lzma.open("arknights_mower/models/operator_select.model", "wb") as f:
    pickle.dump(model, f)
