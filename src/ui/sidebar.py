# --- src/ui/sidebar.py ---
import pygame
from src.definitions import *
from src.entities import NPC, Resource
from src.quest_system import (
    TASK_TYPE_MAIN, TASK_TYPE_SURVIVAL, TASK_TYPE_INTEL, TASK_TYPE_FACTION,
    TASK_PRIORITY, TASK_TYPE_STYLES, TaskDisplayData
)

def draw_sidebar_panel(screen, rect, player, all_cards, tech_mgr, quest_mgr, ui_font, big_font, small_font, mx=0, my=0, click_event=False):
    """
    玩家信息面板 v3 - 精简美化版
    
    返回值：
        None - 无操作
        'OPEN_PLAYER_DETAIL' - 打开角色卡（默认tab）
        ('OPEN_PLAYER_DETAIL', tab_index) - 打开角色卡并切换到指定tab
    """
    result = None
    
    is_hover = rect.collidepoint(mx, my)
    
    pad_x = rect.x + 12
    cur_y = rect.y + 10
    content_w = rect.width - 24
    
    # 记录各区域的Y坐标范围，用于判断点击位置
    click_zones = {}  # {区域名: (y_start, y_end, 返回值)}
    
    # 背景
    pygame.draw.rect(screen, (28, 32, 38), rect)
    pygame.draw.line(screen, (60, 65, 75), (rect.x, rect.y), (rect.x, rect.bottom), 2)

    def draw_section_title(text, color=(255, 215, 0)):
        nonlocal cur_y
        surf = ui_font.render(text, True, color)
        screen.blit(surf, (pad_x, cur_y))
        cur_y += 24
    
    def draw_divider():
        nonlocal cur_y
        cur_y += 4
        pygame.draw.line(screen, (55, 60, 70), (rect.x + 8, cur_y), (rect.right - 8, cur_y), 1)
        cur_y += 8

    # 1. 标题
    title_surf = big_font.render("我的状态", True, (255, 215, 0))
    screen.blit(title_surf, (pad_x, cur_y))
    cur_y += 32
    
    if not player:
        empty_surf = ui_font.render("(无玩家数据)", True, (100, 100, 100))
        screen.blit(empty_surf, (pad_x, cur_y))
        return result
    
    # 玩家职业
    from src.definitions import JOB_LABELS
    job_label = JOB_LABELS.get(getattr(player, 'job', 'NONE'), '平民')
    job_surf = small_font.render(f"身份: {job_label}", True, (150, 160, 180))
    screen.blit(job_surf, (pad_x, cur_y))
    cur_y += 18
    
    draw_divider()

    # 2. 金钱/声望
    money = getattr(player, 'money', 0)
    money_color = (255, 215, 0) if money > 0 else (120, 120, 120)  # 金黄色
    money_surf = ui_font.render(f"[金钱] {money} 铜", True, money_color)
    screen.blit(money_surf, (pad_x, cur_y))
    cur_y += 24
    
    fame = getattr(player, 'fame', 0)
    fame_color = (100, 200, 255) if fame >= 0 else (255, 100, 100)
    fame_label = "声望" if fame >= 0 else "恶名"
    
    if fame >= 100: fame_rank = "名震江湖"
    elif fame >= 50: fame_rank = "小有名气"
    elif fame >= 20: fame_rank = "略有所闻"
    elif fame >= 0: fame_rank = "籍籍无名"
    elif fame >= -20: fame_rank = "声名狼藉"
    elif fame >= -50: fame_rank = "人人喊打"
    else: fame_rank = "恶贯满盈"
    
    fame_surf = ui_font.render(f"[{fame_label}] {abs(fame)}", True, fame_color)
    screen.blit(fame_surf, (pad_x, cur_y))
    rank_surf = small_font.render(f"({fame_rank})", True, (140, 145, 155))
    screen.blit(rank_surf, (pad_x + fame_surf.get_width() + 6, cur_y + 3))
    cur_y += 24
    
    # 悬赏状态
    bounty_value = getattr(player, 'bounty_value', 0)
    if bounty_value > 0:
        bounty_surf = ui_font.render(f"[悬赏] {bounty_value}铜", True, (255, 80, 80))
        screen.blit(bounty_surf, (pad_x, cur_y))
        cur_y += 22
        bounty_issuer = getattr(player, 'bounty_issuer', None)
        if bounty_issuer:
            from src.data.character_seeds import ORGANIZATIONS
            org_name = ORGANIZATIONS.get(bounty_issuer, {}).get('name', bounty_issuer)
            issuer_surf = small_font.render(f"来自: {org_name}", True, (255, 150, 150))
            screen.blit(issuer_surf, (pad_x + 12, cur_y))
            cur_y += 18
    
    draw_divider()
    
    # 3. 状态数值
    hp = getattr(player, 'hp', 100)
    max_hp = getattr(player, 'max_hp', 100)
    hunger = getattr(player, 'hunger', 0)
    cold = getattr(player, 'cold', 0)
    
    hp_color = (100, 220, 100) if hp > max_hp * 0.5 else (255, 180, 80) if hp > max_hp * 0.2 else (255, 80, 80)
    hunger_color = (255, 120, 80) if hunger >= 60 else (255, 180, 100) if hunger >= 40 else (140, 200, 140)
    cold_color = (100, 180, 255) if cold >= 60 else (150, 200, 255) if cold >= 40 else (140, 200, 140)
    
    hp_text = f"生命 {hp}/{max_hp}"
    hp_surf = ui_font.render(hp_text, True, hp_color)
    screen.blit(hp_surf, (pad_x, cur_y))
    cur_y += 22
    
    hunger_text = f"饥饿:{hunger}"
    hunger_surf = ui_font.render(hunger_text, True, hunger_color)
    screen.blit(hunger_surf, (pad_x, cur_y))
    
    cold_text = f"寒冷:{cold}"
    cold_surf = ui_font.render(cold_text, True, cold_color)
    screen.blit(cold_surf, (pad_x + hunger_surf.get_width() + 15, cur_y))
    cur_y += 22
    
    # 状态警告
    warnings = []
    if hunger >= 80:
        warnings.append(("饥肠辘辘!", (255, 100, 80)))
    elif hunger >= 60:
        warnings.append(("有些饿了", (255, 180, 100)))
    if cold >= 80:
        warnings.append(("寒冷刺骨!", (100, 150, 255)))
    elif cold >= 60:
        warnings.append(("有点冷", (150, 180, 220)))
    if hp <= max_hp * 0.2:
        warnings.append(("生命垂危!", (255, 80, 80)))
    
    if warnings:
        warn_x = pad_x
        for warn_text, warn_color in warnings:
            warn_surf = small_font.render(warn_text, True, warn_color)
            screen.blit(warn_surf, (warn_x, cur_y))
            warn_x += warn_surf.get_width() + 8
        cur_y += 18
    
    draw_divider()
    
    # 4. 六维属性（属性名与角色卡 npc_detail_panel 保持一致）
    draw_section_title("-- 属性 --", (180, 200, 230))
    
    attrs = [
        ('力量', getattr(player, 'strength', 50)),
        ('敏捷', getattr(player, 'agility', 50)),
        ('智力', getattr(player, 'wit', 50)),
        ('魅力', getattr(player, 'charm', 50)),
    ]
    
    col_w = (content_w - 10) // 2
    for i, (name, val) in enumerate(attrs):
        col = i % 2
        if col == 0:
            row_y = cur_y
        x = pad_x + col * col_w
        
        name_surf = small_font.render(f"{name}:", True, (140, 145, 155))
        screen.blit(name_surf, (x, row_y))
        val_color = (100, 220, 120) if val >= 70 else (220, 200, 100) if val >= 40 else (220, 120, 100)
        val_surf = small_font.render(str(val), True, val_color)
        screen.blit(val_surf, (x + 50, row_y))
        
        if col == 1:
            cur_y += 18
    
    if len(attrs) % 2 == 1:
        cur_y += 18
    
    draw_divider()
    
    # 5. 战斗属性
    from src.item_system import ItemManager
    item_sys = ItemManager.get_instance()
    
    base_atk = getattr(player, 'atk', 0)
    base_def = getattr(player, 'def_', 0)
    
    weapon = getattr(player, 'equip_weapon', None)
    armor = getattr(player, 'equip_armor', None)
    clothing = getattr(player, 'equip_clothing', None)
    
    atk_bonus = item_sys.get_atk_bonus(weapon) if weapon else 0
    armor_def_bonus = item_sys.get_def_bonus(armor) if armor else 0
    clothing_def_bonus = item_sys.get_def_bonus(clothing) if clothing else 0
    total_def_bonus = armor_def_bonus + clothing_def_bonus
    warm_bonus = item_sys.get_warm_val(clothing) if clothing else 0
    
    total_atk = base_atk + atk_bonus
    total_def = base_def + total_def_bonus
    
    x_pos = pad_x
    
    atk_text = f"攻击:{total_atk}"
    if atk_bonus > 0:
        atk_text += f"(+{atk_bonus})"
    atk_surf = ui_font.render(atk_text, True, (220, 100, 100))
    screen.blit(atk_surf, (x_pos, cur_y))
    x_pos += atk_surf.get_width() + 10
    
    def_text = f"防御:{total_def}"
    if total_def_bonus > 0:
        def_text += f"(+{total_def_bonus})"
    def_surf = ui_font.render(def_text, True, (100, 150, 220))
    screen.blit(def_surf, (x_pos, cur_y))
    cur_y += 22
    
    if warm_bonus > 0:
        warm_surf = ui_font.render(f"保暖:+{warm_bonus}", True, (220, 180, 100))
        screen.blit(warm_surf, (pad_x, cur_y))
        cur_y += 20
    
    equips = []
    if weapon: equips.append(f"武:{weapon[:4]}")
    if armor: equips.append(f"甲:{armor[:4]}")
    if clothing: equips.append(f"衣:{clothing[:4]}")
    if equips:
        equip_surf = small_font.render(" ".join(equips), True, (120, 125, 135))
        screen.blit(equip_surf, (pad_x, cur_y))
        cur_y += 18
    
    skills = getattr(player, 'skills', [])
    if skills:
        skill_text = ", ".join(skills[:3])
        if len(skills) > 3:
            skill_text += f" +{len(skills)-3}"
        skill_surf = small_font.render(f"技能: {skill_text}", True, (200, 180, 255))
        screen.blit(skill_surf, (pad_x, cur_y))
        cur_y += 18
    
    draw_divider()
    zone_rela_y_start = cur_y  # 人际区域从分隔线之后开始（标题之前）
    
    # 6. 人际关系（点击打开角色卡→关系tab）
    draw_section_title("-- 人际 --", (180, 200, 230))
    
    followers = []
    friends = []
    enemies = []
    
    for card in all_cards:
        if isinstance(card, NPC) and card != player and card.safety not in [SAFETY_DEAD, SAFETY_EXILED]:
            if getattr(card, 'is_follower', False):
                followers.append(card)
            else:
                affinity = getattr(card, 'affinity_to_player', 0)
                if affinity >= 50:
                    friends.append((card, affinity))
                elif affinity <= -50:
                    enemies.append((card, affinity))
    
    friends.sort(key=lambda x: -x[1])
    enemies.sort(key=lambda x: x[1])
    
    has_relations = followers or friends or enemies
    
    if not has_relations:
        empty_surf = small_font.render("暂无特殊关系", True, (100, 105, 115))
        screen.blit(empty_surf, (pad_x, cur_y))
        cur_y += 18
    else:
        if followers:
            label_surf = small_font.render(f"门客({len(followers)}):", True, (255, 215, 0))
            screen.blit(label_surf, (pad_x, cur_y))
            
            manage_surf = small_font.render("[管理]", True, (150, 180, 255))
            manage_rect = pygame.Rect(rect.right - manage_surf.get_width() - 12, cur_y, manage_surf.get_width(), 16)
            if manage_rect.collidepoint(mx, my):
                manage_surf = small_font.render("[管理]", True, (200, 230, 255))
                if click_event:
                    result = 'OPEN_FOLLOWER_PANEL'
            screen.blit(manage_surf, (manage_rect.x, manage_rect.y))
            cur_y += 16
            
            names = ", ".join([f.name for f in followers[:3]])
            if len(followers) > 3:
                names += f" +{len(followers)-3}"
            names_surf = small_font.render(f"  {names}", True, (200, 190, 150))
            screen.blit(names_surf, (pad_x, cur_y))
            cur_y += 16
        
        if friends:
            names = ", ".join([f[0].name for f in friends[:3]])
            if len(friends) > 3:
                names += f" +{len(friends)-3}"
            friend_surf = small_font.render(f"好友: {names}", True, (120, 200, 120))
            screen.blit(friend_surf, (pad_x, cur_y))
            cur_y += 16
        
        if enemies:
            names = ", ".join([e[0].name for e in enemies[:2]])
            if len(enemies) > 2:
                names += f" +{len(enemies)-2}"
            enemy_surf = small_font.render(f"仇敌: {names}", True, (255, 120, 120))
            screen.blit(enemy_surf, (pad_x, cur_y))
            cur_y += 16
    
    draw_divider()
    zone_bag_y_start = cur_y  # 背包区域从分隔线之后开始（标题之前）
    
    # 7. 背包（点击打开角色卡→背包tab）
    draw_section_title("-- 背包 --", (180, 200, 230))
    
    inventory = getattr(player, 'inventory', {})
    if inventory:
        item_texts = []
        for item_name, count in list(inventory.items())[:5]:
            if count > 0:
                item_texts.append(f"{item_name}x{count}")
        
        if item_texts:
            col_w = (content_w - 5) // 2
            for i, text in enumerate(item_texts):
                col = i % 2
                if col == 0:
                    row_y = cur_y
                x = pad_x + col * col_w
                item_surf = small_font.render(text[:8], True, (170, 175, 185))
                screen.blit(item_surf, (x, row_y))
                if col == 1:
                    cur_y += 16
            if len(item_texts) % 2 == 1:
                cur_y += 16
        
        if len(inventory) > 5:
            more_surf = small_font.render(f"...还有{len(inventory)-5}种", True, (110, 115, 125))
            screen.blit(more_surf, (pad_x, cur_y))
            cur_y += 16
    else:
        empty_surf = small_font.render("(空)", True, (100, 105, 115))
        screen.blit(empty_surf, (pad_x, cur_y))
        cur_y += 16

    draw_divider()
    zone_task_y_start = cur_y  # 要务区域从分隔线之后开始（标题之前）
    
    # 8. 当前任务 — 多任务分类展示
    draw_section_title("-- 要务 --", (255, 215, 0))
    cur_y += 6  # 要务标题和第一个任务类型之间的间距
    
    # 获取多任务数据（已按优先级排序）
    task_list = quest_mgr.get_all_task_displays(player, all_cards)
    
    if not task_list:
        empty_surf = small_font.render("(暂无要务)", True, (100, 105, 115))
        screen.blit(empty_surf, (pad_x, cur_y))
        cur_y += 18
    else:
        # 按类型分组显示
        current_type = None
        for task in task_list:
            # 获取任务样式
            style = TASK_TYPE_STYLES.get(task.type, TASK_TYPE_STYLES[TASK_TYPE_MAIN])
            
            # 如果是新类型，先绘制类型标题行
            if task.type != current_type:
                # 如果不是第一个类型，先留出间距
                if current_type is not None:
                    cur_y += 12  # 类型之间的间距（增大）
                
                current_type = task.type
                
                # 类型标题背景
                type_label = style.get('label', task.type)
                
                # 先渲染文本，获取实际高度用于居中对齐
                type_text = f"[{type_label}]"
                type_surf = small_font.render(type_text, True, style['color'])
                text_h = type_surf.get_height()
                
                # 背景矩形（高度根据文本调整，保证垂直居中）
                # 上下各留4像素边距 + 额外2像素让视觉更舒适
                bg_h = text_h + 10
                type_bg_rect = pygame.Rect(pad_x - 4, cur_y, content_w + 8, bg_h)
                
                # 只有非主线任务才有背景色（主线 bg_color 为 None）
                bg_color = style.get('bg_color')
                if bg_color:
                    pygame.draw.rect(screen, bg_color, type_bg_rect, border_radius=2)
                    # 左侧颜色条
                    pygame.draw.rect(screen, style['color'], (pad_x - 4, cur_y, 3, bg_h))
                
                # 类型标题文本（垂直居中于背景）
                text_y = cur_y + (bg_h - text_h) // 2
                screen.blit(type_surf, (pad_x + 8, text_y))
                cur_y += bg_h + 4  # 背景高度 + 下方间距
            
            # 任务内容行（缩进显示）
            # 构建完整文本
            full_text = task.text
            if task.progress:
                full_text = f"{task.text} ({task.progress})"
            
            # 完成状态前缀
            if task.is_complete:
                prefix = "√ "
                text_color = (100, 255, 100)
            elif task.is_urgent:
                prefix = "! "
                text_color = (255, 100, 100)
            else:
                prefix = "· "
                text_color = style['color']
            
            # 截断过长文本（最多12个中文字符，约24个英文字符）
            if len(full_text) > 12:
                display_text = full_text[:12] + "..."
            else:
                display_text = full_text
            
            # 绘制任务文本（缩进4像素）
            task_text = f"{prefix}{display_text}"
            task_surf = small_font.render(task_text, True, text_color)
            screen.blit(task_surf, (pad_x + 8, cur_y))
            cur_y += 18

    # ══════════════════════════════════════════════════════════════
    # 点击区域判断（在不同区域点击有不同行为）
    # ══════════════════════════════════════════════════════════════
    # 已记录的Y坐标：
    # zone_rela_y_start: 人际区域内容起始Y
    # zone_bag_y_start: 背包区域内容起始Y  
    # zone_task_y_start: 要务区域内容起始Y
    
    if click_event and rect.collidepoint(mx, my) and result is None:
        # 判断点击位置（从下往上判断）
        if my >= zone_task_y_start:
            # 点击了要务区域 → 不打开角色卡
            pass
        elif zone_bag_y_start <= my < zone_task_y_start:
            # 点击了背包区域 → 打开角色卡（背包tab=1）
            result = ('OPEN_PLAYER_DETAIL', 1)
        elif zone_rela_y_start <= my < zone_bag_y_start:
            # 点击了人际区域 → 打开角色卡（关系tab=3）
            result = ('OPEN_PLAYER_DETAIL', 3)
        else:
            # 点击了其他区域（状态/属性等） → 打开角色卡（属性tab=0）
            result = ('OPEN_PLAYER_DETAIL', 0)
    
    return result


