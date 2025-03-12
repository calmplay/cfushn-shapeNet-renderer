# -*- coding: utf-8 -*-
# @Time    : 2025/3/7 17:41
# @Author  : cfushn
# @Comments: 
# @Software: PyCharm

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

class BaseConfig:
    # ---------------- 全局配置 ----------------

    is_test = False  # 如果是测试, 则每个模型输出单张图片,仅供预览
    multi_output_channel = False  # 是否需要额外的输出通道
    h5_output = True  # 是否输出h5文件

    # class_id_list = ["02924116","04379243","04401088","02773838","02843684","02992529","04225987","04530566","03948459","03636649","04004475","03325088","02747177","02942699","02876657","03759954","04554684","04074963","03337140","02818832","03467517","02801938","03790512","02933112","03991062","02880940","03710193","03593526","04090263","02808440","03624134","03085013","02946921","03001627","03642806","03797390","02958343","03938244","02691156","04460130","03691459","03046257","03207941","02871439","04256520","02954340","03261776","03761084","03513137","02828884","04099429","03211117","03928116","04468005","04330267"]
    class_id_list = ["02691156", "02773838", "02954340", "02958343", "03001627",
                     "03261776", "03467517", "03624134", "03636649", "03642806", "03790512",
                     "03797390", "03948459", "04099429", "04225987", "04379243"]
    # class_id_list = ["03790512"]
    obj_per_class: int = 100  # 每个类别读取的obj模型个数
    obj_batch_size: int = 10  # 每个任务处理的obj个数(不宜过高,考虑内存堆积或泄露等隐患)

    """渲染总数量 = 类别数 ✕ 每类下obj数 ✕ 焦距steps ✕ 俯仰角steps ✕ 水平角steps """

    version: str = "v1"  # shapeNet版本
    resolution: int = 256  # 分辨率
    render_dropout: float = 0.99  # 每次放弃渲染的概率(减少连续标签组合导致的爆炸式渲染数量)
    lens_list: [float] = [100]  # 焦距mm (50mm为标准焦距(近似人眼))
    elevation_min: float = 0  # 俯仰旋转角度min°
    elevation_max: float = 60  # 俯仰旋转角度max°
    elevation_step_degree: float = 1  # 俯仰旋转角度间隔°
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
