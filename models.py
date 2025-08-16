from tortoise.models import Model
from tortoise import fields

from utils import short_uuid


class PIM(Model):
    """问诊对话"""
    id = fields.IntField(pk=True)
    uid = fields.CharField(max_length=6, unique=True, default=short_uuid)

    # patient = fields.JSONField(default=list)  # 患者回答 ["...", "...", ...]
    # ai = fields.JSONField(default=list)  # AI 提问 ["...", "...", ...]

    qa_messages = fields.JSONField(default=list)  # 问诊对话 [{"role": "user", "content": "..."}, {"role": "system", "content": "..."}, ...]

    diseases = fields.JSONField(default=list)  # 每轮问诊对话的各个疾病概率 [{"D1": 0.4, ...}, ...]
    symptoms = fields.JSONField(default=dict)  # 根据患者回答判断症状是否发生 {"S1": True, "S2": False, "S3": None, ...}

    ieg = fields.JSONField(default=list)  # 每轮问诊对话，针对各个症状带来的熵增 [{"S1": 0.003, ...}, ...]

    addition = fields.CharField(max_length=60, default="")  # 患者补充内容 "..."

    symptom_opt = fields.CharField(max_length=30, default="")  # 辅助：最优症状
    delta_ieg = fields.JSONField(default=list)  # 辅助：熵增的变化率 [0.001, 0.004, ...]
    is_related = fields.BooleanField(default=True)  # 辅助：患者当前轮次的回答是否与问题相关
    unrelated_count = fields.IntField(default=0)  # 辅助：患者不相关回答的次数

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "pim"


class PSG(Model):
    """患者报告记录"""
    id = fields.IntField(pk=True)
    uid = fields.CharField(max_length=6, unique=True)

    pim = fields.ForeignKeyField("models.PIM", related_name="psg", on_delete=fields.CASCADE)

    disease_opt = fields.CharField(max_length=32, default="")  # 最可能疾病名
    report = fields.TextField(default="")  # 患者报告记录（较长），markdown 语法，含表情

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "psg"


class CDG(Model):
    """病历记录"""
    id = fields.IntField(pk=True)
    uid = fields.CharField(max_length=6, unique=True)

    pim = fields.ForeignKeyField("models.PIM", related_name="cdg", on_delete=fields.CASCADE)

    initial = fields.TextField(default="")  # 初步诊断
    disease_opt = fields.CharField(max_length=32, default="")  # 最可能疾病名
    soap = fields.TextField(default="")  # 病历记录（较长），markdown 语法

    disease_opt_dict = fields.JSONField(default=dict)  # 最可能疾病字典 {'D1': 0.3, ...}

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "cdg"


# 下面的表为评分表
class EVAL(Model):
    """评分"""
    id = fields.IntField(pk=True)
    uid = fields.CharField(max_length=6, unique=True)

    pim = fields.ForeignKeyField("models.PIM", related_name="eval", on_delete=fields.CASCADE)

    patient_eval = fields.JSONField(default=list)
    doctor_eval = fields.JSONField(default=list)

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "eval"


# 管理员用户
class Admin(Model):
    """管理员用户"""
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=32, unique=True)
    password = fields.CharField(max_length=128)

    class Meta:
        table = "admin"


# 下面三个表仅作为查询
class DiseaseProb(Model):
    """查询疾病概率，只读"""
    id = fields.IntField(pk=True)

    disease = fields.CharField(max_length=32)
    probability = fields.FloatField()

    class Meta:
        table = "disease_prob"


class SymptomProb(Model):
    """查询症状概率，只读"""
    id = fields.IntField(pk=True)

    symptom = fields.CharField(max_length=32)
    probability = fields.FloatField()

    class Meta:
        table = "symptom_prob"


# 暂未使用!
class RelationDiseaseSymptom(Model):
    """查询各种疾病的症状列表，只读"""
    id = fields.IntField(pk=True)

    disease = fields.CharField(max_length=32)
    symptom_list = fields.JSONField(default=list)

    class Meta:
        table = "relation_disease_symptom"


