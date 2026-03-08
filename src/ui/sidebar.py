# --- src/ui/sidebar.py ---
import pygame
from src.definitions import *
from src.entities import NPC, Resource

def draw_sidebar_panel(screen, rect, player, all_cards, tech_mgr, quest_mgr, ui_font, big_font, small_font, mx=0, my=0, click_event=False):
    """
    玩家信息面板 v3 - 精简美化版
    """
    result = None
    
    if click_event and rect.collidepoint(mx, my):
        result = 'OPEN_PLAYER_DETAIL'
    
    is_hover = rect.collidepoint(mx, my)
    
    pad_x = rect.x + 12
    cur_y = rect.y + 10
    content_w = rect.width - 24
    
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
    
    # 4. 六维属性
    draw_section_title("-- 属性 --", (180, 200, 230))
    
    attrs = [
        ('武力', getattr(player, 'attr_force', 50)),
        ('智谋', getattr(player, 'attr_intellect', 50)),
        ('魅力', getattr(player, 'attr_charisma', 50)),
        ('勇气', getattr(player, 'attr_courage', 50)),
        ('敏捷', getattr(player, 'attr_agility', 50)),
        ('运气', getattr(player, 'attr_luck', 50)),
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
    
    # 6. 人际关系
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
    
    # 7. 背包
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
    
    # 8. 当前任务
    draw_section_title("-- 要务 --", (255, 215, 0))
    
    obj_text = quest_mgr.get_current_objective_text(player, all_cards)
    is_complete = "[√]" in obj_text
    obj_color = (100, 255, 100) if is_complete else (200, 205, 215)
    
    max_chars = 14
    lines = [obj_text[i:i+max_chars] for i in range(0, len(obj_text), max_chars)]
    for line in lines[:3]:
        obj_surf = small_font.render(line, True, obj_color)
        screen.blit(obj_surf, (pad_x, cur_y))
        cur_y += 18
    if len(lines) > 3:
        more_surf = small_font.render("...", True, (120, 125, 135))
        screen.blit(more_surf, (pad_x, cur_y))
        cur_y += 18

    # 9. 悬停提示
    if is_hover:
        pygame.draw.rect(screen, (80, 120, 180), rect, 2, border_radius=4)
        hint_surf = small_font.render("点击打开详情", True, (150, 200, 255))
        screen.blit(hint_surf, (rect.centerx - hint_surf.get_width() // 2, rect.bottom - 22))
    
    return result
