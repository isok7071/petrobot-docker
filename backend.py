from calendar import week
import threading
from bs4 import BeautifulSoup
import schedule
import requests
from requests_ntlm import HttpNtlmAuth
from config import *
import json
import os
import re
import time
import pandas as pd
from pandas import ExcelFile, json_normalize
import datetime
import parse
from telegraph import Telegraph

# Для правильного вывода и отображения данных
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('max_colwidth', None)

try:
    PetroScheduleTypes = parse.PetroSchedule(username, password)

    PetroScheduleTypes.saveByGroup()
    PetroScheduleTypes.saveByAudit()
    PetroScheduleTypes.saveByPrepod()
except:
    logging.critical("\n\nНе удалось скачать расписание при старте бота ПОРТАЛ НЕДОСТУПЕН\n\n")

class PetroChanges:
    changes = {}

    def __init__(self, username, password, replacements_url):
        #Авторизация на портале и получение json для работы с заменами
        self.auth = HttpNtlmAuth(username, password)

        self.headers = {'Accept': 'application/json;odata=verbose'}
        self.replacements_url = replacements_url
        response = requests.get(
            self.replacements_url, verify=False, auth=self.auth, headers=self.headers)
        self.response_json = response.json()

    def getDictChanges(self):
        for item in self.response_json["d"]["results"]:
            self.changes[item["Id"]] = {
                "Title": item["Title"], "html": item["OData__x0421__x043e__x0434__x0435__x04"]}

        return self.changes

    def getNamesChanges(self):
        '''
        Get dict of schedules change names
        :return: dict {id:name}
        '''
        names = {}
        for item in self.response_json["d"]["results"]:
            names[item["Id"]] = item["Title"]
        return names

    def gitDictChangesByDate(self, date):
        '''
        Получение замен по дню
        date(string): Дата в формате ДДММГГГГ (01012022)

        return: dict {Id:{Title:title, html: html}
        '''
        changes = self.getDictChanges()

        for day in changes:
            if date == re.sub("[^0-9]", "", changes[day]["Title"]):
                return changes[day]
        return "В данный момент либо изменений нет, либо вы ввели неправильное значение"

    def getChangesByDay(self, date):
        '''
        Получение для отправки замен по дню 
        date(string): Дата в формате ДДММГГГГ (01012022)
        
        return: message(string) - отформатированный текст с заменами
        '''
        message = f"<strong>Замены на {date[0:2]}.{date[2:4]}.{date[4:9]}</strong>\n"
        data = self.gitDictChangesByDate(date)
        if type(data) == str:
            return data
        html = data["html"].split("1 пара")[0]
        soup = BeautifulSoup(html, 'lxml')
        table_rows = soup.find_all("tr")
        i = 0
        for tr_row in table_rows:
            # Пропускаем названия колонок на портале
            i += 1
            if (i < 3):
                continue
            columns_in_row = tr_row.find_all("td")
            for column_td in columns_in_row:
                # Формирование нормального отображения для замен
                if re.findall(r'\d\d[-]{0,1}\d\d["к","з"]{0,1}[" "]{0,1}(\(подг\)){0,1}$', column_td.text):
                    message += "ГРУППА: " + column_td.text+"\nНОМЕР ПАРЫ: "
                else:
                    message += column_td.text+"\n"

                if columns_in_row.index(column_td) == 1:
                    message += "ПО РАСПИСАНИЮ: "

                elif columns_in_row.index(column_td) == 2:
                    message += "ПО ЗАМЕНЕ: "
            message += '_______\n\n'

        return (message)

    def getChangesByQuery(self, date, query):
        '''
        Получение замен по дню и поисковому запросу
        date(string): Дата в формате ДДММГГГГ (01012022)
        query(string): Поисковый запрос по заменам
        return: message(string) - отформатированный текст с заменами, содержащий замены из поискового запроса
        '''
        message = f"<strong>Замены на {date[0:2]}.{date[2:4]}.{date[4:9]}</strong>\n"

        data = self.gitDictChangesByDate(date)
        if type(data) == str:
            return data
        html = data["html"].split("1 пара")[0]
        soup = BeautifulSoup(html, 'lxml')
        tables_rows = soup.find_all("tr")
        i = 0
        for tr_row in tables_rows:
            # Пропуск названия колонок
            i += 1
            if (i < 3):
                continue
            #Поиск по заменам
            if query.lower() in (str(tr_row)).lower() or "№ пары".lower() in (str(tr_row)).lower():
                columns_in_row = tr_row.find_all("td")
                #Форматирвоние замен
                for column_td in columns_in_row:
                    if re.findall(r'\d\d[-]{0,1}\d\d["к","з"]{0,1}[" "]{0,1}(\(подг\)){0,1}$', column_td.text):
                        message += "ГРУППА: " + column_td.text+"\nНОМЕР ПАРЫ: "
                    else:
                        message += column_td.text+"\n"

                    if columns_in_row.index(column_td) == 1:
                        message += "ПО РАСПИСАНИЮ: "

                    elif columns_in_row.index(column_td) == 2:
                        message += "ПО ЗАМЕНЕ: "

                message += '_______\n\n'
        if not message:
            return "Ничего не найдено, ваш запрос: " + query
        return message

    def getCabsChanges(self, date):
        message = f"<strong>Переносы кабинетов на {date[0:2]}.{date[2:4]}.{date[4:9]}</strong>\n"
        data = self.gitDictChangesByDate(date)
        if type(data) == str:
            return data
        try:
            html = data["html"].split('6 пара</strong></td></tr>')[1]
            soup = BeautifulSoup(html, 'lxml')
            table_rows = soup.find_all("tr")
            message += "|Откуда |1 пара | 2 пара | 3 пара | 4 пара | 5 пара | 6 пара|\n"
            for tr_row in table_rows:
                table_td = tr_row.find_all("td")
                for td_text in table_td:
                    message += "| " + td_text.text
                message += '\n\n'
        except:
            message += "Переносов кабинетов не обнаружено"
        return (message)


