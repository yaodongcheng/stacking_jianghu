# --- src/pathfinding.py ---
import pygame
import math
from src.definitions import *
from src.utils import log_game_event

class FloydPathfinder:
    def __init__(self, world_map):
        self.map_w = world_map.w
        self.map_h = world_map.h
        self.walls = world_map.walls
        self.nodes = []
        self.dist_matrix = []
        self.next_node_matrix = []
        self.debug_raw_edges = []  # <--- [新增] 用于存储原始直连边，供画图使用
        self._build_graph(world_map)
        self._run_floyd_warshall()
        log_game_event(f"[Pathfinding] Graph built with {len(self.nodes)} nodes. Floyd-Warshall complete.")
   
    def _build_graph(self, world_map):
        """
        构建关键路点：
        增加 [城门外侧] 节点，确保进出城逻辑顺畅。
        """
        rect = world_map.city_rect
        margin = 100 # 离墙的缓冲距离
        inner_margin = 105 
        
        # 辅助函数：获取城门内侧和外侧的引导点
        def get_gate_points(gate_rect, direction):
            cx, cy = gate_rect.center
            offset_in = 90 # 向内缩进（加大，确保节点远离墙体阻挡范围）
            offset_out = 90 # 向外延伸（同上）
            
            p_in, p_out = (cx, cy), (cx, cy)
            
            if direction == 'NORTH': 
                p_in = (cx, cy + offset_in)
                p_out = (cx, cy - offset_out)
            elif direction == 'SOUTH': 
                p_in = (cx, cy - offset_in)
                p_out = (cx, cy + offset_out)
            elif direction == 'WEST':  
                p_in = (cx + offset_in, cy)
                p_out = (cx - offset_out, cy)
            elif direction == 'EAST':  
                p_in = (cx - offset_in, cy)
                p_out = (cx + offset_out, cy)
            return [ p_in, p_out]

        # 收集所有关键点
        raw_points = []
        
        # 1. 核心区域中心
        raw_points.append(rect.center)

        # 2. 城门组 (中心、内侧、外侧) - 这是解决进出城问题的关键
        raw_points.extend(get_gate_points(world_map.gates['NORTH'], 'NORTH'))
        raw_points.extend(get_gate_points(world_map.gates['SOUTH'], 'SOUTH'))
        raw_points.extend(get_gate_points(world_map.gates['WEST'], 'WEST'))
        raw_points.extend(get_gate_points(world_map.gates['EAST'], 'EAST'))

        # 3. 城内四角中途点 (防止内城卡墙角)
        raw_points.append((rect.left + inner_margin, rect.top + inner_margin))      # 左上内
        raw_points.append((rect.right - inner_margin, rect.top + inner_margin))     # 右上内
        raw_points.append((rect.right - inner_margin, rect.bottom - inner_margin))  # 右下内
        raw_points.append((rect.left + inner_margin, rect.bottom - inner_margin))   # 左下内

        # 4. 城外四角拐点 (防止外城卡墙角) - 关键：让外面的路点也能绕过墙角
        raw_points.append((rect.left - margin, rect.top - margin))     # 左上外
        raw_points.append((rect.right + margin, rect.top - margin))    # 右上外
        raw_points.append((rect.right + margin, rect.bottom + margin)) # 右下外
        raw_points.append((rect.left - margin, rect.bottom + margin))  # 左下外

        # 去重并转为整数坐标
        self.nodes = sorted(list(set([(int(x), int(y)) for x, y in raw_points])))
        n = len(self.nodes)
        # 初始化矩阵
        self.dist_matrix = [[float('inf')] * n for _ in range(n)]
        self.next_node_matrix = [[-1] * n for _ in range(n)]

        # 构建连通图
        print(f"[Graph] 开始构建图，节点数: {n}")
        for i in range(n):
            self.dist_matrix[i][i] = 0
            self.next_node_matrix[i][i] = i
            for j in range(i + 1, n):
                # 检测两点之间是否无阻挡
                debug_this_pair = (i == 12 and j == 16) or (i == 16 and j == 12)
                debug_this_pair = False
                noblock = self._has_line_of_sight(self.nodes[i], self.nodes[j], width=60, debug=debug_this_pair)
                # 检测两点之间是否无阻挡 (传入 debug 参数)
                if noblock:
                    dist = math.hypot(self.nodes[i][0] - self.nodes[j][0], 
                                      self.nodes[i][1] - self.nodes[j][1])
                    # 双向连接
                    self.dist_matrix[i][j] = dist
                    self.dist_matrix[j][i] = dist
                    self.next_node_matrix[i][j] = j
                    self.next_node_matrix[j][i] = i
                    self.debug_raw_edges.append((i, j)) # <--- [新增] 记录这条边用于Debug绘制
                    if debug_this_pair:
                        log_game_event(f"  >>> [RESULT] Node {i}-{j}: 连通! (距离 {dist:.1f})")
                else:
                    if debug_this_pair:
                        log_game_event(f"  >>> [RESULT] Node {i}-{j}: 被阻挡!")
                    

    def _has_line_of_sight(self, p1, p2, width=60,debug= False):
        """
        检测两点之间是否有障碍物。
        使用【墙体膨胀 + 线段相交】算法，比步进采样更精准，杜绝穿墙。
        """
        # 1. 距离极近直接通过
        if math.hypot(p2[0] - p1[0], p2[1] - p1[1]) < 1: return True
    
        # 2. 遍历墙体检测
        # 稍微缩小一点判定宽度(0.8)，允许稍微切角，防止在门口因为过于严格而卡住
        check_width = width * 0.8
        if debug:
            log_game_event(f"  [Check] 线段 {p1} -> {p2} (Width: {check_width})")
        for i, wall in enumerate(self.walls):
            
            inflated_wall = wall.inflate(check_width, check_width)
            hit_segment = inflated_wall.clipline(p1, p2)
            if hit_segment:
                if debug:
                    log_game_event(f"  [X] 撞墙! Wall Index {i}")
                    log_game_event(f"      Wall: {wall}")
                    log_game_event(f"      Hit : {hit_segment}")
                return False # <--- 只要撞到一个，立即返回 False
        if debug:
            log_game_event(f"  [OK] 所有墙体检测通过，无阻挡。")
        return True

        

    def _run_floyd_warshall(self):
        """计算所有节点对的最短路径"""
        n = len(self.nodes)
        for k in range(n):
            for i in range(n):
                for j in range(n):
                    new_dist = self.dist_matrix[i][k] + self.dist_matrix[k][j]
                    if new_dist < self.dist_matrix[i][j]:
                        self.dist_matrix[i][j] = new_dist
                        # 关键：如果我们想从 i 去 j，应该先去 "从 i 去 k 的第一步"
                        self.next_node_matrix[i][j] = self.next_node_matrix[i][k]
 
    def get_next_move_target(self, current_pos, final_target, force_graph=False,agent = None):
        """
        [核心修复] 获取下一步移动坐标。
        逻辑：
        1. 尝试直连终点。
        2. 如果不行，遍历所有 (入口点 -> 出口点) 组合。
        3. 寻找 min( dist(我, 入口) + graph_dist(入口, 出口) + dist(出口, 终点) )
        """
        is_player = agent is not None and getattr(agent, 'job', '') == 'PLAYER'
        is_dbg_npc = DEBUG_NPC_PATH_VERBOSE and agent is not None and getattr(agent, 'debug_selected', False)
        is_dbg = is_dbg_npc or (DEBUG_PLAYER_PATH and is_player)

        # 1. 如果直连畅通，直接走 (使用较大的宽度确保安全)
        if not force_graph and self._has_line_of_sight(current_pos, final_target, width=90):
            if is_dbg:
                log_game_event(f"[Path] {agent.name}: 直连畅通，无需绕路")
            return final_target
        if is_dbg:
            log_game_event(f"[Path] {agent.name}: 直连受阻，开始图寻路")
        if is_dbg:
            log_game_event(f"[DBG路径] {agent.name} 直连受阻 force={force_graph} 当前={current_pos} 终点={final_target}")
        n = len(self.nodes)
        best_entry_idx = -1
        min_total_dist = float('inf')

        # 2. 寻找最佳切入路径
        # 这是一个 O(N^2) 的搜索，但在 N=30 左右时非常快 (~900次浮点加法，忽略不计)
        
        # 预计算：我能看到哪些点 (Entry candidates)
        visible_entries = []
        for i in range(n):
            if self._has_line_of_sight(current_pos, self.nodes[i], width=20):
                d = math.hypot(current_pos[0]-self.nodes[i][0], current_pos[1]-self.nodes[i][1])
                visible_entries.append((i, d))

        # 预计算：哪些点能看到终点 (Exit candidates)
        visible_exits = []
        for j in range(n):
            if self._has_line_of_sight(self.nodes[j], final_target, width=20):
                d = math.hypot(self.nodes[j][0]-final_target[0], self.nodes[j][1]-final_target[1])
                visible_exits.append((j, d))

        # 3. 组合最优路径
        for i, dist_to_entry in visible_entries:
            for j, dist_from_exit in visible_exits:
                graph_dist = self.dist_matrix[i][j]
                
                if graph_dist == float('inf'): continue
                
                total_dist = dist_to_entry + graph_dist + dist_from_exit
                
                if total_dist < min_total_dist:
                    min_total_dist = total_dist
                    best_entry_idx = i
                    # 也可以记录 best_exit_idx 用于调试，但移动只需要知道入口

        # 4. 如果找到了路径
        if best_entry_idx != -1:
            # 这里的逻辑是：
            # 如果我离最佳入口点很远，我就走向入口点。
            # 如果我已经到了入口点（或非常近），我就通过查表走向 graph 中的下一个点。
            
            entry_node = self.nodes[best_entry_idx]
            dist_to_entry = math.hypot(current_pos[0]-entry_node[0], current_pos[1]-entry_node[1])
            
            # 阈值：如果离入口点还有距离，先走到入口点
            # 注意：阈值不能太小，否则 NPC 会在边界上反复横跳
            if dist_to_entry > 40:
                if is_dbg:
                    log_game_event(f"[Path] {agent.name} 前往入口点#{best_entry_idx}{entry_node} 距{dist_to_entry:.0f}px 可见入口={len(visible_entries)} 可见出口={len(visible_exits)}")
                return entry_node
            else:
                # 已经到了入口点附近，查询 Floyd 表，去往最佳出口点方向的下一跳
                # 我们需要知道最佳出口点是谁吗？
                # 上面的循环里我们只记录了 best_entry。
                # 为了精确导航，我们需要知道对于这个 best_entry，哪个 exit 产生了最小值。
                
                # 重新简单查找一下（因为上面没存 best_exit_idx，不想让代码太乱）
                # 在确定了 best_entry_idx 的情况下，找最佳 exit
                best_exit_for_entry = -1
                local_min = float('inf')
                for j, dist_from_exit in visible_exits:
                    d = self.dist_matrix[best_entry_idx][j] + dist_from_exit
                    if d < local_min:
                        local_min = d
                        best_exit_for_entry = j
                
                if best_exit_for_entry != -1:
                    # 如果入口和出口是同一个节点，说明从该节点能直连终点
                    # 但还需确认当前位置到终点是否真的畅通，否则会形成死循环
                    if best_exit_for_entry == best_entry_idx:
                        # 必须用和"直连受阻"相同的宽度(90)来验证，否则会产生矛盾判断导致震颤
                        if self._has_line_of_sight(current_pos, final_target, width=90):
                            if is_dbg:
                                log_game_event(f"[DBG路径] {agent.name} 入口=出口=#{best_entry_idx}，视线畅通(w90)，直连终点={final_target}")
                            return final_target
                        else:
                            # 视线实际不通，但图上无更好路径，尝试从出口节点附近绕行
                            # 选择除 entry 本身之外、距终点最近的可见出口作为下一跳
                            alt_exits = [(j, d) for j, d in visible_exits if j != best_entry_idx]
                            if alt_exits:
                                alt_exit_idx = min(alt_exits, key=lambda x: x[1])[0]
                                next_hop_idx = self.next_node_matrix[best_entry_idx][alt_exit_idx]
                                if next_hop_idx != best_entry_idx and next_hop_idx != -1:
                                    if is_dbg:
                                        log_game_event(f"[DBG路径] {agent.name} 入口=出口=#{best_entry_idx} 但视线不通(w90)，改走备选出口#{alt_exit_idx}→下一跳#{next_hop_idx}")
                                    return self.nodes[next_hop_idx]
                            # 真的无路可走，直接走向终点（允许穿墙兜底）
                            if is_dbg:
                                log_game_event(f"[DBG路径] {agent.name} 入口=出口=#{best_entry_idx} 视线不通且无备选出口，强制直连终点")
                            return final_target
                    next_hop_idx = self.next_node_matrix[best_entry_idx][best_exit_for_entry]
                    # 如果下一跳就是自身（Floyd表问题），跳过直接走向终点
                    if next_hop_idx == best_entry_idx or next_hop_idx == -1:
                        if is_dbg:
                            log_game_event(f"[DBG路径] {agent.name} 下一跳={next_hop_idx}回到自身，改为直连终点={final_target}")
                        return final_target
                    if is_dbg:
                        log_game_event(f"[Path] {agent.name} 已过入口，前往下一跳 入口#{best_entry_idx}{self.nodes[best_entry_idx]} 出口#{best_exit_for_entry} 下一跳#{next_hop_idx}{self.nodes[next_hop_idx]} 可见入口={len(visible_entries)} 可见出口={len(visible_exits)}")
                    return self.nodes[next_hop_idx]

        # 兜底：如果实在找不到路（完全被封死），尝试直走
        if is_dbg:
            log_game_event(f"[DBG路径] {agent.name} 找不到路径！可见入口={len(visible_entries)} 可见出口={len(visible_exits)} 兜底直连终点={final_target}")
        return final_target

    def draw_debug(self, screen, font):
        """
        绘制调试信息：
        1. 连线 (蓝色)
        2. 障碍物 + 序号 (红色)
        3. 路点 + 序号 (绿色/黄色)
        """
        # 1. 绘制连线
        # 1. 绘制连线 (修改后)
        for u, v in self.debug_raw_edges:
            start = self.nodes[u]
            end = self.nodes[v]
            pygame.draw.line(screen, (0, 100, 255), start, end, 1)
            
        n = len(self.nodes)
