# -*- coding: utf-8 -*-
# @Time    : 2025/3/7 17:45
# @Author  : cfushn
# @Comments: 
# @Software: PyCharm

import os
import random

from joblib import Parallel, delayed

from renderer.config import cfg
from renderer.h5_packager import package_h5


def render_task(class_id, obj_id_list):
    blender_location = "blender"  # 配置blender为环境变量
    render_script = "renderer/blender_renderer.py"
    obj_ids_concat = " ".join(obj_id_list)
    cmd = (f"{blender_location} --background --python {render_script} "
           "-- "  # 注意! # blender约定使用--分隔blender的参数和用户脚本的参数
           f"--class_id {class_id} "
           f"--obj_id_list {obj_ids_concat} ")
    print("新建任务: " + cmd)
    os.system(cmd)


if __name__ == "__main__":

    # class_id_list = ["02924116","04379243","04401088","02773838","02843684","02992529","04225987","04530566","03948459","03636649","04004475","03325088","02747177","02942699","02876657","03759954","04554684","04074963","03337140","02818832","03467517","02801938","03790512","02933112","03991062","02880940","03710193","03593526","04090263","02808440","03624134","03085013","02946921","03001627","03642806","03797390","02958343","03938244","02691156","04460130","03691459","03046257","03207941","02871439","04256520","02954340","03261776","03761084","03513137","02828884","04099429","03211117","03928116","04468005","04330267"]
    class_id_list = ["02691156", "02773838", "02954340", "02958343", "03001627",
                     "03261776", "03467517", "03624134", "03636649", "03642806", "03790512",
                     "03797390", "03948459", "04099429", "04225987", "04379243"]
    # class_id_list = ["03790512"]
    # 并行开启的blender进程数量
    parallel_num = 5
    # 单个进程最多处理的obj个数 (过少会频繁启动blender,过多会有内存隐患,具体还得考虑每个obj的渲染数量)
    obj_batch_size = 2
    obj_batch = []  # 每个任务处理的obj批次
    task_list = []  # 任务列表

    for class_id in class_id_list:
        files = os.listdir(os.path.join(str(cfg.data_folder), class_id))
        # for file in files:
        for file in random.sample(files, 10):  # test1: 随机找
            obj_batch.append(file)
            # 每个task最多处理batch_size个obj
            if len(obj_batch) == obj_batch_size:
                task_list.append((class_id, obj_batch))
                obj_batch = []
        # 最后一个不满batch_size个
        if len(obj_batch) > 0:
            task_list.append((class_id, obj_batch))
            obj_batch = []

    # 预览全部任务列表
    print(f"\n{task_list}\n")

    # 并行处理
    with Parallel(n_jobs=parallel_num) as parallel:
        parallel(delayed(render_task)(class_id, obj_batch) for class_id, obj_batch in task_list)

    # 等待上面任务全部结束后整合为h5文件
    if (not cfg.is_test) and cfg.h5_output:
        package_h5()

"""
Airplane 02691156
Bag	02773838
Cap	02954340
Car	02958343
Chair 03001627
Earphone 03261776
Guitar 03467517
Knife 03624134
Lamp 03636649
Laptop 03642806
Motorbike 03790512
Mug	03797390
Pistol 03948459
Rocket 04099429
Skateboard 04225987
Table 04379243
"""
