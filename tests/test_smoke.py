import unittest

from fastapi.testclient import TestClient

from app.main import app


class SmokeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_health(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_mock_order_routes(self) -> None:
        order_payload = {
            "platform": "meituan",
            "order_id": "T1001",
            "items": [{"name": "套餐A", "quantity": 1, "unit_price": 20}],
            "amount": 20,
            "expected_income": 18,
            "raw_payload": {"id": "T1001"},
        }
        status_payload = {
            "platform": "meituan",
            "order_id": "T1001",
            "status": "delivering",
            "rider_status_text": "骑手配送中",
            "event_time": "2026-04-07T00:00:00+08:00",
            "raw_payload": {"id": "T1001"},
        }
        self.assertEqual(self.client.post("/mock/orders", json=order_payload).status_code, 200)
        self.assertEqual(self.client.post("/mock/order-status", json=status_payload).status_code, 200)
        self.assertEqual(self.client.get("/mock/orders").status_code, 200)
        self.assertEqual(self.client.get("/mock/order-status").status_code, 200)

    def test_playwright_demo_routes(self) -> None:
        page_response = self.client.get("/playwright-demo")
        self.assertEqual(page_response.status_code, 200)
        self.assertIn("Playwright 本地验证页", page_response.text)

        order_response = self.client.get("/playwright-demo/api/order/query")
        self.assertEqual(order_response.status_code, 200)
        self.assertEqual(order_response.json()["data"]["orders"][0]["bizOrderId"], "LOCAL-ORDER-1001")

        status_response = self.client.get("/playwright-demo/api/delivery/status")
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.json()["delivery"]["orderId"], "LOCAL-ORDER-1001")


if __name__ == "__main__":
    unittest.main()