# =============================================================================
#         for i in range(n):
#             for j in range(i + 1, n):
#                 if self.dist_matrix[i][j] != float('inf'):
#                     start = self.nodes[i]
#                     end = self.nodes[j]
#                     pygame.draw.line(screen, (0, 100, 255), start, end, 1)
# 
# =============================================================================
        # 2. 绘制障碍物 & 序号 (红色)
        s = pygame.Surface((self.map_w, self.map_h), pygame.SRCALPHA)
        for i, wall in enumerate(self.walls):
            # 物理墙 (深红)
            pygame.draw.rect(s, (255, 0, 0, 80), wall) 
            
            # 膨胀框示意 (淡橙色，表示逻辑阻挡范围)
            # 这里画出 60px 宽度对应的阻挡区，让你直观看到为什么线断了或没断
            inflation = wall.inflate(48, 48)
            pygame.draw.rect(s, (255, 100, 0, 30), inflation, 1)
            
            # [新增] 绘制墙体序号
            cx, cy = wall.center
            id_surf = font.render(f"W{i}", True, (255, 255, 255)) # 白色字
            # 直接画在 screen 上，不画在透明层 s 上，保证清晰
            screen.blit(id_surf, (cx - 10, cy - 8))
            
        screen.blit(s, (0,0))
    
        # 3. 绘制路点 & 序号 (绿色)
        for i, node in enumerate(self.nodes):
            cx, cy = int(node[0]), int(node[1])
            pygame.draw.circle(screen, (0, 255, 0), (cx, cy), 4)
            
            # [新增] 绘制节点序号
            txt = font.render(str(i), True, (255, 255, 0)) # 黄色字
            screen.blit(txt, (cx + 6, cy - 6))