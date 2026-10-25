"""Rebuild the overview graphic and apply lossless paragraph formatting once.

Run from any directory. Requires Pillow for the PNG overview.
"""
from pathlib import Path
import re
from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent
REPORT = BASE.parent / '02-技术方案' / 'PoL2存储技术方案.md'
FIG = BASE / 'figures'
FIG.mkdir(exist_ok=True)
font_path = 'C:/Windows/Fonts/msyh.ttc'
def font(size):
    return ImageFont.truetype(font_path, size)

im = Image.new('RGB', (1600, 920), '#f3f6fa')
d = ImageDraw.Draw(im)
d.text((65, 40), 'PoL2 高密度存储 · 架构总览', font=font(46), fill='#172b4d')
d.text((65, 110), '方案提议 / 待工程验证    |    先保证事实与版本正确，再按测量扩展规模', font=font(25), fill='#465b75')
cards = [
    (65, 190, 525, 455, '#e1edff', '01  权威事实', ['不可变多模态原件', '版本化事件账本', '事务性元数据'], '保存事实、历史与当前可见状态'),
    (570, 190, 1030, 455, '#e0f2eb', '02  版本化派生', ['混合检索与关系投影', '训练数据集与代理记忆', '索引、摘要与缓存'], '有来源、可撤销、按条件重建'),
    (1075, 190, 1535, 455, '#fff0d8', '03  受控行动', ['一致快照中的证据', '当前权限与撤销检查', '许可消费与执行留痕'], '确定性门禁约束 AI 行动'),
]
for x1,y1,x2,y2,color,title,items,foot in cards:
    d.rounded_rectangle((x1,y1,x2,y2), 18, fill=color)
    d.text((x1+25,y1+20), title, font=font(31), fill='#172b4d')
    for j,item in enumerate(items):
        d.text((x1+25,y1+82+j*42), '• '+item, font=font(26), fill='#263d55')
    d.text((x1+25,y2-43), foot, font=font(22), fill='#465b75')
for x in [535,1040]:
    d.polygon([(x,305),(x+23,320),(x,335)],fill='#536b89')
d.rounded_rectangle((65,505,1535,635),18,fill='#172b4d')
d.text((95,525), '贯穿全链路的约束',font=font(30),fill='white')
d.text((95,579), '来源与许可  /  版本与快照  /  保留与删除  /  故障恢复  /  可观测与回放',font=font(28),fill='#e5edf7')
d.text((65,683),'实施顺序',font=font(30),fill='#172b4d')
for x,title,sub in [(65,'地面原型','验证提交、过滤、撤销、回放、迁移'),(570,'地面生产','实测瓶颈触发分区、解耦与湖仓'),(1075,'轨道配置','另行通过辐照、热、功率资格验证')]:
    d.text((x,741),title,font=font(29),fill='#172b4d')
    d.text((x,790),sub,font=font(23),fill='#465b75')
d.text((65,865),'读图提示：派生物不能代替权威事实；轨道配置不代表已经具备飞行资格。',font=font(22),fill='#465b75')
im.save(FIG/'architecture-overview.png')

text = REPORT.read_text(encoding='utf-8')
if '<!-- readability-v2 -->' in text:
    print('Overview regenerated; report already formatted.')
    raise SystemExit(0)
old = text
blocks = text.split('\n\n')
output=[]
in_fence=False
changed=0
for block in blocks:
    if '```' in block:
        output.append(block)
        continue
    # Tables, headings, equations, lists and source blocks retain their layout.
    if len(block)>210 and '\n' not in block and not re.match(r'\s*(?:[|#>\-$]|\d+[.)])',block):
        parts = re.split(r'(?<=[。！？])', block)
        groups=[]
        current=''
        for part in parts:
            if current and len(current)+len(part)>175:
                groups.append(current)
                current=part
            else:
                current+=part
        if current: groups.append(current)
        assert ''.join(groups)==block
        output.append('\n\n'.join(groups))
        changed+=len(groups)-1
    else:
        output.append(block)
text='\n\n'.join(output)
# All pre-existing characters remain in their original order; only whitespace added.
assert re.sub(r'\s','',old)==re.sub(r'\s','',text)
nav='''<!-- readability-v2 -->

> **汇报主线：先建立可信事实与版本边界，再扩展 AI 检索、训练与行动闭环。** 本文为技术方案；容量数字属于假设情景，性能与轨道能力仍待验证。

![PoL2 架构总览：权威事实、版本化派生、受控行动及实施顺序](../03-复算与支撑/figures/architecture-overview.png)

*图 1｜阅读总览。详细的数据流、提交时序与恢复状态图分别见第 4、5、9 节。*

### 按汇报问题阅读

| 你要回答的问题 | 直接阅读 | 应带走的结论 |
| --- | --- | --- |
| 为什么需要 V2？ | [执行摘要](#section-1)、[V1 修正](#section-2) | 保留事实，把索引和模型产物作为派生层 |
| 系统具体怎么组织？ | [数据模型](#section-3)、[架构](#section-4)、[写入协议](#section-5) | 权威状态、版本发布和可见性必须一致 |
| 如何适应 AI？ | [混合检索](#section-6)、[数据闭环](#section-7)、[回放与 API](#section-11) | 检索、训练、记忆、授权分别管理 |
| 规模和成本多大？ | [容量模型与情景](#section-8) | 计算副本、迁移和空闲储备；不能只算向量 |
| 如何保证可靠与自治？ | [恢复与删除](#section-9)、[安全边界](#section-10) | 可恢复、可撤销、可审计才能进入生产 |
| 现在能做什么，怎么验收？ | [代码衔接](#section-13)、[验收路线](#section-14)、[风险](#section-15) | 先过正确性闸门，再测规模与故障 |
| 轨道部署有哪些前提？ | [轨道约束](#section-12)、[一手来源](#section-16) | 地面验证不能替代任务资格验证 |

---

'''
pos=text.index('## 1.')
text=text[:pos]+nav+text[pos:]
text=re.sub(r'(?m)^(## (\d+)\. .*)$',lambda m:f'<a id="section-{m[2]}"></a>\n\n{m[1]}',text)
REPORT.write_text(text,encoding='utf-8')
print(f'Added {changed} paragraph breaks, navigation and overview graphic; original text preserved.')
