# -*- coding: utf-8 -*-
# @Time    : 2025/3/8 13:11
# @Author  : cfushn
# @Comments: 
# @Software: PyCharm
import sys

import bpy

from config import cfg

context = bpy.context
scene = bpy.context.scene
render = bpy.context.scene.render
_inited = False


def initialize():
    global _inited
    # 同一线程中初始化保证仅一次
    if _inited:
        return

    # 删除默认立方体
    context.active_object.select_set(True)  # 仅选中当前激活的对象
    bpy.ops.object.delete()  # 删除选中的对象 (use_global=False是默认值)

    # --------------------------- 渲染设置 ---------------------------
    render.engine = cfg.engine
    render.image_settings.color_mode = 'RGBA'  # 颜色模式（RGB 或 RGBA）
    render.image_settings.color_depth = cfg.color_depth
    render.image_settings.file_format = cfg.format  # 输出文件格式
    render.resolution_x = cfg.resolution
    render.resolution_y = cfg.resolution
    render.resolution_percentage = 100  # 100% 解析度
    render.film_transparent = cfg.bg_transparent  # 是否启用透明背景

    # --------------------------- 背景设置 ---------------------------
    if not cfg.bg_transparent:
        # todo
        pass

    # --------------------------- 多通道输出节点设置 ---------------------------
    multi_output()

    # --------------------------- 光源设置 ---------------------------
    # 获取默认的光源并修改其参数
    light = bpy.data.lights['Light']
    light.type = 'SUN'  # 设置为太阳光
    # 添加第二个太阳光源，用于填充阴影区域
    bpy.ops.object.light_add(type='SUN')
    light2 = bpy.data.lights['Sun']
    light.use_shadow = False  # 关闭阴影
    light2.use_shadow = False
    light.specular_factor = 1.0  # 维持高光
    light2.specular_factor = 1.0
    light.energy = cfg.light_energy  # 调整光照强度
    light2.energy = cfg.light_energy / 2  # 辅助光源强度
    # 旋转第二个光源，使其方向与第一个相反
    bpy.data.objects['Sun'].rotation_euler = bpy.data.objects['Light'].rotation_euler
    bpy.data.objects['Sun'].rotation_euler[0] += 180

    # --------------------------- 相机设置 ---------------------------
    # 获取场景中的默认相机
    camera = scene.objects['Camera']
    camera.data.sensor_width = 36  # 传感器宽度设置,默认36
    camera.data.sensor_height = 36  # 传感器高度设置,默认24,这里我们要的是方形图片
    scene.collection.objects.link(camera)
    scene.camera = camera
    # 添加摄像机对准原点(创建一个位于原点的空物体)的约束
    obj_empty = bpy.data.objects.new("Empty", None)  # 创建空物体
    obj_empty.location = (0.0, 0.0, 0.0)
    scene.collection.objects.link(obj_empty)
    track_constraint = camera.constraints.new(type='TRACK_TO')
    track_constraint.target = obj_empty
    track_constraint.track_axis = 'TRACK_NEGATIVE_Z'
    track_constraint.up_axis = 'UP_Y'

    _inited = True



