"""Minimal stdlib web dashboard (no external deps)."""
import json
import logging
import threading
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class BufferHandler(logging.Handler):
    def __init__(self, maxlen=200):
        super().__init__()
        self.lines = deque(maxlen=maxlen)
        self.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%H:%M:%S"))

    def emit(self, record):
        try:
            self.lines.append(self.format(record))
        except Exception:
            pass


PAGE = """<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0b0d10"><title>RSI-бот</title><style>
*{box-sizing:border-box}body{margin:0;padding:16px 14px 28px;background:#0b0d10;color:#e8eaed;
font-family:-apple-system,BlinkMacSystemFont,sans-serif;-webkit-font-smoothing:antialiased}
.top{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px}
.badge{font-size:22px;font-weight:800;letter-spacing:.5px;padding:12px 18px;border-radius:14px}
.g{background:#12351f;color:#3ddc84}.y{background:#3a3110;color:#f5c542}.r{background:#3d1416;color:#ff5c5c}.n{background:#22262b;color:#9aa0a6}
.tag{font-size:11px;font-weight:700;padding:4px 8px;border-radius:8px;background:#22262b;color:#9aa0a6;margin-left:4px}
.sym{color:#9aa0a6;font-size:13px;font-weight:600;letter-spacing:1px}
.price{font-size:46px;font-weight:800;letter-spacing:-1px;margin:2px 0 4px;font-variant-numeric:tabular-nums}
.sub{color:#6b7178;font-size:12px}
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:16px 0}
.card,.box{background:#14171b;border-radius:14px;padding:12px}
.card .l{color:#9aa0a6;font-size:12px;font-weight:600}.card .v{font-size:30px;font-weight:800;margin:4px 0 8px;font-variant-numeric:tabular-nums}
.bar{position:relative;height:4px;background:#2a2f35;border-radius:2px}.bar i{position:absolute;left:0;top:0;bottom:0;border-radius:2px}
.bar b{position:absolute;top:-3px;width:1px;height:10px;background:#555}
.cg{color:#3ddc84}.cr{color:#ff5c5c}.cn{color:#e8eaed}
.box{margin-bottom:10px}.h{color:#9aa0a6;font-size:12px;font-weight:700;letter-spacing:1px;margin-bottom:8px}
.row{display:flex;justify-content:space-between;font-size:14px;padding:6px 0;border-top:1px solid #1f2328;font-variant-numeric:tabular-nums}
.row:first-of-type{border-top:0}.muted{color:#6b7178;font-size:13px}
details summary{color:#9aa0a6;font-size:12px;font-weight:700;letter-spacing:1px;list-style:none;cursor:pointer}
pre{white-space:pre-wrap;font-size:10.5px;color:#9aa0a6;margin:8px 0 0;max-height:260px;overflow:auto}
button{width:100%;margin-top:8px;padding:18px;font-size:18px;font-weight:800;border:0;border-radius:16px;background:#e5383b;color:#fff}
button:disabled{background:#3a3d42;color:#888}
</style></head><body>
<div class="top"><div id="badge" class="badge n">…</div><div id="tags"></div></div>
<div class="sym" id="sym">BTCUSDT</div><div class="price" id="price">—</div><div class="sub" id="sub"></div>
<div class="cards" id="cards"></div>
<div class="box" id="pos"></div>
<div class="box"><div class="h">СДЕЛКИ</div><div id="tr"></div></div>
<div class="box"><details><summary>ЖУРНАЛ ▾</summary><pre id="lg"></pre></details></div>
<button id="stop">Остановить бота</button>
<script>
const f=(v,d=2)=>v==null?'—':Number(v).toLocaleString('ru-RU',{minimumFractionDigits:d,maximumFractionDigits:d});
const col=v=>v==null?'cn':v<30?'cg':v>70?'cr':'cn';
const bg=v=>v==null?'#555':v<30?'#3ddc84':v>70?'#ff5c5c':'#9aa0a6';
async function load(){try{const d=await (await fetch('/api/status')).json();
let t,c;if(d.status=='stopped'){t='ОСТАНОВЛЕН';c='n'}else if(d.position&&d.signal=='SELL'){t='ПРОДАЁТ';c='r'}
else if(d.position){t='В РЫНКЕ';c='g'}else{t='В ОЖИДАНИИ';c='y'}
badge.textContent=t;badge.className='badge '+c;
tags.innerHTML=(d.dry_run?'<span class="tag">DRY RUN</span>':'')+(d.testnet?'<span class="tag">TESTNET</span>':'<span class="tag" style="color:#ff5c5c">LIVE</span>');
sym.textContent=d.symbol+' · '+d.interval;price.textContent=f(d.price);
const s=d.rsi[String(d.strategy_period)];
sub.innerHTML='RSI '+d.strategy_period+': <b class="'+col(s)+'">'+f(s,1)+'</b> · '+(d.updated?d.updated.slice(11):'—')+(d.error?' · <span class="cr">ошибка</span>':'');
cards.innerHTML=['6','12','24'].map(p=>{const v=d.rsi[p];return `<div class="card"><div class="l">RSI ${p}</div><div class="v ${col(v)}">${f(v,1)}</div><div class="bar"><i style="width:${v==null?0:v}%;background:${bg(v)}"></i><b style="left:30%"></b><b style="left:70%"></b></div></div>`}).join('');
pos.innerHTML=d.position?`<div class="h">ПОЗИЦИЯ</div><div class="row"><span>${f(d.position.qty,6)}</span><span>вход ${f(d.position.entry_price)}</span></div>`:'<div class="muted">Нет позиции</div>';
tr.innerHTML=d.trades.length?d.trades.map(x=>`<div class="row"><span class="${x.side=='BUY'?'cg':'cr'}">${x.side=='BUY'?'▲ покупка':'▼ продажа'}</span><span>${f(x.price)}</span><span class="muted">${x.time.slice(11,16)}</span></div>`).join(''):'<div class="muted">Пока нет</div>';
lg.textContent=d.logs.join('\\n');
if(d.status=='stopped'){stop.disabled=true;stop.textContent='Бот остановлен'}}
catch(e){badge.textContent='НЕТ СВЯЗИ';badge.className='badge n'}}
stop.onclick=async()=>{if(!confirm('Остановить бота?'))return;try{await fetch('/api/stop',{method:'POST'})}catch(e){}stop.disabled=true;stop.textContent='Бот остановлен';badge.textContent='ОСТАНОВЛЕН';badge.className='badge n'};
load();setInterval(load,5000);
</script></body></html>"""


def make_handler(trader, buffer, on_stop):
    class H(BaseHTTPRequestHandler):
        def _send(self, code, body, ctype="application/json; charset=utf-8"):
            data = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self._send(200, PAGE, "text/html; charset=utf-8")
            elif self.path.startswith("/api/status"):
                self._send(200, json.dumps(trader.status(buffer.lines), ensure_ascii=False))
            else:
                self._send(404, '{"error":"not found"}')

        def do_POST(self):
            if self.path.startswith("/api/stop"):
                self._send(200, '{"ok":true,"message":"stopping"}')
                trader.stop()
                if on_stop:
                    threading.Thread(target=on_stop, daemon=True).start()
            else:
                self._send(404, '{"error":"not found"}')

        def log_message(self, *a):
            pass

    return H


def start_dashboard(trader, buffer, port=8000, host="127.0.0.1", on_stop=None):
    server = ThreadingHTTPServer((host, port), make_handler(trader, buffer, on_stop))
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    logging.getLogger("rsi_bot").info("Dashboard: http://localhost:%d", server.server_address[1])
    return server
