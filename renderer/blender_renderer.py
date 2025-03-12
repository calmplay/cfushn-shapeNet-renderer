# -*- coding: utf-8 -*-
# @Time    : 2025/3/8 13:04
# @Author  : cfushn
# @Comments: 
# @Software: PyCharm

import argparse
import math
import os
import random
import sys
from contextlib import contextmanager

import bmesh
import bpy

# 获取当前脚本所在的目录,将其添加到 Python 的 sys.path(这一步必须放到import二方包之前)
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from blender_initializer import initialize
from config import cfg

context = bpy.context
scene = bpy.context.scene
render = bpy.context.scene.render


def render_shapeNet(class_id, model_id):
    # 清除所有物体(灯光和相机除外)
    for o in bpy.context.scene.objects:
        # 仅删除非相机和灯光的对象
        if o.type not in {'CAMERA', 'LIGHT', 'EMPTY'}:
            bpy.data.objects.remove(o, do_unlink=True)

    # 导入 OBJ 文件
    file_path = os.path.join(cfg.data_folder, class_id, model_id,
                             "model.obj" if cfg.version == "v1" else "models/model_normalized.obj")
    # bpy.ops.import_scene.obj(filepath=file_path) # 旧版blender
    bpy.ops.wm.obj_import(filepath=file_path)  # 新版blender
    # obj = bpy.context.selected_objects[0]

    # # 遍历模型的所有材质槽
    # for slot in obj.material_slots:
    #     # 获取材质中的 "Principled BSDF" 节点
    #     node = slot.material.node_tree.nodes['Principled BSDF']
    #     # 降低镜面反射强度，避免高光影响
    #     node.inputs['Specular'].default_value = 0.05

    # # 遍历模型的所有材质槽 todo
    # for slot in obj.material_slots:
    #     if not slot.material:  # 避免材质槽为空
    #         continue
    #
    #     mat = slot.material
    #     if not mat.use_nodes:  # 确保启用了节点系统
    #         continue
    #
    #     nodes = mat.node_tree.nodes
    #     bsdf_node = None
    #
    #     # 遍历材质节点，找到 "Principled BSDF"
    #     for node in nodes:
    #         if node.type == 'BSDF_PRINCIPLED':  # 确保正确查找 Principled BSDF 节点
    #             bsdf_node = node
    #             break
    #
    #     if bsdf_node:
    #         if "Specular" in bsdf_node.inputs:  # 确保 "Specular" 插槽存在
    #             bsdf_node.inputs["Specular"].default_value = 0.05
    #         else:
    #             print(f"❌ [ERROR] 'Specular' slot not found in {mat.name}")
    #     else:
    #         print(f"❌ [ERROR] 'Principled BSDF' node not found in {mat.name}")

    # 调整模型位置,并计算包围盒对应的球体半径
    # bound_radius = obj_location_processing()
    bound_radius = 0.5  # 经测试发现,包围盒大小是固定的,且模型主体都位于原点,无需调整

    # 如果需要缩放模型
    if math.fabs(cfg.scale - 1.0) > 1e-4:
        bpy.ops.transform.resize(value=(cfg.scale, cfg.scale, cfg.scale))  # 进行缩放
        bpy.ops.object.transform_apply(scale=True)  # 应用缩放变换

    # 移除重复顶点，优化网格
    if cfg.remove_doubles:
        bpy.ops.object.mode_set(mode='EDIT')  # 进入编辑模式
        bpy.ops.mesh.remove_doubles()  # 删除重复顶点
        bpy.ops.object.mode_set(mode='OBJECT')  # 退出编辑模式

    # 添加边缘分割修正
    if cfg.edge_split:
        bpy.ops.object.modifier_add(type='EDGE_SPLIT')  # 添加 Edge Split 修正
        context.object.modifiers["EdgeSplit"].split_angle = 1.32645  # 设置分割角度
        bpy.ops.object.modifier_apply(modifier="EdgeSplit")  # 应用修正

    # ----------------------- 预览图 -----------------------
    # 渲染预览图时,临时关闭额外通道输出
    with disable_multi_output():
        # locate_camera(3, 20.0, 45.0)
        locate_camera(bound_radius, 15.0, 45.0, 200)
        render.filepath = os.path.join(cfg.out_folder, "preview", f"{class_id}_{model_id}.png")
        print("Saved for preview:")
        os.makedirs(os.path.join(cfg.out_folder, "preview"), exist_ok=True)
        bpy.ops.render.render(write_still=True)

    # 如果是测试模式, 仅渲染预览角度的图像
    if cfg.is_test:
        return

    # ----------------------- 非测试模式下,全方位渲染 -----------------------
    # 标准输出图片存放文件夹
    os.makedirs(os.path.join(cfg.out_folder, class_id, model_id), exist_ok=True)
    # 多通道输出存放文件夹
    if cfg.multi_output_channel:
        os.makedirs(os.path.join(cfg.out_folder, class_id, model_id, "multi_channel"),
                    exist_ok=True)
    # 初始化相机角度
    assert cfg.elevation_min <= cfg.elevation_max
    assert cfg.azimuth_min <= cfg.azimuth_max

    for lens in cfg.lens_list:
        elevation_degree = cfg.elevation_min
        while elevation_degree <= cfg.elevation_max:
            azimuth_degree = cfg.azimuth_min
            while azimuth_degree <= cfg.azimuth_max:

                if random.random() <= cfg.render_dropout:  # random.random() in [0,1)
                    # 用概率控制生成数量
                    azimuth_degree += cfg.azimuth_step_degree  # 水平旋转角度++
                    continue

                # 相机位置调整
                locate_camera(bound_radius, elevation_degree, azimuth_degree)
                # 设置输出路径,分文件夹存放
                label = f"{lens}_{elevation_degree:.1f}_{azimuth_degree:.1f}"
                render.filepath = os.path.join(cfg.out_folder, class_id, model_id, f"{label}.png")
                if cfg.multi_output_channel:
                    # 节点(Compositor)输出系统的路径由两部分组成: base_path + file_slots[.].path
                    # 各节点的base_path已经在blender_initializer.py中初始化设置好了
                    s = f"{class_id}/{model_id}/multi_channel"
                    cfg.depth_file_output.file_slots[0].path = f"{s}/{label}_depth"
                    cfg.normal_file_output.file_slots[0].path = f"{s}/{label}_normal"
                    cfg.albedo_file_output.file_slots[0].path = f"{s}/{label}_albedo"
                    cfg.id_file_output.file_slots[0].path = f"{s}/{label}_id"
                # 渲染并保存
                bpy.ops.render.render(write_still=True)
                azimuth_degree += cfg.azimuth_step_degree  # 水平旋转角度++
            elevation_degree += cfg.elevation_step_degree  # 俯仰旋转角度++


