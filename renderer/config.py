# -*- coding: utf-8 -*-
# @Time    : 2025/3/7 17:41
# @Author  : cfushn
# @Comments: 
# @Software: PyCharm

class BaseConfig:
    # ---------------- 全局配置 ----------------

    is_test = True  # 如果是测试, 则每个模型输出单张图片,仅供预览
    multi_output_channel = False  # 是否需要额外的输出通道
    h5_output = True  # 是否输出h5文件

    version: str = "v1"  # shapeNet版本
    resolution: int = 128  # 分辨率
    lens_list: [float] = [10, 50, 100]  # 焦距mm (50mm为标准焦距)
    elevation_min: float = 0  # 俯仰旋转角度min°
    elevation_max: float = 60  # 俯仰旋转角度max°
    elevation_step_degree: float = 10  # 俯仰旋转角度间隔°
    azimuth_min: float = 0  # 水平旋转角度min°
    azimuth_max: float = 90  # 水平旋转角度max°
    azimuth_step_degree: float = 1  # 水平旋转角度间隔°
    color_depth: str = '8'  # 颜色深度('8','16'),RGBA每通道的比特数,前者对应0-255,后者0-65535
    format: str = 'PNG'  # 输出文件格式 'PNG', 'OPEN_EXR', 'JPEG', ...
    engine: str = 'BLENDER_EEVEE'  # 渲染引擎 "CYCLES",'BLENDER_EEVEE'
    bg_transparent = True  # 是否启用透明背景

    scale: float = 1.0  # 缩放模型
    depth_scale: float = 1.0  # 深度缩放比例
    light_energy: float = 5.0  # 主光源强度
    remove_doubles = True  # 是否需要移除重复顶点，优化网格
    edge_split = True  # 是需要否添加边缘分割修正

    @property
    def data_folder(self) -> str:
        """shapeNetCore文件夹"""
        return f"/home/cy/datasets/ShapeNetCore.{self.version}"

    @property
    def out_folder(self) -> str:
        return (f"/home/cy/workdir/cfushn-shapeNet-renderer/out"
                f"/{self.version}/{self.resolution}x{self.resolution}")

    # ---------------- 程序内传值用变量, 无需设置 ----------------
    # 额外的输出通道节点引用,便于后续设置路径
    depth_file_output = None
    normal_file_output = None
    albedo_file_output = None
    id_file_output = None

    # 配置类,采用单例模式
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(BaseConfig, cls).__new__(cls)
        return cls._instance


# 直接创建默认配置（单例）
cfg = BaseConfig.__new__(BaseConfig)
