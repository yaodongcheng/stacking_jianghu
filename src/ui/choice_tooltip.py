# src/ui/choice_tooltip.py
"""
选项Tooltip通用模块
========================================

提供选项tooltip的通用功能，可被多个UI组件复用：
- LiveSnapshotPanel (快信处理面板)
- StoryUI (剧情对话选择界面)
"""

import pygame
import re
from typing import Dict, List, Optional, Tuple, Any, Callable

from src.data_loader import get_npc_name_by_id_global


class ChoiceTooltipHelper:
    """选项Tooltip辅助工具类
    
    提供静态方法用于：
    1. 格式化条件/消耗/效果文本
    2. 检查玩家条件
    3. 准备tooltip内容
    4. 绘制tooltip
    """
    
    # 属性名映射
    ATTR_NAMES = {
        'money': '金钱', 'charm': '魅力', 'str': '力量', 'strength': '力量',
        'int': '智力', 'wit': '智力', 'fame': '声望', 
        'health': '生命', 'energy': '精力', 'kungfu': '武功',
        'mood': '心情', 'stress': '压力', 'fatigue': '疲劳',
        'agility': '敏捷',
        'affinity_to_player': '好感度',
    }
    
    # 比较符映射
    COMPARE_MAP = {
        '>=': '大于等于', '>::': '大于等于',
        '<=': '小于等于', '<::': '小于等于',
        '>': '大于', '>>': '大于',
        '<': '小于', '<<': '小于',
        '==': '等于', '=': '等于'
    }
    
    @staticmethod
    def get_font(font_cache: Dict[int, pygame.font.Font], size: int) -> pygame.font.Font:
        """获取缓存的字体"""
        if size not in font_cache:
            font_names = "microsoftyahei,simhei,pingfangsc,notosanscjk,arial"
            font_cache[size] = pygame.font.SysFont(font_names, size)
        return font_cache[size]
    
    @staticmethod
    def format_compare_symbol(compare: str) -> str:
        """将比较符格式化为自然语言"""
        return ChoiceTooltipHelper.COMPARE_MAP.get(compare, compare)
    
    @staticmethod
    def check_requirement(player, req_str: str) -> bool:
        """检查选项是否满足条件
        
        格式: "actor_name:attribute:compare:needvalue"
        示例: "PLAYER:money:>=:100" 或 "1001:charm:>::50"
        """
        if not req_str or not player:
            return True
        
        try:
            parts = req_str.split(':')
            if len(parts) < 4:
                return True
            
            actor, attr, compare, need_val = parts[0], parts[1], parts[2], parts[3]
            
            # 解析数值
            try:
                need_num = int(need_val)
            except:
                need_num = need_val
            
            # 获取实际值
            if actor == 'PLAYER':
                actual_val = getattr(player, attr, 0)
            else:
                # NPC 属性检查 - 简化处理，默认通过
                return True
            
            # 比较
            if compare in ('>=', '>::'):
                return actual_val >= need_num
            elif compare in ('<=', '<::'):
                return actual_val <= need_num
            elif compare in ('>', '>>'):
                return actual_val > need_num
            elif compare in ('<', '<<'):
                return actual_val < need_num
            elif compare in ('=', '=='):
                return actual_val == need_num
            
            return True
        except:
            return True
    
    @staticmethod
    def format_requirement_text(req_str: str) -> str:
        """将 requirement 格式化为自然语言"""
        if not req_str or str(req_str).lower() == 'null':
            return ""
        
        try:
            parts = req_str.split(':')
            if len(parts) < 4:
                return ""
            
            actor, attr, compare, need_val = parts[0], parts[1], parts[2], parts[3]
            
            # affinity_to_player 特殊处理
            if attr == 'affinity_to_player':
                npc_name = get_npc_name_by_id_global(actor) or f"NPC{actor}"
                compare_text = ChoiceTooltipHelper.format_compare_symbol(compare)
                return f"与{npc_name}好感度{compare_text}{need_val}"
            
            # 关系属性特殊处理
            if attr == 'relation' or attr.endswith('_relation'):
                npc_name = get_npc_name_by_id_global(actor)
                compare_text = ChoiceTooltipHelper.format_compare_symbol(compare)
                return f"与{npc_name}好感{compare_text}{need_val}"
            
            # 属性名映射
            attr_name = ChoiceTooltipHelper.ATTR_NAMES.get(attr, attr)
            
            # 比较符映射为自然语言
            compare_text = ChoiceTooltipHelper.format_compare_symbol(compare)
            
            return f"拥有{compare_text}{need_val}{attr_name}"
        except:
            return req_str
    
    @staticmethod
    def format_effect_text(effect_str: str, is_cost: bool) -> str:
        """格式化 effect/cost 文本为自然语言，支持多个效果"""
        if not effect_str or effect_str.lower() == 'null':
            return "无"
        
        # 支持多个效果（用分号分隔）
        effects = effect_str.split(';')
        result_parts = []
        
        for effect in effects:
            effect = effect.strip()
            if not effect or effect.lower() == 'null':
                continue
            
            try:
                parts = effect.split(':')
                if len(parts) < 3:
                    continue
                
                actor, attr, val = parts[0], parts[1], parts[2]
                
                # 关系属性特殊处理
                if attr == 'relation' or attr.endswith('_relation'):
                    npc_name = get_npc_name_by_id_global(actor)
                    try:
                        num = int(val)
                        if num > 0:
                            result_parts.append(f"与{npc_name}关系变好({num})")
                        else:
                            result_parts.append(f"与{npc_name}关系变差({num})")
                    except:
                        result_parts.append(f"与{npc_name}关系变化")
                    continue
                
                # NPC情绪属性特殊处理
                if attr == 'emotion':
                    npc_name = get_npc_name_by_id_global(actor)
                    from src.definitions import EMOTION_CN
                    if val in EMOTION_CN:
                        emotion_text = EMOTION_CN.get(val, val)
                        result_parts.append(f"{npc_name}变得{emotion_text}")
                    continue
                
                # 特殊处理 affinity_to_player 格式
                if attr == 'affinity_to_player':
                    attr_name = "对你好感度"
                elif attr.startswith('affinity_to_'):
                    attr_name = "对你好感度"
                else:
                    attr_name = ChoiceTooltipHelper.ATTR_NAMES.get(attr, attr)
                
                # 获取actor的名称
                if actor == 'PLAYER':
                    actor_name = '玩家'
                else:
                    actor_name = get_npc_name_by_id_global(actor)
                
                # 数值处理
                try:
                    num = int(val)
                    
                    # 资源类属性特殊处理
                    is_money = attr in ('money', '金钱')
                    
                    if is_cost:
                        if is_money:
                            if actor == 'PLAYER':
                                result_parts.append(f"花费{abs(num)}{attr_name}")
                            else:
                                result_parts.append(f"{actor_name}花费{abs(num)}{attr_name}")
                        elif num > 0:
                            if actor == 'PLAYER':
                                result_parts.append(f"消耗{num}{attr_name}")
                            else:
                                result_parts.append(f"{actor_name}消耗{num}{attr_name}")
                        else:
                            result_parts.append(f"{actor_name}减少{abs(num)}{attr_name}")
                    else:
                        # 收益/效果
                        is_affinity = attr == 'affinity_to_player'
                        
                        if is_money:
                            if actor == 'PLAYER':
                                result_parts.append(f"获得{abs(num)}{attr_name}")
                            else:
                                result_parts.append(f"{actor_name}获得{abs(num)}{attr_name}")
                        elif is_affinity:
                            if num > 0:
                                result_parts.append(f"{actor_name}对你好感度提升{num}")
                            else:
                                result_parts.append(f"{actor_name}对你好感度下降{abs(num)}")
                        elif num > 0:
                            if actor == 'PLAYER':
                                result_parts.append(f"获得{num}{attr_name}")
                            else:
                                result_parts.append(f"{actor_name}获得{num}{attr_name}")
                        else:
                            result_parts.append(f"{actor_name}失去{abs(num)}{attr_name}")
                except:
                    result_parts.append(f"{actor_name}{attr_name}{val}")
            except:
                continue
        
        if not result_parts:
            return "无"
        
        return "，".join(result_parts)
    
    @staticmethod
    def parse_transfer_text(transfer_str: str) -> Dict[str, List[str]]:
        """解析 transfer 字段，返回消耗和收益的文本列表
        
        格式: from_actor->to_actor:attr:value，多个用分号分隔
        返回: {'cost': [...], 'gain': [...]}
        """
        if not transfer_str or transfer_str.lower() == 'null':
            return {'cost': [], 'gain': []}
        
        cost_list = []
        gain_list = []
        
        transfers = transfer_str.split(';')
        
        for transfer in transfers:
            transfer = transfer.strip()
            if not transfer or transfer.lower() == 'null':
                continue
            
            try:
                parts = transfer.split('->')
                if len(parts) != 2:
                    continue
                
                from_part = parts[0].strip()
                to_attr_val = parts[1].split(':')
                
                if len(to_attr_val) != 3:
                    continue
                
                to_actor = to_attr_val[0].strip()
                attr = to_attr_val[1].strip()
                val_str = to_attr_val[2].strip()
                
                try:
                    value = int(val_str)
                except:
                    continue
                
                # 属性名映射
                attr_names = {
                    'money': '金钱', 'item': '物品', 'items': '物品',
                    'gold': '黄金', 'silver': '白银', 'coin': '铜钱'
                }
                attr_name = attr_names.get(attr, attr)
                
                # 获取名称
                if from_part == 'PLAYER':
                    from_name = '玩家'
                else:
                    from_name = get_npc_name_by_id_global(from_part) or f"NPC{from_part}"
                
                if to_actor == 'PLAYER':
                    to_name = '玩家'
                else:
                    to_name = get_npc_name_by_id_global(to_actor) or f"NPC{to_actor}"
                
                # 判断是消耗还是收益
                if from_part == 'PLAYER':
                    cost_list.append(f"花费{value}{attr_name}")
                elif to_actor == 'PLAYER':
                    gain_list.append(f"获得{value}{attr_name}")
                else:
                    cost_list.append(f"{from_name}失去{value}{attr_name}")
                    gain_list.append(f"{to_name}获得{value}{attr_name}")
                    
            except:
                continue
        
        return {'cost': cost_list, 'gain': gain_list}
    
    @staticmethod
    def format_all_effects(choice: dict, format_effect_func: Callable = None) -> tuple:
        """统一解析选项的所有效果，返回 (消耗文本, 收益文本)
        
        整合了 cost、effect 和 transfer 三个字段
        """
        cost_parts = []
        gain_parts = []
        
        # 如果提供了自定义格式化函数，使用它；否则使用默认
        format_effect = format_effect_func or ChoiceTooltipHelper.format_effect_text
        
        # 1. 解析 transfer
        transfer = choice.get('transfer')
        transfer_has_money = False
        if transfer and str(transfer).lower() != 'null':
            transfer_result = ChoiceTooltipHelper.parse_transfer_text(transfer)
            cost_parts.extend(transfer_result.get('cost', []))
            gain_parts.extend(transfer_result.get('gain', []))
            if '金钱' in str(transfer_result.get('cost', [])) or 'money' in str(transfer).lower():
                transfer_has_money = True
        
        # 2. 解析 cost
        cost = choice.get('cost')
        if cost and str(cost).lower() != 'null':
            if transfer_has_money:
                cost_items = str(cost).split(';')
                filtered_cost_items = []
                for item in cost_items:
                    if 'money' not in item.lower() and '金钱' not in item:
                        filtered_cost_items.append(item)
                if filtered_cost_items:
                    cost = ';'.join(filtered_cost_items)
                else:
                    cost = None
            
            if cost and str(cost).lower() != 'null':
                cost_text = format_effect(cost, is_cost=True)
                if cost_text != "无":
                    cost_parts.append(cost_text)
        
        # 3. 解析 effect
        effect = choice.get('effect')
        if effect and str(effect).lower() != 'null':
            effect_text = format_effect(effect, is_cost=False)
            if effect_text != "无":
                gain_parts.append(effect_text)
        
        # 合并文本
        cost_result = "，".join(cost_parts) if cost_parts else "无"
        gain_result = "，".join(gain_parts) if gain_parts else "无"
        
        return cost_result, gain_result
    
    @staticmethod
    def prepare_tooltip_lines(choice: dict, player=None) -> List[Tuple[str, str]]:
        """准备tooltip的内容行
        
        Returns:
            List of (text, color_type) tuples
        """
        lines = []
        
        # Requirement（条件）
        req_str = choice.get('requirement')
        req_satisfied = True
        if req_str and str(req_str).lower() != 'null':
            req_text = ChoiceTooltipHelper.format_requirement_text(req_str)
            req_satisfied = ChoiceTooltipHelper.check_requirement(player, req_str)
            lines.append(('【条件】', 'title'))
            lines.append((req_text, 'req_unsatisfied' if not req_satisfied else 'req_satisfied'))
        
        # 消耗和收益
        cost_text, gain_text = ChoiceTooltipHelper.format_all_effects(choice)
        
        if cost_text != "无":
            lines.append(('【消耗】', 'title'))
            lines.append((cost_text, 'cost'))
        
        if gain_text != "无":
            lines.append(('【影响】', 'title'))
            lines.append((gain_text, 'effect'))
        
        # Consequence preview
        preview = choice.get('consequence_preview')
        if preview and str(preview).lower() != 'null':
            preview = re.sub(r'[\r\n]+', '', preview)
            lines.append(('', 'normal'))
            lines.append(('【预测】', 'title'))
            for tag in ['[即时反应]', '[埋下隐患]', '[最终走向]', '[长远影响]']:
                if tag in preview:
                    start = preview.find(tag)
                    end = preview.find('[', start + 1)
                    if end == -1:
                        end = len(preview)
                    content = preview[start:end].replace(tag, '').strip()
                    if content:
                        lines.append((f"  {tag} {content}", 'normal'))
        
        return lines
    
    @staticmethod
    def draw_tooltip(
        surface: pygame.Surface,
        tooltip_data: Dict,
        font_cache: Dict[int, pygame.font.Font],
        fixed_width: int = 280,
        line_height: int = 26,
        padding: int = 12,
        panel_h: int = None,
        panel_offset: tuple = (0, 0)
    ):
        """绘制tooltip
        
        Args:
            surface: 要绘制的目标surface
            tooltip_data: tooltip数据，包含 'lines', 'btn_rect', 'alpha'
            font_cache: 字体缓存
            fixed_width: 固定宽度
            line_height: 行高
            padding: 内边距
            panel_h: 面板高度（用于边界检测）
            panel_offset: 面板偏移量（用于坐标转换）
        """
        if not tooltip_data:
            return
        
        lines = tooltip_data['lines']
        btn_rect = tooltip_data['btn_rect']
        
        # 淡入动画
        tooltip_data['alpha'] = min(1.0, tooltip_data['alpha'] + 0.15)
        alpha = int(255 * tooltip_data['alpha'])
        
        # 获取字体
        font = ChoiceTooltipHelper.get_font(font_cache, 16)
        
        # 固定宽度
        tooltip_w = fixed_width
        
        # 文本换行处理
        wrapped_lines = []
        max_width = tooltip_w - padding * 2
        
        for line_data in lines:
            if isinstance(line_data, tuple):
                text, color_type = line_data
            else:
                text = line_data
                color_type = 'normal'
            
            if not text:
                wrapped_lines.append((text, color_type))
                continue
            
            # 按字符逐个添加，超过宽度才换行
            current_line = ""
            for char in text:
                test_line = current_line + char
                if font.size(test_line)[0] <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        wrapped_lines.append((current_line, color_type))
                    current_line = char
            if current_line:
                wrapped_lines.append((current_line, color_type))
        
        tooltip_h = len(wrapped_lines) * line_height + padding * 2
        
        # 位置计算
        tooltip_x = btn_rect.right + 25
        tooltip_y = btn_rect.top + panel_offset[1]
        
        # 边界检测
        if panel_h is not None and tooltip_y + tooltip_h > panel_h - 10:
            tooltip_y = panel_h - tooltip_h - 10
        
        tooltip_rect = pygame.Rect(tooltip_x, tooltip_y, tooltip_w, tooltip_h)
        
        # 绘制背景
        bg_color = (25, 25, 35, alpha)
        bg_surface = pygame.Surface((tooltip_w, tooltip_h), pygame.SRCALPHA)
        bg_surface.fill(bg_color)
        surface.blit(bg_surface, tooltip_rect)
        
        # 绘制边框
        border_color = (180, 150, 100, alpha)
        pygame.draw.rect(surface, border_color, tooltip_rect, 2, border_radius=6)
        
        # 绘制文本
        y = tooltip_rect.top + padding
        for line, color_type in wrapped_lines:
            # 根据颜色类型决定颜色
            if color_type == 'title':
                color = (255, 255, 255)
            elif color_type == 'req_satisfied':
                color = (100, 220, 100)
            elif color_type == 'req_unsatisfied':
                color = (255, 80, 80)
            elif color_type == 'cost':
                color = (255, 180, 100)
            elif color_type == 'effect':
                color = (100, 220, 100)
            elif color_type == 'normal':
                color = (255, 255, 255)
            else:
                color = (255, 255, 255)
            
            text_surf = font.render(line, True, color)
            surface.blit(text_surf, (tooltip_rect.left + padding, y))
            y += line_height
    
    @staticmethod
    def create_tooltip_data(choice: dict, btn_rect: pygame.Rect, player=None) -> Optional[Dict]:
        """创建tooltip数据对象
        
        Returns:
            {'lines': [...], 'btn_rect': Rect, 'alpha': 0.0} 或 None
        """
        lines = ChoiceTooltipHelper.prepare_tooltip_lines(choice, player)
        if not lines:
            return None
        
        return {
            'lines': lines,
            'btn_rect': btn_rect.copy(),
            'alpha': 0.0
        }
