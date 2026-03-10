"""
NPC性格维度与人情值系统演示

本示例展示如何：
1. 生成NPC的性格维度（基于职业）
2. 使用人情值系统进行社交互动
3. 根据性格影响人情值成本
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.npc_personality import (
    NPCPersonality, 
    generate_personality_from_job,
    get_social_credit_system,
    TemperEnum, SpiritEnum, IsmEnum, ActStyleEnum
)

# ═══════════════════════════════════════════════════════════════
# 示例1：生成不同职业NPC的性格
# ═══════════════════════════════════════════════════════════════
print("=" * 60)
print("【示例1】不同职业NPC的性格生成")
print("=" * 60)

test_jobs = [
    ('OFFICIAL', ['SMART', 'RIGHTEOUS']),
    ('BANDIT', ['STRONG', 'VILLAIN']),
    ('SCHOLAR', ['SMART', 'RIGHTEOUS']),
    ('MERCHANT', ['GREEDY']),
    ('GUARD', ['BRAVE', 'STRONG']),
]

for job, tags in test_jobs:
    personality = generate_personality_from_job(job, tags)
    print(f"\n职业: {job}")
    print(f"  脾气: {personality.temper_str} ({personality.temper.name})")
    print(f"  胆量: {personality.spirit_str} ({personality.spirit.name})")
    print(f"  主义: {personality.ism_str} ({personality.ism.name})")
    print(f"  风格: {personality.act_style_str} ({personality.act_style.name})")
    print(f"  情义: {personality.friendship_str}")
    print(f"  野心: {personality.ambition}")
    if personality.desire_type_str:
        print(f"  物欲: {personality.desire_type_str} ({personality.desire_str})")

# ═══════════════════════════════════════════════════════════════
# 示例2：人情值系统基础操作
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("【示例2】人情值系统基础操作")
print("=" * 60)

credit_system = get_social_credit_system()

# 玩家ID为0，NPC ID为1、2、3
player_id = 0
npc_a_id = 1
npc_b_id = 2
npc_c_id = 3

# 1. 初始状态
print("\n1. 初始人情值状态:")
print(f"   玩家对NPC A: {credit_system.get_credit(player_id, npc_a_id)}")
print(f"   玩家对NPC B: {credit_system.get_credit(player_id, npc_b_id)}")

# 2. 玩家帮助了NPC A，NPC A欠玩家人情
credit_system.add_credit(player_id, npc_a_id, 50)
print("\n2. 玩家帮助NPC A，获得50人情值:")
print(f"   玩家对NPC A: {credit_system.get_credit(player_id, npc_a_id)}")
print(f"   (正值表示NPC A欠玩家人情)")

# 3. NPC B帮助了玩家，玩家欠NPC B人情
credit_system.add_credit(player_id, npc_b_id, -30)
print("\n3. NPC B帮助玩家，玩家欠30人情值:")
print(f"   玩家对NPC B: {credit_system.get_credit(player_id, npc_b_id)}")
print(f"   (负值表示玩家欠NPC B人情)")

# 4. 检查是否可以请求帮助
print("\n4. 检查请求帮助:")
can_ask_a, reason_a = credit_system.check_can_request(player_id, npc_a_id, 30)
print(f"   向NPC A请求30人情值帮助: {'可以' if can_ask_a else '不可以'} ({reason_a})")

can_ask_b, reason_b = credit_system.check_can_request(player_id, npc_b_id, 30)
print(f"   向NPC B请求30人情值帮助: {'可以' if can_ask_b else '不可以'} ({reason_b})")

# 5. 消耗人情值请求帮助
print("\n5. 消耗人情值:")
success = credit_system.consume_credit(player_id, npc_a_id, 20)
print(f"   向NPC A消耗20人情值: {'成功' if success else '失败'}")
print(f"   剩余人情值: {credit_system.get_credit(player_id, npc_a_id)}")

# ═══════════════════════════════════════════════════════════════
# 示例3：性格影响人情值成本
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("【示例3】性格影响人情值成本")
print("=" * 60)

# 创建不同性格的NPC
idealist = NPCPersonality(
    temper_str="温和", spirit_str="勇敢", ism_str="理想",
    act_style_str="慎重", friendship_str="重视情义",
    ambition=30, desire_str="无欲", desire_type_str="书籍"
)

realist = NPCPersonality(
    temper_str="普通", spirit_str="普通", ism_str="现实",
    act_style_str="普通", friendship_str="普通",
    ambition=70, desire_str="普通", desire_type_str="金钱"
)

greedy = NPCPersonality(
    temper_str="性急", spirit_str="胆小", ism_str="现实",
    act_style_str="轻率", friendship_str="不重情义",
    ambition=80, desire_str="贪心", desire_type_str="金钱"
)

base_cost = 50

print(f"\n基础请求成本: {base_cost}")

# 检查不同性格对请求的影响
print("\n理想主义者（重视情义）:")
can_help, reason = credit_system.check_can_request(player_id, npc_a_id, base_cost, idealist)
print(f"  请求{base_cost}人情值: {'可以' if can_help else '不可以'} - {reason}")

print("\n现实主义者（普通情义）:")
can_help, reason = credit_system.check_can_request(player_id, npc_a_id, base_cost, realist)
print(f"  请求{base_cost}人情值: {'可以' if can_help else '不可以'} - {reason}")

print("\n贪婪者（不重情义）:")
can_help, reason = credit_system.check_can_request(player_id, npc_a_id, base_cost, greedy)
print(f"  请求{base_cost}人情值: {'可以' if can_help else '不可以'} - {reason}")

# ═══════════════════════════════════════════════════════════════
# 示例4：序列化与反序列化
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("【示例4】序列化与反序列化")
print("=" * 60)

# 将性格转为字典（用于存档）
personality_dict = idealist.to_dict()
print("\n性格序列化为字典:")
for key, value in personality_dict.items():
    print(f"  {key}: {value}")

# 从字典恢复
restored = NPCPersonality.from_dict(personality_dict)
print(f"\n恢复后的性格:")
print(f"  脾气: {restored.temper_str}")
print(f"  胆量: {restored.spirit_str}")
print(f"  主义: {restored.ism_str}")

# ═══════════════════════════════════════════════════════════════
# 示例5：每日衰减
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("【示例5】人情值每日衰减")
print("=" * 60)

# 设置一些人情值
credit_system.add_credit(player_id, npc_c_id, 100)
print(f"\n初始人情值: {credit_system.get_credit(player_id, npc_c_id)}")

# 模拟每日衰减（每天衰减5%）
for day in range(1, 6):
    credit_system.daily_decay()
    print(f"第{day}天后: {credit_system.get_credit(player_id, npc_c_id)}")

print("\n" + "=" * 60)
print("演示完成！")
print("=" * 60)