class PetroBot:

    def scheduleType(message):
        """Вывод клавиатуры с выбором типа расписания

        Args:
            message (string): Сообщение от пользователя
        """
        # инициализация клавиатуры и добавление кнопок
        markup = telebot.types.ReplyKeyboardMarkup(
            resize_keyboard=True, one_time_keyboard=True, row_width=4)
        markup.add("По номеру группы")
        markup.add("По ФИО преподавателя")
        markup.add("По номеру аудитории")
        bot.send_message(
            message.from_user.id, "Пожалуйста, выберите тип нужного вам расписания.", reply_markup=markup)

    def formatDf(datafr):
        """Функция форматирующая DataFrame,убирает ненужную итнформацию

        Args:
            datafr : Получаемый датафрейм

        Returns:
            formatted_str (string): Возвращает строку готовую для вывода
        """
        # преобразуем датафрейм в html, для того чтобы убрать пустые пространство в строках
        try:
            html = datafr.to_html(index=False)
            soup = BeautifulSoup(html, 'lxml')
            # Выбор всех строк полученной таблицы парсером
            table_rows = soup.find_all("tr")

            # Форматирование полученных строк и создание результирующей строки
            formatted_str = ""
            for tr_row in table_rows:
                formatted_str += tr_row.text.replace(
                    "NaN", "Нет пары").replace("\\n", "\n")
            return formatted_str

        except:
            # Форматирование на случай если не парсер не сработает
            formatted_str = datafr.to_string(index=False).replace(" ", "").replace("NaN", "Нет пары").replace("\n", "\n\n").replace(
                "\\n", "\n")
            formatted_str = re.sub("([А-Я])", " \\1", str)
            formatted_strtr = re.sub(" С Д О", "СДО", str)
            return formatted_str

    def groups(message):
        """Вывод клавиатуры со списком групп

        Args:
            message (string): Сообщение от пользователя
        """
        try:
            file = 'raspisaniye.xlsx'
        except:
            logging.critical("Не удалось прочитать файл")
        # Load spreadsheet

        xl = pd.read_excel(file)

        group_frame = pd.DataFrame(xl).head(0)[2:]
        # Убираем ненужные поля
        group_frame.drop(group_frame.columns[group_frame.columns.str.contains('unnamed', case=False) | group_frame.columns.str.contains(
            'День', case=False) | group_frame.columns.str.contains('Интервал', case=False)], axis=1, inplace=True)

        markup = telebot.types.ReplyKeyboardMarkup(
            resize_keyboard=True, one_time_keyboard=True, row_width=4)

        # Считаем сколько всего записей
        i = 0
        for item in group_frame:
            i += 1

        # Обработка ограничения по количеству кнопок в Reply keyboard
        if i > 295:
            bot.send_message(message.from_user.id,
                             "Напишите номер группы как на шаблоне: <strong><i>3242 или 4543</i></strong>. \n\n<strong>ВНИМАНИЕ!</strong> Перед отправкой сообщения пожалуйста убедитесь в соответствии представленному шаблону.", parse_mode="HTML")
        else:
            # Добавляем массив из номеров групп в клавиатуру
            markup.add(*group_frame)
            bot.send_message(message.from_user.id,
                             "Выберите номер группы", reply_markup=markup)

    def prepodSelect(message):
        """Выбор преподавателя с клавиатуры
        Args:
            message (string): Сообщение от пользователя
        """
        try:
            file = 'raspisaniyebyprepod.xlsx'
        except:
            logging.critical("Не удалось прочитать файл")
        # Load spreadsheet
        xl = pd.read_excel(file)

        # Список с преподами
        prepod = pd.DataFrame(xl).head(0)[2:]
        prepod.drop(prepod.columns[prepod.columns.str.contains('unnamed', case=False) | prepod.columns.str.contains(
            'День', case=False) | prepod.columns.str.contains('Интервал', case=False)], axis=1, inplace=True)

        markupKeyboard = telebot.types.ReplyKeyboardMarkup(
            resize_keyboard=True, one_time_keyboard=True, row_width=2)

        # Добавляем массив из преподов в клавиатуру
        try:
            markupKeyboard.add(*prepod)
            bot.send_message(message.from_user.id,
                            "Выберите преподавателя", reply_markup=markupKeyboard)
        except:
            bot.send_message(message.from_user.id,
                            "Напишите ФИО преподавателя в <strong><i>формате Фамилия И.О.(Иванов И.И.)</i></strong>. \n\n<strong>ВНИМАНИЕ!</strong> Перед отправкой сообщения пожалуйста убедитесь в соответствии представленному шаблону.", parse_mode="HTML")

    def auditSelect(message):
        """Вывод клавиатуры с номерами аудиторий

        Args:
            message (string): Сообщение от пользователя
        """
        try:
            file = 'raspisaniyebyaudit.xlsx'
        except:
            logging.critical("Не удалось прочитать файл")
        # Load spreadsheet
        xl = pd.read_excel(file)

        # Список с номерами аудиторий
        auditorii = pd.DataFrame(xl).head(0)[2:]
        auditorii.drop(auditorii.columns[auditorii.columns.str.contains('unnamed', case=False) | auditorii.columns.str.contains(
            'День', case=False) | auditorii.columns.str.contains('Интервал', case=False)], axis=1, inplace=True)

        markupKeyboard = telebot.types.ReplyKeyboardMarkup(
            resize_keyboard=True, one_time_keyboard=True, row_width=4)

        # Считаем сколько всего записей
        i = 0
        for item in auditorii:
            i += 1

        # Обработка ограничения по количеству кнопок в Reply keyboard
        if i > 295:
            bot.send_message(message.from_user.id,
                             "Напишите номер аудитории в <strong><i>формате корпус/кабинет (1/310 или 6/507)</i></strong>. \n\n<strong>ВНИМАНИЕ!</strong> Перед отправкой сообщения пожалуйста убедитесь в соответствии представленному шаблону.", parse_mode="HTML")
        else:
            # Добавляем массив из номеров аудиторий в клавиатуру
            markupKeyboard.add(*auditorii)
            bot.send_message(message.from_user.id,
                             "Выберите номер аудитории", reply_markup=markupKeyboard)


    def groups_api():
        """Вывод клавиатуры со списком групп

        Args:
            message (string): Сообщение от пользователя
        """
        try:
            file = 'raspisaniye.xlsx'
        except:
            logging.critical("Не удалось прочитать файл")
        # Load spreadsheet

        xl = pd.read_excel(file)

        group_frame = pd.DataFrame(xl).head(0)[2:]
        # Убираем ненужные поля
        group_frame.drop(group_frame.columns[group_frame.columns.str.contains('unnamed', case=False) | group_frame.columns.str.contains(
            'День', case=False) | group_frame.columns.str.contains('Интервал', case=False)], axis=1, inplace=True)

        group_dict = group_frame.to_dict()

        return group_dict

    def get_rasp_by_day_and_week_number(group: str,day_number: int, week_number:int)->json:
        # Определяем какая неделя, нечетная или четная(числитель или знаменатель), после определяем день недели
        rasp = {}

        try:
            xl = pd.read_excel('raspisaniye.xlsx')
        except:
            logging.critical("Не удалось прочитать файл")
        # Выбор расписания по конкретной column(группа или ФИО или номер аудитории)
        raspisaniye = pd.DataFrame(xl, columns=[group])[0:]

        if week_number % 2 == 0:  # нечетная
            if day_number == 1:
                rasp = {
                    'Понедельник числитель': raspisaniye[0:6].fillna('').to_dict()
                }
            elif day_number == 2:
                rasp = {
                    'Вторник числитель': raspisaniye[6:12].fillna('').to_dict()
                }
            elif day_number == 3:
                rasp = {
                    'Среда числитель': raspisaniye[12:18].fillna('').to_dict()
                }
            elif day_number == 4:
                rasp = {
                    'Четверг числитель': raspisaniye[18:24].fillna('').to_dict()
                }

            elif day_number == 5:
                rasp = {
                    'Пятница числитель': raspisaniye[24:30].fillna('').to_dict()
                }
            elif day_number == 6:
                rasp = {
                    'Суббота числитель': raspisaniye[30:36].fillna('').to_dict()
                }

        if week_number % 2 != 0:  # Четная
            if day_number == 1:
                rasp = {
                    'Понедельник знаменатель': raspisaniye[36:42].fillna('').to_dict()
                }
            elif day_number == 2:
                rasp = {
                    'Вторник знаменатель': raspisaniye[42:48].fillna('').to_dict()
                }

            elif day_number == 3:
                rasp = {
                    'Среда знаменатель': raspisaniye[48:54].fillna('').to_dict()
                }

            elif day_number == 4:
                rasp = {
                    'Четверг знаменатель': raspisaniye[54:60].fillna('').to_dict()
                }
            elif day_number == 5:
                rasp = {
                    'Пятница знаменатель': raspisaniye[60:66].fillna('').to_dict()
                }
            elif day_number == 6:
                rasp = {
                    'Суббота знаменатель': raspisaniye[66:72].fillna('').to_dict()
                }
            
        return rasp

    def two_days_api(group:str)->json:
        # Вызов функций по определению номеров дня недели и недели в месяце
        today_day = PetroBot.getDayNumber(0)
        week_num = PetroBot.getWeekNumber(0)
        next_day = today_day + 1
        next_week = week_num
        if today_day == 7 or today_day == 6:
            next_day = 1
        
        #Те. понедельник, получается нужно получить номер след недели (если у нас суб или воскресенье кароче + 2 дня)
        if next_day == 1:
            next_week = PetroBot.getWeekNumber(2)
      
        today_rasp = PetroBot.get_rasp_by_day_and_week_number(group,today_day, week_num)
        next_day_rasp = PetroBot.get_rasp_by_day_and_week_number(group,next_day, next_week)

        scheduleDict = [
            today_rasp,
            next_day_rasp
        ]
        return scheduleDict

    
    def all_days_api(message: str, file: str)->json:
        """Выводит расписание на все дни недели (числитель и знаменатель)
        Args:
            message (string): Сообщение от пользователя
            file(string): Название файла с расписанием
        """

        try:
            xl = pd.read_excel(file)
        except:
            logging.critical("Не удалось прочитать файл")

        column = message

        schedule = pd.DataFrame(xl, columns=[column])[0:]

        scheduleDict = {
            'chislit':{
                '0':schedule[0:6].fillna('').to_dict(),
                '1':schedule[6:12].fillna('').to_dict(),
                '2':schedule[12:18].fillna('').to_dict(),
                '3':schedule[18:24].fillna('').to_dict(),
                '4':schedule[24:30].fillna('').to_dict(),
                '5':schedule[30:36].fillna('').to_dict(),
            },
            'znamenatel':{
                '0':schedule[36:42].fillna('').to_dict(),
                '1':schedule[42:48].fillna('').to_dict(),
                '2':schedule[48:54].fillna('').to_dict(),
                '3':schedule[54:60].fillna('').to_dict(),
                '4':schedule[60:66].fillna('').to_dict(),
                '5':schedule[66:72].fillna('').to_dict(),
            }

        }
        return scheduleDict


    def all_days_output(message, file):
        """Выводит расписание на все дни недели (числитель и знаменатель)
        Args:
            message (string): Сообщение от пользователя
            file(string): Название файла с расписанием
        """

        try:
            xl = pd.read_excel(file)
        except:
            logging.critical("Не удалось прочитать файл")

        column = message.text

        if file == 'raspisaniye.xlsx':
            # Если группа в группах на практике выводится сообщение
            if column in str(parse.PetroSchedule(username, password).internship()):
                bot.send_message(message.from_user.id, "<strong>Внимание, группа на практике!!!</strong>",
                                 reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

        raspisaniye = pd.DataFrame(xl, columns=[column])[0:]

        chislit_mond = f"<strong>ПОНЕДЕЛЬНИК числитель: </strong> {PetroBot.formatDf(raspisaniye[0:6])}"
        bot.send_message(message.from_user.id, chislit_mond,
                         reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

        chislit_tues = f"<strong>ВТОРНИК числитель: </strong> {PetroBot.formatDf(raspisaniye[6:12])}"
        bot.send_message(message.from_user.id, chislit_tues,
                         reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

        chislit_wednes = f"<strong>СРЕДА числитель: </strong> {PetroBot.formatDf(raspisaniye[12:18])}"
        bot.send_message(message.from_user.id, chislit_wednes,
                         reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

        chislit_thirsd = f"<strong>ЧЕТВЕРГ числитель: </strong> {PetroBot.formatDf(raspisaniye[18:24])}"
        bot.send_message(message.from_user.id, chislit_thirsd,
                         reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

        chislit_friday = f"<strong>ПЯТНИЦА числитель: </strong> {PetroBot.formatDf(raspisaniye[24:30])}"
        bot.send_message(message.from_user.id, chislit_friday,
                         reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

        chislit_sat = f"<strong>СУББОТА числитель: </strong> {PetroBot.formatDf(raspisaniye[30:36])}"
        bot.send_message(message.from_user.id, chislit_sat,
                         reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

        znam_mond = f"<strong>ПОНЕДЕЛЬНИК знаменатель: </strong> {PetroBot.formatDf(raspisaniye[36:42])}"
        bot.send_message(message.from_user.id, znam_mond,
                         reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

        znam_tues = f"<strong>ВТОРНИК знаменатель: </strong> {PetroBot.formatDf(raspisaniye[42:48])}"
        bot.send_message(message.from_user.id, znam_tues,
                         reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

        znam_wednes = f"<strong>СРЕДА знаменатель: </strong> {PetroBot.formatDf(raspisaniye[48:54])}"
        bot.send_message(message.from_user.id, znam_wednes,
                         reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

        znam_thirsd = f"<strong>ЧЕТВЕРГ знаменатель: </strong> {PetroBot.formatDf(raspisaniye[54:60])}"
        bot.send_message(message.from_user.id, znam_thirsd,
                         reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

        znam_friday = f"<strong>ПЯТНИЦА знаменатель: </strong> {PetroBot.formatDf(raspisaniye[60:66])}"
        bot.send_message(message.from_user.id,  znam_friday,
                         reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

        znam_sat = f"<strong>СУББОТА знаменатель: </strong> {PetroBot.formatDf(raspisaniye[66:72])}"
        bot.send_message(message.from_user.id,
                         znam_sat, reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

        telegraph_page_text = f"{chislit_mond} <br><br> {chislit_tues} <br><br> {chislit_wednes} <br><br> {chislit_thirsd} <br><br> {chislit_friday} <br><br> {chislit_sat} <br><br> {znam_mond} <br><br> {znam_tues} <br><br> {znam_wednes} <br><br> {znam_thirsd} <br><br> {znam_friday} <br><br> {znam_sat}"
        
        telegraph_link = PetroBot.generateTelegraphPage(telegraph_page_text)

        bot.send_message(message.from_user.id, telegraph_link,
                         reply_markup=telebot.types.ReplyKeyboardRemove(), protect_content=True)

    def by_day_output(message, column, file):
        """Вывод расписания по конкретному дню недели
        Args:
            message (string): Сообщение от пользователя
            column (string): Номер группы, либо номер аудитории, либо ФИО преподавателя
            file(string): Название файла(тип нужного расписания)
        """
        if message.text == "Понедельник числитель":
            # Определяет с какой по какую строку выводится расписание
            rowStart = 0
            rowEnd = 6
        elif message.text == "Вторник числитель":
            rowStart = 6
            rowEnd = 12
        elif message.text == "Среда числитель":
            rowStart = 12
            rowEnd = 18
        elif message.text == "Четверг числитель":
            rowStart = 18
            rowEnd = 24
        elif message.text == "Пятница числитель":
            rowStart = 24
            rowEnd = 30
        elif message.text == "Суббота числитель":
            rowStart = 30
            rowEnd = 36
        elif message.text == "Понедельник знаменатель":
            rowStart = 36
            rowEnd = 42
        elif message.text == "Вторник знаменатель":
            rowStart = 42
            rowEnd = 48
        elif message.text == "Среда знаменатель":
            rowStart = 48
            rowEnd = 54
        elif message.text == "Четверг знаменатель":
            rowStart = 54
            rowEnd = 60
        elif message.text == "Пятница знаменатель":
            rowStart = 60
            rowEnd = 66
        elif message.text == "Суббота знаменатель":
            rowStart = 66
            rowEnd = 72
        else:
            bot.send_message(message.from_user.id,
                             "Пожалуйста, введите верные значения, запустив функцию заново", reply_markup=telebot.types.ReplyKeyboardRemove())
            return 0

        if file == 'raspisaniye.xlsx':
            if column in str(parse.PetroSchedule(username, password).internship()):
                bot.send_message(message.from_user.id, "<strong>Внимание, группа на практике!!!</strong>",
                                 reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

        try:
            xl = pd.read_excel(file)
        except:
            logging.critical("Не удалось прочитать файл")

        raspisaniye = pd.DataFrame(xl, columns=[column])[rowStart:rowEnd]
        formatted_string = PetroBot.formatDf(raspisaniye)

        telegraph_link = PetroBot.generateTelegraphPage(formatted_string)

        bot.send_message(message.from_user.id, formatted_string,
                         reply_markup=telebot.types.ReplyKeyboardRemove(), protect_content=True)

        bot.send_message(message.from_user.id, telegraph_link,
                         reply_markup=telebot.types.ReplyKeyboardRemove(), protect_content=True)

    def todayOrNextDayOutput(message, file, next_day_bool):
        """Вывод расписания на текущий или на следующий день

        Args:
            message (string): Сообщение от пользователя
            next_day_bool (bool): Если переменная = 1, то расписание выводится на след день, если = 0, то на текущий
            file(string): Название файла(тип нужного расписания)
        """
        # Чтение файла с расписанием
        try:
            xl = pd.read_excel(file)
        except:
            logging.critical("Не удалось прочитать файл")

        column = message.text
        if file == 'raspisaniye.xlsx':
            if column in str(parse.PetroSchedule(username, password).internship()):
                bot.send_message(message.from_user.id, "<strong>Внимание, группа на практике!!!</strong>",
                                 reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

        # Вызов функций по определению номеров дня недели и недели в месяце
        today_day = PetroBot.getDayNumber(next_day_bool)
        week_num = PetroBot.getWeekNumber(next_day_bool)

        # Выбор расписания по конкретной column(группа или ФИО или номер аудитории)
        raspisaniye = pd.DataFrame(xl, columns=[column])[0:]

        # Определяем какая неделя, нечетная или четная(числитель или знаменатель), после определяем день недели
        if week_num % 2 == 0:  # нечетная
            if today_day == 1:
                formatted_string = PetroBot.formatDf(raspisaniye[0:6])
                bot.send_message(message.from_user.id, f"<strong>ПОНЕДЕЛЬНИК числитель: </strong> {formatted_string}",
                 reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

            elif today_day == 2:
                formatted_string = PetroBot.formatDf(raspisaniye[6:12])
                bot.send_message(message.from_user.id, f"<strong>ВТОРНИК числитель: </strong> {formatted_string}",
                 reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)
            elif today_day == 3:
                formatted_string = PetroBot.formatDf(raspisaniye[12:18])
                bot.send_message(message.from_user.id, f"<strong>СРЕДА числитель: </strong> {formatted_string}",
                 reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

            elif today_day == 4:
                formatted_string = PetroBot.formatDf(raspisaniye[18:24])
                bot.send_message(message.from_user.id, f"<strong>ЧЕТВЕРГ числитель: </strong> {formatted_string}",
                 reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

            elif today_day == 5:
                formatted_string = PetroBot.formatDf(raspisaniye[24:30])
                bot.send_message(message.from_user.id, f"<strong>ПЯТНИЦА числитель: </strong> {formatted_string}", reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

            elif today_day == 6:
                formatted_string = PetroBot.formatDf(raspisaniye[30:36])
                bot.send_message(message.from_user.id, f"<strong>СУББОТА числитель: </strong> {formatted_string}",
                 reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)
            elif today_day == 7:
                formatted_string = "Выходной"
                bot.send_message(message.from_user.id, "Это воскресенье - выходной",
                                 reply_markup=telebot.types.ReplyKeyboardRemove(), protect_content=True)

        if week_num % 2 != 0:  # Четная
            if today_day == 1:
                formatted_string = PetroBot.formatDf(raspisaniye[36:42])
                bot.send_message(message.from_user.id, f"<strong>ПОНЕДЕЛЬНИК знаменатель: </strong> {formatted_string}", reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)
            elif today_day == 2:
                formatted_string = PetroBot.formatDf(raspisaniye[42:48])
                bot.send_message(message.from_user.id, f"<strong>ВТОРНИК знаменатель: </strong> {formatted_string}", reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

            elif today_day == 3:
                formatted_string = PetroBot.formatDf(raspisaniye[48:54])
                bot.send_message(message.from_user.id, f"<strong>СРЕДА знаменатель: </strong> {formatted_string}", reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

            elif today_day == 4:
                formatted_string = PetroBot.formatDf(raspisaniye[54:60])
                bot.send_message(message.from_user.id, f"<strong>ЧЕТВЕРГ знаменатель: </strong> {formatted_string}",
                 reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)
            elif today_day == 5:
                formatted_string = PetroBot.formatDf(raspisaniye[60:66])
                bot.send_message(message.from_user.id, f"<strong>ПЯТНИЦА знаменатель: </strong> {formatted_string}",
                 reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

            elif today_day == 6:
                formatted_string = PetroBot.formatDf(raspisaniye[66:72])
                bot.send_message(message.from_user.id, f"<strong>СУББОТА знаменатель: </strong> {formatted_string}", reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)
            elif today_day == 7:
                formatted_string = "Выходной"
                bot.send_message(message.from_user.id, "Это воскресенье - выходной",
                                 reply_markup=telebot.types.ReplyKeyboardRemove(), protect_content=True)

        # Проверка замен
        changes = ""
        date = datetime.datetime.today() + datetime.timedelta(days=next_day_bool)
        date_formatted = date.strftime('%d%m%Y')
        changes = PetroChanges(username, password, replacements_url).getChangesByQuery(
            date_formatted, column)
        if len(column) > 2 and column in changes:
            bot.send_message(
                message.from_user.id, f"<i>По запросу есть изменения в расписании</i>: \n\n {changes}", parse_mode="HTML", protect_content=True)
        else:
            changes = ""

        page_text = f"{formatted_string} <br><br> {changes}"
        telegraph_link = PetroBot.generateTelegraphPage(page_text)

        bot.send_message(message.from_user.id, telegraph_link,
                         reply_markup=telebot.types.ReplyKeyboardRemove(), protect_content=True)

    def by_week_output(message, file):
        week_num = PetroBot.getWeekNumber(0)
        # Чтение файла с расписанием
        try:
            xl = pd.read_excel(file)
        except:
            logging.critical("Не удалось прочитать файл")

        column = message.text
        if file == 'raspisaniye.xlsx':
            if column in str(parse.PetroSchedule(username, password).internship()):
                bot.send_message(message.from_user.id, "<strong>Внимание, группа на практике!!!</strong>",
                                 reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

        # Выбор расписания по конкретной column(группа или ФИО или номер аудитории)
        raspisaniye = pd.DataFrame(xl, columns=[column])[0:]

        # Определяем какая неделя, нечетная или четная(числитель или знаменатель), после определяем день недели
        if week_num % 2 == 0:  # нечетная
            chislit_mond = f"<strong>ПОНЕДЕЛЬНИК числитель: </strong> {PetroBot.formatDf(raspisaniye[0:6])}"
            bot.send_message(message.from_user.id, chislit_mond,
                             reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

            chislit_tues = f"<strong>ВТОРНИК числитель: </strong> {PetroBot.formatDf(raspisaniye[6:12])}"
            bot.send_message(message.from_user.id, chislit_tues,
                             reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

            chislit_wednes = f"<strong>СРЕДА числитель: </strong> {PetroBot.formatDf(raspisaniye[12:18])}"
            bot.send_message(message.from_user.id, chislit_wednes,
                             reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

            chislit_thirsd = f"<strong>ЧЕТВЕРГ числитель: </strong> {PetroBot.formatDf(raspisaniye[18:24])}"
            bot.send_message(message.from_user.id, chislit_thirsd,
                             reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

            chislit_friday = f"<strong>ПЯТНИЦА числитель: </strong> {PetroBot.formatDf(raspisaniye[24:30])}"
            bot.send_message(message.from_user.id, chislit_friday,
                             reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

            chislit_sat = f"<strong>СУББОТА числитель: </strong> {PetroBot.formatDf(raspisaniye[30:36])}"
            bot.send_message(message.from_user.id, chislit_sat,
                             reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

            telegraph_page_text = f"{chislit_mond} <br><br> {chislit_tues} <br><br> {chislit_wednes} <br><br> {chislit_thirsd} <br><br> {chislit_friday} <br><br> {chislit_sat}"
            telegraph_link = PetroBot.generateTelegraphPage(
                telegraph_page_text)

            bot.send_message(message.from_user.id, telegraph_link,
                             reply_markup=telebot.types.ReplyKeyboardRemove(), protect_content=True)

        if week_num % 2 != 0:  # Четная
            znam_mond = f"<strong>ПОНЕДЕЛЬНИК знаменатель: </strong> {PetroBot.formatDf(raspisaniye[36:42])}"
            bot.send_message(message.from_user.id, znam_mond,
                             reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

            znam_tues = f"<strong>ВТОРНИК знаменатель: </strong> {PetroBot.formatDf(raspisaniye[42:48])}"
            bot.send_message(message.from_user.id, znam_tues,
                             reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

            znam_wednes = f"<strong>СРЕДА знаменатель: </strong> {PetroBot.formatDf(raspisaniye[48:54])}"
            bot.send_message(message.from_user.id, znam_wednes,
                             reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

            znam_thirsd = f"<strong>ЧЕТВЕРГ знаменатель: </strong> {PetroBot.formatDf(raspisaniye[54:60])}"
            bot.send_message(message.from_user.id, znam_thirsd,
                             reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

            znam_friday = f"<strong>ПЯТНИЦА знаменатель: </strong> {PetroBot.formatDf(raspisaniye[60:66])}"
            bot.send_message(message.from_user.id,  znam_friday,
                             reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

            znam_sat = f"<strong>СУББОТА знаменатель: </strong> {PetroBot.formatDf(raspisaniye[66:72])}"
            bot.send_message(message.from_user.id,
                             znam_sat, reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

            telegraph_page_text = f"{znam_mond} <br><br> {znam_tues} <br><br> {znam_wednes} <br><br> {znam_thirsd} <br><br> {znam_friday} <br><br> {znam_sat}"
            telegraph_link = PetroBot.generateTelegraphPage(
                telegraph_page_text)

            bot.send_message(message.from_user.id, telegraph_link,
                             reply_markup=telebot.types.ReplyKeyboardRemove(), protect_content=True)

    def sendWeekNumber(message):
        week_num = PetroBot.getWeekNumber(next_day_bool=0)
        if week_num % 2 == 0:  # нечетная
            bot.send_message(message.from_user.id,
                             "Сейчас <strong>числитель</strong>", parse_mode="HTML", protect_content=True)
        if week_num % 2 != 0:  # Четная
            bot.send_message(message.from_user.id,
                             "Сейчас <strong>знаменатель</strong>", parse_mode="HTML", protect_content=True)

    def getDayNumber(next_day_bool):
        # Определяется номер дня недели
        # Если next_dayh_bool = 1, то прибавляем 1 день
        today_day = datetime.datetime.today() + datetime.timedelta(days=next_day_bool)
        today_day = today_day.isoweekday()
        return today_day

    def getWeekNumber(next_day_bool):
        # Определяется номер номер недели в месяце, то есть числитель или знаменатель
        # Если next_dayh_bool = 1, то прибавляем 1 день
        week_num = datetime.datetime.utcnow() + datetime.timedelta(days=next_day_bool)
        week_num = int(week_num.isocalendar()[1])
        return week_num

    def generateTelegraphPage(page_text):
        """Функция создающая Telegraph страницу

        Args:
            page_text (string): Любая строка

        Returns:
            string: Ссылка на страницу
        """
        try:
            telegraph = Telegraph()
            telegraph.create_account(short_name='bot-petrovsky')

            page_text = re.sub('\n', '<br>', page_text)
            page_text = re.sub('\n\n', '<br><br>', page_text)
            response = telegraph.create_page(
                author_name='Бот',
                title='Расписание/Замены',
                html_content='<p>'+page_text+'</p>')

            telegraph_page_url = "Вы можете просмотреть запрошенную информацию в виде статьи Telegraph(Веб страницы) по ссылке ниже: \n\n" + format(
                response['url'])
            return telegraph_page_url
        except:
            logging.warning('Телеграф старница не была создана')
            return "К сожалению сейчас невозможно просмотреть информацию в виде Telegraph статьи."

    def send_all_changes(message):
        next_day_date = datetime.datetime.today() + datetime.timedelta(days=1)
        next_date_formatted = next_day_date.strftime('%d%m%Y')
        changes = PetroChanges(username, password, replacements_url).getChangesByDay(next_date_formatted)
        # Если нет изменений выходим из из функции
        if (changes == "В данный момент либо изменений нет, либо вы ввели неправильное значение"):
            bot.send_message(message.from_user.id, "В данный момент изменений нет",
                             reply_markup=telebot.types.ReplyKeyboardRemove(), protect_content=True)
            return 0
        # Иначе делим отправляем сообщение и делим если оно больше чем 4096 символов
        else:
            if len(changes) > 4096:
                for x in range(0, len(changes), 4096):
                    bot.send_message(message.from_user.id,  '{}'.format(
                        changes[x:x + 4096]), parse_mode="HTML", reply_markup=telebot.types.ReplyKeyboardRemove(), protect_content=True)
            else:
                bot.send_message(message.from_user.id, '{}'.format(
                    changes), parse_mode="HTML", reply_markup=telebot.types.ReplyKeyboardRemove(), protect_content=True)

            # Переносы кабинетов
            cabs = PetroChanges(username, password, replacements_url).getCabsChanges(next_date_formatted)
            # Делим если сообщение больше 4096
            if len(cabs) > 4096:
                for x in range(0, len(cabs), 4096):
                    bot.send_message(message.from_user.id,  '{}'.format(
                        cabs[x:x + 4096]), parse_mode="HTML", reply_markup=telebot.types.ReplyKeyboardRemove(), protect_content=True)
            else:
                bot.send_message(message.from_user.id, '{}'.format(
                    cabs), parse_mode="HTML", reply_markup=telebot.types.ReplyKeyboardRemove(), protect_content=True)

            # Отсылаем ссылку на телеграф страницу
            telegraph_text = changes + cabs
            telegraph_link = PetroBot.generateTelegraphPage(telegraph_text)
            bot.send_message(message.from_user.id, telegraph_link, protect_content=True)

    def changesByQuery(message, date_formatted):
        if(len(message.text) < 2):
            bot.send_message(
                message.from_user.id, "Ваш запрос слишком короткий, введите команду заново", parse_mode='HTML', reply_markup=telebot.types.ReplyKeyboardRemove())
            return 0
        else:
            query = message.text
            changes = PetroChanges(username, password, replacements_url).getChangesByQuery(date_formatted, query)
            # Если нет изменений выходим из из функции
            if (changes == "В данный момент либо изменений нет, либо вы ввели неправильное значение"):
                bot.send_message(message.from_user.id, "В данный момент изменений нет",
                                 reply_markup=telebot.types.ReplyKeyboardRemove(), protect_content=True)
                return 0
            # Иначе делим отправляем сообщение и делим если оно больше чем 4096 символов
            else:
                if len(changes) > 4096:
                    for x in range(0, len(changes), 4096):
                        bot.send_message(message.from_user.id,  '{}'.format(
                            changes[x:x + 4096]), parse_mode="HTML", reply_markup=telebot.types.ReplyKeyboardRemove(), protect_content=True)
                else:
                    bot.send_message(message.from_user.id, '{}'.format(
                        changes), parse_mode="HTML", reply_markup=telebot.types.ReplyKeyboardRemove(), protect_content=True)

                # Переносы кабинетов
                cabs = PetroChanges(username, password, replacements_url).getCabsChanges(date_formatted)
                # Делим если сообщение больше 4096
                if len(cabs) > 4096:
                    for x in range(0, len(cabs), 4096):
                        bot.send_message(message.from_user.id,  '{}'.format(
                            cabs[x:x + 4096]), parse_mode="HTML", reply_markup=telebot.types.ReplyKeyboardRemove(), protect_content=True)
                else:
                    bot.send_message(message.from_user.id, '{}'.format(
                        cabs), parse_mode="HTML", reply_markup=telebot.types.ReplyKeyboardRemove(), protect_content=True)

                # Отсылаем ссылку на телеграф страницу
                telegraph_text = changes + cabs
                telegraph_link = PetroBot.generateTelegraphPage(telegraph_text)
                bot.send_message(message.from_user.id, telegraph_link, protect_content=True)

    def subscribeSaveChoice(message, file):
        # Чтение файла с расписанием
        try:
            xl = pd.read_excel(file)
        except:
            logging.critical("Не удалось прочитать файл")

        column = message.text
        if file == 'raspisaniye.xlsx':
            group_frame = pd.DataFrame(xl).head(0)[2:]
            # Убираем ненужные поля
            group_frame.drop(group_frame.columns[group_frame.columns.str.contains('unnamed', case=False) | group_frame.columns.str.contains(
                'День', case=False) | group_frame.columns.str.contains('Интервал', case=False)], axis=1, inplace=True)

            if column in group_frame.to_dict():
                Subscribe().create(message.from_user.id, file, column)
                bot.send_message(message.from_user.id, "Вы успешно подписаны на рассылку расписания, чтобы отписаться введите команду /subscribe ещё раз.",
                                 reply_markup=telebot.types.ReplyKeyboardRemove())
            else:
                bot.send_message(message.from_user.id, "Вы ввели неверный номер группы, запустите функцию заново",
                                 reply_markup=telebot.types.ReplyKeyboardRemove())
                return 0

        elif file == 'raspisaniyebyprepod.xlsx':
            prepod_frame = pd.DataFrame(xl).head(0)[2:]
            # Убираем ненужные поля
            prepod_frame.drop(prepod_frame.columns[prepod_frame.columns.str.contains('unnamed', case=False) | prepod_frame.columns.str.contains(
                'День', case=False) | prepod_frame.columns.str.contains('Интервал', case=False)], axis=1, inplace=True)

            if column in prepod_frame.to_dict():
                Subscribe().create(message.from_user.id, file, column)
                bot.send_message(message.from_user.id, "Вы успешно подписаны на рассылку расписания, чтобы отписаться введите команду /subscribe ещё раз.",
                                 reply_markup=telebot.types.ReplyKeyboardRemove())
            else:
                bot.send_message(message.from_user.id, "Вы ввели неверное ФИО преподавателя, запустите функцию заново",
                                 reply_markup=telebot.types.ReplyKeyboardRemove())
                return 0
        elif file == 'raspisaniyebyaudit.xlsx':
            auditorii = pd.DataFrame(xl).head(0)[2:]
            # Убираем ненужные поля
            auditorii.drop(auditorii.columns[auditorii.columns.str.contains('unnamed', case=False) | auditorii.columns.str.contains(
                'День', case=False) | auditorii.columns.str.contains('Интервал', case=False)], axis=1, inplace=True)

            if column in auditorii.to_dict():
                Subscribe().create(message.from_user.id, file, column)
                bot.send_message(message.from_user.id, "Вы успешно подписаны на рассылку расписания, чтобы отписаться введите команду /subscribe ещё раз.",
                                 reply_markup=telebot.types.ReplyKeyboardRemove())
            else:
                bot.send_message(message.from_user.id, "Вы ввели неверный номер аудитории, запустите функцию заново",
                                 reply_markup=telebot.types.ReplyKeyboardRemove())
                return 0

    def sendScheduleToSubs():
        subscribes = Subscribe().read()
        #TODO Читаем таблицу с подпиской на рассылку, и проверяем есть ли чувак в таблице с платной подпиской(тут должна быть дата меньше чем сейчас ну то есть активная)
        #То есть должно быть по идеи два запроса  SELECT * from subscribe, SELECT user_id, expire_date from payment where expirde_date < datetime.now() ну и кароче как то надо заджоинить это все я хз как 
        #Ну это потом сделай, пока что оставлю in array
        for sub in subscribes:
            try:
                week_num = PetroBot.getWeekNumber(0)
                # Чтение файла с расписанием
                try:
                    file = sub['schedule_type']
                    xl = pd.read_excel(file)
                except:
                    logging.critical("Не удалось прочитать файл")

                column = sub['query_column']
                sub_id = sub['user_id']

                if file == 'raspisaniye.xlsx':
                    if column in str(parse.PetroSchedule(username, password).internship()):
                        bot.send_message(sub_id, "<strong>Внимание, группа на практике!!!</strong>",
                                         reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

                # Выбор расписания по конкретной column(группа или ФИО или номер аудитории)
                raspisaniye = pd.DataFrame(xl, columns=[column])[0:]

                # Определяем какая неделя, нечетная или четная(числитель или знаменатель)
                if week_num % 2 != 0:  # Четная
                    # отправляем на след неделю
                    chislit_mond = f"<strong>ПОНЕДЕЛЬНИК числитель: </strong> {PetroBot.formatDf(raspisaniye[0:6])}"
                    bot.send_message(sub_id, chislit_mond,
                                     reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

                    chislit_tues = f"<strong>ВТОРНИК числитель: </strong> {PetroBot.formatDf(raspisaniye[6:12])}"
                    bot.send_message(sub_id, chislit_tues,
                                     reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

                    chislit_wednes = f"<strong>СРЕДА числитель: </strong> {PetroBot.formatDf(raspisaniye[12:18])}"
                    bot.send_message(sub_id, chislit_wednes,
                                     reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

                    chislit_thirsd = f"<strong>ЧЕТВЕРГ числитель: </strong> {PetroBot.formatDf(raspisaniye[18:24])}"
                    bot.send_message(sub_id, chislit_thirsd,
                                     reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

                    chislit_friday = f"<strong>ПЯТНИЦА числитель: </strong> {PetroBot.formatDf(raspisaniye[24:30])}"
                    bot.send_message(sub_id, chislit_friday,
                                     reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

                    chislit_sat = f"<strong>СУББОТА числитель: </strong> {PetroBot.formatDf(raspisaniye[30:36])}"
                    bot.send_message(sub_id, chislit_sat,
                                     reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

                    telegraph_page_text = f"{chislit_mond} <br><br> {chislit_tues} <br><br> {chislit_wednes} <br><br> {chislit_thirsd} <br><br> {chislit_friday} <br><br> {chislit_sat}"
                    telegraph_link = PetroBot.generateTelegraphPage(
                        telegraph_page_text)

                    bot.send_message(sub_id, telegraph_link,
                                     reply_markup=telebot.types.ReplyKeyboardRemove(), protect_content=True)

                if week_num % 2 == 0:  # нечетная
                    # отправляем на след неделю
                    znam_mond = f"<strong>ПОНЕДЕЛЬНИК знаменатель: </strong> {PetroBot.formatDf(raspisaniye[36:42])}"
                    bot.send_message(sub_id, znam_mond,
                                     reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

                    znam_tues = f"<strong>ВТОРНИК знаменатель: </strong> {PetroBot.formatDf(raspisaniye[42:48])}"
                    bot.send_message(sub_id, znam_tues,
                                     reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

                    znam_wednes = f"<strong>СРЕДА знаменатель: </strong> {PetroBot.formatDf(raspisaniye[48:54])}"
                    bot.send_message(sub_id, znam_wednes,
                                     reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

                    znam_thirsd = f"<strong>ЧЕТВЕРГ знаменатель: </strong> {PetroBot.formatDf(raspisaniye[54:60])}"
                    bot.send_message(sub_id, znam_thirsd,
                                     reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

                    znam_friday = f"<strong>ПЯТНИЦА знаменатель: </strong> {PetroBot.formatDf(raspisaniye[60:66])}"
                    bot.send_message(sub_id,  znam_friday,
                                     reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

                    znam_sat = f"<strong>СУББОТА знаменатель: </strong> {PetroBot.formatDf(raspisaniye[66:72])}"
                    bot.send_message(sub_id,
                                     znam_sat, reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode="HTML", protect_content=True)

                    telegraph_page_text = f"{znam_mond} <br><br> {znam_tues} <br><br> {znam_wednes} <br><br> {znam_thirsd} <br><br> {znam_friday} <br><br> {znam_sat}"
                    telegraph_link = PetroBot.generateTelegraphPage(
                        telegraph_page_text)

                    bot.send_message(sub_id, telegraph_link,
                                     reply_markup=telebot.types.ReplyKeyboardRemove(), protect_content=True)
            except:
                # Удаляем пользователя если не удалось ему оптравить сообщение(он заблокировал бота)
                Subscribe().delete_by_user_id(sub_id)
            time.sleep(1)
    
    def sendSomethingToSubs(some_admin_text):
        statistic = BotSubscribtion().read()
        i = 0
        for stat in statistic:
            i += 1
            if i == 5:
                i = 0
                time.sleep(2)
                logging.info('\nСплю\n')
            try:
                stat_user_id = stat['user_id']
                bot.send_message(stat_user_id, some_admin_text, parse_mode="HTML")
                logging.info(f'Выслал {stat_user_id}')
            except:
                # Удаляем пользователя если не удалось ему оптравить сообщение(он заблокировал бота)
                logging.error(f'Ошибка в рассылке на {stat_user_id}')
                continue
    """
    def ScheduleSearchParamSaveDb(message, file):
        # Чтение файла с расписанием
        try:
            xl = pd.read_excel(file)
        except:
            print("Не удалось прочитать файл")

        column = message.text
        if file == 'raspisaniye.xlsx':
            group_frame = pd.DataFrame(xl).head(0)[2:]
            # Убираем ненужные поля
            group_frame.drop(group_frame.columns[group_frame.columns.str.contains('unnamed', case=False) | group_frame.columns.str.contains(
                'День', case=False) | group_frame.columns.str.contains('Интервал', case=False)], axis=1, inplace=True)

            if column in group_frame.to_dict():
                User_commands().create(message.from_user.id, column, file)
                bot.send_message(message.from_user.id, "Группа успешно сохранена, чтобы удалить выбор напишите команду /delete.",
                                    reply_markup=telebot.types.ReplyKeyboardRemove())
            else:
                bot.send_message(message.from_user.id, "Вы ввели неверный номер группы, запустите функцию заново",
                                    reply_markup=telebot.types.ReplyKeyboardRemove())
                return 0

        elif file == 'raspisaniyebyprepod.xlsx':
            prepod_frame = pd.DataFrame(xl).head(0)[2:]
            # Убираем ненужные поля
            prepod_frame.drop(prepod_frame.columns[prepod_frame.columns.str.contains('unnamed', case=False) | prepod_frame.columns.str.contains(
                'День', case=False) | prepod_frame.columns.str.contains('Интервал', case=False)], axis=1, inplace=True)

            if column in prepod_frame.to_dict():
                User_commands().create(message.from_user.id, column, file)
                bot.send_message(message.from_user.id, "ФИО преподавателя успешно сохранено, чтобы удалить выбор напишите команду /delete.",
                                    reply_markup=telebot.types.ReplyKeyboardRemove())
            else:
                bot.send_message(message.from_user.id, "Вы ввели неверное ФИО преподавателя, запустите функцию заново",
                                    reply_markup=telebot.types.ReplyKeyboardRemove())
                return 0
        elif file == 'raspisaniyebyaudit.xlsx':
            auditorii = pd.DataFrame(xl).head(0)[2:]
            # Убираем ненужные поля
            auditorii.drop(auditorii.columns[auditorii.columns.str.contains('unnamed', case=False) | auditorii.columns.str.contains(
                'День', case=False) | auditorii.columns.str.contains('Интервал', case=False)], axis=1, inplace=True)

            if column in auditorii.to_dict():
                User_commands().create(message.from_user.id, file, column)
                bot.send_message(message.from_user.id, "Номер аудитории успешно сохранён, чтобы удалить выбор напишите команду /delete.",
                                    reply_markup=telebot.types.ReplyKeyboardRemove())
            else:
                bot.send_message(message.from_user.id, "Вы ввели неверный номер аудитории, запустите функцию заново",
                                    reply_markup=telebot.types.ReplyKeyboardRemove())
                return 0
    """



# def sched_send():
#     schedule.every().sunday.at("18:00").do(PetroBot.sendScheduleToSubs)      
#     schedule.run_pending() 
#     while True:
#         time.sleep(1)


# Запускаем в отдельном потоке
# thr = threading.Thread(target=sched_send).start()

# print(PetroBot.groups_api())
#print(PetroChanges.getChangesByQuery('27042022', 'По'))
# print(PetroChanges.getChangesByDay('14052022'))
# print(PetroChanges.getCabsChanges('28042022'))
#print(PetroBot.two_days_api("51-55"))