# medical 知识库
class MedicalKnowledge(Model):
    """医学百科"""
    name = fields.CharField(max_length=32)  # 疾病名称

    check = fields.JSONField(default=list)  # 检测项目
    category = fields.JSONField(default=list)  # 所属科室
    cure_department = fields.JSONField(default=list)  # 治疗科室

    symptom = fields.JSONField(default=list)  # 病征
    accompany = fields.JSONField(default=list)  # 并发症

    prevent = fields.TextField(default="")  # 预防方式
    cure_way = fields.JSONField(default=list)  # 治疗方法

    common_drug = fields.JSONField(default=list)  # 常用药
    recommend_drug = fields.JSONField(default=list)  # 推荐药物
    not_eat = fields.JSONField(default=list)  # 忌口
    do_eat = fields.JSONField(default=list)  # 推荐饮食

    class Meta:
        table = "medical_knowledge"


class ExperimentData(Model):
    """测试数据"""
    uid = fields.CharField(max_length=10, unique=True)  # uid
    diagnosis = fields.CharField(max_length=32)  # 诊断结果 "..."
    self_report = fields.TextField(default="")  # 初次自述 "..."
    dialogue = fields.JSONField(default=list)  # 对话 [{"医生": "..."}, {"患者": "..."}]
    description = fields.TextField(default="")  # 整理后的主诉
    symptom = fields.JSONField(default=dict)  # 症状 {"S1": True, ...}

    class Meta:
        table = "experiment_data"


class ExperimentPIM(Model):
    """模拟测试"""
    uid = fields.CharField(max_length=10, unique=True)  # uid
    diagnosis = fields.CharField(max_length=32)  # 诊断结果 "..."
    self_report = fields.TextField(default="")  # 初次自述 "..."

    dialogue = fields.JSONField(default=list)  # 问诊对话 [{"doctor": "..."}, {"patient": "..."}, ...]

    diseases = fields.JSONField(default=list)  # 每轮问诊对话的各个疾病概率 [{"D1": 0.4, ...}, ...]
    symptoms = fields.JSONField(default=dict)  # 症状 {"S1": True, ...}

    ieg = fields.JSONField(default=list)  # 每轮问诊对话，针对各个症状带来的熵增 [{"S1": 0.003, ...}, ...]
    symptom_opt = fields.CharField(max_length=30, default="")  # 辅助：最优症状
    delta_ieg = fields.JSONField(default=list)  # 辅助：熵增的变化率 [0.001, 0.004, ...]

    diseases_with_ai = fields.JSONField(default=list)

    # session_id = fields.CharField(max_length=100, null=True, default=None)
    assistant_id = fields.CharField(max_length=100, null=True, default=None)
    thread_id = fields.CharField(max_length=100, null=True, default=None)

    disease_prob_addition = fields.JSONField(default=dict)  # {"D1": 0.4, ...}
    symptom_dict_addition = fields.JSONField(default=dict)  # {"S1": True, ...}

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "experiment_pim"


class ExperimentOnlyAI(Model):
    """模拟测试, 只有 AI"""
    uid = fields.CharField(max_length=10, unique=True)  # uid
    diagnosis = fields.CharField(max_length=32)  # 诊断结果 "..."
    self_report = fields.TextField(default="")  # 初次自述 "..."

    dialogue = fields.JSONField(default=list)  # 问诊对话 [{"doctor": "..."}, {"patient": "..."}, ...]

    symptoms = fields.JSONField(default=dict)  # 症状 {"S1": True, ...}, 来自 ExperimentData

    diseases_pred = fields.JSONField(default=list)

    # session_id = fields.CharField(max_length=100, null=True, default=None)
    assistant_id = fields.CharField(max_length=100, null=True, default=None)
    thread_id = fields.CharField(max_length=100, null=True, default=None)

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "experiment_only_ai"
