# src/live_news_to_dialog.py
"""
大宋实况 → 对话系统桥接器
将 LiveNewsItem 转换为可播放的 AVG 对话序列

功能：
1. 从 LiveNewsItem 提取事件信息
2. 调用 EventDialogGenerator 生成完整对话剧本
3. 将剧本转换为 StoryUI 可播放的格式
4. 支持玩家选择后触发效果
"""

import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from src.ui.event_notification import (
    LiveNewsItem, EventNotificationManager, NewsCategory)

from src.llm.event_dialog_generator import (
    EventDialogGenerator, EventScriptFull, EventDialogLine,
    get_event_dialog_generator
)
from src.data_loader import NPC_ID_NAME_MAP, get_npc_name_by_id_global, get_npc_id_by_name_global


def convert_effect_to_directive(effect_str: str, actor_ids: list = None) -> str:
    """
    将旧格式效果字符串转换为 StoryDirective 格式
    
    旧格式: "A:affinity:+30;PLAYER:fame:+10;B:hatred:+20"
    新格式: "SET_AFFINITY:PLAYER:NPC_ID:+30;PLAYER_FAME:+10;SET_HATRED:PLAYER:NPC_ID:+20"
    
    Args:
        effect_str: 旧格式效果字符串
        actor_ids: 事件关联的 NPC ID 列表，用于将 A/B/C 转换为实际 ID
        
    Returns:
        StoryDirective 格式的效果字符串
    """
    if not effect_str:
        return ""
    
    actor_ids = actor_ids or []
    result_parts = []
    
    for cmd in effect_str.split(';'):
        cmd = cmd.strip()
        if not cmd:
            continue
        
        parts = cmd.split(':')
        if len(parts) < 3:
            # 可能已经是新格式，直接保留
            result_parts.append(cmd)
            continue
        
        target, attr, val_str = parts[0].strip(), parts[1].strip().lower(), parts[2].strip()
        
        # 转换目标标识
        if target == 'PLAYER':
            # 玩家属性：PLAYER:fame:+10 → PLAYER_FAME:+10
            attr_map = {
                'fame': 'PLAYER_FAME',
                'money': 'PLAYER_MONEY',
                'infamy': 'PLAYER_INFAMY',
                'hp': 'PLAYER_HP'
            }
            if attr in attr_map:
                result_parts.append(f"{attr_map[attr]}:{val_str}")
            else:
                # 未知属性，保留原格式
                result_parts.append(cmd)
        elif target in ['A', 'B', 'C', 'D', 'E']:
            # NPC属性：A:affinity:+30 → SET_RELATION:PLAYER:NPC_ID:+30
            # （使用 SET_RELATION 支持任意两个角色间的关系变化）
            idx = ord(target) - ord('A')
            if idx < len(actor_ids):
                npc_id = actor_ids[idx]
                if attr == 'affinity':
                    # SET_RELATION:PLAYER:NPC_ID:+30 表示玩家对NPC的好感变化
                    result_parts.append(f"SET_RELATION:PLAYER:{npc_id}:{val_str}")
                elif attr == 'hatred':
                    # hatred 通过 SET_RELATION 实现，用负数表示
                    # A:hatred:+30 意味着 A 对玩家增加 30 仇恨 → 等效于玩家对A减少30好感
                    # 但更准确的做法是设置 NPC 的 hatred 属性
                    result_parts.append(f"SET_HATRED:{npc_id}:PLAYER:{val_str}")
                elif attr == 'trust':
                    # trust 暂时用 SET_RELATION 代替
                    result_parts.append(f"SET_RELATION:PLAYER:{npc_id}:{val_str}")
                else:
                    # 未知属性，跳过（或保留原格式）
                    print(f"[EffectConvert] 未知NPC属性: {attr}")
            else:
                print(f"[EffectConvert] 找不到 {target} 对应的 actor_id")
        else:
            # 可能是新格式或未知格式，直接保留
            result_parts.append(cmd)
    
    return ';'.join(result_parts)


@dataclass
class PlayableDialog:
    """可播放的对话数据（兼容 StoryUI 的 DialogData 格式）"""
    quest_id: str
    speaker: str
    text: str
    bg_img: str
    action: str
    speaker_id: Optional[int]
    
    def __post_init__(self):
        # 确保 speaker_id 有默认值
        if self.speaker_id is None:
            # 特殊处理：PLAYER = 9999, NARRATOR = -1
            if self.speaker == 'PLAYER':
                self.speaker_id = 9999
            elif self.speaker == 'NARRATOR':
                self.speaker_id = -1


