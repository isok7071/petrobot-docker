from calendar import month
import datetime
import pytz
import os
from re import sub
from time import time
import psycopg2
import psycopg2.extras
import telebot
import logging
logging.basicConfig(level=logging.INFO, filename="log.log")
import os
from dotenv import dotenv_values

config_values = {}

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    config_values = dotenv_values(".env")
else:
    logging.critical("No dotenv found")

logging.info(f'\n---------------------\nЗапустился в {datetime.datetime.now(pytz.timezone("Europe/Moscow"))}\n---------------------\n',)

username = config_values['PORTAL_USERNAME']
password = config_values['PORTAL_PASSWORD']

bot = telebot.TeleBot(
    config_values['BOT_TOKEN'], parse_mode=None)
replacements_url = config_values['PORTAL_REPLACEMENTS_URL']

class db:
    def __init__(self):
        try:
            self.conn = psycopg2.connect(user=config_values['DB_USER'],password=config_values['DB_PASSWORD'], host=config_values['DB_HOST'], port='5432')
            self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        except:
            logging.critical("\n\nОшибка с подключением к базе данных\n\n")

    def close_db(self):
        self.conn.close()

class Subscribe(db):
    def create(self, user_id, file, query_column):
        try:
            self.cursor.execute('INSERT INTO subscribe (user_id, schedule_type, query_column) VALUES (%s, %s, %s)', (user_id, file, query_column))
            self.conn.commit()
            self.close_db()
        except:
            self.close_db()
    
    def delete_by_user_id(self, user_id):
        try:
            self.cursor.execute('DELETE FROM subscribe WHERE user_id = %s', (user_id, ))
            self.conn.commit()
            self.close_db()
        except:
            self.close_db()


    def get_one_user_by_id(self, user_id):
        try:
            self.cursor.execute('SELECT * FROM subscribe WHERE user_id = %s', (user_id, ))
            result =  self.cursor.fetchone()
            self.close_db()
            return result
        except:
            self.close_db()
      
    def read(self):
            self.cursor.execute('SELECT subscribe.user_id, subscribe.schedule_type, subscribe.query_column FROM subscribe JOIN bot_subscribtion ON subscribe.user_id = bot_subscribtion.user_id WHERE bot_subscribtion.expire_date > CURRENT_TIMESTAMP')
            result =  self.cursor.fetchall()
            self.close_db()
            return result
    
    def count(self):
        try:
            self.cursor.execute('SELECT COUNT(id) FROM subscribe')
            result =  self.cursor.fetchall()
            self.close_db()
            return result
        except:
            self.close_db()


class Stats(db):
    def read(self):
        try:
            self.cursor.execute('SELECT * FROM stats')
            result =  self.cursor.fetchall()
            self.close_db()
            return result
            #return [1459498902, 1459498902, 1459498902, 971622425, 1459498902, 1459498902 , 1459498902, 1459498902, 1459498902, 1459498902]
        except:
            self.close_db()

    def create(self, user_id, date):
        try:
            self.cursor.execute('INSERT INTO stats (user_id, date) VALUES (%s, %s)', (user_id, date))
            self.conn.commit()
            self.close_db()
        except:
            self.close_db()

    def get_one_user_by_id(self, user_id):
        try:
            self.cursor.execute('SELECT user_id FROM stats WHERE user_id = %s', (user_id, ))
            result =  self.cursor.fetchone()
            self.close_db()
            return result
        except:
            self.close_db()
    
    def deleteByUserId(self, user_id):
        try:
            self.cursor.execute('DELETE FROM stats WHERE user_id = %s', (user_id, ) )
            self.conn.commit()
            self.close_db()
            logging.error(f'Удалил из рассылки{user_id}')
        except:
            self.close_db()
      
    def count(self):
        try:
            self.cursor.execute('SELECT COUNT(id) FROM stats')
            result =  self.cursor.fetchall()
            self.close_db()
            return result
        except:
            self.close_db()


"""
нет подписки - первый раз подписка - create
кончилась подписка - обновить
"""

class BotSubscribtion(db):
    def read(self):
        try:
            self.cursor.execute('SELECT * FROM bot_subscribtion')
            result =  self.cursor.fetchall()
            self.close_db()
            return result
        except:
            self.close_db()

    def getActiveUsers(self):
        try:
            nowDateTime = datetime.datetime.now()
            self.cursor.execute('SELECT user_id FROM bot_subscribtion where expire_date > %s LEFT JOIN subscribe ON user_id = user_id', (nowDateTime,))
            result =  self.cursor.fetchall()
            logging.info(result)
            self.close_db()
            return result
        except:
            self.close_db()

    def create(self, userId):
        try:
            subscribtionExpireDate = datetime.datetime.now() + datetime.timedelta(days=30)
            self.cursor.execute('INSERT INTO bot_subscribtion (user_id, expire_date, payment_times) VALUES (%s, %s, %s)', (userId, subscribtionExpireDate, 1))
            self.conn.commit()
            self.close_db()
        except:
            logging.critical(f'\n\nНе получилось создать подписку у пользователя {userId}, из-за системной ошибки')
            self.close_db()

    def getOneUserById(self, userId):
        try:
            print(self.cursor)
            self.cursor.execute('SELECT user_id, expire_date FROM bot_subscribtion WHERE user_id = %s', (userId, ))
            result =  self.cursor.fetchone()
            self.close_db()
            return result
        except:
            self.close_db()
    
    def update(self, userId, expireDate):
        try:
            subscribtionExpireDate = expireDate + datetime.timedelta(days=30)
            self.cursor.execute('UPDATE bot_subscribtion SET expire_date = %s, payment_times = payment_times + 1  WHERE user_id = %s', (subscribtionExpireDate, userId, ))
            self.conn.commit()
            self.close_db()
        except:
            logging.critical(f'\n\nНе получилось обновить подписку у пользователя {userId}, из-за системной ошибки')
            self.close_db()
    
    def deleteByUserId(self, user_id):
        try:
            self.cursor.execute('DELETE FROM bot_subscribtion WHERE user_id = %s', (user_id, ) )
            self.conn.commit()
            self.close_db()
        except:
            self.close_db()




"""

class User_commands(db):
    def create(self, user_id, file, query_column):
        try:
            self.cursor.execute('INSERT INTO user_commands (user_id, query_column, schedule_type) VALUES (%s, %s, %s)', (user_id, query_column, file))
            self.conn.commit()
            self.close_db()
        except:
            self.close_db()
    
    def delete_by_user_id(self, user_id):
        try:
            self.cursor.execute('DELETE FROM user_commands WHERE user_id = %s', (user_id, ) )
            self.conn.commit()
            self.close_db()
        except:
            self.close_db()

    def get_one_user_by_id(self, user_id):
        try:
            self.cursor.execute('SELECT * FROM user_commands WHERE user_id = %s', (user_id, ))
            result =  self.cursor.fetchone()
            self.close_db()
            return result
        except:
            self.close_db()
      
    def read(self):
        try:
            self.cursor.execute('SELECT * FROM user_commands')
            result =  self.cursor.fetchall()
            self.close_db()
            return result
        except:
            self.close_db()
"""