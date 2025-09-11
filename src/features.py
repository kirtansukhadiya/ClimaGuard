import pandas as pd
import sqlalchemy as sa
from sqlalchemy import create_engine, URL
from dotenv import dotenv_values

env = dotenv_values(".env")
db_user =env.get("DB_USER"),
db_password =env.get("DB_PASSWORD"),
db_host =env.get("DB_HOST"),
db_name =env.get("DB_NAME")

engine = create_engine(f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}")

df = pd.read_sql_table('weather_row', con=engine)
#df = pd.read_sql_query('SELECT * FROM your_table_name WHERE column = "value"', con=engine)