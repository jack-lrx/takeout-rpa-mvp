# Takeout RPA MVP

一个完整可运行的 Python MVP，用于实现：

外卖平台订单监听 -> 数据解析 -> 本地存储 -> 推送 ERP Mock -> 失败重试

当前仓库已经完成阶段 1 到阶段 7 的全部要求。

## 技术栈

- Python 3.11+
- FastAPI
- SQLite
- Playwright
- httpx
- pydantic
- logging

## 目录结构

```text
takeout-rpa-mvp/
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── erp_mock.py
│   │   └── health.py
│   ├── models/
│   │   ├── order.py
│   │   └── status.py
│   ├── services/
│   │   ├── parser.py
│   │   ├── dedup.py
│   │   ├── erp_client.py
│   │   └── store.py
│   ├── db/
│   │   └── schema.sql
│   └── core/
│       ├── config.py
│       └── logging.py
├── rpa/
│   ├── login_and_listen.py
│   ├── listeners.py
│   ├── extractors.py
│   └── session.py
├── scripts/
│   ├── init_db.py
│   └── retry_failed_push.py
├── data/
│   └── app.db
├── tests/
│   └── test_smoke.py
├── requirements.txt
├── README.md
└── .env.example
```

## 快速开始

### 1. 创建虚拟环境

```bash
cd /Users/gavin/codeProject/python/takeout-rpa-mvp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### 2. 初始化环境变量

```bash
cp .env.example .env
```

### 3. 初始化数据库

```bash
PYTHONPATH=. python scripts/init_db.py
```

成功后会创建：

- `data/app.db`

### 4. 启动 API

```bash
PYTHONPATH=. uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## 已实现接口

### 健康检查

```http
GET /health
```

返回示例：

```json
{
  "status": "ok",
  "app": "Takeout RPA MVP",
  "environment": "development",
  "time": "2026-04-06T10:00:00.000000+00:00"
}
```

### ERP Mock

```http
POST /mock/orders
POST /mock/order-status
GET /mock/orders
GET /mock/order-status
```

## RPA 运行

### Demo 模式

无需真实外卖后台，直接模拟订单与状态链路：

```bash
PYTHONPATH=. python rpa/login_and_listen.py --demo
```

### 本地 Playwright 验证页

如果你暂时没有真实外卖平台后台，可以用仓库内置的本地验证页来测试 Playwright 浏览器监听能力。

1. 启动 API：

```bash
PYTHONPATH=. uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

2. 启动 RPA，并把商家后台地址指向本地验证页：

```bash
PYTHONPATH=. python rpa/login_and_listen.py \
  --platform meituan \
  --merchant-url "http://127.0.0.1:8000/playwright-demo"
```

本地验证页会在浏览器加载后自动发起：

- 一个带 `order` 关键字的 HTTP 请求
- 一个带 `delivery/status` 关键字的 HTTP 请求
- 一个带 `delivery/status` 关键字的 WebSocket 消息

这样可以验证：

- Playwright 是否成功打开浏览器页面
- `page.on("response")` 是否成功监听接口响应
- `page.on("websocket")` 是否成功监听 WebSocket 消息
- 监听结果是否进入解析、SQLite 入库和 ERP Mock 推送链路

你也可以直接在浏览器打开：

```text
http://127.0.0.1:8000/playwright-demo
```

然后查看：

- `GET /mock/orders`
- `GET /mock/order-status`

确认本地演示数据是否已经被接收。

### 真实监听模式

```bash
PYTHONPATH=. python rpa/login_and_listen.py \
  --platform meituan \
  --merchant-url "https://你的商家后台地址"
```

说明：

- 启动持久化浏览器
- 支持人工扫码登录
- 自动监听 `page.on("response")`
- 自动监听 WebSocket frame
- 自动过滤 `order / status / delivery / dispatch`
- 自动打印 URL、状态码、响应体截断内容
- 自动解析、入库、推送 ERP

## 失败重试

```bash
PYTHONPATH=. python scripts/retry_failed_push.py
```

## 数据流说明

1. RPA 监听到订单或配送状态网络事件
2. `parser.py` 解析并标准化订单与状态
3. `store.py` 写入 SQLite，并借助唯一索引做幂等
4. `erp_client.py` 推送到 ERP Mock
5. 推送结果写入 `push_logs`
6. 失败记录可通过 `retry_failed_push.py` 重试

## 数据库说明

当前初始化了 3 张核心表：

- `orders`
- `status`
- `push_logs`

唯一索引：

- `UNIQUE(platform, order_id)`
- `UNIQUE(platform, order_id, status, event_time)`

## 端到端验证

### 验证数据库初始化

```bash
PYTHONPATH=. python scripts/init_db.py
```

预期输出：

```text
SQLite database initialized: /Users/gavin/codeProject/python/takeout-rpa-mvp/data/app.db
```

### 验证 API

```bash
curl http://127.0.0.1:8000/health
```

预期输出：

```json
{
  "status": "ok",
  "app": "Takeout RPA MVP",
  "environment": "development",
  "time": "..."
}
```

### 验证 Mock API

```bash
curl -X POST http://127.0.0.1:8000/mock/orders \
  -H "Content-Type: application/json" \
  -d '{
    "platform":"meituan",
    "order_id":"TEST1001",
    "items":[{"name":"红烧肉饭","quantity":1,"unit_price":25}],
    "amount":25,
    "expected_income":22,
    "raw_payload":{"id":"TEST1001"}
  }'
```

### 验证 Demo 链路

```bash
PYTHONPATH=. python rpa/login_and_listen.py --demo
```

预期结果：

- 控制台打印监听日志
- `orders` 表新增订单
- `status` 表新增配送状态
- `/mock/orders` 与 `/mock/order-status` 可查询已接收数据
- `push_logs` 记录推送日志

# takeout-rpa-mvp
