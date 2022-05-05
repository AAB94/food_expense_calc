import sqlite3
from abc import ABC, abstractmethod
from requests import Response

class Sqlite3DBHelper():
    def __init__(self):
        self.dbfile = "food_expenses.db"
        self.con = None
        self.cur = None
    
    def connect(self) -> None:
        self.con = sqlite3.connect(self.dbfile)
        self.con.row_factory = sqlite3.Row

    def get_cursor(self) -> None:
        if not self.con:
            self.connect()
        if not self.cur:
            self.cur = self.con.cursor()
        return self.cur
        
    def commit(self) -> None:
        self.con.commit()
    
    def close(self) -> None:
        self.con.close()


class ExpenseCalc(ABC):
    sleep_dur = [3, 4, 5]

    @abstractmethod
    def get_details(self) -> None:
        pass

    @abstractmethod
    def parse_orders(self, orders: object) -> None:
        pass

    def db_setup(self, sql_stmt) -> None:
        db = Sqlite3DBHelper()
        cur = db.get_cursor()
        cur.execute(sql_stmt)
        db.commit()
        db.close()


class UserSession():

    def __init__(self, filename: str):
        self.headers = {}
        self.creds = {}
        self.filename = filename

    def set_default_headers(self):
        with open(self.filename, "r") as f:
            for  line in f:
                k, v = line.strip().split(": ")
                k, v = k.strip(), v.strip()
                self.headers[k] = v

    @abstractmethod
    def set_cred(self, reply: Response):
        pass

    @abstractmethod
    def build_header(self):
        pass

    @abstractmethod
    def doauth(self):
        pass

    @abstractmethod
    def logout(self):
        pass

    def has_failed(self, reply):
        if reply.status_code != 200:
            print(reply.text)

    def get_session(self):
        return self.sess