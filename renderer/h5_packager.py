import gc
import os
from concurrent.futures import ThreadPoolExecutor

import h5py
import numpy as np
from PIL import Image

try:
    from .config import cfg  # 适用于包内导入
except ImportError:
    from config import cfg  # 适用于独立运行（主脚本）


def package_h5():
    """ 分批处理图片并流式写入 HDF5 """
    raw_folder = cfg.out_folder  # 原始数据目录
    r = cfg.resolution
    h5_file_path = os.path.join(cfg.out_folder, f"shapeNet_{r}x{r}.h5")

    print(f"Prepare packaging {h5_file_path} ...")

    # 获取所有图片路径
    image_classes = []
    image_paths = []
    for class_id in os.listdir(raw_folder):
        class_path = os.path.join(raw_folder, class_id)
        if not os.path.isdir(class_path) or class_id == "preview":
            continue
        for model_id in os.listdir(class_path):
            model_path = os.path.join(class_path, model_id)
            if not os.path.isdir(model_path):
                continue
            for img_file in os.listdir(model_path):
                if img_file.endswith(('.png', '.jpg', '.jpeg')):
                    image_classes.append(class_id)
                    image_paths.append(os.path.join(model_path, img_file))
    print(f"Total: {len(image_paths)} ，start processing...")

    # 分批处理
    batch_size = 10000  # 每批处理1万张图片
    num_batches = (len(image_paths) + batch_size - 1) // batch_size

    with h5py.File(h5_file_path, "w") as h5f:
        # 预创建数据集
        img_dataset = h5f.create_dataset(
                "images",
                shape=(len(image_paths), 3, r, r),  # 假设图片是RGB格式
                dtype=np.uint8,
                compression="gzip",
                chunks=(1000, 3, r, r)  # 分块存储
                # 分块存储将数据划分为固定大小的块（Chunk），每个块可以独立压缩、存储和读取 (避免整体压缩)
                # 如果数据集需要动态扩展（例如逐步追加数据），分块存储可以更高效地管理数据的扩展
                # 分块存储允许你逐块写入数据，而不需要一次性将整个数据集加载到内存中，从而减少内存占用
                # 最后不满足1000的块仍会占用1000的空间
                # 另外, 下次追加数据时, 不会自动合并到最后的残缺块, 得手动合并
        )
        class_dataset = h5f.create_dataset(
                "classes",
                shape=(len(image_paths),),
                dtype='S10'  # 假设类别名称不超过10个字符
        )
        labels_dataset = h5f.create_dataset(
                "labels",
                shape=(len(image_paths), 3),  # 每个图片有3个连续标签属性
                dtype=np.float32
        )

        # 分批处理图片
        for batch_idx in range(num_batches):
            start = batch_idx * batch_size
            end = min((batch_idx + 1) * batch_size, len(image_paths))
            batch_classes = image_classes[start:end]
            batch_paths = image_paths[start:end]

            # 多线程处理当前批次
            with ThreadPoolExecutor(max_workers=8) as executor:
                results = list(executor.map(process_image, batch_classes, batch_paths))

            # 过滤掉处理失败的图片
            img_list, class_list, labels_list = [], [], []
            for res in results:
                if res is not None:
                    img_list.append(res[0])
                    class_list.append(res[1])
                    labels_list.append(res[2])

            # 将当前批次写入HDF5
            img_dataset[start:end] = np.array(img_list, dtype=np.uint8)
            class_dataset[start:end] = np.array(class_list, dtype='S10')
            labels_dataset[start:end] = np.array(labels_list, dtype=np.float32)

            # 释放内存
            del img_list, class_list, labels_list, results
            gc.collect()

            print(f"Processed batch {batch_idx + 1}/{num_batches}")

    print(f"Saved: {h5_file_path}")


def process_image(class_id, img_path):
    """ 读取 & 预处理图片，返回 (img_data, class_id, labels) """
    try:
        img_file = os.path.basename(img_path)
        labels = list(map(float, img_file.replace('.png', '').split('_')))

        img = Image.open(img_path).convert("RGBA") if cfg.bg_transparent else Image.open(
                img_path).convert("RGB")
        img_np = np.array(img)  # (H, W, 3/4)

        if cfg.bg_transparent:
            rgb = img_np[..., :3]  # (H, W, 3)
            alpha = img_np[..., 3]  # (H, W)
            rgb[alpha == 0] = 255
            img_np = rgb  # 去掉 Alpha 通道

        img_np = np.transpose(img_np, (2, 0, 1))  # (3, H, W)
        return img_np, class_id, labels

    except Exception as e:
        print(f"Error: {img_path}: {e}")
        return None


if __name__ == "__main__":
    package_h5()
