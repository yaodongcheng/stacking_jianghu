"""
经济循环检查脚本 - 分析物品流通、孤立系统、生产消费链
"""
import csv
from collections import defaultdict

def parse_item(s):
    """解析 ITEM:物品名:数量 格式"""
    if not s or not s.startswith('ITEM:'):
        return None
    parts = s.split(':')
    return parts[1] if len(parts) >= 2 else None

def load_recipes():
    recipes = []
    with open('data/recipes.csv', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            # 跳过注释行
            if r.get('id', '').startswith('#') or not r.get('id'):
                continue
            recipes.append(r)
    return recipes

def load_items():
    items = {}
    with open('data/items.csv', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            items[r['id']] = r
    return items

def analyze_economy():
    recipes = load_recipes()
    all_items = load_items()
    
    # 追踪每个物品的生产和消费配方
    produced_by = defaultdict(list)  # 物品 -> 生产它的配方
    consumed_by = defaultdict(list)  # 物品 -> 消费它的配方
    
    for r in recipes:
        recipe_id = r['id']
        
        # 检查产出
        output = r.get('output', '')
        if output.startswith('ITEM:'):
            item_name = parse_item(output)
            if item_name:
                produced_by[item_name].append(recipe_id)
        
        # 检查输入
        inp = r.get('input', '')
        if inp and inp not in ['ANY', 'PLAYER', 'NONE'] and not inp.isupper():
            consumed_by[inp].append(recipe_id)
        
        # 检查ext_input
        ext = r.get('ext_input', '')
        if ext:
            item_name = ext.split(':')[0]
            if item_name:
                consumed_by[item_name].append(recipe_id)
    
    print("=" * 60)
    print("【经济循环分析报告】")
    print("=" * 60)
    
    # 1. 孤立物品 - 既不被生产也不被消费
    all_item_names = set(all_items.keys())
    in_economy = set(produced_by.keys()) | set(consumed_by.keys())
    orphan_items = all_item_names - in_economy
    
    print(f"\n📦 items.csv中定义的物品: {len(all_item_names)}个")
    print(f"🔄 参与经济循环的物品: {len(in_economy)}个")
    print(f"[x] 孤立物品: {len(orphan_items)}个")
    if orphan_items:
        print("   (这些物品没有任何配方使用)")
        for item in sorted(orphan_items):
            item_data = all_items.get(item, {})
            desc = item_data.get('desc', '无描述')
            print(f"   - {item}: {desc}")
    
    # 2. 终端产品 - 只被生产，不被消费
    terminal_products = set(produced_by.keys()) - set(consumed_by.keys())
    print(f"\n🏁 终端产品(只生产不消费): {len(terminal_products)}个")
    print("   (这些物品需要能被出售或使用)")
    for item in sorted(terminal_products):
        producers = produced_by[item]
        print(f"   - {item} <- 来自: {', '.join(producers[:3])}")
    
    # 3. 原材料 - 只被消费，不被生产
    raw_materials = set(consumed_by.keys()) - set(produced_by.keys())
    print(f"\n🌱 原材料(只消费不生产): {len(raw_materials)}个")
    print("   (这些物品需要能采集或购买)")
    for item in sorted(raw_materials):
        consumers = consumed_by[item]
        print(f"   - {item} -> 用于: {', '.join(consumers[:3])}")
    
    # 4. 检查终端产品是否有销售渠道
    print("\n" + "=" * 60)
    print("【终端产品销售渠道检查】")
    print("=" * 60)
    
    sellable_outputs = []
    for r in recipes:
        if 'SELL' in r['id'] or r.get('target_type') == 'BUILDING' and r.get('target_id') == 'MARKET':
            inp = r.get('input', '')
            ext = r.get('ext_input', '')
            if inp and not inp.isupper():
                sellable_outputs.append(inp)
            if ext:
                sellable_outputs.append(ext.split(':')[0])
    
    sellable_set = set(sellable_outputs)
    unsellable = terminal_products - sellable_set - {'铜钱'}  # 铜钱本身就是货币
    
    print(f"[ok] 可出售的物品: {len(sellable_set)}种")
    print(f"[x] 无法出售的终端产品: {len(unsellable)}种")
    if unsellable:
        for item in sorted(unsellable):
            print(f"   - {item} (无销售配方!)")
    
    # 5. 检查原材料获取途径
    print("\n" + "=" * 60)
    print("【原材料获取途径检查】")
    print("=" * 60)
    
    gatherable = set()
    buyable = set()
    
    for r in recipes:
        output = r.get('output', '')
        cost = r.get('cost_money', '')
        
        if output.startswith('ITEM:'):
            item = parse_item(output)
            if item:
                # 如果有cost_money说明可以购买
                if cost and cost.isdigit() and int(cost) > 0:
                    buyable.add(item)
                # 如果input是ANY或无消耗，说明可以采集
                inp = r.get('input', '')
                if inp in ['ANY', 'PLAYER', 'NONE'] and not r.get('ext_input'):
                    gatherable.add(item)
    
    unobtainable = raw_materials - gatherable - buyable - produced_by.keys()
    
    print(f"🌿 可采集的物品: {sorted(gatherable)}")
    print(f"💰 可购买的物品: {sorted(buyable)}")
    print(f"[x] 无法获取的原材料: {len(unobtainable)}种")
    if unobtainable:
        for item in sorted(unobtainable):
            consumers = consumed_by.get(item, [])
            print(f"   - {item} (被 {', '.join(consumers[:2])} 需要，但无法获取!)")
    
    # 6. 职业工作检查
    print("\n" + "=" * 60)
    print("【职业配方覆盖检查】")
    print("=" * 60)
    
    jobs = ['FARMER', 'MERCHANT', 'SCHOLAR', 'MONK', 'ARTISAN', 'GUARD', 
            'OFFICIAL', 'DANCER', 'BANDIT', 'HUNTER', 'FISHERMAN', 'MINER', 'WOODCUTTER']
    
    job_recipes = defaultdict(list)
    for r in recipes:
        inp = r.get('input', '')
        if inp in jobs:
            job_recipes[inp].append(r['id'])
    
    for job in jobs:
        count = len(job_recipes[job])
        status = "[ok]" if count > 0 else "[x]"
        print(f"   {status} {job}: {count}个配方")
        if count == 0:
            print(f"      (该职业NPC可能无法自动工作!)")

    return orphan_items, unsellable, unobtainable

if __name__ == '__main__':
    orphans, unsellable, unobtainable = analyze_economy()
    
    print("\n" + "=" * 60)
    print("【修复建议】")
    print("=" * 60)
    
    if orphans:
        print(f"\n需要为 {len(orphans)} 个孤立物品添加配方:")
        for item in list(orphans)[:5]:
            print(f"   - {item}: 考虑添加生产/使用配方")
    
    if unsellable:
        print(f"\n需要为 {len(unsellable)} 个终端产品添加销售渠道:")
        for item in list(unsellable)[:5]:
            print(f"   - {item}: 在MARKET添加SELL_{item.upper()}配方")
    
    if unobtainable:
        print(f"\n需要为 {len(unobtainable)} 个原材料添加获取途径:")
        for item in list(unobtainable)[:5]:
            print(f"   - {item}: 添加采集/购买配方")