class LiveNewsToDialogBridge:

    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = LiveNewsToDialogBridge()
        return cls._instance
    
    def __init__(self):
        self.dialog_generator = get_event_dialog_generator()
        
        # 缓存：避免重复生成同一事件的对话
        self._cache: Dict[str, EventScriptFull] = {}
        self._cache_max_size = 20
        
        # 当前正在处理的事件（用于选择后续）
        self._current_news: Optional[LiveNewsItem] = None
        self._current_script: Optional[EventScriptFull] = None
        self._choice_pending = False
    
    def convert_news_to_dialogs(
        self, 
        news: LiveNewsItem, 
        ctx,
        use_llm: bool = True
    ) -> List[PlayableDialog]:
        """
        将 LiveNewsItem 转换为可播放的开场对话序列
        
        Args:
            news: LiveNewsItem 事件
            ctx: 游戏上下文（用于获取NPC信息）
            use_llm: 是否使用LLM生成（False则使用模板）
            
        Returns:
            List[PlayableDialog]: 开场对话列表
        """
        # ═══════════════════════════════════════════════════════════════
        # 【优化】优先使用预生成的剧本
        # ═══════════════════════════════════════════════════════════════
        
        cache_key = news.news_id
        
        # 1. 检查是否有预生成的剧本（由 Director 并行扩写生成）
        if hasattr(news, '_pregen_script') and news._pregen_script is not None:
            print(f"[NewsDialogBridge] [ok] 使用预生成剧本: {cache_key}")
            self._current_script = news._pregen_script
            # 同时放入缓存
            self._cache[cache_key] = news._pregen_script
        else:
            #如果没有就不演出
            return None
        
        self._current_news = news
        self._choice_pending = True
        
        # 转换开场对话为可播放格式
        return self._convert_to_playable(
            self._current_script.intro_dialogs,
            news,
            ctx
        )
    
    def get_choice_followup_dialogs(
        self, 
        choice_key: str, 
        ctx
    ) -> List[PlayableDialog]:
        """
        获取玩家选择后的后续对话
        
        Args:
            choice_key: 选择的key（'A', 'B', 'C' 或 0, 1, 2）
            ctx: 游戏上下文
            
        Returns:
            List[PlayableDialog]: 后续对话列表
        """
        if not self._current_script or not self._current_news:
            print("[NewsDialogBridge] 错误: 没有当前事件/剧本")
            return []
        
        self._choice_pending = False
        
        # 根据选择获取对应对话（兼容新格式 choice_dialogues 字典）
        choice_dialogues = getattr(self._current_script, 'choice_dialogues', {})
        
        # 获取选项对话列表，优先使用新格式
        choice_0_dialogs = choice_dialogues.get('choice_0', getattr(self._current_script, 'choice_a_dialogs', []))
        choice_1_dialogs = choice_dialogues.get('choice_1', getattr(self._current_script, 'choice_b_dialogs', []))
        choice_2_dialogs = choice_dialogues.get('choice_2', getattr(self._current_script, 'choice_c_dialogs', []))
        
        key_map = {
            'A': choice_0_dialogs,
            'B': choice_1_dialogs,
            'C': choice_2_dialogs,
            '0': choice_0_dialogs,
            '1': choice_1_dialogs,
            '2': choice_2_dialogs,
            0: choice_0_dialogs,
            1: choice_1_dialogs,
            2: choice_2_dialogs,
        }
        
        choice_dialogs = key_map.get(choice_key, choice_0_dialogs)
        
        return self._convert_to_playable(
            choice_dialogs,
            self._current_news,
            ctx
        )
    
    def is_choice_pending(self) -> bool:
        """检查是否等待玩家选择"""
        return self._choice_pending
    
    def get_current_news(self) -> Optional[LiveNewsItem]:
        """获取当前正在处理的事件"""
        return self._current_news
    
    def clear_current(self):
        """清除当前事件状态"""
        self._current_news = None
        self._current_script = None
        self._choice_pending = False
    
    # ═══════════════════════════════════════════════════════════════
    # 内部方法
    # ═══════════════════════════════════════════════════════════════
    
    def _generate_full_script(
        self, 
        news: LiveNewsItem, 
        ctx,
        use_llm: bool
    ) -> EventScriptFull:
        """生成完整对话剧本"""
        
        # 1. 提取NPC信息
        npc_a_name, npc_a_desc = self._get_npc_info(news, 0, ctx)
        npc_b_name, npc_b_desc = self._get_npc_info(news, 1, ctx)
        
        # 2. 提取效果字符串
        effect_a = news.choices[0].get('effect', '') if len(news.choices) > 0 else ''
        effect_b = news.choices[1].get('effect', '') if len(news.choices) > 1 else ''
        effect_c = news.choices[2].get('effect', '') if len(news.choices) > 2 else ''
        
        # 3. 生成完整剧本（LLM不可用则不生成）
        if use_llm and self.dialog_generator.is_available():
            print(f"[NewsDialogBridge] 使用LLM生成对话: {news.title}")
            try:
                # 直接传递 news，函数内部会提取所有需要的信息（包括tooltip）
                full_script = self.dialog_generator.expand_to_full_script(
                    news_item=news,
                    npc_a_name=npc_a_name,
                    npc_b_name=npc_b_name,
                    effect_a=effect_a,
                    effect_b=effect_b,
                    effect_c=effect_c
                )
                return full_script
            except Exception as e:
                print(f"[NewsDialogBridge] LLM生成失败: {e}")
                return None
        
        # LLM不可用，不生成剧本
        print(f"[NewsDialogBridge] LLM不可用，跳过对话生成: {news.title}")
        return None
    
    def _get_npc_info(self, news: LiveNewsItem, index: int, ctx) -> tuple:
        """获取NPC信息"""
        default_name = f"当事人{chr(ord('甲') + index)}"
        default_desc = "一个普通人"
        
        # 从 actor_names 获取
        if index < len(news.actor_names):
            name = news.actor_names[index]
        else:
            return default_name, default_desc
        
        # 尝试从游戏中查找NPC获取更多信息
        if ctx and hasattr(ctx, 'all_cards'):
            for card in ctx.all_cards:
                if hasattr(card, 'name') and card.name == name:
                    job = getattr(card, 'job', '')
                    power_type = getattr(card, 'power_type', '')
                    org = getattr(card, 'org_id', '')
                    
                    desc_parts = []
                    if org:
                        desc_parts.append(f"隶属{org}")
                    if job:
                        desc_parts.append(f"职业{job}")
                    if power_type:
                        desc_parts.append(f"{power_type}籍")
                    
                    desc = "，".join(desc_parts) if desc_parts else default_desc
                    return name, desc
        
        return name, default_desc
    
    def _convert_to_playable(
        self, 
        dialog_lines: List[EventDialogLine],
        news: LiveNewsItem,
        ctx
    ) -> List[PlayableDialog]:
        """将 EventDialogLine 转换为 PlayableDialog"""
        from src.entities import NPC
        
        result = []
        
        for line in dialog_lines:
            # 新格式：使用 speaker_name 和 speaker_id
            speaker = line.speaker_name
            speaker_id = line.speaker_id
            
            # 校验：检查 id 和 name 是否匹配 NPC_ID_NAME_MAP
            if speaker_id is not None and speaker_id > 0:
                expected_name = get_npc_name_by_id_global(speaker_id)
                # 如果映射表中有这个名字，且与 LLM 输出的名字不一致，使用映射表的名字
                if expected_name and expected_name != f'NPC({speaker_id})':
                    if speaker != expected_name:
                        print(f"[NewsDialogBridge] 校验修正: ID={speaker_id}, '{speaker}' → '{expected_name}'")
                        speaker = expected_name
            
            # 【重要】如果 speaker_id == 0 或 None，从全局映射表或 ctx.all_cards 中查找对应的 NPC ID
            if (speaker_id is None or speaker_id == 0) and speaker not in ['旁白', '我', '玩家', 'NARRATOR', 'PLAYER']:
                # 1. 优先从全局映射表查找（NPC_ID_NAME_MAP 反向查找）
                speaker_id = get_npc_id_by_name_global(speaker)
                if speaker_id:
                    print(f"[NewsDialogBridge] 说话人ID修正(全局表): '{speaker}' → ID={speaker_id}")
                # 2. 回退到运行时 ctx.all_cards 查找
                elif ctx and hasattr(ctx, 'all_cards'):
                    for card in ctx.all_cards:
                        if isinstance(card, NPC) and hasattr(card, 'name') and card.name == speaker:
                            speaker_id = card.id
                            print(f"[NewsDialogBridge] 说话人ID修正(运行时): '{speaker}' → ID={speaker_id}")
                            break
            
            # 替换文本中的占位符
            text = self._resolve_text_placeholders(line.text, news)
            
            # 转换动作格式（如果需要）
            action = self._convert_action_format(line.action, news, ctx)
            
            playable = PlayableDialog(
                quest_id=f"news_{news.news_id}",
                speaker=speaker,
                text=text,
                bg_img="",  # 事件对话不使用背景图
                action=action,
                speaker_id=speaker_id
            )
            result.append(playable)
        
        return result
    
    def _resolve_speaker(
        self, 
        speaker_code: str, 
        news: LiveNewsItem, 
        ctx
    ) -> tuple:
        """解析说话者代号为实际名字和ID"""
        
        if speaker_code == 'NARRATOR' or speaker_code == '旁白':
            return '旁白', -1
        
        if speaker_code == 'PLAYER':
            player_name = '我'
            if ctx and hasattr(ctx, 'player') and hasattr(ctx.player, 'name'):
                player_name = ctx.player.name
            return player_name, 9999
        
        if speaker_code == 'SELF':
            # 主角NPC（第一个演员）
            if news.actor_names:
                name = news.actor_names[0]
                npc_id = news.actor_ids[0] if news.actor_ids else None
                return name, npc_id
            return '当事人', None
        
        if speaker_code == 'OTHER':
            # 配角NPC（第二个演员）
            if len(news.actor_names) > 1:
                name = news.actor_names[1]
                npc_id = news.actor_ids[1] if len(news.actor_ids) > 1 else None
                return name, npc_id
            return '对方', None
        
        # 直接使用名字，尝试在 ctx.all_cards 中查找对应的 NPC ID
        if ctx and hasattr(ctx, 'all_cards'):
            from src.entities import NPC
            for card in ctx.all_cards:
                if isinstance(card, NPC) and hasattr(card, 'name') and card.name == speaker_code:
                    return speaker_code, card.id
        
        return speaker_code, None
    
    def _resolve_text_placeholders(self, text: str, news: LiveNewsItem) -> str:
        """替换文本中的占位符"""
        result = text
        
        # 替换 {A}, {B} 为实际名字
        if news.actor_names:
            result = result.replace('{A}', news.actor_names[0])
            result = result.replace('{SELF}', news.actor_names[0])
        if len(news.actor_names) > 1:
            result = result.replace('{B}', news.actor_names[1])
            result = result.replace('{OTHER}', news.actor_names[1])
        
        # 替换地点
        if news.location:
            result = result.replace('{LOC}', news.location)
            result = result.replace('{LOCATION}', news.location)
        
        return result
    
    def _convert_action_format(
        self, 
        action: str, 
        news: LiveNewsItem, 
        ctx
    ) -> str:
        """
        转换动作格式以兼容 QuestManager/StoryDirectiveExecutor
        
        将旧格式 "A:affinity:+30;PLAYER:fame:+10" 
        转换为 "SET_AFFINITY:PLAYER:NPC_ID:+30;PLAYER_FAME:+10"
        """
        if not action:
            return ""
        
        # 保留特殊动作（如 SHOW_EVENT_CHOICE）
        if action.startswith('SHOW_') or action.startswith('END_') or action.startswith('FADE_'):
            return action
        
        # 检测是否是旧格式（包含 ":affinity:", ":fame:", ":money:" 等）
        old_format_markers = [':affinity:', ':fame:', ':money:', ':hatred:', ':trust:', ':infamy:', ':hp:']
        is_old_format = any(marker in action.lower() for marker in old_format_markers)
        
        if is_old_format:
            # 获取 actor_ids 用于转换
            actor_ids = list(news.actor_ids) if news.actor_ids else []
            converted = convert_effect_to_directive(action, actor_ids)
            print(f"[NewsDialogBridge] 转换效果格式: {action} → {converted}")
            return converted
        
        # 替换NPC名字占位符（用于其他格式）
        result = action
        if news.actor_names:
            result = result.replace('SELF', news.actor_names[0])
        if len(news.actor_names) > 1:
            result = result.replace('OTHER', news.actor_names[1])
        
        return result


# ═══════════════════════════════════════════════════════════════
# 全局访问函数
# ═══════════════════════════════════════════════════════════════

def get_news_dialog_bridge() -> LiveNewsToDialogBridge:
    """获取桥接器单例"""
    return LiveNewsToDialogBridge.get_instance()
