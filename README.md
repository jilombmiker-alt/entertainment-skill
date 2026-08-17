# 娱乐类 Skills

面向 AI 产品经理作品集的三个娱乐体验 Skill，重点展示真实世界 Agent、状态管理、多模态交互和安全边界设计。

## 包含的 Skill

| Skill | 核心体验 | 产品设计亮点 |
|---|---|---|
| `run-parallel-city-adventure` | 把真实城市变成可分支的户外冒险 | 北京样板路线、地点核验、自由选择完成验证、状态保存、天气和地点安全降级 |
| `play-story-reflection-cards` | 用原创卡牌进行个人反思、朋友对话或创作 | 24 张原创卡、Seed 复现、无重复抽取、三种视觉形式、随时跳过与非占卜边界 |
| `interpret-bazi-astrology` | 进行八字、星盘、命盘与星象的文化解读 | 动态资料确认、精度分级、跨体系综合、连续追问与非决定论安全边界 |

## 本地安装

### Codex Skill 安装器

```text
$skill-installer 安装这个仓库中的全部 Skill：
https://github.com/jilombmiker-alt/entertainment-skill/tree/main/skills
```

### Mac 终端

```bash
git clone https://github.com/jilombmiker-alt/entertainment-skill.git
cd entertainment-skill
bash install.sh
```

默认安装到 `~/.agents/skills/`。脚本发现同名 Skill 时会跳过，不会覆盖已有内容。

## Mac 桌面端使用

1. 打开 ChatGPT Mac 桌面端并登录。
2. 在侧边栏打开 **Skills**，确认三个 Skill 已出现。
3. 在 ChatGPT 中输入 `@` 后选择 Skill；在 Codex CLI 或 IDE 中输入 `$` 后选择 Skill。
4. 也可以直接描述任务，让系统根据 Skill 描述自动调用。
5. 刚安装后未出现时，刷新或重新打开 Skills 页面。

## 使用示例

### 城市平行人生

```text
@run-parallel-city-adventure
周六下午我想在北京什刹海进行一次 60 分钟的单人实景冒险。
不进入收费场馆，不要求上传照片，完成验证由我自己选择。
```

适合城市寻宝、实景剧情和互动 Citywalk。普通旅游攻略、餐厅推荐或纯虚构故事不会触发它。

### 故事反思卡

```text
@play-story-reflection-cards
给我抽 3 张朋友对话卡，不要恋爱和家庭话题。
使用文字符号卡，逐张展示，我可以随时跳过。
```

也可以上传照片生成故事卡。它用于轻反思和创作，不提供占卜、诊断或心理治疗。

### 观象命盘顾问

```text
@interpret-bazi-astrology
我想从八字或星盘看看事业方向。请先确认还缺哪些出生资料，资料不足时不要猜盘。
```

支持八字、西方星盘、紫微斗数、六爻及跨体系综合解读。它会先确认日期口径、出生时间、出生城市和咨询主题，再按资料精度作非决定论分析。

## 自测

```bash
python3 skills/run-parallel-city-adventure/scripts/adventure_state.py self-test
python3 skills/play-story-reflection-cards/scripts/draw_cards.py self-test
```

两个脚本均只使用 Python 标准库。

## 官方文档

- [OpenAI 文档：构建 Skills](https://learn.chatgpt.com/docs/build-skills)
- [OpenAI 文档：ChatGPT 桌面应用](https://learn.chatgpt.com/docs/app)
