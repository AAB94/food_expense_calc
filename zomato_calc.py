import json
import logging
import requests
import datetime
import locale
import time
import random
from common import ExpenseCalc, Sqlite3DBHelper, UserSession


class ZomatoUserSession(UserSession):
    def __init__(self, filename: str):
        super().__init__(filename)
    
    def set_cred(self, reply):
        self.headers["x-zomato-csrft"] = reply.json()["csrf"]

    def build_header(self):
        self.headers.clear()
        self.set_default_headers()

    def doauth(self) -> dict:
        self.build_header()
        self.sess = requests.Session()
        reply = self.sess.get("https://www.zomato.com/webroutes/auth/init", headers=self.headers)
        self.has_failed(reply)
        country_id = reply.json()["selected_country_code"]["countryId"]
        reply = self.sess.get("https://www.zomato.com/webroutes/auth/csrf", headers=self.headers)
        self.has_failed(reply)
        self.set_cred(reply)
        while True:
            mob_num = input("Enter Mobile Number: ")
            ch = input("Continue Y/y or N/n ? ")
            if ch.lower() == 'y':
                break
        payload = f'{{"country_id":{country_id},"phone":"{mob_num}","verification_type":"sms","method":"phone"}}'
        reply = self.sess.post("https://www.zomato.com/webroutes/auth/login", data=payload, headers=self.headers)
        self.has_failed(reply)
        while True:
            otp = input("Enter OTP: ")
            ch = input("Continue Y/y or N/n ? ")
            if ch.lower() == 'y':
                break
        payload = f'{{"phone":"{mob_num}","code":"{otp}","country_id":{country_id}}}'
        reply = self.sess.post("https://www.zomato.com/webroutes/auth/mobile_login/verify", data=payload, headers=self.headers)
        self.has_failed(reply)
        self.username = reply.json().get("username")
        return self.headers
    
    def get_username(self):
        return self.username
    
    def logout(self):
        reply = self.sess.get("https://www.zomato.com/webroutes/auth/logout", headers=self.headers)
        if reply.status_code != 200:
            logging.error("Logout unsuccessful...")
        else:
            logging.info("Logout successful...")


class ZomatoCalc(ExpenseCalc): 
    def __init__(self):
        self.url = 'https://www.zomato.com/webroutes/user/orders?page={}'
        self.failed_pages = []
        self.json_arr = []
        self.user_session = ZomatoUserSession("zomato_header")
        self.headers = self.user_session.doauth()
        self.headers['referer'] = 'https://www.zomato.com/{}/ordering'.format(self.user_session.get_username())
        sql_stmt = (
            "CREATE TABLE IF NOT EXISTS zomato_expense"
            "(order_id TEXT UNIQUE, cost REAL, date TEXT, restaurant_name TEXT, food_items TEXT);"
        )
        self.db_setup(sql_stmt)

    def get_details(self) -> None:
        cur_page = 1
        sess = self.user_session.get_session()
        print("Parsing orders...")
        response = sess.get(url=self.url.format(cur_page), headers=self.headers)
        if response.status_code != 200:
            raise Exception("Request failed, please try later.")
        json_data = response.json()
        max_page_no = int(json_data["sections"]["SECTION_USER_ORDER_HISTORY"]["totalPages"])
        logging.info("Total pages to parse {}".format(max_page_no))
        orders = json_data["entities"]["ORDER"]
        self.parse_orders(orders)
        cur_page += 1
        while cur_page <= max_page_no:
            response = sess.get(url=self.url.format(cur_page), headers=self.headers)
            if response.status_code == 200:
                json_data = response.json()
                orders = json_data["entities"]["ORDER"]
                self.parse_orders(orders)
            else:
                logging.warn("Unable to complete request for page {}".format(cur_page))
                self.failed_pages.append(cur_page)
            cur_page += 1
            time.sleep(self.sleep_dur[random.randint(0,2)])
        if self.failed_pages:
            self.retry_pages()
        with open("zomato_data.json", "w") as f:
            json.dump(self.json_arr, f)
        self.user_session.logout()
    
    def parse_orders(self, orders: dict) -> None:
        db = Sqlite3DBHelper()
        cur = db.get_cursor()
        sql_stmt = ("INSERT OR IGNORE INTO "
            "zomato_expense(order_id, cost, date, restaurant_name, food_items) VALUES (?, ?, ?, ?, ?)")
        arr = [] 
        for value in orders.values():
            self.json_arr.append(value)
            if "delivered" not in value["deliveryDetails"]["deliveryLabel"].lower():
                msg = "Skipping entry for orderid: {} with status: {} ".format(value["orderId"], value["deliveryDetails"]["deliveryLabel"])
                logging.info(msg)
                continue
            order_id = value["orderId"]
            cost = float(value["totalCost"].replace('₹','').replace(',',''))
            date = datetime.datetime.strptime(value["orderDate"], "%B %d, %Y at %I:%M %p").isoformat()
            food_items = value["dishString"]
            restaurant_name = value["resInfo"]["name"]
            arr.append((order_id, cost, date, restaurant_name, food_items))
        cur.executemany(sql_stmt, arr)
        db.commit()
        db.close()
        
    def retry_pages(self) -> None:
        logging.info("Retrying failed pages...")
        sess = self.user_session.get_session()
        for page_no in self.failed_pages:
            response = sess.get(url=self.url.format(page_no), headers=self.headers)
            if response.status_code == 200:
                json_data = response.json()
                orders = json_data["entities"]["ORDER"]
                self.parse_orders(orders)
            else:
                logging.warn("Unable to complete request for page {}".format(page_no))
            time.sleep(self.sleep_dur[random.randint(0,2)])


def main() -> None:
    logging.basicConfig(level = logging.INFO)
    locale.setlocale(locale.LC_TIME, "en_US")
    random.seed()
    logging.info("Starting...")
    ZomatoCalc().get_details()
    logging.info("Complete.")


if __name__ == '__main__':
    main()
