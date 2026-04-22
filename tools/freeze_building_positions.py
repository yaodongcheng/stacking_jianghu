"""
快照工具：把 building_config.csv 里 SANDBOX 行的最终坐标固化到 pos_x/pos_y。

用法（项目根目录下）：
    python tools/freeze_building_positions.py

工作流程：
  1. 用沙盒固定世界尺寸 (5600x4200) 创建 WorldMap
  2. 复用 src/data_loader.py 的 _precompute_zones / _resolve_position
  3. 复用 src/world_loader.py 的 find_valid_building_position（80px 间距 + 城墙避让）
  4. 把每行算出来的 (x, y) 写回 CSV 的 pos_x / pos_y 列
  5. CSV 表头从 (offset_x, offset_y, spread) 改成 (pos_x, pos_y)

策划新增 CSV 行后，可以重跑此工具填默认坐标，再手工微调。
"""
import csv
import os
import sys

# 让脚本能从项目根直接运行
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pygame
pygame.init()

from src.definitions import CARD_W, CARD_H
from src.world_map import WorldMap
from src.data_loader import _precompute_zones, _resolve_position

CSV_PATH = os.path.join(ROOT, 'data', 'building_config.csv')

# 沙盒世界固定尺寸（与 main.py SCENARIO_WORLD_SIZES[SCENARIO_SANDBOX] 一致）
SANDBOX_W, SANDBOX_H = 5600, 4200
# 屏幕尺寸只影响 WorldMap 的 screen_view_*，对 city_rect/gates 不起作用
DUMMY_SCREEN_W, DUMMY_SCREEN_H = 1920, 1080

NEW_HEADER = ['id', 'building_type', 'zone', 'pos_x', 'pos_y',
              'owner_type', 'owner_id', 'is_home', 'inventory', 'scenario']
NEW_TYPES = ['str', 'str', 'str', 'int', 'int',
             'str', 'str', 'int', 'str', 'str']
NEW_LABELS = ['建筑ID', '建筑类型', '位置区域', 'X坐标', 'Y坐标',
              '所有者类型', '所有者ID', '是住所', '初始库存', '场景']

MIN_EDGE = 80  # 与 world_loader.BUILDING_MIN_EDGE_DISTANCE 保持一致


def _rects_too_close(ax, ay, bx, by, min_edge=MIN_EDGE, w=CARD_W, h=CARD_H):
    """判断两栋卡牌是否重叠或边距小于 min_edge。"""
    h_dist = max(ax - w // 2 - (bx + w // 2), bx - w // 2 - (ax + w // 2))
    v_dist = max(ay - h // 2 - (by + h // 2), by - h // 2 - (ay + h // 2))
    if h_dist < 0 and v_dist < 0:
        return True
    return max(h_dist, v_dist) < min_edge


def _wall_collision(x, y, world_map, w=CARD_W, h=CARD_H):
    rect = pygame.Rect(x - w // 2, y - h // 2, w, h)
    return any(rect.colliderect(wall) for wall in world_map.walls)


def _find_non_overlap_pos(base_x, base_y, placed, world_map, search_radius=200):
    """围绕 base 螺旋搜索一个不重叠、不撞墙的位置。"""
    import math
    if not _wall_collision(base_x, base_y, world_map) and \
       all(not _rects_too_close(base_x, base_y, px, py) for px, py in placed):
        return base_x, base_y

    # 螺旋采样：每圈 12 个方向，半径 40 -> search_radius
    for r in range(40, search_radius + 1, 30):
        for k in range(12):
            angle = k * (2 * math.pi / 12)
            nx = int(base_x + r * math.cos(angle))
            ny = int(base_y + r * math.sin(angle))
            nx = max(60, min(nx, world_map.w - 60))
            ny = max(60, min(ny, world_map.h - 60))
            if _wall_collision(nx, ny, world_map):
                continue
            if all(not _rects_too_close(nx, ny, px, py) for px, py in placed):
                return nx, ny

    print(f"  [!] 找不到非重叠位置，原坐标 ({base_x}, {base_y}) 可能与他人冲突")
    return base_x, base_y


def freeze():
    print(f"[Freeze] 创建沙盒 WorldMap ({SANDBOX_W}x{SANDBOX_H}) ...")
    world_map = WorldMap(DUMMY_SCREEN_W, DUMMY_SCREEN_H,
                         world_w=SANDBOX_W, world_h=SANDBOX_H)
    zone_data = _precompute_zones(world_map)

    print(f"[Freeze] 读取 {CSV_PATH}")
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        rows = list(csv.reader(f))

    if len(rows) < 4:
        print("[Freeze] CSV 行数不足")
        return

    old_header = rows[0]
    idx = {k: i for i, k in enumerate(old_header)}

    placed = []      # [(x, y), ...] 已放置的位置
    market_pos = None
    out_rows = [NEW_HEADER, NEW_TYPES, NEW_LABELS]

    sandbox_count = 0
    skipped_tutorial = 0

    for row in rows[3:]:
        if not row or not row[0].strip():
            continue

        # 补齐缺失列
        while len(row) < len(old_header):
            row.append('')

        scenario = row[idx['scenario']].strip()
        if scenario != 'SANDBOX':
            # TUTORIAL 行已是 dead config（world_loader.py 硬编码加载），删除
            skipped_tutorial += 1
            print(f"  [drop] {row[idx['id']]} (scenario={scenario}) — TUTORIAL 走代码硬编码，CSV 行不再使用")
            continue

        bid = row[idx['id']].strip()
        building_type = row[idx['building_type']].strip()
        zone_str = row[idx['zone']].strip() or 'CITY'
        offset_x = int(row[idx['offset_x']] or 0)
        offset_y = int(row[idx['offset_y']] or 0)
        spread = int(row[idx['spread']] or 0)

        # MARKET_NEAR 依赖 B_MARKET_MAIN 已经定位
        if zone_str == 'MARKET_NEAR' and market_pos:
            zone_data['MARKET_NEAR'] = market_pos

        bx, by = _resolve_position(zone_str, offset_x, offset_y, spread,
                                   zone_data, world_map)

        # 防重叠：所有建筑都跑一遍（更早的随机布局只对部分类型做，这里统一）
        bx, by = _find_non_overlap_pos(bx, by, placed, world_map)
        placed.append((bx, by))

        if bid == 'B_MARKET_MAIN':
            market_pos = (bx, by)

        out_rows.append([
            bid,
            building_type,
            zone_str,                              # 保留作语义注释
            str(bx),
            str(by),
            row[idx['owner_type']].strip(),
            row[idx['owner_id']].strip(),
            row[idx['is_home']].strip() or '0',
            row[idx['inventory']].strip(),
            scenario,
        ])
        sandbox_count += 1

    print(f"[Freeze] 处理 SANDBOX 行: {sandbox_count}, 删除 TUTORIAL dead config: {skipped_tutorial}")

    print(f"[Freeze] 写回 {CSV_PATH}")
    with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(out_rows)

    print(f"[Freeze] 完成。新表头: {NEW_HEADER}")


if __name__ == '__main__':
    freeze()
