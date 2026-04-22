# --- src/task/quest_presenter.py ---
"""
任务系统的 UI 展示数据生成器

策划须知：
- 这里只负责"读 quest 状态、产出 UI 要的字符串/对象"，不会修改任何任务状态
- 想改侧边栏文字、详情面板字段、日志格式 → 都在这个文件里改
- 想给某种任务类型改"完成条件"或"进度文案" → 改 quest_types/<类型>.py 里的方法
"""

from .display import TaskDisplayData
from .npc_registry import resolve_npc_display_name
from . import quest_types
from src.definitions import QS_AVAILABLE, QS_ACTIVE, QS_READY


class QuestPresenter:
    """任务系统的 UI 展示数据生成器（无状态，依赖 QuestManager 只读）"""

    def __init__(self, qm):
        self.qm = qm

    # ─────────────────────────────────────────────────────────
    # 任务日志面板
    # ─────────────────────────────────────────────────────────
    def get_quest_log_data(self):
        """返回 (active_list, finished_list) 供任务日志 UI 显示"""
        qm = self.qm
        active_list = []
        if qm.active_quest_id != "Q_FREE_PLAY":
            q = qm.get_current_quest()
            status_str = {
                QS_ACTIVE: "进行中",
                QS_READY: "可交付",
            }.get(qm.quest_status, "待接取")
            active_list.append({
                'title': q.title,
                'desc': q.desc,
                'target': f"{q.target} x{q.count}" if q.count > 0 else "与NPC交谈",
                'status': status_str,
            })

        finished_list = [
            {'title': qm.quests[qid].title, 'desc': qm.quests[qid].desc}
            for qid in qm.quests if qid in qm.finished_quests
        ]
        return active_list, finished_list

    # ─────────────────────────────────────────────────────────
    # 详情面板：完成条件文案
    # ─────────────────────────────────────────────────────────
    def derive_objective(self, q, player=None, all_cards=()) -> str:
        """从 QuestData 派生"完成条件"。委托给 quest_types/<类型>.py。
        传入 player 时，会自动追加"（当前 X）"后缀（若该任务类型有可观测进度）。
        """
        if not q:
            return ""
        qt = quest_types.get(q.type)
        base = qt.objective_text(q)
        if not base:
            return ""
        if player is None:
            return base
        current = qt.current_value_text(q, player, all_cards)
        if not current:
            return base
        return f"{base}（当前 {current}）"

    # ─────────────────────────────────────────────────────────
    # 侧边栏：当前任务文字（带状态前缀和进度）
    # ─────────────────────────────────────────────────────────
    def get_current_objective_text(self, player=None, all_cards=()) -> str:
        qm = self.qm
        if not qm.flags['guidance_visible']:
            return ""
        q = qm.get_current_quest()
        if not q:
            return ""

        submit_npc_name = resolve_npc_display_name(q.submit_npc)
        is_auto = (q.submit_npc == '9999')

        if qm.quest_status == QS_AVAILABLE:
            if is_auto:
                return f"[!] 新任务：{q.title} (自动触发)"
            return f"[!] 新任务：{q.title} (找{submit_npc_name}接取)"

        if qm.quest_status == QS_READY:
            if is_auto:
                return f"[√] {q.title} 完成 (等待剧情触发...)"
            return f"[√] {q.title} 完成 (找{submit_npc_name}复命)"

        if qm.quest_status == QS_ACTIVE:
            prog_str = quest_types.get(q.type).progress_text(q, player, all_cards) if player else ""
            return f">> {q.desc} {prog_str}"

        return ""

    # ─────────────────────────────────────────────────────────
    # 侧边栏：所有任务展示数据（按优先级排序）
    # ─────────────────────────────────────────────────────────
    def get_all_task_displays(self, player=None, all_cards=()) -> list:
        """获取所有任务的展示数据。
        开场剧情期间（guidance_visible=False）只显示主线任务。
        """
        # 延迟导入避免循环
        from .quest_system import (
            TASK_TYPE_MAIN, TASK_TYPE_SURVIVAL, TASK_PRIORITY,
        )

        qm = self.qm
        tasks = []
        show_side_tasks = qm.flags.get('guidance_visible', False)

        # ===== 1. 生存任务（开场剧情期间隐藏）=====
        if player and show_side_tasks:
            tasks.extend(self._build_survival_tasks(player, TASK_TYPE_SURVIVAL))

        # ===== 2. 情报委托 / 3. 势力任务（待实现） =====

        # ===== 4. 主线任务（始终显示）=====
        main_task = self._build_main_task(player, all_cards, TASK_TYPE_MAIN)
        if main_task:
            tasks.append(main_task)

        tasks.sort(key=lambda t: TASK_PRIORITY.get(t.type, 99))
        return tasks

    def _build_survival_tasks(self, player, task_type) -> list:
        """生存类任务的展示数据（饥饿/寒冷）"""
        out = []
        hunger = getattr(player, 'hunger', 0)
        cold = getattr(player, 'cold', 0)

        if hunger >= 70:
            out.append(TaskDisplayData(
                task_type=task_type, is_urgent=True,
                text=f"得找点吃的，把饥饿值降到 50 以下（当前 {int(hunger)}）",
                description="饥饿是会死人的。再不进食，体力崩溃只是时间问题。",
                objective=f"将饥饿值降到 50 以下（当前 {int(hunger)}）",
                target_npc="玩家",
            ))
        elif hunger >= 50:
            out.append(TaskDisplayData(
                task_type=task_type, is_urgent=False,
                text=f"肚子有些饿了，把饥饿值降到 50 以下（当前 {int(hunger)}）",
                description="还能撑一阵子，但久了对身子不好。",
                objective=f"将饥饿值降到 50 以下（当前 {int(hunger)}）",
                target_npc="玩家",
            ))

        if cold >= 70:
            out.append(TaskDisplayData(
                task_type=task_type, is_urgent=True,
                text=f"快冻僵了，找件衣裳或近火取暖（当前寒冷 {int(cold)}）",
                description="再这么冻下去，命都要保不住。",
                objective=f"找件衣裳或近火取暖（当前寒冷 {int(cold)}）",
                target_npc="玩家",
            ))
        return out

    def _build_main_task(self, player, all_cards, task_type):
        """主线任务的展示数据。开场剧情期间也显示。"""
        qm = self.qm
        # 临时启用 guidance_visible 以确保主线文字不被过滤
        saved_gv = qm.flags.get('guidance_visible', False)
        qm.flags['guidance_visible'] = True
        main_text = self.get_current_objective_text(player, all_cards)
        qm.flags['guidance_visible'] = saved_gv

        if not main_text:
            return None

        is_complete = "[√]" in main_text
        clean_text = main_text.replace("[!]", "").replace("[√]", "").replace(">>", "").strip()

        q = qm.get_current_quest()
        if q and q.submit_npc == '9999':
            target_npc = "玩家"
        else:
            target_npc = resolve_npc_display_name(q.submit_npc) if q else ""

        reward_text = ""
        if q and q.reward:
            from .dsl import parse_dsl, format_dsl
            reward_text = format_dsl(parse_dsl(q.reward))

        return TaskDisplayData(
            task_type=task_type,
            text=clean_text,
            is_complete=is_complete,
            description=q.desc if q else "",
            target_npc=target_npc,
            objective=self.derive_objective(q, player, all_cards) if q else "",
            reward=reward_text,
            deadline_days=q.deadline if q else 0,
        )