# 调整模型主体位置 & 计算包围盒对应的球体半径
def obj_location_processing():
    x_min, x_max, y_min, y_max, z_min, z_max = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    for obj in objects:
        # 进入编辑模式
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')

        # 获取网格数据
        mesh = bmesh.from_edit_mesh(obj.data)
        vert_list = [v.co for v in mesh.verts]

        for v in vert_list:
            # 更新 x_bound, y_bound, z_bound
            x_min = min(x_min, v.x)
            y_min = min(y_min, v.y)
            z_min = min(z_min, v.z)
            x_max = max(x_max, v.x)
            y_max = max(y_max, v.y)
            z_max = max(z_max, v.z)

        # 退出编辑模式
        bpy.ops.object.mode_set(mode='OBJECT')
    xx = (x_min + x_max) / 2
    yy = (y_min + y_max) / 2
    zz = (z_min + z_max) / 2
    for obj in objects:
        obj.location.x -= xx
        obj.location.y -= yy
        obj.location.z -= zz
    # 应用变换
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.transform_apply(location=True)

    # 计算包围盒对应的球体半径
    a = (x_max - x_min) / 2
    b = (y_max - y_min) / 2
    c = ((z_max - z_min) / 2)
    bound_radius = math.sqrt(a ** 2 + b ** 2 + c ** 2)
    return bound_radius


# 根据包围球半径,相机视角,焦距调整方位 (保证全景且尽可能占满屏幕)
def locate_camera(bound_radius, elevation_degree, azimuth_degree, lens=50.0):
    # 科普: 50mm:标准焦距(人眼等效视角), 25mm:0.5x; 100mm:2x; 200mm:4x
    camera = scene.objects['Camera']
    camera.data.lens = lens  # 35mm:正常; 100mm:双倍镜
    w = camera.data.sensor_width  # 初始化时已设置传感器w=h=36
    # 计算视角Fov (单位: 弧度)
    fov = 2 * math.atan((w / 2) / lens)
    # 计算摄像机到原点的距离(能囊括obj的最小距离)
    distance = bound_radius / math.sin(fov / 2)
    distance *= 1.105  # 拉远一点点,留点空白

    # 相机初始化设置见blender_initializer.py
    radius_xy = distance * math.cos(math.radians(elevation_degree))  # 投影在xy平面上的半径
    height = distance * math.sin(math.radians(elevation_degree))  # 摄像机的高度
    camera.location.x = radius_xy * math.cos(math.radians(azimuth_degree))
    camera.location.y = radius_xy * math.sin(math.radians(azimuth_degree))
    camera.location.z = height
    bpy.context.view_layer.update()  # 强制刷新视图层，确保生效


@contextmanager
def disable_multi_output():
    try:
        # 临时关闭额外通道输出
        cfg.depth_file_output.mute = True
        cfg.normal_file_output.mute = True
        cfg.albedo_file_output.mute = True
        cfg.id_file_output.mute = True
        yield
    finally:
        # 恢复启用 (depth,normal,albedo,id图层)
        if cfg.multi_output_channel:
            cfg.depth_file_output.mute = False
            cfg.normal_file_output.mute = False
            cfg.albedo_file_output.mute = False
            cfg.id_file_output.mute = False


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
            description='Renders given obj file by rotation a camera around it.')
    parser.add_argument('--class_id', type=str, required=True)
    parser.add_argument('--obj_id_list', type=str, nargs='+', required=True,
                        help='多个obj_id用空格隔开')
    argv = sys.argv[sys.argv.index("--") + 1:]  # blender约定使用--分隔它的参数和用户脚本的参数
    args = parser.parse_args(argv)  # 自定义args解析 (直接parser.parse_args()会涵盖blender的args导致报错)
    class_id = args.class_id
    obj_id_list = args.obj_id_list  # nargs='+',会使其解析后变成列表

    # 初始化blender环境
    initialize()

    # 将本批次的obj全部渲染
    for obj_id in obj_id_list:
        render_shapeNet(class_id, obj_id)
