from common import Sqlite3DBHelper
from datetime import date, timedelta, datetime


def do_calc():
    db = Sqlite3DBHelper()
    cur = db.get_cursor()
    tables = {"Zomato": "zomato_expense", "Swiggy": "swiggy_expense", "Dominos": "dominos_expense"}
    for label, table_name in tables.items():
        cur.execute("select name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if cur.fetchone():
            print(f"{label} expenses")
            print("-"*20)
            cur.execute(f"select sum(cost) total_cost from {table_name}")
            r = cur.fetchone()
            total_cost = round(r["total_cost"], 2)
            cur.execute(f"select count(*) total_orders from {table_name}")
            r = cur.fetchone()
            total_orders = r["total_orders"]
            cur.execute(f"select min(date) start_date, max(date) end_date from {table_name}")
            r = cur.fetchone()
            start_date = datetime.fromisoformat(r['start_date']).strftime("%d/%b/%Y")
            end_date = datetime.fromisoformat(r['end_date']).strftime("%d/%b/%Y")
            print(f"Total orders placed from {start_date} to {end_date}: {total_orders}\n")
            print(f"Total Expenses from {start_date} to {end_date}: Rs. {total_cost}\n")
            cur.execute(f"select sum(cost) cost from {table_name} where date >=  '2020-03-25T00:00:00' and date <= '2021-10-01T00:00:00'")
            r = cur.fetchone()
            print("Expenses from lockdown(25/Mar/2020) to 01/Oct/2021: Rs. %s\n" % round(r["cost"], 2))
            param = datetime.now() - timedelta(days=30)
            cur.execute(f"select sum(cost) cost from {table_name} where date>= ?", (param.isoformat(),))
            r = cur.fetchone()
            print("Expense for the last 30 days: Rs. %s\n" % round(r["cost"], 2))
            param = datetime.now() - timedelta(days=365)
            cur.execute(f"select sum(cost) cost from {table_name} where date >= ?", (param.isoformat(),))
            r = cur.fetchone()
            print("Expense for the last 365 days: Rs. %s\n" % round(r["cost"], 2))
            print("\n\n", end="")
        else:
            print(f"No data for {label}")

if __name__ == "__main__":
    print("\n")
    do_calc()