"""
困境生成 + 性格维度集成演示

展示如何使用NPC的多维度性格来生成更有深度的困境。
"""
import sys
sys.path.insert(0, 'e:\\pyscript\\aistory')

from src.aistory.dilemma_deriver import NPCData, DilemmaDeriver
from src.aistory.dilemma_seed import DilemmaPhase
from src.aistory.shared_types import WorldSnapshot


def demo_personality_impact():
    """演示不同性格如何影响困境生成"""
    
    print("=" * 60)
    print("困境生成 - 性格维度影响演示")
    print("=" * 60)
    
    # 创建两个性格迥异的NPC
    npcs = [
        # NPC 1: 理想主义的勇敢侠客
        NPCData(
            npc_id="1",
            name="李大侠",
            gender="男",
            age=35,
            identity="侠客",
            org="游侠会",
            wealth=80,
            emotion=70,
            health=95,
            backstory="曾是朝廷武将，因不满官场腐败而辞官行走江湖",
            # 性格维度
            temper="温和",
            spirit="勇敢",
            ism="理想",
            act_style="慎重",
            friendship="重视情义",
            ambition=75,
            desire_type="名声",
            desire_level="高",
            social_credit=20  # 欠玩家人情
        ),
        
        # NPC 2: 现实主义的谨慎商人
        NPCData(
            npc_id="2",
            name="王掌柜",
            gender="男",
            age=50,
            identity="商人",
            org="商会",
            wealth=500,
            emotion=40,
            health=70,
            backstory="白手起家，靠精明算计积累财富",
            # 性格维度
            temper="性急",
            spirit="谨慎",
            ism="现实",
            act_style="大胆",
            friendship="轻视情义",
            ambition=60,
            desire_type="金钱",
            desire_level="极高",
            social_credit=-30  # 玩家欠他人情
        ),
        
        # NPC 3: 胆小的理想主义学者
        NPCData(
            npc_id="3",
            name="张书生",
            gender="男",
            age=25,
            identity="学者",
            org="太学",
            wealth=20,
            emotion=60,
            health=80,
            backstory="寒窗苦读，希望考取功名报效国家",
            # 性格维度
            temper="温和",
            spirit="胆小",
            ism="理想",
            act_style="慎重",
            friendship="重视情义",
            ambition=80,
            desire_type="知识",
            desire_level="高",
            social_credit=0
        )
    ]
    
    # 创建困境生成器（无LLM模式，使用启发式规则）
    deriver = DilemmaDeriver(llm_service=None)
    
    # 创建世界状态
    world_state = WorldSnapshot(
        timestamp=1.0,
        game_time="第1天 12:00",
        player_reputation={},
        faction_tensions={}
    )
    
    print("\n" + "=" * 60)
    print("1. 性格画像展示")
    print("=" * 60)
    
    for npc in npcs:
        print(f"\n【{npc.name}】")
        print(npc.get_personality_profile())
        print(f"行为倾向: {npc.get_behavior_tendency()}")
    
    print("\n" + "=" * 60)
    print("2. 核心矛盾推导（基于性格）")
    print("=" * 60)
    
    for npc in npcs:
        desire, reality = deriver._derive_core_conflict(npc)
        print(f"\n【{npc.name}】")
        print(f"  欲望: {desire}")
        print(f"  阻碍: {reality}")
    
    print("\n" + "=" * 60)
    print("3. 张力线生成（启发式规则）")
    print("=" * 60)
    
    for npc in npcs:
        tensions = deriver._derive_tensions_heuristic(npc, world_state)
        print(f"\n【{npc.name}】")
        if tensions:
            for t in tensions:
                print(f"  [{t.type.value}] {t.force_a} vs {t.force_b}")
                print(f"    强度: {t.intensity} | 潜在危机: {t.potential_crisis}")
        else:
            print("  暂无显著张力")
    
    print("\n" + "=" * 60)
    print("4. 完整困境种子生成")
    print("=" * 60)
    
    import asyncio
    
    async def generate_seeds():
        for npc in npcs:
            seed = await deriver.create_seed(npc, world_state)
            print(f"\n【{npc.name} 的困境种子】")
            print(f"  核心欲望: {seed.desire}")
            print(f"  现实阻碍: {seed.reality_block}")
            print(f"  当前热度: {seed.heat:.1f}")
            print(f"  困境阶段: {seed.phase.value}")
            print(f"  张力线数量: {len(seed.tensions)}")
            for t in seed.tensions:
                print(f"    - [{t.type.value}] 强度{t.intensity}: {t.force_a[:20]}... vs {t.force_b[:20]}...")
    
    asyncio.run(generate_seeds())
    
    print("\n" + "=" * 60)
    print("5. 人情值系统演示")
    print("=" * 60)
    
    for npc in npcs:
        print(f"\n【{npc.name}】")
        if npc.social_credit > 0:
            print(f"  ✓ 欠玩家 {npc.social_credit} 点人情")
            print(f"  → 可以消耗人情请TA帮忙")
        elif npc.social_credit < 0:
            print(f"  ✗ 玩家欠其 {-npc.social_credit} 点人情")
            print(f"  → TA可能会要求回报")
        else:
            print(f"  ○ 人情值平衡")
    
    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)
    print("""
总结：
1. 不同性格的NPC会产生不同类型的困境
2. 理想主义者面临理想与现实的冲突
3. 现实主义者面临利益与道德的权衡
4. 重视情义的人会在人际关系中陷入困境
5. 人情值系统影响NPC帮助玩家的意愿
""")


if __name__ == "__main__":
    demo_personality_impact()
