# -*- coding: utf-8 -*-
# @Time    : 2025/3/9 15:59
# @Author  : cfushn
# @Comments: 
# @Software: PyCharm

import os

import h5py
import numpy as np
from PIL import Image

from .config import cfg


def package_h5():
    # 定义数据目录和 H5 文件路径
    raw_folder = cfg.out_folder
    r = cfg.resolution
    h5_file_path = os.path.join(cfg.out_folder, f"shapeNet_{r}x{r}.h5")

    print(f"Preparing for packaging shapeNet_{r}x{r}.h5 ...")

    # 创建 H5 文件
    with h5py.File(h5_file_path, "w") as h5f:
        img_list = []
        class_list = []
        labels_list = []

        for class_id in os.listdir(raw_folder):  # 遍历类别

            class_path = os.path.join(raw_folder, class_id)
            if class_id == "preview" or (not os.path.isdir(class_path)):
                # 若文件夹名称为"preview"(预览文件夹),或非文件夹,跳过
                continue

            for model_id in os.listdir(class_path):  # 遍历模型
                model_path = os.path.join(class_path, model_id)
                if not os.path.isdir(model_path):
                    continue

                for img_file in os.listdir(model_path):  # 遍历图片
                    if not img_file.endswith(('.png', '.jpg', '.jpeg')):
                        continue

                    img_path = os.path.join(model_path, img_file)

                    # 如果背景透明,增加特殊处理:转为纯白色
                    if cfg.bg_transparent:
                        img = Image.open(img_path).convert("RGBA")  # (H, W, 4)
                        img_np = np.array(img)  # 转换为 NumPy 数组 (H, W, 4)
                        # 分离 RGB 和 Alpha 通道
                        # 注意: img_np[..., 3:]<=>img_np[..., 3:4]=>(H, W, 1)
                        # 而写成img_np[..., 3]就会自动砍掉一个维度变成(H, W)
                        rgb = img_np[..., :3]  # (H, W, 3)
                        alpha = img_np[..., 3]  # (H, W)
                        # 只修改完全透明的像素，保留半透明像素 (Alpha值越小越透明, alpha=0表示纯透明)
                        rgb[alpha == 0] = 255  # 仅对 alpha = 0 的像素改为白色
                        # 去掉 Alpha 通道（因为已经处理了透明背景）
                        img_rgb = rgb
                    else:
                        img_rgb = Image.open(img_path).convert("RGB")  # 转换为 NumPy 数组 (H, W, 3)
                        img_rgb = np.array(img_rgb)  # 转换为 NumPy 数组

                    # 转换后的shape是[h,w,c], 转换为[c,h,w], 跟自己的实验对齐
                    img_rgb = np.transpose(img_rgb, (2, 0, 1))

                    # 解析标签 (文件名由其标签属性构成)
                    labels = list(map(float, img_file.replace('.png', '').split('_')))

                    img_list.append(img_rgb)
                    class_list.append(class_id)
                    labels_list.append(labels)  # 注意,labels本身也是一个list
                # end 遍历图片
            # end 遍历3D模型
        # end 遍历模型大类

        # 转换为 NumPy 数组
        img_array = np.array(img_list, dtype=np.uint8)
        class_array = np.array(class_list, dtype='S')  # 字符串存储
        labels_array = np.array(labels_list, dtype=np.float32)

        # 存入 H5 文件
        h5f.create_dataset("images", data=img_array, compression="gzip")
        h5f.create_dataset("classes", data=class_array)
        h5f.create_dataset("labels", data=labels_array)

    print(f"Saved: {h5_file_path}")


if __name__ == "__main__":
    package_h5()
