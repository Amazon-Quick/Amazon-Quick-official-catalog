"""
description: The one-page report's stylesheet for create_report.py.
last_updated: 2026-11-24
"""

from __future__ import annotations

from report_format import (
    AVAILABLE,
    FAINT,
    INK,
    MUTED,
    OPEN,
    OVER,
    PAPER,
    PLAN_LINE,
    RULE,
    SPENT,
    UNDER,
)


def report_css() -> str:
    """The report's stylesheet, inlined so the page opens offline."""
    return f"""
:root {{ --ink:{INK}; --muted:{MUTED}; --faint:{FAINT}; --rule:{RULE}; --paper:{PAPER}; --over:{OVER}; --under:{UNDER}; }}
* {{ box-sizing: border-box; }}
html {{ background: #EEEBE4; }}
body {{ margin: 0; color: var(--ink); font: 13px/1.45 ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; font-variant-numeric: tabular-nums; -webkit-font-smoothing: antialiased; }}
::selection {{ background: #CFDDE6; color: var(--ink); }}
.sheet {{ width: min(1500px, 100vw); margin: 24px auto; background: var(--paper); padding: 36px 44px 22px; box-shadow: 0 1px 2px rgba(27,31,36,.06), 0 8px 28px rgba(27,31,36,.08); }}
.notice {{ margin: -12px 0 18px; padding: 8px 12px; border: 1px dashed {OVER}; border-radius: 4px; color: #6E2E1E; background: #FBEFEA; font-size: 12px; }}
.notice b {{ margin-right: 8px; text-transform: uppercase; letter-spacing: .05em; font-size: 11px; }}
.top {{ display: flex; align-items: baseline; justify-content: space-between; gap: 24px; border-bottom: 1px solid var(--ink); padding-bottom: 10px; }}
h1 {{ margin: 0; font: 600 22px/1.2 "Iowan Old Style", "Palatino Linotype", Charter, Georgia, serif; letter-spacing: -0.01em; }}
.meta {{ margin: 0; color: var(--muted); font-size: 12px; white-space: nowrap; }}
.headline {{ margin: 14px 0 22px; font: 400 21px/1.42 "Iowan Old Style", "Palatino Linotype", Charter, Georgia, serif; max-width: 118ch; text-wrap: pretty; }}
.headline b {{ font-weight: 650; }}
h2 {{ margin: 0 0 10px; font-size: 11.5px; font-weight: 650; letter-spacing: .04em; text-transform: uppercase; color: var(--muted); }}
h2.gap {{ margin-top: 22px; }}
h2 .count {{ display: inline-block; min-width: 20px; padding: 0 6px; margin-left: 6px; border-radius: 10px; background: var(--over); color: #fff; text-align: center; letter-spacing: 0; }}
.row1 {{ display: grid; grid-template-columns: 1fr 1.25fr; gap: 40px; margin-top: 26px; padding-top: 18px; border-top: 1px solid var(--rule); }}
.kpis {{ display: grid; grid-template-columns: repeat(6, 1fr); gap: 14px; margin: 22px 0 14px; }}
.kpi {{ background: #fff; border: 1px solid var(--rule); border-radius: 6px; padding: 14px 16px 13px; box-shadow: 0 1px 2px rgba(27,31,36,.04); display: flex; flex-direction: column; gap: 3px; }}
.kl {{ font-size: 11.5px; font-weight: 650; letter-spacing: .03em; text-transform: uppercase; color: var(--muted); }}
.kv {{ font-size: 30px; line-height: 1.15; font-weight: 650; letter-spacing: -0.02em; margin-top: 4px; }}
.kv.o {{ color: var(--over); }} .kv.u {{ color: var(--under); }}
.kv.na {{ font-size: 18px; font-weight: 500; color: var(--faint); padding: 7px 0 4px; }}
.ks {{ font-size: 11.5px; color: var(--muted); }}
.meter {{ position: relative; height: 5px; margin-top: 8px; background: {AVAILABLE}; border-radius: 3px; }}
.meter span {{ position: absolute; left: 0; top: 0; bottom: 0; border-radius: 3px; }}
.meter i {{ position: absolute; top: -3px; bottom: -3px; width: 1.5px; background: var(--ink); }}
.walk {{ margin: 0 0 4px; }}
.wbar {{ position: relative; display: flex; height: 14px; border-radius: 3px; overflow: visible; background: {AVAILABLE}; }}
.wbar .ws {{ height: 100%; }}
.wbar .ws:first-child {{ border-radius: 3px 0 0 3px; }}
.wbar .ws.rest {{ background: {AVAILABLE}; border-radius: 0 3px 3px 0; }}
.wbar .ws.over {{ background: repeating-linear-gradient(45deg, {OVER} 0 3px, #F2D6CE 3px 6px); }}
.wbar b {{ position: absolute; top: -4px; bottom: -4px; width: 2px; background: var(--ink); }}
.wbar u {{ position: absolute; top: -4px; bottom: -4px; width: 1px; background: var(--muted); }}
.wcap {{ display: flex; justify-content: space-between; gap: 24px; margin-top: 8px; font-size: 11.5px; color: var(--muted); }}
.wleg {{ display: flex; gap: 16px; white-space: nowrap; }}
.wleg i {{ display: inline-block; width: 9px; height: 9px; border-radius: 2px; margin-right: 6px; vertical-align: -1px; }}
.wleg i.rest {{ background: {AVAILABLE}; box-shadow: inset 0 0 0 1px rgba(27,31,36,.15); }}
.wtxt {{ text-align: right; }}

.block {{ margin-top: 8px; }}
.bhead {{ display: flex; align-items: baseline; justify-content: space-between; }}
.tbtn {{ font: inherit; font-size: 11.5px; color: var(--ink); background: #fff; border: 1px solid var(--rule); border-radius: 4px; padding: 3px 10px; cursor: pointer; }}
.tbtn:hover {{ border-color: var(--muted); }}
.tbtn:focus-visible, tr.grp:focus-visible {{ outline: 2px solid var(--under); outline-offset: 1px; }}
.tablewrap {{ overflow-x: auto; }}
table.bt {{ width: 100%; border-collapse: collapse; font-size: 12.5px; }}
.bt th {{ text-align: right; font-size: 10.5px; font-weight: 650; letter-spacing: .03em; text-transform: uppercase; color: var(--muted); padding: 6px 10px; border-bottom: 1px solid var(--ink); white-space: nowrap; }}
.bt td {{ text-align: right; padding: 6px 10px; border-bottom: 1px solid var(--rule); white-space: nowrap; }}
.bt .tl {{ text-align: left; }}
.bt td.o {{ color: var(--over); font-weight: 600; }} .bt td.u {{ color: var(--under); font-weight: 600; }}
.bt tr.grp {{ cursor: pointer; }}
.bt tr.grp td {{ font-weight: 600; }}
.bt tr.grp:hover td {{ background: #F4F2EC; }}
.bt tr.line td {{ color: #3A424C; }}
.bt tr.line td.tl {{ padding-left: 28px; }}
.bt tr.total td {{ font-weight: 700; border-top: 1px solid var(--ink); border-bottom: 0; }}
.caret {{ display: inline-block; width: 10px; height: 10px; margin-right: 6px; vertical-align: -1px; transition: transform .15s ease-out; color: var(--muted); }}
tr.grp[aria-expanded="true"] .caret {{ transform: rotate(90deg); }}
.n {{ font-weight: 400; color: var(--faint); font-size: 11px; margin-left: 6px; }}
.np {{ font-size: 10px; font-weight: 650; color: var(--over); border: 1px solid currentColor; border-radius: 3px; padding: 0 4px; margin-left: 6px; }}
.bt td.used {{ text-align: left; min-width: 150px; }}
.bt th.used {{ text-align: left; }}
.ub {{ position: relative; display: inline-block; vertical-align: middle; width: 110px; height: 8px; background: {AVAILABLE}; border-radius: 2px; overflow: visible; }}
.ub .sp {{ position: absolute; left: 0; top: 0; bottom: 0; background: {SPENT}; border-radius: 2px 0 0 2px; }}
.ub .cm {{ position: absolute; top: 0; bottom: 0; background: {OPEN}; }}
.ub i {{ position: absolute; top: -3px; bottom: -3px; width: 1.5px; background: var(--ink); }}
.up {{ display: inline-block; width: 36px; margin-left: 8px; font-size: 11.5px; color: var(--muted); }}
.up.o {{ color: var(--over); font-weight: 650; }}
.chip {{ display: inline-block; margin-right: 4px; padding: 0 5px; border-radius: 3px; background: #F6E3DD; color: var(--over); font-size: 10.5px; font-weight: 650; }}
.chip.more {{ background: #EFEDE7; color: var(--muted); }}
.row2 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 40px; margin-top: 26px; padding-top: 18px; border-top: 1px solid var(--rule); }}
svg {{ display: block; width: 100%; height: auto; overflow: visible; }}
svg text {{ font-family: inherit; }}
.lbl {{ font-size: 11px; fill: var(--ink); }}
.lbl.strong {{ font-weight: 650; }}
.axis {{ font-size: 10.5px; fill: var(--muted); }}
.axis.open {{ fill: var(--faint); }}
.axis.faint {{ fill: var(--faint); font-size: 10px; }}
.num {{ font-size: 11px; font-weight: 600; fill: var(--ink); }}
.tag {{ font-size: 10px; font-weight: 650; }}
.legend {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 4px 18px; margin-top: 2px; }}
.leg {{ display: grid; grid-template-columns: 10px 1fr; column-gap: 8px; align-items: center; }}
.sw {{ width: 10px; height: 10px; border-radius: 2px; box-shadow: inset 0 0 0 1px rgba(27,31,36,.12); }}
.lt {{ color: var(--muted); font-size: 11.5px; }}
.lv {{ grid-column: 2; font-size: 17px; font-weight: 600; letter-spacing: -0.01em; }}
.lv.na {{ font-size: 13px; font-weight: 500; color: var(--faint); }}
.mini-legend {{ display: flex; gap: 16px; margin-top: 6px; font-size: 11px; color: var(--muted); }}
.mini-legend i {{ display: inline-block; vertical-align: middle; margin-right: 6px; }}
.mini-legend i.bar {{ width: 9px; height: 9px; background: {SPENT}; }}
.mini-legend i.line {{ width: 14px; height: 2px; background: {PLAN_LINE}; }}
.mini-legend .o {{ color: var(--over); }} .mini-legend .u {{ color: var(--under); }}
.ilist {{ list-style: none; margin: 0; padding: 0; }}
.ilist li {{ padding: 9px 0 10px; border-top: 1px solid var(--rule); }}
.ilist li:first-child {{ border-top: 0; padding-top: 2px; }}
.ih {{ display: grid; grid-template-columns: 36px 1fr auto; gap: 8px; align-items: baseline; }}
.iid {{ color: var(--faint); font-size: 11px; font-weight: 600; }}
.il {{ font-weight: 600; }}
.ia {{ font-weight: 650; font-size: 14px; }}
.ia.o {{ color: var(--over); }} .ia.u {{ color: var(--under); }}
.ib {{ margin: 3px 0 0 44px; color: #3A424C; font-size: 12px; }}
.kind {{ display: inline-block; margin-right: 6px; padding: 0 6px; border: 1px solid var(--rule); border-radius: 3px; font-size: 10.5px; font-weight: 600; color: var(--muted); background: #fff; }}
.more {{ margin: 6px 0 0 38px; color: var(--muted); font-size: 11.5px; }}
.none {{ color: var(--muted); }}
.conf {{ list-style: none; margin: 0; padding: 0; }}
.conf li {{ display: grid; grid-template-columns: 16px 86px 1fr; gap: 9px; align-items: start; padding: 6px 0; border-top: 1px solid var(--rule); font-size: 12px; }}
.conf li:first-child {{ border-top: 0; padding-top: 0; }}
.ic {{ width: 16px; height: 16px; margin-top: 1px; }}
.cl {{ font-weight: 600; }}
.ct {{ color: #3A424C; }}
.empty {{ color: var(--muted); }}
.foot {{ margin-top: 22px; padding-top: 10px; border-top: 1px solid var(--rule); color: var(--muted); font-size: 11px; }}
.foot p {{ margin: 0; max-width: 170ch; }}
@media (max-width: 1100px) {{ .kpis {{ grid-template-columns: repeat(3, 1fr); }} .row1, .row2 {{ grid-template-columns: 1fr; }} .top {{ flex-direction: column; }} .meta {{ white-space: normal; }} .legend {{ grid-template-columns: repeat(2, 1fr); }} }}
@page {{ size: 16in 10in; margin: 0.3in; }}
@media print {{ .tbtn {{ display: none; }} html {{ background: #fff; }} .sheet {{ margin: 0; width: auto; box-shadow: none; padding: 0; }} }}
"""
