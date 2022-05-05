import json
import logging
import requests
import datetime
import time
import random
from common import ExpenseCalc, Sqlite3DBHelper, UserSession


class SwiggyUserSession(UserSession):
    def __init__(self, filename: str):
        super().__init__(filename)
    
    def set_cred(self, reply):
        pass

    def build_header(self):
        self.headers.clear()
        self.set_default_headers()

    def doauth(self) -> dict:
        self.build_header()
        self.sess = requests.Session()
        reply = self.sess.get("https://www.swiggy.com/dapi/cart", headers=self.headers)
        if reply.status_code != 200:
            raise Exception(reply.text)
        self.csrf = reply.json().get('csrfToken')
        while True:
            mob_num = input("Enter Mobile Number: ")
            ch = input("Continue Y/y or N/n ? ")
            if ch.lower() == 'y':
                break
        payload = f'{{"mobile": "{mob_num}","_csrf":"{self.csrf}"}}'
        reply = self.sess.post("https://www.swiggy.com/dapi/auth/sms-otp", headers=self.headers, data=payload)
        self.has_failed(reply)
        while True:
            otp = input("Enter OTP: ")
            ch = input("Continue Y/y or N/n ? ")
            if ch.lower() == 'y':
                break
        payload = f'{{"otp":"{otp}","_csrf":"{self.csrf}"}}'
        reply = self.sess.post("https://www.swiggy.com/dapi/auth/otp-verify", headers=self.headers, data=payload)
        self.has_failed(reply)
        reply = self.sess.get("https://www.swiggy.com/dapi/order/all?order_id=", headers=self.headers)
        self.has_failed(reply)
        self.csrf = reply.json().get('csrfToken')
        return self.headers
    
    def has_failed(self, reply):
        if reply.status_code == 200 and reply.json().get("statusCode") != 0:
            raise Exception(reply.text) 

    def logout(self):
        payload = '{{"_csrf":"{}"}}'.format(self.csrf)
        reply = self.sess.post("https://www.swiggy.com/dapi/auth/logout", headers=self.headers, data=payload)
        if reply.status_code == 200 and reply.json().get("statusCode") != 0:
            logging.error("Logout unsuccessful...")
        else:
            logging.info("Logout successful...")


class SwiggyCalc(ExpenseCalc):
    def __init__(self):
        self.json_arr = []
        self.url = 'https://www.swiggy.com/dapi/order/all?order_id={}'
        self.user_session = SwiggyUserSession("swiggy_header")
        self.headers = self.user_session.doauth()
        sql_stmt = (
            "CREATE TABLE IF NOT EXISTS "
            "swiggy_expense(order_id TEXT UNIQUE, cost REAL, date TEXT, "
            "restaurant_name TEXT, food_items TEXT, post_status TEXT);"
        )
        self.db_setup(sql_stmt)

    def get_details(self) -> None:
        print("Parsing orders...")
        sess = self.user_session.get_session()
        response = sess.get(url=self.url.format(""), headers=self.headers)
        if response.status_code != 200:
            raise Exception("Request failed, try later.")
        json_data = response.json()
        self.total_orders = int(json_data["data"]["total_orders"])
        logging.info("Total Orders {}".format(self.total_orders))
        orders = json_data["data"]["orders"]
        self.parse_orders(orders)
        while True:
            if not orders:
                logging.info("Orders array empty.")
                break
            response = sess.get(url=self.url.format(orders[-1]["order_id"]), headers=self.headers)
            retry = 2
            while response.status_code != 200 and retry != 0:
                time.sleep(self.sleep_dur[random.randint(0,2)])
                response = sess.get(url=self.url.format(orders[-1]["order_id"]), headers=self.headers)
                retry -= 1
            if response.status_code != 200:
                raise Exception("Unable to complete request for page.")
            json_data = response.json()
            orders = json_data["data"]["orders"]
            self.parse_orders(orders)
            time.sleep(self.sleep_dur[random.randint(0,2)])
        with open("swiggy_data.json", "w") as f:
            json.dump(self.json_arr, f)
        self.user_session.logout()

    def parse_orders(self, orders: list) -> None:
        db = Sqlite3DBHelper()
        cur = db.get_cursor()
        sql_stmt = ("INSERT OR IGNORE "
        "INTO swiggy_expense(order_id, cost, date, restaurant_name, food_items, post_status) VALUES (?, ?, ?, ?, ?, ?)")
        arr = [] 
        for order in orders:
            self.json_arr.append(order)
            if "delivered" not in order["order_status"].lower():
                order_id = order["order_id"]
                order_status = order["order_status"]
                post_status = order["post_status"]
                msg = f"Skipping entry for orderid: {order_id}, order_status: {order_status}, post_status: {post_status}"
                logging.info(msg)
                continue
            order_id = order["order_id"]
            cost = float(order["order_total_with_tip"])
            date = datetime.datetime.strptime(order["order_time"], "%Y-%m-%d %H:%M:%S").isoformat()
            restaurant_name = order.get("restaurant_name", "NA")
            food_items = []
            for order_items in order["order_items"]:
                food_items.append("{qty} x {name}".format(qty=order_items["quantity"], name=order_items["name"]))
            arr.append((order_id, cost, date, restaurant_name, ", ".join(food_items), order["post_status"]))
        cur.executemany(sql_stmt, arr)
        db.commit()
        db.close()


def main() -> None:
    logging.basicConfig(level = logging.INFO)
    random.seed()
    logging.info("Starting...")
    SwiggyCalc().get_details()
    logging.info("Complete.")

if __name__ == '__main__':
    main()