def multi_output():
    # 启用额外的渲染通道（法线、颜色）
    # 获取当前的 View Layer
    view_layer = bpy.context.view_layer
    # 启用法线通道（用于生成法线贴图）
    view_layer.use_pass_normal = True
    # 启用漫反射颜色通道（用于获取 Albedo 贴图）
    view_layer.use_pass_diffuse_color = True
    # 启用物体索引通道（用于 ID 贴图）
    view_layer.use_pass_object_index = True
    # 启用深度通道
    view_layer.use_pass_z = True

    # 启用 Blender 的节点渲染系统
    scene.use_nodes = True
    nodes = bpy.context.scene.node_tree.nodes
    links = bpy.context.scene.node_tree.links
    # 清空默认节点
    for n in nodes:
        nodes.remove(n)

    # 创建输入渲染层节点
    render_layers = nodes.new('CompositorNodeRLayers')

    # ----------------- 1.创建深度图输出节点 -----------------
    depth_file_output = nodes.new(type="CompositorNodeOutputFile")
    depth_file_output.label = 'Depth Output'
    depth_file_output.file_slots[0].use_node_format = True
    depth_file_output.format.file_format = cfg.format
    depth_file_output.format.color_depth = cfg.color_depth
    if cfg.format == 'OPEN_EXR':
        # 如果格式是 OPEN_EXR，直接连接深度输出
        links.new(render_layers.outputs['Depth'], depth_file_output.inputs[0])  # 直接连接
    else:
        # 如果是 PNG 或其他格式，需要对深度图进行归一化
        depth_file_output.format.color_mode = "BW"  # 黑白图像
        _map = nodes.new(type="CompositorNodeMapValue")  # 归一化深度
        _map.offset = [-0.7]  # 调整深度偏移
        _map.size = [cfg.depth_scale]  # 设定缩放因子
        _map.use_min = True
        _map.min = [0]  # 最小深度为 0
        links.new(render_layers.outputs['Depth'], _map.inputs[0])  # 连接深度通道
        links.new(_map.outputs[0], depth_file_output.inputs[0])  # 连接归一化后的深度图

    # ----------------- 2.创建法线贴图输出节点 -----------------
    # 创建法线贴图输出节点(用于将法线颜色归一化到 [0,1])
    scale_node = nodes.new(type="CompositorNodeMixRGB")
    scale_node.blend_type = 'MULTIPLY'  # 乘法混合模式
    scale_node.inputs[2].default_value = (0.5, 0.5, 0.5, 1)  # 将法线映射到 [0,1] 范围
    links.new(render_layers.outputs['Normal'], scale_node.inputs[1])
    # 添加偏移，使法线贴图居中在 0.5
    bias_node = nodes.new(type="CompositorNodeMixRGB")
    bias_node.blend_type = 'ADD'  # 加法混合模式
    bias_node.inputs[2].default_value = (0.5, 0.5, 0.5, 0)
    links.new(scale_node.outputs[0], bias_node.inputs[1])  # 连接缩放后的法线到偏移节点
    # 输出节点
    normal_file_output = nodes.new(type="CompositorNodeOutputFile")
    normal_file_output.label = 'Normal Output'
    normal_file_output.file_slots[0].use_node_format = True
    normal_file_output.format.file_format = cfg.format
    links.new(bias_node.outputs[0], normal_file_output.inputs[0])  # 连接到法线输出

    # ----------------- 3.创建反照率（Albedo）输出节点 -----------------
    alpha_albedo = nodes.new(type="CompositorNodeSetAlpha")
    links.new(render_layers.outputs['DiffCol'], alpha_albedo.inputs['Image'])
    links.new(render_layers.outputs['Alpha'], alpha_albedo.inputs['Alpha'])
    albedo_file_output = nodes.new(type="CompositorNodeOutputFile")
    albedo_file_output.label = 'Albedo Output'
    albedo_file_output.file_slots[0].use_node_format = True
    albedo_file_output.format.file_format = cfg.format
    albedo_file_output.format.color_mode = 'RGBA'
    albedo_file_output.format.color_depth = cfg.color_depth
    links.new(alpha_albedo.outputs['Image'], albedo_file_output.inputs[0])

    # ----------------- 4.创建 ID 贴图输出节点 -----------------
    id_file_output = nodes.new(type="CompositorNodeOutputFile")
    id_file_output.label = 'ID Output'
    id_file_output.file_slots[0].use_node_format = True
    id_file_output.format.file_format = cfg.format
    id_file_output.format.color_depth = cfg.color_depth

    if cfg.format == 'OPEN_EXR':
        # 如果是 OPEN_EXR 格式，直接链接ID通道
        links.new(render_layers.outputs['IndexOB'], id_file_output.inputs[0])
    else:
        # 如果是 PNG 或其他格式，则需要映射索引值
        if 'IndexOB' in render_layers.outputs:
            id_file_output.format.color_mode = 'BW'  # 设置 ID 贴图为黑白模式
            divide_node = nodes.new(type='CompositorNodeMath')  # 创建一个数学运算节点（用于数值归一化）
            divide_node.operation = 'DIVIDE'  # 除法运算
            divide_node.use_clamp = False  # 允许超出范围值（不限制输出）
            # 设置除数，将索引归一化到 [0,1] 范围
            divide_node.inputs[1].default_value = 2 ** int(cfg.color_depth)
            # 连接渲染层的物体索引通道（IndexOB）到数学运算节点
            links.new(render_layers.outputs['IndexOB'], divide_node.inputs[0])
            # 将处理后的索引贴图连接到 ID 贴图输出节点
            links.new(divide_node.outputs[0], id_file_output.inputs[0])
        else:
            print("✕ [ERROR] 'IndexOB' output not found in render_layers!")

    # 注意:节点（Compositor）输出系统的路径由两部分组成: base_path + path
    depth_file_output.base_path = cfg.out_folder
    normal_file_output.base_path = cfg.out_folder
    albedo_file_output.base_path = cfg.out_folder
    id_file_output.base_path = cfg.out_folder
    # 保存节点引用,供渲染程序设置输出path
    cfg.depth_file_output = depth_file_output
    cfg.normal_file_output = normal_file_output
    cfg.albedo_file_output = albedo_file_output
    cfg.id_file_output = id_file_output
    # 默认情况下,关闭这些多通道输出节点
    cfg.depth_file_output.mute = True
    cfg.normal_file_output.mute = True
    cfg.albedo_file_output.mute = True
    cfg.id_file_output.mute = True
