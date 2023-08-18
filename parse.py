#Для многопоточности(чтобы обновлять расписание)
import re
from sys import excepthook
import schedule
import threading
from time import sleep
from requests_ntlm import HttpNtlmAuth
import requests
from config import *
import pandas as pd
from pandas import json_normalize
import datetime
import pytz
from bs4 import BeautifulSoup

#Дата с действия расписания
dateRasp = ""

#Класс реализующий обновление расписания
class PetroSchedule:
    def __init__(self, username, password):
        #Аутентификация на портале
        self.headers = {'Accept': 'application/json;odata=verbose'}
        self.auth = HttpNtlmAuth(username, password)

    def internship(self):
        """Функция возвращающая список групп на практике
        с датами практики

        Returns:
            string: Строка с группами на практике
        """
        try:
            groups = {}
            link = r"https://portal.petrocollege.ru/_api/Web/Lists(guid'56ecc37a-ca5b-49a0-ae72-41f386e3abef')/Items?$top=10&$orderby=Id desc"
            responce = requests.get(link,
                            verify=False, auth=self.auth, headers=self.headers)
            response_json = responce.json()
        except:
            logging.error("Не получилось выполнить функцию группп на практике")
            return "Не удалось получить информацию"
        #Получаем результаты запроса на портал, смраницу с группами на практике
        for item in response_json["d"]["results"]:
            groups[item["Id"]] = {"Title": item["Title"], "html": item["Body"]}
            soup = BeautifulSoup(groups[item["Id"]]['html'], 'lxml')
            #Форматирование сообщения
            text = soup.find_all(text=re.compile('группы на практике:|1|2|3|4|5|6|7|8|9|0'))
            message = ""
            #Форматирование
            for item in text:
                groupsString = str(re.findall(r'\d\d[.]\d\d,', item)).replace("[" ,"").replace("'" ,"").replace("]" ,"").replace(",",';').strip()+"\n\n"
                message += re.sub(r'\d\d[.]\d\d,', groupsString, item)
            return message.split('группы на практике:')[1:]
        
    #Сохранение актуального расписания по группе
    def saveByGroup(self):
        """Сохранения расписания по группе с портала
        """
        try:   
            try:
                #Авторизация на портале
                responce = requests.get(r"https://portal.petrocollege.ru/_api/Web/Lists(guid'9c095153-274d-4c73-9b8b-4e3dd6af89e5')/Items(10)/AttachmentFiles",
                                    verify=False, auth=self.auth, headers=self.headers)

                #Получаем название файла прикрепленного и переводим название в строку 
                response_json = responce.json()
            except:
                logging.error("\n\nРасписание по группе НЕ УДАЛОСЬ ОБНОВИТЬ В "+ str(datetime.datetime.now(pytz.timezone("Europe/Moscow")))+"\n\n")
                return "Портал недоступен"
            response_json_norm = json_normalize(response_json['d']['results'])
            df = pd.DataFrame.from_dict(response_json_norm["FileName"]).tail(1)
            df_filename = df.FileName.to_string(index=False)
            #Ссылка на актуальное расписание
            link = f"https://portal.petrocollege.ru/Lists/2014/Attachments/10/{df_filename}"
            filename = "raspisaniye.xlsx"
            r = requests.get(link, verify=False, auth=self.auth,
                                headers=self.headers, allow_redirects=True)
            open(filename, "wb").write(r.content)
            global dateRasp
            try:
                dateRasp = df_filename
                dateRasp = re.findall(r"[0-9][0-9]", dateRasp)
                dateRasp = "<strong>Внимание! Текущее расписание (числитель и знаменатель) в боте с " + dateRasp[0]+"." + dateRasp[1] + " по "+ dateRasp[2] + "." + dateRasp[3] + " </strong>\nПожалуйста, сверьтесь с текущей датой."
            except:
                dateRasp = df_filename
                dateRasp = re.split(r"_|xlsx",dateRasp)
                dateRasp = "<strong>Внимание! Текущее расписание (числитель и знаменатель) в боте с " + dateRasp[1].replace("-"," по ").rstrip(".")+"</strong>\nПожалуйста, сверьтесь с текущей датой."
            logging.info("\n\nРасписание по группе обновлено в "+ str(datetime.datetime.now(pytz.timezone("Europe/Moscow")))+"\n\n")
        except:
            logging.error("\n\nРасписание по группе НЕ УДАЛОСЬ ОБНОВИТЬ В "+ str(datetime.datetime.now(pytz.timezone("Europe/Moscow")))+"\n\n")

    def saveByPrepod(self):
        """Сохранения расписания по преподавателю с портала
        """
        try:
            try:
                #Авторизация на портале
                responce = requests.get(r"https://portal.petrocollege.ru/_api/Web/Lists(guid'9c095153-274d-4c73-9b8b-4e3dd6af89e5')/items(12)/AttachmentFiles",
                                    verify=False, auth=self.auth, headers=self.headers)

                #Получаем название файла прикрепленного и переводим название в строку 
                response_json = responce.json()
            except:
                logging.error("\n\nРасписание по преподавателям НЕ УДАЛОСЬ ОБНОВИТЬ В "+ str(datetime.datetime.now(pytz.timezone("Europe/Moscow")))+"\n\n")   
                return "Портал недоступен"
            response_json_norm = json_normalize(response_json['d']['results'])
            df = pd.DataFrame.from_dict(response_json_norm["FileName"]).tail(1)
            df_filename = df.FileName.to_string(index=False)
            #Ссылка на актуальное расписание
            link = f"https://portal.petrocollege.ru/Lists/2014/Attachments/12/{df_filename}"
            filename = "raspisaniyebyprepod.xlsx"
            r = requests.get(link, verify=False, auth=self.auth,
                            headers=self.headers, allow_redirects=True)
            open(filename, "wb").write(r.content)
            logging.info("\n\nРасписание по преподавателям обновлено в "+ str(datetime.datetime.now(pytz.timezone("Europe/Moscow")))+"\n\n")
        except:
            logging.error("\n\nРасписание по преподавателям НЕ УДАЛОСЬ ОБНОВИТЬ В "+ str(datetime.datetime.now(pytz.timezone("Europe/Moscow")))+"\n\n")

    def saveByAudit(self):
        """Сохранения расписания по аудитории с портала
        """
        try:
            try:
                #Авторизация на портале
                responce = requests.get(r"https://portal.petrocollege.ru/_api/Web/Lists(guid'9c095153-274d-4c73-9b8b-4e3dd6af89e5')/items(13)/AttachmentFiles",
                                    verify=False, auth=self.auth, headers=self.headers)

                #Получаем название файла прикрепленного и переводим название в строку 
                response_json = responce.json()
            except:
                logging.error("\n\nРасписание по кабинетам НЕ УДАЛОСЬ ОБНОВИТЬ В "+ str(datetime.datetime.now(pytz.timezone("Europe/Moscow")))+"\n\n")
                return "Портал недоступен"
            response_json_norm = json_normalize(response_json['d']['results'])
            df = pd.DataFrame.from_dict(response_json_norm["FileName"]).tail(1)
            df_filename = df.FileName.to_string(index=False)
            #Ссылка на актуальное расписание
            link = f"https://portal.petrocollege.ru/Lists/2014/Attachments/13/{df_filename}"
            filename = "raspisaniyebyaudit.xlsx"
            r = requests.get(link, verify=False, auth=self.auth,
                            headers=self.headers, allow_redirects=True)
            open(filename, "wb").write(r.content)
            logging.info("\n\nРасписание по кабинетам обновлено в "+ str(datetime.datetime.now(pytz.timezone("Europe/Moscow")))+"\n\n")
        except:
            logging.error("\n\nРасписание по кабинетам НЕ УДАЛОСЬ ОБНОВИТЬ В "+ str(datetime.datetime.now(pytz.timezone("Europe/Moscow")))+"\n\n")


#Создание задач на обновление расписания каждые 24 минуты
schedule.every(24).minutes.do(PetroSchedule(username, password).saveByGroup)
schedule.every(24).minutes.do(PetroSchedule(username, password).saveByPrepod)
schedule.every(24).minutes.do(PetroSchedule(username, password).saveByAudit)


def shed_update():
    while True:
        schedule.run_pending()
        sleep(1)

#Запуск в отдельном потоке функции-счетчика времени до по выполнения задач
thr = threading.Thread(target=shed_update).start()




