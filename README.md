<!-- 项目 Logo 或开篇示意图（请在本地 repo 的 Fig 文件夹中替换同名文件即可） -->
<p align="center">
  <img src="Fig/SuperWriter.png" width="500px" alt="SuperWriter Logo">
</p>


# 📚 SuperWriter: Reflection-Driven Long-Form Generation with Large Language Models


*SuperWriter*-agent 是一个面向 **长篇文本生成** 的智能写作框架，灵感源于人类作者的“先思考、后下笔”工作流。通过 **Plan → Write → Refine** 的三阶段代理式流程生成数据与分层偏好优化（Hierarchical DPO），训练后的SuperWriter-LM 在 **7 B 参数** 规模下即可实现对更大模型的竞争性甚至领先性表现。

---

## 🚀 论文速览


> **标题**  SuperWriter: *Reflection-Driven Long-Form Generation with Large Language Models*  
> **模型**  即将开放 - SuperWriter-LM (Qwen-2.5-7B-instruction 基础)  
> **要点** :
> 1. 提出 **SuperWriter-Agent**，显式嵌入 *Thinking* 与 *Reflection* 信号。  
> 2. 构建三阶段、共 **12 k** 条 SFT 数据 (4 k Plan / 4 k Write / 4 k Refine)。  
> 3. 设计 **Hierarchical DPO + MCTS**，从最终输出反向传播质量信号。  
> 4. 在 **WritingBench** 综合得分 **8.51**，位列全部模型第二，仅次于 DeepSeek-R1 (671 B)。  


---

## 🛠️ 方法框架
<p align="center">
  <img src="/Users/wyh/Desktop/SuperWriter/Fig/Agent (1).png" width="700px" alt="SuperWriter Logo">
</p>


| 阶段 | 角色 / 子步骤 | 目标 | 关键机制 |
|------|---------------|------|----------|
| **1️⃣ Plan** | *AI Commentators ↔ Writer*<br/>Plan Checker | - 提炼主题、设定结构<br/>- 输出段落级大纲 | Story-Workshop 式对话；字数分配；结构一致性检测 |
| **2️⃣ Write** | *Thinker → Writer* | - 按大纲逐段撰写<br/>- 保持章节连贯 | **Thinker Step**：列要点 & 逻辑 & 衔接<br/>**Writer Step**：生成正文，引用上一段上下文 |
| **3️⃣ Refine** | Checker → Editor | - 精准润色草稿<br/>- 提升语言与逻辑质量 | **Checker**：定位问题段落<br/>**Editor**：针对性重写或合并 |

### 分层 DPO (Hierarchical DPO)

<p align="center">
  <img src="Fig/DPO (1).png" width="600px" alt="SuperWriter Logo">
</p>

> 使用 **Monte-Carlo Tree Search** 构建 (Plan i, Draft j, Refine k) 三层写作树，  
> 以叶节点最终质量打分并离散化 (+2 ~ −2)，自下而上平均聚合形成多级偏好对，  
> 再用 DPO 损失统一优化。

---

## 📈 实验结果

### 1. WritingBench 综合评测

<p align="center">
  <img src="/Users/wyh/Desktop/SuperWriter/Fig/WritingBench.png" width="600px" alt="SuperWriter Logo">
</p>

*SuperWriter-LM* 在 **Academic & Engineering / Finance & Business / Politics & Law / Education** 四大领域取得最高分，在同尺寸模型中排名第一。

### 2. 用户查询 Win-Rate
<p align="center">
  <img src="/Users/wyh/Desktop/SuperWriter/Fig/winrate_plots.png" width="600px" alt="SuperWriter Logo">
</p>
> **计算规则**：Win = 1，Tie = 0.5，Loss = 0 ；共 8 组 Donut 图，其中第 8 组为人工评估。SuperWriter-LM 在 7 B 组别保持绝对领先，对更大模型亦具竞争力。

---

## 🧑‍💻 代码说明

### 1. Agent 数据生成
- 使用 `Agent/Super_write_agent.py` 和 `Agent/Super_write_agent_cn.py`  
  根据输入的 `query` 分别生成英文版与中文版的三阶段（Plan/Write/Refine）SFT 数据。

### 2. SFT 数据后处理
- 使用 `Agent/SFT-Process.py`  
  对 Agent 生成的原始 SFT 数据进行清洗，输出统一结构的 JSONL 文件。

---

### 🔄 分层 DPO 数据构建

1. 部署SFT的model评估服务（如使用 SGLang 或自定义 HTTP 接口）。

2. 使用 `DPO/MCTS_inference.py`  
   基于清洗后的 SFT 数据和三阶段 Agent 输出，通过 MCTS 探索不同的 Plan → Write → Refine 组合，产出候选叶子节点集。

3. 使用 `DPO/Step_1_query_evaluation_stand.py`  
   为每个 `query` 生成三阶段的评价标准文本，用于后续打分。

4. 使用 `DPO/Step_2_LLM_judge.py`  
   利用部署好的评估服务，对所有 MCTS 叶子节点进行质量打分。

5. 在 `DPO/create_dpo_pair.ipynb` 中  
   根据叶子节点分数，从每棵 MCTS 树中选取“优”与“劣”样本对，生成最终的 DPO 训练对。

---

### ▶️ 推理流程
- 推理分为三阶段：Plan → Write → Refine。  
- 每个阶段使用对应的 Prompt 模板，串联三次推理获得最终输出，参考`Inference/superwrite_gen.py`的输出方式

---

### 🏋️‍♂️ 模型训练
- 使用 **LLaMA-Factory** 与 **360-LLama-Factory** 进行微调。  

---

## 🤝 引用

```bibtex
@article{wu2025superwriter,
  title   = {SuperWriter: Reflection-Driven Long-Form Generation with Large Language Models},
  author  = {Yuhao Wu and Yushi Bai and Zhiqiang Hu and Juanzi Li and Roy Ka-Wei Lee},
  journal = {arXiv preprint arXiv:2506.XXXXX},
  year    = {2025}
}
```

---