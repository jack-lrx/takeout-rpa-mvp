from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/playwright-demo", tags=["playwright-demo"])


@router.get("", response_class=HTMLResponse)
async def playwright_demo_page() -> HTMLResponse:
    return HTMLResponse(
        """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Playwright 本地验证页</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f4efe6;
      --panel: #fffaf2;
      --ink: #1f2937;
      --accent: #b45309;
      --accent-soft: #fde6bf;
      --border: #e5d2b1;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
      background:
        radial-gradient(circle at top left, #ffe8b8 0, transparent 30%),
        linear-gradient(135deg, #f7f1e8, #efe4d1);
      color: var(--ink);
      min-height: 100vh;
    }
    main {
      max-width: 860px;
      margin: 0 auto;
      padding: 48px 20px 64px;
    }
    .card {
      background: rgba(255, 250, 242, 0.92);
      border: 1px solid var(--border);
      border-radius: 24px;
      padding: 28px;
      box-shadow: 0 16px 40px rgba(120, 53, 15, 0.12);
      backdrop-filter: blur(6px);
    }
    h1 {
      margin: 0 0 12px;
      font-size: clamp(28px, 5vw, 46px);
    }
    p {
      line-height: 1.7;
      margin: 0 0 16px;
    }
    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin: 24px 0;
    }
    button {
      border: 0;
      border-radius: 999px;
      padding: 12px 18px;
      background: var(--accent);
      color: white;
      cursor: pointer;
      font-size: 15px;
    }
    button.secondary {
      background: var(--accent-soft);
      color: var(--accent);
    }
    pre {
      margin: 0;
      background: #24180d;
      color: #f9f1e6;
      border-radius: 18px;
      padding: 18px;
      min-height: 260px;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 13px;
      line-height: 1.6;
    }
    .hint {
      margin-top: 18px;
      color: #7c5a2c;
      font-size: 14px;
    }
  </style>
</head>
<body>
  <main>
    <section class="card">
      <h1>Playwright 本地验证页</h1>
      <p>这个页面会主动发起一个订单查询请求、一个配送状态请求，再建立一个带有 delivery 关键字的 WebSocket 连接。</p>
      <p>只要你的 RPA 指向这个页面，当前项目就能在没有真实外卖后台的情况下验证 Playwright 的浏览器监听能力。</p>
      <div class="actions">
        <button id="run-sequence">触发完整链路</button>
        <button id="run-fetch" class="secondary">只发 HTTP 请求</button>
        <button id="run-ws" class="secondary">只发 WebSocket</button>
      </div>
      <pre id="log">等待触发…</pre>
      <p class="hint">建议先启动 API，再让 Playwright 打开这个页面：<code>http://127.0.0.1:8000/playwright-demo</code></p>
    </section>
  </main>
  <script>
    const log = document.getElementById("log");

    function append(message, payload) {
      const line = `[${new Date().toLocaleTimeString()}] ${message}`;
      const body = payload ? `\\n${JSON.stringify(payload, null, 2)}` : "";
      log.textContent = `${line}${body}\\n\\n${log.textContent}`.trim();
    }

    async function triggerFetches() {
      const orderRes = await fetch("/playwright-demo/api/order/query");
      append("order query finished", await orderRes.json());

      const statusRes = await fetch("/playwright-demo/api/delivery/status");
      append("delivery status finished", await statusRes.json());
    }

    async function triggerWebSocket() {
      return new Promise((resolve, reject) => {
        const protocol = window.location.protocol === "https:" ? "wss" : "ws";
        const socket = new WebSocket(`${protocol}://${window.location.host}/playwright-demo/ws/delivery/status`);
        socket.addEventListener("open", () => {
          append("websocket opened");
        });
        socket.addEventListener("message", (event) => {
          append("websocket message received", JSON.parse(event.data));
          socket.close();
          resolve();
        });
        socket.addEventListener("error", () => reject(new Error("websocket failed")));
      });
    }

    async function runSequence() {
      append("start full demo");
      await triggerFetches();
      await triggerWebSocket();
      append("full demo done");
    }

    document.getElementById("run-sequence").addEventListener("click", () => void runSequence());
    document.getElementById("run-fetch").addEventListener("click", () => void triggerFetches());
    document.getElementById("run-ws").addEventListener("click", () => void triggerWebSocket());

    window.addEventListener("load", () => {
      void runSequence();
    });
  </script>
</body>
</html>
        """
    )


@router.get("/api/order/query")
async def demo_order_query() -> dict:
    return {
        "data": {
            "orders": [
                {
                    "bizOrderId": "LOCAL-ORDER-1001",
                    "productList": [
                        {"skuName": "黄焖鸡米饭", "quantity": 1, "price": 26},
                        {"skuName": "可乐", "quantity": 1, "price": 5},
                    ],
                    "payAmount": 31,
                    "merchantIncome": 27,
                }
            ]
        }
    }


@router.get("/api/delivery/status")
async def demo_delivery_status() -> dict:
    return {
        "delivery": {
            "orderId": "LOCAL-ORDER-1001",
            "deliveryStatus": "delivering",
            "riderStatusText": "骑手已到达商圈，正在接近用户",
            "updateTime": datetime.now(timezone.utc).isoformat(),
        }
    }


@router.websocket("/ws/delivery/status")
async def demo_delivery_status_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.send_json(
        {
            "delivery": {
                "orderId": "LOCAL-ORDER-1001",
                "deliveryStatus": "arrived",
                "riderStatusText": "骑手已到达用户门口",
                "updateTime": datetime.now(timezone.utc).isoformat(),
            }
        }
    )
    await websocket.close()
