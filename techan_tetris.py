#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""特产后备箱模拟器 techan-tetris。

国庆返程玩梗：爸妈往你后备箱里塞了 8 样特产，后备箱只有 6x4 格，
载重上限 28 斤。轮流放置、可以旋转，实在放不下就含泪舍弃——
但超重会直接把后备箱压塌。

纯 Python 标准库，无第三方依赖。
"""

import argparse
import random
import sys
from collections import Counter

W, H = 6, 4          # 后备箱：宽 6 格，高 4 格
WEIGHT_LIMIT = 28    # 载重上限（斤，玩梗单位）
DISCARD_PENALTY = 5  # 每舍弃一样特产扣的爱意值

# 全部虚构命名：形状 / 重量(斤) / 爱意值
ITEMS = [
    {"name": "土鸡蛋", "cells": [(0, 0)], "weight": 1, "love": 5},
    {"name": "腊肉", "cells": [(0, 0), (0, 1), (1, 0), (1, 1)], "weight": 6, "love": 14},
    {"name": "香肠", "cells": [(0, 0), (0, 1), (0, 2)], "weight": 3, "love": 10},
    {"name": "土鸡", "cells": [(0, 0), (1, 0), (1, 1)], "weight": 5, "love": 14},
    {"name": "月饼盒", "cells": [(0, 0), (0, 1)], "weight": 4, "love": 11},
    {"name": "辣椒串", "cells": [(0, 0), (1, 0)], "weight": 2, "love": 8},
    {"name": "腌菜坛", "cells": [(0, 0), (0, 1), (1, 0)], "weight": 4, "love": 9},
    {"name": "红薯", "cells": [(0, 0), (0, 1), (0, 2), (1, 1)], "weight": 5, "love": 13},
]


def rotate_cells(cells):
    """顺时针旋转 90 度，并归一化到原点。"""
    turned = [(c, -r) for r, c in cells]
    min_r = min(r for r, _ in turned)
    min_c = min(c for _, c in turned)
    return sorted((r - min_r, c - min_c) for r, c in turned)


def rotations_of(cells):
    """返回去重后的全部旋转形态（顺时针 0/90/180/270）。"""
    seen = set()
    out = []
    cur = sorted(cells)
    for _ in range(4):
        key = tuple(cur)
        if key not in seen:
            seen.add(key)
            out.append(cur)
        cur = rotate_cells(cur)
    return out


for _it in ITEMS:
    _it["rots"] = rotations_of(_it["cells"])
del _it


class Trunk:
    """6x4 后备箱状态机。"""

    def __init__(self):
        self.grid = [[0] * W for _ in range(H)]
        self.weight = 0
        self.love = 0
        self.discarded = 0
        self.discarded_names = []
        self.placed_names = []
        self.overloaded = False

    def fits(self, cells, r, c):
        """(r, c) 处能否放下该形状：不越界且不重叠。"""
        for dr, dc in cells:
            rr, cc = r + dr, c + dc
            if not (0 <= rr < H and 0 <= cc < W):
                return False
            if self.grid[rr][cc] != 0:
                return False
        return True

    def any_fit(self, item):
        """该特产是否还存在任何可放位置。"""
        return any(
            self.fits(rot, r, c)
            for rot in item["rots"]
            for r in range(H)
            for c in range(W)
        )

    def put(self, idx, item, cells, r, c):
        """放置（调用前请先用 fits 校验）。超重则标记压塌。"""
        for dr, dc in cells:
            self.grid[r + dr][c + dc] = idx + 1
        self.weight += item["weight"]
        self.love += item["love"]
        self.placed_names.append(item["name"])
        if self.weight > WEIGHT_LIMIT:
            self.overloaded = True

    def drop(self, item):
        """含泪舍弃。"""
        self.discarded += 1
        self.discarded_names.append(item["name"])

    def render(self):
        lines = ["+" + "-" * W + "+"]
        for row in self.grid:
            lines.append("|" + "".join(str(v) if v else "·" for v in row) + "|")
        lines.append("+" + "-" * W + "+")
        return "\n".join(lines)


TITLE_ORDER = ["后备箱大师", "妈妈的骄傲", "特产刺客", "妈妈再也不塞了", "超载战神"]

COMMENTS = {
    "后备箱大师": "连妈妈都惊呆了：这孩子后备箱装得比货车还齐！",
    "妈妈的骄傲": "妈妈逢人就夸：我家孩子，后备箱装得可整齐了。",
    "特产刺客": "你含泪舍弃特产的样子，像个没有感情的刺客。",
    "妈妈再也不塞了": "妈妈宣布：以后特产直接快递，到付。",
    "超载战神": "哐当！后备箱盖被压变形了。妈妈：下次我直接给你寄快递！",
}


def settle(trunk):
    """结算：返回 (称号, 得分, 评语)。"""
    if trunk.overloaded:
        return "超载战神", trunk.love, COMMENTS["超载战神"]
    score = max(0, trunk.love - DISCARD_PENALTY * trunk.discarded)
    if score >= 68:
        title = "后备箱大师"
    elif score >= 50:
        title = "妈妈的骄傲"
    elif score >= 30:
        title = "特产刺客"
    else:
        title = "妈妈再也不塞了"
    return title, score, COMMENTS[title]


def greedy_place(trunk, order):
    """AI：按顺序给每样特产找第一个能放且不超重的位置，否则舍弃。"""
    for idx in order:
        item = ITEMS[idx]
        if trunk.weight + item["weight"] > WEIGHT_LIMIT:
            trunk.drop(item)
            continue
        done = False
        for rot in item["rots"]:
            for r in range(H):
                for c in range(W):
                    if trunk.fits(rot, r, c):
                        trunk.put(idx, item, rot, r, c)
                        done = True
                        break
                if done:
                    break
            if done:
                break
        if not done:
            trunk.drop(item)
    return trunk


def auto_game(seed):
    rng = random.Random(seed)
    order = list(range(len(ITEMS)))
    rng.shuffle(order)
    return greedy_place(Trunk(), order)


def run_auto(games, seed, verbose):
    dist = Counter()
    for i in range(games):
        trunk = auto_game(seed + i)
        title, score, _ = settle(trunk)
        dist[title] += 1
        if verbose:
            print(f"=== 第 {i + 1} 局（seed={seed + i}）===")
            print(trunk.render())
            print(f"称号：{title}（{score} 分），"
                  f"装下 {len(trunk.placed_names)} 样，"
                  f"舍弃 {trunk.discarded} 样，"
                  f"载重 {trunk.weight}/{WEIGHT_LIMIT} 斤\n")
    print(f"共 {games} 局，称号分布：")
    for t in TITLE_ORDER:
        if dist[t]:
            print(f"  {t}：{'█' * dist[t]} ({dist[t]})")


def preview(item):
    """特产形状预览（■ 为占用格）。"""
    rots = item["rots"][0]
    max_r = max(r for r, _ in rots)
    max_c = max(c for _, c in rots)
    return "\n".join(
        "".join("■" if (r, c) in rots else "·" for c in range(max_c + 1))
        for r in range(max_r + 1)
    )


def interactive():
    trunk = Trunk()
    print("=== 特产后备箱 ===")
    print(f"后备箱 {W}x{H} 格，载重上限 {WEIGHT_LIMIT} 斤，8 样特产排队等装车。")
    print("每样特产：输入「行 列 旋转次数」(如 0 2 1)，或输入 q 含泪舍弃。\n")
    for idx in range(len(ITEMS)):
        item = ITEMS[idx]
        print(f"【{item['name']}】重 {item['weight']} 斤 · 爱意 {item['love']}")
        print(preview(item))
        if not trunk.any_fit(item):
            print("（好像已经放不下了，不如含泪舍弃？）")
        while True:
            try:
                s = input("> ").strip()
            except EOFError:
                print("\n已退出。")
                return 2
            if s.lower() == "q":
                trunk.drop(item)
                print(f"含泪舍弃了{item['name']}（爱意 -{DISCARD_PENALTY}）\n")
                break
            parts = s.split()
            if len(parts) != 3:
                print("格式不对：请输入「行 列 旋转次数」，如 0 2 1；舍弃请输 q")
                continue
            try:
                r, c, k = (int(x) for x in parts)
            except ValueError:
                print("行、列、旋转次数都得是数字。")
                continue
            rots = item["rots"]
            if not 0 <= k < len(rots):
                print(f"旋转次数要在 0~{len(rots) - 1} 之间（该特产有 {len(rots)} 种形态）。")
                continue
            cells = rots[k]
            if not trunk.fits(cells, r, c):
                print("这里放不下（越界或与已装特产重叠），换个位置试试。")
                continue
            trunk.put(idx, item, cells, r, c)
            print(trunk.render())
            print(f"当前载重 {trunk.weight}/{WEIGHT_LIMIT} 斤\n")
            break
        if trunk.overloaded:
            print("⚠ 哐当！后备箱被压塌了！")
            break
    title, score, comment = settle(trunk)
    print(trunk.render())
    print(f"装下 {len(trunk.placed_names)} 样，舍弃 {trunk.discarded} 样，得分 {score}")
    print(f"称号：{title}\n{comment}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="特产后备箱模拟器：把爸妈塞的 8 样特产装进 6x4 后备箱。")
    ap.add_argument("--auto", action="store_true", help="AI 自动演示")
    ap.add_argument("--games", type=int, default=1, help="自动演示局数")
    ap.add_argument("--seed", type=int, default=42, help="随机种子")
    ap.add_argument("--verbose", action="store_true", help="打印每局后备箱图")
    args = ap.parse_args(argv)
    if args.auto:
        if args.games < 1:
            ap.error("--games 必须 ≥ 1")
        run_auto(args.games, args.seed, args.verbose)
        return 0
    if not sys.stdin.isatty():
        print("交互模式需要终端运行；非交互演示请用 --auto。")
        return 2
    return interactive()


if __name__ == "__main__":
    sys.exit(main())
