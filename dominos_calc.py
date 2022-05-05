import json
import logging
import requests
import datetime
import time
import random
from common import ExpenseCalc, Sqlite3DBHelper, UserSession


class DominosUserSession(UserSession):
    def __init__(self, filename: str):
        super().__init__(filename)

    def set_cred(self, reply):
        for k,v in reply.json().get("credentials").items():
            self.creds[k.lower()] = v
        self.creds["userid"] = reply.json().get("userId")
        self.creds["authtoken"] = self.creds["accesskeyid"]

    def build_header(self):
        self.headers.clear()
        self.set_default_headers()
        if self.payload:
            self.headers["content-length"]= str(len(self.payload))
        if self.creds:
            self.headers.update(self.creds)

    def doauth(self) -> dict:        
        self.payload = {}
        self.build_header()
        reply = requests.post("https://api.dominos.co.in/loginhandler/anonymoususer", data=self.payload, headers=self.headers)   
        self.has_failed(reply)
        self.set_cred(reply)
        self.sess = requests.Session()
        while True:
            mob_num = input("Enter Mobile Number: ")
            ch = input("Continue Y/y or N/n ? ")
            if ch.lower() == 'y':
                break
        self.payload = f'{{"lastName":"","mobile":"{mob_num}","firstName":""}}'
        self.build_header()
        reply = self.sess.post("https://api.dominos.co.in/loginhandler/forgotpassword", data=self.payload, headers=self.headers)
        self.has_failed(reply)
        while True:
            otp = input("Enter OTP: ")
            ch = input("Continue Y/y or N/n ? ")
            if ch.lower() == 'y':
                break
        self.payload = f'{{"mobile": "{mob_num}","code": "{otp}","screenName": "Login Screen"}}'
        self.build_header()
        reply = self.sess.post("https://api.dominos.co.in/loginhandler/validatecode", data=self.payload, headers=self.headers)
        self.has_failed(reply)
        self.creds = {}
        self.payload = {}
        self.build_header()
        self.headers["userid"] = reply.json()["attributes"]["userId"]
        self.headers["authtoken"] = reply.json()["credentials"]["accessToken"]
        self.headers["isloggedin"] = "true"
        logging.info("login successful...")
        return self.headers
    
    def logout(self):
        reply = self.sess.post("https://api.dominos.co.in/loginhandler/anonymoususer", headers=self.headers)
        if reply.status_code != 200:
            logging.error("Logout unsuccessful...")
        else:
            logging.info("Logout successful...")


class DominosCalc(ExpenseCalc):
    def __init__(self):
        self.json_arr = []
        self.user_session = DominosUserSession("dominos_header")
        self.headers = self.user_session.doauth()
        self.url = "https://api.dominos.co.in/{}"
        self.total_orders = 0
        
        sql_stmt = (
            "CREATE TABLE IF NOT EXISTS "
            "dominos_expense(order_id TEXT UNIQUE, cost REAL, date TEXT, food_items TEXT)")
        self.db_setup(sql_stmt)
        
    def get_details(self) -> None:
        print("Parsing orders...")
        response = requests.get(url="https://api.dominos.co.in/order-service/ve1/orders?userid={}".format(self.headers["userid"]), headers=self.headers)
        if response.status_code != 200:
            raise Exception("Request failed, try later.")
        json_data = response.json()
        orders = json_data["orders"]
        self.parse_orders(orders)
        while "link" in json_data:
            response = requests.get(url=self.url.format(json_data["link"]["href"]), headers=self.headers)
            retry = 2
            while response.status_code != 200 and retry != 0:
                time.sleep(self.sleep_dur[random.randint(0,2)])
                response = requests.get(url=self.url.format(json_data["link"]["href"]), headers=self.headers)
                retry -= 1
            if response.status_code != 200:
                raise Exception("Unable to complete request.")
            json_data = response.json()
            orders = json_data["orders"]
            self.parse_orders(orders)
            time.sleep(self.sleep_dur[random.randint(0,2)])
        with open("dominos_data.json", "w") as f:
            json.dump(self.json_arr, f)
        self.user_session.logout()        

    def parse_orders(self, orders: list) -> None:
        db = Sqlite3DBHelper()
        cur = db.get_cursor()
        sql_stmt = ("INSERT OR IGNORE INTO "
        "dominos_expense(order_id, cost, date, food_items) VALUES (?, ?, ?, ?)")
        arr = [] 
        for order in orders:
            self.json_arr.append(order)
            if "success" not in order["orderState"].lower():
                order_id = order["orderId"]
                msg = f"Skipping entry for orderid: {order_id}"
                logging.info(msg)
                continue
            self.total_orders += 1
            order_id = order["orderId"]
            cost = float(order["netPrice"])
            date = datetime.datetime.strptime(order["store"]["orderDate"] + " " + order["store"]["orderTime"], "%Y-%m-%d %H:%M:%S" ).isoformat()
            food_items = []
            for item in order["items"]:
                food_items.append("{qty} x {name}".format(qty=item["quantity"], name=item["product"]["name"]))
            arr.append((order_id, cost, date, ", ".join(food_items)))
        cur.executemany(sql_stmt, arr)
        db.commit()
        db.close()

    def set_default_headers(self,headers):
        with open("headers_dominos", "r") as f:
            for  line in f:
                k, v = line.strip().split(": ")
                k, v = k.strip(), v.strip()
                headers[k] = v

    def set_cred(self, creds, reply):
        for k,v in reply.json().get("credentials").items():
            creds[k.lower()] = v
        creds["userid"] = reply.json().get("userId")
        creds["authtoken"] = creds["accesskeyid"]

    def build_header(self, headers, payload=None, creds=None):
        headers.clear()
        self.set_default_headers(headers)
        if payload:
            headers["content-length"]= str(len(payload))
        if creds:
            headers.update(creds)


def main() -> None:
    logging.basicConfig(level = logging.INFO)
    random.seed()
    logging.info("Starting...")
    DominosCalc().get_details()
    logging.info("Complete.")


if __name__ == '__main__':
    main()