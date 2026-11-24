---
description: "The audit report's stylesheet: plain CSS for layout, tabs, light and dark colours, and print rules. render_report.py reads the css block below into the page."
last_updated: 2026-11-24
---
# Report stylesheet

The HTML report embeds the CSS in the block below. It has no `url()`, `@import`, scripts or external references.

```css

:root{
--bg:var(--color-bg,#faf9fc);--card:var(--color-bg-secondary,#fff);--surface:var(--color-surface,#f9fafb);
--hover:var(--color-surface-hover,#f3f4f6);--active:var(--color-surface-active,#e5e7eb);
--text:var(--color-text,#1a1a1a);--text2:var(--color-text-secondary,#5e5e5e);--muted:var(--color-text-muted,#9ca3af);
--line:var(--color-border,rgba(0,0,0,.12));--line-l:var(--color-border-light,rgba(0,0,0,.06));--line-s:var(--color-border-strong,#d1d5db);
--primary:var(--color-primary,#9333ea);--primary-bg:var(--color-primary-bg,#f3e8ff);--on-primary:var(--color-text-on-primary,#fff);
--err:var(--color-error,#ef4444);--err-bg:var(--color-error-bg,rgba(239,68,68,.1));--err-bd:var(--color-error-border,rgba(239,68,68,.3));--err-tx:var(--color-error-text,#b91c1c);
--warn:var(--color-warning,#f59e0b);--warn-bg:var(--color-warning-bg,rgba(245,158,11,.1));--warn-bd:var(--color-warning-border,rgba(245,158,11,.3));--warn-tx:var(--color-warning-text,#92400e);
--info:var(--color-info,#3b82f6);--info-bg:var(--color-info-bg,rgba(59,130,246,.1));--info-bd:var(--color-info-border,rgba(59,130,246,.3));--info-tx:var(--color-info-text,#1e40af);
--ok:var(--color-success,#22c55e);--ok-bg:var(--color-success-bg,rgba(34,197,94,.1));--ok-bd:var(--color-success-border,rgba(34,197,94,.3));--ok-tx:var(--color-success-text,#166534);
--code-bg:var(--color-code-bg,#f6f8fa);
--sans:var(--font-sans,'Helvetica Neue','Segoe UI',Roboto,Helvetica,Arial,sans-serif);
--mono:var(--font-mono,'SF Mono','Monaco','Menlo','Consolas',monospace);
--r-sm:var(--radius-sm,6px);--r-md:var(--radius-md,10px);--r-lg:var(--radius-lg,16px);--r-pill:var(--radius-pill,17px);
--sh-sm:var(--shadow-sm,0 1px 2px rgba(0,0,0,.05));--sh-md:var(--shadow-md,0 4px 12px rgba(0,0,0,.08))}
@media (prefers-color-scheme:dark){:root{
--bg:var(--color-bg,#151518);--card:var(--color-bg-secondary,#1e1e22);--surface:var(--color-surface,#232328);
--hover:var(--color-surface-hover,#2a2a30);--active:var(--color-surface-active,#34343b);
--text:var(--color-text,#ececee);--text2:var(--color-text-secondary,#b5b5bb);--muted:var(--color-text-muted,#85858d);
--line:var(--color-border,rgba(255,255,255,.14));--line-l:var(--color-border-light,rgba(255,255,255,.07));--line-s:var(--color-border-strong,#4b4b53);
--primary:var(--color-primary,#a855f7);--primary-bg:var(--color-primary-bg,rgba(168,85,247,.16));
--err-tx:var(--color-error-text,#fca5a5);--warn-tx:var(--color-warning-text,#fcd34d);--info-tx:var(--color-info-text,#93c5fd);--ok-tx:var(--color-success-text,#86efac);
--code-bg:var(--color-code-bg,#26262b)}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 var(--sans);-webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:0 32px}
header.top{padding:28px 0 4px}
.eyebrow{font-size:12px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--primary)}
h1{font-size:22px;line-height:1.3;margin:4px 0 4px;font-weight:600}
h2{font-size:16px;font-weight:600;margin:28px 0 12px}
h3{font-size:12px;font-weight:600;margin:0 0 10px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}
.meta{color:var(--text2);font-size:13px}.meta span+span::before{content:"\00b7";margin:0 8px;color:var(--muted)}
.sub{color:var(--text2);font-size:13px}.muted{color:var(--muted)}
p{margin:0 0 10px}
/* tabs */
.tabs{display:flex;flex-wrap:wrap}
.tabs>input{position:absolute;opacity:0;pointer-events:none}
.tabbar{flex-basis:100%;height:0}
.tabs>label{padding:12px 4px 10px;margin:14px 22px 0 0;cursor:pointer;color:var(--text2);border-bottom:2px solid transparent;font-weight:500;transition:color .15s ease,border-color .15s ease}
.tabs>label:first-of-type{margin-left:max(32px,calc((100% - 1180px)/2 + 32px))}
.tabs>label:hover{color:var(--text)}
.tabs>input:checked+label{color:var(--text);border-bottom-color:var(--primary);font-weight:600}
.tabs>input:focus-visible+label{outline:2px solid var(--primary);outline-offset:2px;border-radius:var(--r-sm)}
.panels{flex-basis:100%;border-top:1px solid var(--line);padding:8px 0 56px;min-height:80vh}
.panels .wrap>section{display:none}
#t-summary:checked~.panels #p-summary,#t-issues:checked~.panels #p-issues,#t-changes:checked~.panels #p-changes,
#t-map:checked~.panels #p-map,#t-performance:checked~.panels #p-performance{display:block}
@media (prefers-reduced-motion:no-preference){.panels .wrap>section{animation:fade .2s ease-out}@keyframes fade{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}}
.cnt{display:inline-block;min-width:20px;padding:0 7px;margin-left:6px;border-radius:var(--r-pill);background:var(--active);color:var(--text2);font-size:12px;font-weight:600;text-align:center;line-height:20px}
.cnt.crit{background:var(--err-bg);color:var(--err-tx)}.cnt.warn{background:var(--warn-bg);color:var(--warn-tx)}.cnt.ok{background:var(--ok-bg);color:var(--ok-tx)}
/* surfaces */
.card{background:var(--card);border:1px solid var(--line-l);border-radius:var(--r-md);padding:18px 20px;box-shadow:var(--sh-sm)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}
.grid.areas{grid-template-columns:repeat(auto-fit,minmax(200px,1fr))}
.stack>*+*{margin-top:16px}
/* verdict */
.verdict{display:flex;gap:16px;align-items:flex-start;margin:20px 0 4px;padding:20px 22px;border-radius:var(--r-lg);background:var(--card);border:1px solid var(--line-l);box-shadow:var(--sh-sm)}
.v-mark{flex:0 0 40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:700}
.v-crit .v-mark{background:var(--err-bg);color:var(--err-tx)}.v-warn .v-mark{background:var(--warn-bg);color:var(--warn-tx)}.v-ok .v-mark{background:var(--ok-bg);color:var(--ok-tx)}
.v-head{font-size:18px;font-weight:600;line-height:1.35}.v-next{color:var(--text2);margin-top:4px}.v-sum{margin-top:10px}
/* tiles */
.tile{background:var(--card);border:1px solid var(--line-l);border-radius:var(--r-md);padding:16px 18px;box-shadow:var(--sh-sm)}
.t-top{display:flex;justify-content:space-between;align-items:baseline;gap:8px}
.t-name{font-weight:600}.t-big{font-family:var(--mono);font-size:24px;font-weight:600;line-height:1}
.t-unit{font-size:12px;color:var(--muted);margin-left:4px}
.bar{display:flex;height:8px;border-radius:var(--r-pill);overflow:hidden;background:var(--active);margin:14px 0 10px}
.bar i{display:block;height:100%}.bar .b-c{background:var(--err)}.bar .b-w{background:var(--warn)}.bar .b-i{background:var(--info)}.bar .b-f{background:var(--ok)}
.t-leg{display:flex;flex-wrap:wrap;gap:4px 12px;font-size:12px;color:var(--text2)}
.t-leg b{font-family:var(--mono);font-weight:600;color:var(--text)}
.sw{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px;vertical-align:1px}
.sw.c{background:var(--err)}.sw.w{background:var(--warn)}.sw.i{background:var(--info)}.sw.f{background:var(--ok)}.sw.q{background:var(--primary)}
.bar .b-q{background:var(--primary)}
.tile.clear .t-big{color:var(--ok-tx)}.t-foot{margin-top:8px;font-size:12px;color:var(--muted)}
/* tables */
table{width:100%;border-collapse:separate;border-spacing:0;background:var(--card);border:1px solid var(--line-l);border-radius:var(--r-md);overflow:hidden;font-size:13px}
th,td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--line-l);vertical-align:top}
th{font-size:12px;color:var(--muted);font-weight:500;background:var(--surface);border-bottom-color:var(--line)}
tbody tr:last-child td{border-bottom:0}tbody tr:hover td{background:var(--hover)}
td.num,.num{font-family:var(--mono);font-variant-numeric:tabular-nums;white-space:nowrap}
.loc .lab{display:block;font-weight:600;color:var(--text)}.loc .ref{display:block;font-family:var(--mono);font-size:12px;color:var(--text2)}
.loc .ref:only-child{color:var(--text);font-size:12.5px}
.what{color:var(--text)}.also{color:var(--text2);margin-top:4px}.fix{color:var(--text2);margin-top:6px}
.fix b,.impact b,.rev b{font-weight:600;color:var(--text)}
.impact{margin-top:6px;padding:6px 10px;border-radius:var(--r-sm);background:var(--warn-bg);color:var(--text)}
.rev{margin-top:6px;color:var(--text2);font-style:italic}
/* chips */
.chip{display:inline-flex;align-items:center;gap:4px;padding:2px 9px;border-radius:var(--r-pill);font-size:12px;font-weight:600;white-space:nowrap;border:1px solid transparent;line-height:18px}
.chip.critical{background:var(--err-bg);color:var(--err-tx);border-color:var(--err-bd)}
.chip.warning,.chip.confirm{background:var(--warn-bg);color:var(--warn-tx);border-color:var(--warn-bd)}
.chip.info{background:var(--info-bg);color:var(--info-tx);border-color:var(--info-bd)}
.chip.safe,.chip.applied{background:var(--ok-bg);color:var(--ok-tx);border-color:var(--ok-bd)}
.chip.manual,.chip.proposed{background:var(--active);color:var(--text2)}
.chip.skipped{background:var(--err-bg);color:var(--err-tx)}
.chips{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}
.chip.basis-j{background:var(--primary-bg);color:var(--text);border-color:var(--primary)}
.sevcell{display:flex;flex-direction:column;gap:4px;align-items:flex-start}
.q{margin-top:6px;padding:6px 10px;border-radius:var(--r-sm);background:var(--primary-bg);color:var(--text)}
.q b{font-weight:600}
.qlist{display:grid;gap:10px}.qitem{background:var(--card);border:1px solid var(--line-l);border-left:3px solid var(--primary);border-radius:var(--r-md);padding:12px 16px;box-shadow:var(--sh-sm)}
.qitem .qq{font-weight:600;margin-top:4px}.qitem .qmeta{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}
.disclaimer{margin-top:24px;font-size:12.5px;color:var(--text2);padding:12px 16px;border:1px dashed var(--line);border-radius:var(--r-md)}
/* callouts */
.note{display:flex;gap:10px;padding:12px 16px;border-radius:var(--r-md);margin:12px 0;background:var(--info-bg);border:1px solid var(--info-bd)}
.note.warn{background:var(--warn-bg);border-color:var(--warn-bd)}.note.ok{background:var(--ok-bg);border-color:var(--ok-bd)}.note.crit{background:var(--err-bg);border-color:var(--err-bd)}
.note b{font-weight:600}
/* filters */
.filters{display:flex;flex-wrap:wrap;gap:10px 22px;align-items:center;margin:16px 0 12px;padding:12px 14px;background:var(--card);border:1px solid var(--line-l);border-radius:var(--r-md)}
.fg{display:flex;flex-wrap:wrap;align-items:center;gap:4px}
.fg .fl{font-size:12px;color:var(--muted);margin-right:4px;text-transform:uppercase;letter-spacing:.05em}
.fg input{position:absolute;opacity:0;pointer-events:none}
.fg label{padding:3px 10px;border-radius:var(--r-pill);border:1px solid var(--line);cursor:pointer;font-size:12.5px;color:var(--text2);transition:all .15s ease;white-space:nowrap}
.fg label:hover{background:var(--hover);color:var(--text)}
.fg input:checked+label{background:var(--primary-bg);border-color:var(--primary);color:var(--text);font-weight:600}
.fg input:focus-visible+label{outline:2px solid var(--primary);outline-offset:1px}
.fg label .n{color:var(--muted);margin-left:4px;font-weight:400}
.sevleg{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:12.5px;color:var(--text2);margin:0 0 12px}
/* mini cell view */
details.cells{margin-top:8px}details.cells summary{cursor:pointer;color:var(--primary);font-size:12.5px;font-weight:500;list-style:none}
details.cells summary::-webkit-details-marker{display:none}details.cells summary::before{content:"\25B8  "}details.cells[open] summary::before{content:"\25BE  "}
table.mini{width:auto;margin-top:8px;border-radius:var(--r-sm);font-family:var(--mono);font-size:12px;box-shadow:none}
table.mini th,table.mini td{padding:4px 8px;border-right:1px solid var(--line-l);white-space:nowrap;max-width:150px;overflow:hidden;text-overflow:ellipsis}
table.mini th{text-align:center;color:var(--muted);font-weight:400;padding:3px 8px}
table.mini th.rn{text-align:right}table.mini tbody tr:hover td{background:transparent}
table.mini td.k-i,table.mini td.k-f{text-align:right}table.mini td.k-t{color:var(--text2);font-family:var(--sans)}
table.mini td.k-e{color:var(--err-tx);font-weight:600}table.mini td.gap,table.mini th.gap{color:var(--muted);text-align:center;padding:4px 2px}
table.mini td.hl{background:var(--warn-bg)!important;box-shadow:inset 0 0 0 2px var(--warn)}
table.mini.critical td.hl{background:var(--err-bg)!important;box-shadow:inset 0 0 0 2px var(--err)}
.mini-leg{font-size:12px;color:var(--muted);margin-top:4px}
/* changes */
.chg{background:var(--card);border:1px solid var(--line-l);border-radius:var(--r-md);padding:14px 18px;margin:0 0 12px;box-shadow:var(--sh-sm)}
.chg.st-applied{border-left:3px solid var(--ok)}.chg.st-skipped{border-left:3px solid var(--err)}.chg.r-confirm.st-proposed{border-left:3px solid var(--warn)}
.chg-head{display:flex;gap:14px;align-items:flex-start}
.chg-n{font-family:var(--mono);font-weight:600;font-size:15px;min-width:34px;color:var(--text)}
.chg-where{flex:1}.chg-body{margin:8px 0 0 48px}
.chg-what{color:var(--text)}
.diff{margin-top:8px;border:1px solid var(--line-l);border-radius:var(--r-sm);overflow:hidden;font-family:var(--mono);font-size:12.5px;background:var(--code-bg)}
.diff>div{display:flex;gap:10px;padding:6px 10px;overflow-x:auto}
.diff .d-sign{color:var(--muted);user-select:none}.diff code{font-family:inherit;white-space:pre}
.diff .d-old{border-bottom:1px solid var(--line-l)}
del{background:var(--err-bg);color:var(--err-tx);text-decoration:line-through;border-radius:3px;padding:0 2px}
ins{background:var(--ok-bg);color:var(--ok-tx);text-decoration:none;border-radius:3px;padding:0 2px}
.diff-note{font-size:12px;color:var(--muted);margin-top:4px}
.vals{display:flex;flex-wrap:wrap;gap:4px 16px;margin-top:8px;font-size:13px}
.val .vl{color:var(--text2);margin-right:6px}.val .old{font-family:var(--mono);color:var(--text2)}
.val .new{font-family:var(--mono);font-weight:600}.delta{font-family:var(--mono);font-size:12px;color:var(--text2);margin-left:4px}
.basis{font-size:12px;color:var(--muted);margin-top:4px}
/* key results */
.kr td.after{font-weight:600}
/* map */
dl.kv{display:grid;grid-template-columns:150px 1fr;gap:8px 16px;margin:0}dl.kv dt{color:var(--text2)}dl.kv dd{margin:0}
.map{overflow-x:auto;background:var(--card);border:1px solid var(--line-l);border-radius:var(--r-md);padding:12px}
.map svg text{font-family:var(--sans)}
.m-node rect{stroke-width:1.6}.m-t1{fill:var(--text);font-size:14px;font-weight:600}.m-t2{fill:var(--text2);font-size:11px}
.m-inputs rect{fill:var(--info-bg);stroke:var(--info)}.m-calculation rect{fill:var(--surface);stroke:var(--line-s)}
.m-output rect{fill:var(--ok-bg);stroke:var(--ok)}.m-data rect{fill:var(--warn-bg);stroke:var(--warn)}
.m-notes rect,.m-external rect{fill:var(--card);stroke:var(--line-s)}.m-crit rect{stroke:var(--err);stroke-width:2.4}
.m-edge{fill:none;stroke:var(--line-s)}.m-arrow{fill:var(--line-s)}.m-lab{fill:var(--text2);font-size:11px}
.m-badge{fill:var(--warn)}.m-badge.crit{fill:var(--err)}.m-btx{fill:#fff;font-size:11px;font-weight:700}
.legend{display:flex;flex-wrap:wrap;gap:8px 16px;font-size:12px;color:var(--text2);margin:10px 2px}
.legend i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-2px;border:1.5px solid}
.lg-inputs{background:var(--info-bg);border-color:var(--info)!important}.lg-calculation{background:var(--surface);border-color:var(--line-s)!important}
.lg-output{background:var(--ok-bg);border-color:var(--ok)!important}.lg-data{background:var(--warn-bg);border-color:var(--warn)!important}
.lg-notes{background:var(--card);border-color:var(--line-s)!important}.lg-hidden{background:var(--card);border-color:var(--line-s)!important;border-style:dashed!important}
/* performance */
.metrics{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}
.metric{display:inline-flex;gap:6px;align-items:center;padding:4px 10px;border-radius:var(--r-pill);background:var(--card);border:1px solid var(--line-l);font-size:12.5px}
.metric b{font-family:var(--mono);font-weight:600}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px;vertical-align:0}
.dot.green{background:var(--ok)}.dot.yellow{background:var(--warn)}.dot.red{background:var(--err)}.dot.none{background:var(--line-s)}
.empty{color:var(--text2);padding:14px 16px;background:var(--card);border:1px dashed var(--line);border-radius:var(--r-md)}
details.judged{margin-top:20px}details.judged>summary{cursor:pointer;font-weight:600;padding:6px 0}
footer{color:var(--text2);font-size:12.5px;margin-top:40px;border-top:1px solid var(--line-l);padding-top:16px;display:flex;flex-wrap:wrap;gap:10px;align-items:center}
a.btn{display:inline-flex;align-items:center;gap:6px;padding:7px 14px;border:1px solid var(--line);border-radius:var(--r-pill);background:var(--card);color:var(--text);text-decoration:none;font-weight:500;transition:all .15s ease}
a.btn:hover{background:var(--hover);border-color:var(--line-s)}a.btn.primary{background:var(--primary);border-color:var(--primary);color:var(--on-primary)}
.print-only{display:none}
@media (max-width:720px){.wrap{padding:0 16px}.tabs>label{margin-right:14px}.tabs>label:first-of-type{margin-left:16px}.chg-body{margin-left:0}dl.kv{grid-template-columns:1fr}}
@media print{
*{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{background:#fff;font-size:12px}.tabs>label,.tabs>input,.filters,details.cells,a.btn{display:none!important}
.panels{border:0;padding-top:0}.panels .wrap>section{display:block!important;break-before:page;animation:none!important}
.panels .wrap>section:first-of-type{break-before:auto}tr.f{display:table-row!important}
.card,.tile,.chg,.verdict,tr{break-inside:avoid}.print-only{display:block}.card,.tile,.chg,table,.verdict{box-shadow:none}}
```
