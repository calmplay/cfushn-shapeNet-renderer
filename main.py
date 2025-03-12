# -*- coding: utf-8 -*-
# @Time    : 2025/3/7 17:45
# @Author  : cfushn
# @Comments: 
# @Software: PyCharm

import multiprocessing
import os
import random
import signal

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

    # 并行开启的blender进程数量
    parallel_num = 5
    # 单个进程最多处理的obj个数 (过少会频繁启动blender,过多会有内存隐患,具体还得考虑每个obj的渲染数量)
    obj_batch = []  # 每个任务处理的obj批次
    task_list = []  # 任务列表

    for class_id in cfg.class_id_list:
        files = os.listdir(os.path.join(str(cfg.data_folder), class_id))
        if cfg.obj_per_class >= len(files):
            file_scope = files
        else:
            file_scope = random.sample(files, cfg.obj_per_class)
        for file in file_scope:
            obj_batch.append(file)
            # 每个task最多处理batch_size个obj
            if len(obj_batch) == cfg.obj_batch_size:
                task_list.append((class_id, obj_batch))
                obj_batch = []
        # 最后一个不满batch_size个
        if len(obj_batch) > 0:
            task_list.append((class_id, obj_batch))
            obj_batch = []

    # 预览全部任务列表
    print(f"\n预览全部任务列表:\n{task_list}\n")

    try:
        # 多进程并行处理 (注意: 计算密集型(如:渲染)任务应该使用多进程,而非多线程)
        with Parallel(n_jobs=parallel_num) as parallel:
            parallel(delayed(render_task)(class_id, obj_batch) for class_id, obj_batch in task_list)
    except KeyboardInterrupt:
        print("Interrupted! Cleaning up...")
    finally:
        # 主进程关闭时清理子进程
        parent_pid = os.getpid()
        try:
            for proc in multiprocessing.active_children():
                os.kill(proc.pid, signal.SIGTERM)  # 终止子进程
            print("All child processes have been terminated.")
        except Exception as e:
            print(f"Error terminating child processes: {e}")

    # 最后整合为h5文件
    if (not cfg.is_test) and cfg.h5_output:
        # 注意: 如果存在渲染失败保存的残缺PNG图片在文件夹中，会导致h5文件无法生成
        package_h5()