# ======================== 调试打印功能 ========================
# 用于追踪要务显示内容变化

_last_task_print_time = 0      # 上次打印时间
_last_task_content = None      # 上次打印的内容
_TASK_PRINT_INTERVAL = 5000    # 打印间隔（毫秒）

def debug_print_tasks(quest_mgr, player, all_cards, current_time_ms):
    """
    每隔5秒打印一次当前要务内容（内容变化时才打印）
    
    在游戏主循环中调用此函数：
        from src.ui.sidebar import debug_print_tasks
        debug_print_tasks(quest_mgr, player, all_cards, pygame.time.get_ticks())
    """
    global _last_task_print_time, _last_task_content
    
    # 检查是否到达打印间隔
    if current_time_ms - _last_task_print_time < _TASK_PRINT_INTERVAL:
        return
    
    _last_task_print_time = current_time_ms
    
    # 获取任务列表
    task_list = quest_mgr.get_all_task_displays(player, all_cards)
    
    # 构建内容字符串
    lines = []
    if not task_list:
        lines.append("[要务调试] 暂无任务")
    else:
        for task in task_list:
            style = TASK_TYPE_STYLES.get(task.type, TASK_TYPE_STYLES[TASK_TYPE_MAIN])
            label = style.get('label', task.type)
            progress = f" ({task.progress})" if task.progress else ""
            status = "[√]" if task.is_complete else "[!]" if task.is_urgent else ""
            lines.append(f"  [{label}] {status}{task.text}{progress}")
    
    content_str = "\n".join(lines)
    
    # 如果内容与上次相同，跳过打印
    if content_str == _last_task_content:
        return
    
    _last_task_content = content_str
    
    # 打印分隔线和内容
    print("\n" + "=" * 40)
    print(f"[要务调试] {current_time_ms // 1000}秒")
    print(content_str)
    print("=" * 40)
