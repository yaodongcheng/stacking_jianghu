"""
滚动故事生成器 + 性格维度集成演示

展示StoryDirector如何协调滚动故事生成，并确保性格影响叙事。
"""
import sys
sys.path.insert(0, 'e:\\pyscript\\aistory')

import asyncio
from src.aistory.story_director import StoryDirector, DirectorConfig
from src.aistory.dilemma_deriver import NPCData
from src.aistory.shared_types import WorldSnapshot


def create_test_npcs():
    """创建测试NPC"""
    return [
        NPCData(
            npc_id="hero_01",
            name="李大侠",
            gender="男",
            age=35,
            identity="侠客",
            org="游侠会",
            wealth=80,
            emotion=70,
            health=95,
            backstory="曾是朝廷武将，因不满官场腐败而辞官行走江湖",
            temper="温和",
            spirit="勇敢",
            ism="理想",
            act_style="慎重",
            friendship="重视情义",
            ambition=75,
            desire_type="名声",
            desire_level="高",
            social_credit=20
        ),
        NPCData(
            npc_id="merchant_01",
            name="王掌柜",
            gender="男",
            age=50,
            identity="商人",
            org="商会",
            wealth=500,
            emotion=40,
            health=70,
            backstory="白手起家，靠精明算计积累财富",
            temper="性急",
            spirit="谨慎",
            ism="现实",
            act_style="大胆",
            friendship="轻视情义",
            ambition=60,
            desire_type="金钱",
            desire_level="极高",
            social_credit=-30
        )
    ]


async def demo_story_director():
    """演示StoryDirector如何工作"""
    
    print("=" * 70)
    print("滚动故事生成器 + 性格维度集成演示")
    print("=" * 70)
    
    # 创建导演系统（不使用LLM，使用启发式规则）
    config = DirectorConfig(
        max_concurrent_arcs=5,
        heat_threshold=10,  # 降低阈值以便演示
        enable_llm=False
    )
    director = StoryDirector(llm_service=None, config=config)
    
    # 创建世界状态
    world_state = WorldSnapshot(
        timestamp=1.0,
        game_time="第1天 12:00",
        player_reputation={},
        faction_tensions={}
    )
    
    # 注册NPC
    print("\n" + "=" * 70)
    print("1. 注册NPC到导演系统")
    print("=" * 70)
    
    npcs = create_test_npcs()
    for npc in npcs:
        seed = director.register_npc(npc)
        print(f"\n【{npc.name}】已注册")
        print(f"  性格: {npc.temper}、{npc.spirit}、{npc.ism}")
        print(f"  欲望: {npc.desire_type}({npc.desire_level})")
        
        # 初始化张力
        await director.initialize_npc_tensions(npc.id, world_state)
    
    # 显示叙事指导
    print("\n" + "=" * 70)
    print("2. 性格对叙事的指导")
    print("=" * 70)
    
    for npc in npcs:
        print(f"\n【{npc.name}】")
        guidance = director.generator._get_personality_narrative_guidance(npc)
        print(guidance)
    
    # 演示阶段推进
    print("\n" + "=" * 70)
    print("3. 困境阶段演示")
    print("=" * 70)
    
    from src.aistory.dilemma_seed import DilemmaPhase
    
    phases = [
        DilemmaPhase.LATENT,
        DilemmaPhase.SURFACED,
        DilemmaPhase.ESCALATED,
        DilemmaPhase.CRISIS
    ]
    
    for phase in phases:
        instruction = director.generator._get_phase_instruction(phase)
        print(f"\n【{phase.value}】")
        print(instruction[:150] + "...")
    
    # 模拟玩家选择处理
    print("\n" + "=" * 70)
    print("4. 模拟玩家选择处理")
    print("=" * 70)
    
    # 为李大侠创建一个待处理事件
    from src.aistory.rolling_story_generator import EventCard, EventChoice
    
    test_event = EventCard(
        id="test_001",
        title="江湖救急",
        description="李大侠的老友被官府通缉，前来求助",
        npc_id="hero_01",
        choices=[
            EventChoice(
                text="帮助藏匿",
                cost="得罪官府，风险极高",
                consequence="李大侠感激不尽，但你们都被通缉",
                effect="social_credit:+30, reputation:-20",
                heat_delta=20
            ),
            EventChoice(
                text="提供银两让其远走",
                cost="花费100文",
                consequence="李大侠理解你的难处，但关系疏远",
                effect="social_credit:+10, money:-100",
                heat_delta=5
            )
        ],
        ignore_consequence="李大侠只能独自承担风险",
        emotion_tone="紧张"
    )
    
    director.seeds["hero_01"].pending_event = test_event
    director.seeds["hero_01"].heat = 50  # 设置足够的热度
    
    print(f"\n事件: {test_event.title}")
    print(f"描述: {test_event.description}")
    print("\n选项:")
    for i, choice in enumerate(test_event.choices):
        print(f"  {i+1}. {choice.text}")
        print(f"     代价: {choice.cost}")
        print(f"     后果: {choice.consequence}")
    
    # 模拟玩家选择选项1
    print("\n>>> 玩家选择: 帮助藏匿")
    result = await director.process_player_choice("hero_01", 0, world_state)
    
    print(f"\n处理结果:")
    print(f"  成功: {result['success']}")
    print(f"  新阶段: {result['new_phase']}")
    print(f"  涟漪效果数: {len(result['ripples'])}")
    print(f"  招募提供: {result['recruitment_offered']}")
    
    # 显示故事历史
    print("\n" + "=" * 70)
    print("5. 故事历史记录")
    print("=" * 70)
    
    seed = director.seeds["hero_01"]
    if seed.story_beats:
        for beat in seed.story_beats:
            print(f"\n第{beat.beat_number}幕 [{beat.phase.value}]")
            print(f"  事件: {beat.event_summary}")
            print(f"  选择: {beat.player_choice}")
            print(f"  后果: {beat.consequence_summary}")
    
    print("\n" + "=" * 70)
    print("演示完成！")
    print("=" * 70)
    print("""
总结：
1. StoryDirector 协调所有叙事模块
2. 性格维度通过 _get_personality_narrative_guidance 影响LLM提示词
3. 不同性格的NPC会生成不同风格的事件和选项
4. 玩家选择会触发涟漪效果，影响其他NPC
5. 故事节拍被记录，形成连贯的叙事弧线
""")


if __name__ == "__main__":
    asyncio.run(demo_story_director())
