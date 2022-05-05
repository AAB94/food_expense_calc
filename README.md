# food_expense_calc
calculate total cost for orders placed via swiggy, zomato, dominos

#### Login method
Currently only mobile based OTP method is supported.

#### Installation 
1. Please follow the instruction [here](https://docs.python.org/3/library/venv.html) to create a python3 virtual environment.

2. After activating environment run pip install -r requirements.txt

#### Usage
* Please run the `*_calc.py` scripts first. The scripts can't be run parallely as they all use the same sqlite3 DB
* Each script writes data to a table in sqlite3DB, and post completion will create a json file.
* The summary.py script will do the following :
    *  Calculate cost for orders from oldest date to present.
    *  Calculate cost for orders placed since first Covid lockdown(India) till  October, 1st 2021.
    *  Calculate cost for orders placed in last 30 days and 365 days.
* The food_expenses.db created can be opened in DB browser for SQlite or Dbeaver or any others, feel free to have a look at the addtional fields (not all present per order) and run queries
* The JSON files contain all information present per order and can be used for further analysis



