from calendar import week
from config import *
import json
from flask import Flask, request, make_response
import os
import requests
import re
from requests_ntlm import HttpNtlmAuth
import time
import pandas as pd
from pandas import ExcelFile, json_normalize
import datetime
# Файл с бекендом
import backend
import threading
# Файл с обновлением расписания
import parse

#открыть порт занhttp.client ятый
from signal import SIGTERM # or SIGKILL
import subprocess
import os

server = Flask(__name__)

# Antiflood
last_time = {}

def stats(message):
    try:
        if(not(Stats().get_one_user_by_id(message.from_user.id))):
            Stats().create(message.from_user.id, datetime.datetime.now().date())
    except:
        return 0
        
def isUserSubscribedToBot(message):
    userSubscribtion = BotSubscribtion().getOneUserById(message.from_user.id)
    if (not(userSubscribtion) ):
        bot.send_message(message.from_user.id, 'Для начала пожалуйста приобретите подписку, этим вы помогаете проекту существовать')
        bot.send_message(message.from_user.id, 'Чтобы приобрести подписку - воспользуйтесь этой командой /buy_sub')
        return False
    elif userSubscribtion and userSubscribtion['expire_date']< datetime.datetime.now():
        bot.send_message(message.from_user.id, 'Похоже что ваша подписка закончилась, поэтому пожалуйста оплатите её снова')
        bot.send_message(message.from_user.id, 'Чтобы приобрести подписку снова - воспользуйтесь этой командой /buy_sub')
        return False

#TODO пофиксить расписание от - до
#TODO Убрать статистику

@bot.message_handler(commands=['buy_sub'])
def buy_sub(message):
    bot.send_message(message.from_user.id, f'Срок действия подписки - 30 дней, стоимость пожертвования - 45 рублей. Помните что подписка добровольная, и проект работает только на пожертвованиях.\n\n'
    'Что дает подписка: доступ ко всем функциям бота\n\n'
    'Я планирую и дальше развивать проект в свободное время, поэтому будет больше функций, возможно даже сделаю бота и в вк', parse_mode='HTML')
    time.sleep(1)
    bot.send_message(message.from_user.id, f'Чтобы приобрести подписку на 30 дней, вам нужно ОБЯЗАТЕЛЬНО следовать ВСЕМ шагам описанным ниже! (к сожалению способа оплаты проще пока нет)', parse_mode='HTML')
    time.sleep(1)
    bot.send_message(message.from_user.id, f'1. Скопируйте эти цифры (это id в телеграме) \n\n<pre>{message.from_user.id}</pre>\n\n'
    '2. Далее перейдите по ссылке https://donate.stream/petrobot и в поле <strong>НИКНЕЙМ</strong> вставьте скопировнные цифры <strong> - это ОЧЕНЬ важно, если ошибиться, то доступ автоматически не откроется</strong>\n\n'
    '3. После оплаты, вам через пару минут откроется доступ ко всем функциям бота\n\n'
    '4. Если доступ долго не открывается: пишите сразу мне https://vk.com/igor69696', parse_mode='HTML')
    bot.send_message(message.from_user.id, f'В итоге окошко должно будет выглядить так, как на скриншоте ниже, только никнейм будет: \n<pre>{message.from_user.id}</pre>', parse_mode='HTML' )
    img = open('payment.png', 'rb')
    bot.send_photo(message.from_user.id, img)
    bot.send_message(message.from_user.id, 'Демонстрацию работы бота можно посмотреть тут https://raspisanie-petrovskogo.vercel.app/')

@bot.message_handler(commands=['sub_status'])
def buy_sub(message):
    """Антифлуд """
    if message.from_user.id not in last_time:
        last_time[message.from_user.id] = time.time()
    else:
        if (time.time() - last_time[message.from_user.id]) * 1000 < 1500:
            return 0
        del last_time[message.from_user.id]
    
    if isUserSubscribedToBot(message) == False: 
        return 0

    expireDate = (BotSubscribtion().getOneUserById(message.from_user.id))['expire_date']
    try:
        expireDateFormatted = datetime.datetime.strptime(str(expireDate), "%Y-%m-%d %H:%M:%S.%f").strftime("%d-%m-%Y %H:%M")
    except:
        logging.critical('sdfsd')
    bot.send_message(message.from_user.id, f'Ваша подписка заканчивается: {expireDateFormatted}')


@bot.message_handler(commands=['start', 'help'])
def startbot(message):
    """Антифлуд """
    if message.from_user.id not in last_time:
        last_time[message.from_user.id] = time.time()
    else:
        if (time.time() - last_time[message.from_user.id]) * 1000 < 1500:
            return 0
        del last_time[message.from_user.id]
    
    inlineMarkup = telebot.types.InlineKeyboardMarkup();
    inlineMarkup.add(telebot.types.InlineKeyboardButton(text='Разработчик в ВК', url='https://vk.com/igor69696'))
    inlineMarkup.add(telebot.types.InlineKeyboardButton(text='Демонстрация работы бота (видео)', url='https://raspisanie-petrovskogo.vercel.app/'))
    inlineMarkup.add(telebot.types.InlineKeyboardButton(text='Поддержать проект❤️', url='https://yoomoney.ru/to/4100117765250849'))

    """Старт бота
    Args:
        message (string): Сообщение от пользователя
    """
    bot.send_message(message.from_user.id,
                     "Здравствуйте, данный бот поможет вам быстро и удобно узнать расписание занятий Петровского колледжа. По вопросам и предложениям пишите мне Вк.\n"
                     "\nНиже представлен ряд команд, которыми <strong>вы можете воспользоваться через <i>меню</i> или <i>нажав на выбранную команду</i> ниже:</strong>\n"
                     "\n/start или /help - Выводит список доступных команд;\n\n/buy_sub - Приобрести подписку на 30 дней, /sub_status - узнать когда кончается активная подписка;\n"
                     "\n/today - Расписание и замены(если есть) на текущий день;"
                     "\n\n/next_day - Расписание и замены(если есть) на следующий день;\n\n/all_days - Расписание на все две недели(числитель и знаменатель);\n\n/by_day - Расписание по конкретному дню;\n\n/by_week - Расписание на текущую неделю;\n\n/internship - Выводит группы на практике и их сроки практики;"
                     "\n\n/week - Узнать числитель сейчас или знаменатель;\n\n/all_changes - Выводит все замены на следующий день. <strong>Для получения замен по поисковому запросу (по номеру группы и т.д.) пользуйтесь следующей командой!</strong>\n\n/changes - Выводит замены <i>по поисковому запросу</i> на следующий, текущий или прошлый день;"
                     "\n\n/subscribe - Подписаться/отписаться на рассылку расписания. (Расписание высылается <i>на следующую неделю!</i> Отправляется 1 раз в неделю в воскресенье).\n\n", parse_mode='HTML', reply_markup=inlineMarkup)

@bot.message_handler(commands=['admin_rassilka'])
def send_rassilka(message):
    """Антифлуд """
    if message.from_user.id not in last_time:
        last_time[message.from_user.id] = time.time()
    else:
        if (time.time() - last_time[message.from_user.id]) * 1000 < 1500:
            return 0
        del last_time[message.from_user.id]
    if message.from_user.id ==1459498902:
        backend.PetroBot.sendScheduleToSubs()
    else:
        return 0 
    
@bot.message_handler(commands=['admin_statistic'])
def send_stats(message):
    """Антифлуд """
    if message.from_user.id not in last_time:
        last_time[message.from_user.id] = time.time()
    else:
        if (time.time() - last_time[message.from_user.id]) * 1000 < 1500:
            return 0
        del last_time[message.from_user.id]
    if message.from_user.id ==1459498902:
        bot.send_message('1459498902', 'На рассылку подписалось: ')
        bot.send_message('1459498902', Subscribe().count())
        bot.send_message('1459498902', 'Всего пользователей: ')
        bot.send_message('1459498902', Stats().count())   
    else:
        return 0 
    

"""
@bot.message_handler(commands=['delete'])
def deleteScheduleSearchParam(message):
    if User_commands().get_one_user_by_id(message.from_user.id):
        User_commands().delete_by_user_id(message.from_user.id)
        bot.send_message(message.from_user.id,
                         "Ваш прошлый выбор успешно удалён! Теперь вы опять можете изменить свой выбор, путём ввода команды /save.")
    else:
        bot.send_message(message.from_user.id,
                         "У вас нет сохраненного выбора расписания!")
        return 0 

@bot.message_handler(commands=['save'])
def ScheduleSearchParamStart(message):
    if User_commands().get_one_user_by_id(message.from_user.id):
            bot.send_message(message.from_user.id,
                         "У вас уже сохранен выбор! Чтобы изменить его пожалуйста, для начала введите команду /delete, а затем можете снова воспользоваться этой командой.")
    else:
            bot.send_message(message.from_user.id,
                     "Пожалуйста, пройдите процедуру выбора нужного вам критерия для расписания")
            backend.PetroBot.scheduleType(message)
            bot.register_next_step_handler(message, ScheduleSearchParamChoose)

def ScheduleSearchParamChoose(message):
    if message.text == "По номеру группы":
        # Вызов функции возвращающей список групп в виде клавиатуры для ввода
        backend.PetroBot.groups(message)
        # Файл с расписанием по группе
        file = "raspisaniye.xlsx"
        bot.register_next_step_handler(
            message, ScheduleSearchParamSaveDb, file)
    elif message.text == "По ФИО преподавателя":
        # Вызов функции предлагающей пользователю ввести ФИО преподавателя
        backend.PetroBot.prepodSelect(message)
        # Файл с расписанием по преподавателю
        file = "raspisaniyebyprepod.xlsx"
        bot.register_next_step_handler(
            message, ScheduleSearchParamSaveDb, file)
    elif message.text == "По номеру аудитории":
        # Вызов функции возвращающей список аудиторий в виде клавиатуры для ввода
        backend.PetroBot.auditSelect(message)
        # Файл с расписанием по аудитории
        file = "raspisaniyebyaudit.xlsx"
        bot.register_next_step_handler(
            message, ScheduleSearchParamSaveDb, file)
    else:
        bot.send_message(message.from_user.id,
                         "Пожалуйста, введите верное значение, запустив функцию заново", reply_markup=telebot.types.ReplyKeyboardRemove())
        return 0


def ScheduleSearchParamSaveDb(message, file):
    try:
        backend.PetroBot.ScheduleSearchParamSaveDb(message, file)
    except:
        bot.send_message(message.from_user.id,
                         "Не удалось сохранить выбор. Пожалуйста попробуйте позже.")
"""
@bot.message_handler(commands=['internship'])
def groupsInternship(message):

    """Выводит группы на практике

    Args:
        message (string): Сообщение от пользователя
    """
    """Антифлуд """
    if message.from_user.id not in last_time:
        last_time[message.from_user.id] = time.time()
    else:
        if (time.time() - last_time[message.from_user.id]) * 1000 < 1500:
            return 0
        del last_time[message.from_user.id]

    if isUserSubscribedToBot(message) == False: 
        return False

    bot.send_message(message.from_user.id,
                     "<strong>Группы на практике: </strong>", parse_mode="HTML")
    # обращается к функции которая парсит группы на практике с портала
    try:
        bot.send_message(message.from_user.id, parse.PetroSchedule(username, password).internship(), parse_mode="HTML", reply_markup=telebot.types.ReplyKeyboardRemove(), protect_content=True)
    except:
        bot.send_message(message.from_user.id, "Не удалось получить группы на практике, попробуйте позже", parse_mode="HTML", reply_markup=telebot.types.ReplyKeyboardRemove())
    



@bot.message_handler(commands=['all_days'])
def all_days_first(message):
    """Функция инициирующая вывод всего расписания, передает тип название файла расписания
    Args:
        message (string): Сообщение от пользователя
    """
    """Антифлуд """
    if message.from_user.id not in last_time:
        last_time[message.from_user.id] = time.time()
    else:
        if (time.time() - last_time[message.from_user.id]) * 1000 < 1500:
            return 0
        del last_time[message.from_user.id]
    if isUserSubscribedToBot(message) == False: 
        return False
    # фунция выбора типа расписания
    backend.PetroBot.sendWeekNumber(message)
    backend.PetroBot.scheduleType(message)
    bot.register_next_step_handler(message, all_days_sched_type)
        



def all_days_sched_type(message):
    """Получает тип расписания и перенаправляет на нужную функцию

    Args:
        message (string): Сообщение от пользователя

    """
    if message.text == "По номеру группы":
        # Вызов функции возвращающей список групп в виде клавиатуры для ввода
        bot.send_message(message.from_user.id,
                         parse.dateRasp, parse_mode="HTML")
        backend.PetroBot.groups(message)
        # Файл с расписанием по группе
        file = "raspisaniye.xlsx"
        bot.register_next_step_handler(message, all_days_output, file)
    elif message.text == "По ФИО преподавателя":
        # Вызов функции предлагающей пользователю ввести ФИО преподавателя
        bot.send_message(message.from_user.id,
                         parse.dateRasp, parse_mode="HTML")
        backend.PetroBot.prepodSelect(message)
        # Файл с расписанием по преподавателю
        file = "raspisaniyebyprepod.xlsx"
        bot.register_next_step_handler(message, all_days_output, file)
    elif message.text == "По номеру аудитории":
        # Вызов функции возвращающей список аудиторий в виде клавиатуры для ввода
        bot.send_message(message.from_user.id,
                         parse.dateRasp, parse_mode="HTML")
        backend.PetroBot.auditSelect(message)
        # Файл с расписанием по аудитории
        file = "raspisaniyebyaudit.xlsx"
        bot.register_next_step_handler(message, all_days_output, file)
    else:
        bot.send_message(message.from_user.id,
                         "Пожалуйста, введите верное значение, запустив функцию заново", reply_markup=telebot.types.ReplyKeyboardRemove())
        return 0


def all_days_output(message, file):
    """Выводит расписание на все дни недели (числитель и знаменатель)
    Args:
        message (string): Сообщение от пользователя
        file(string): Название файла с расписанием
    """
    try:
        backend.PetroBot.all_days_output(message, file)
        #DonutMurkup = telebot.types.InlineKeyboardMarkup();
        #DonutMurkup.add(telebot.types.InlineKeyboardButton(text='Поддержать проект❤️', url='https://yoomoney.ru/to/4100117765250849'))
        #bot.send_message(message.from_user.id, "Поддержите проект (от этого может зависеть его судьба)", parse_mode="HTML", reply_markup=DonutMurkup)
    except:
        bot.send_message(message.from_user.id,
                         "Что-то пошло не так, пожалуйста попробуйте позже.\n Возможно портал сейчас не доступен или сейчас еще нет расписания.", reply_markup=telebot.types.ReplyKeyboardRemove())


@bot.message_handler(commands=['by_day'])
def by_day_first(message):
    """Функция, передающая необходимые данные(по выбору) в функцию по выводу расписания по конретному дню

    Args:
        message (string): Сообщение от пользователя
    """
    """Антифлуд """
    if message.from_user.id not in last_time:
        last_time[message.from_user.id] = time.time()
    else:
        if (time.time() - last_time[message.from_user.id]) * 1000 < 1500:
            return 0
        del last_time[message.from_user.id]
    if isUserSubscribedToBot(message) == False: 
        return False
    backend.PetroBot.scheduleType(message)
    bot.register_next_step_handler(message, by_day_day_sched_type)


def by_day_day_sched_type(message):
    """Получает типа расписания и перенаправляет на нужную функцию

    Args:
        message (string): Сообщение от пользователя
    """
    if message.text == "По номеру группы":
        # Вызов функции возвращающей список групп в виде клавиатуры для ввода
        bot.send_message(message.from_user.id,
                         parse.dateRasp, parse_mode="HTML")
        backend.PetroBot.groups(message)
        # Файл с расписанием по группе
        file = "raspisaniye.xlsx"
        bot.register_next_step_handler(message, by_day_day_select, file)
    elif message.text == "По ФИО преподавателя":
        # Вызов функции предлагающей пользователю ввести ФИО преподавателя
        bot.send_message(message.from_user.id,
                         parse.dateRasp, parse_mode="HTML")
        backend.PetroBot.prepodSelect(message)
        # Файл с расписанием по преподавателю
        file = "raspisaniyebyprepod.xlsx"
        bot.register_next_step_handler(message, by_day_day_select, file)
    elif message.text == "По номеру аудитории":
        # Вызов функции возвращающей список аудиторий в виде клавиатуры для ввода
        bot.send_message(message.from_user.id,
                         parse.dateRasp, parse_mode="HTML")
        backend.PetroBot.auditSelect(message)
        # Файл с расписанием по аудитории
        file = "raspisaniyebyaudit.xlsx"
        bot.register_next_step_handler(message, by_day_day_select, file)
    else:
        bot.send_message(message.from_user.id,
                         "Пожалуйста, введите верное значение, запустив функцию заново", reply_markup=telebot.types.ReplyKeyboardRemove())
        return 0


def by_day_day_select(message, file):
    """Функция передающая выбор с клавиатуры дня недели для вывода конкретного раписания

    Args:
        message (string): Сообщение от пользователя
        file (string): Название файла с расписанием
    """
    column = message.text

    backend.PetroBot.sendWeekNumber(message)
    reply = telebot.types.ReplyKeyboardMarkup(
        resize_keyboard=True, one_time_keyboard=True, row_width=2)
    reply.add("Понедельник числитель", "Понедельник знаменатель")
    reply.add("Вторник числитель", "Вторник знаменатель")
    reply.add("Среда числитель", "Среда знаменатель")
    reply.add("Четверг числитель", "Четверг знаменатель")
    reply.add("Пятница числитель", "Пятница знаменатель")
    reply.add("Суббота числитель", "Суббота знаменатель")

    bot.send_message(message.from_user.id,
                     "На какой день требуется расписание", reply_markup=reply)
    bot.register_next_step_handler(message, by_day_output, column, file)


def by_day_output(message, column, file):
    """Вывод расписания по конкретному дню недели
    Args:
        message (string): Сообщение от пользователя
        column (string): Номер группы, либо номер аудитории, либо ФИО преподавателя
        file(string): Название файла(тип нужного расписания)
    """
    try:
        backend.PetroBot.by_day_output(message, column, file)
        #DonutMurkup = telebot.types.InlineKeyboardMarkup();
        #DonutMurkup.add(telebot.types.InlineKeyboardButton(text='Поддержать проект❤️', url='https://yoomoney.ru/to/4100117765250849'))
        #bot.send_message(message.from_user.id, "Поддержите проект (от этого может зависеть его судьба)", parse_mode="HTML", reply_markup=DonutMurkup)
    except:
        bot.send_message(message.from_user.id,
                         "Что-то пошло не так, пожалуйста попробуйте позже.\n Возможно портал сейчас не доступен или сейчас еще нет расписания.", reply_markup=telebot.types.ReplyKeyboardRemove())


@bot.message_handler(commands=['next_day'])
def next_day_start(message):
    """Функция, передающая необходимые данные в функцию по выводу расписания на текущий или след день

    Args:
        message (string): Сообщение от пользователя
    """

    """Антифлуд """
    if message.from_user.id not in last_time:
        last_time[message.from_user.id] = time.time()
    else:
        if (time.time() - last_time[message.from_user.id]) * 1000 < 1500:
            return 0
        del last_time[message.from_user.id]
    if isUserSubscribedToBot(message) == False: 
        return False
    # Переменная дающая понять, что нам нужно расписание на след день
    next_day_bool = 1

    backend.PetroBot.scheduleType(message)
    bot.register_next_step_handler(message, next_day_sched_type, next_day_bool)


def next_day_sched_type(message, next_day_bool):
    """Получает тип расписания и перенаправляет на нужную функцию

    Args:
        message (string): Сообщение от пользователя
        next_day_bool (bool): Если переменная = 1, то расписание выводится на след день, если = 0, то на текущий
    """
    if message.text == "По номеру группы":
        # Вызов функции возвращающей список групп в виде клавиатуры для ввода
        bot.send_message(message.from_user.id,
                         parse.dateRasp, parse_mode="HTML")
        backend.PetroBot.groups(message)
        # Файл с расписанием по группе
        file = "raspisaniye.xlsx"
        bot.register_next_step_handler(
            message, todayOrNextDayOutput, file, next_day_bool)
    elif message.text == "По ФИО преподавателя":
        # Вызов функции предлагающей пользователю ввести ФИО преподавателя
        bot.send_message(message.from_user.id,
                         parse.dateRasp, parse_mode="HTML")
        backend.PetroBot.prepodSelect(message)
        # Файл с расписанием по преподавателю
        file = "raspisaniyebyprepod.xlsx"
        bot.register_next_step_handler(
            message, todayOrNextDayOutput, file, next_day_bool)
    elif message.text == "По номеру аудитории":
        # Вызов функции возвращающей список аудиторий в виде клавиатуры для ввода
        bot.send_message(message.from_user.id,
                         parse.dateRasp, parse_mode="HTML")
        backend.PetroBot.auditSelect(message)
        # Файл с расписанием по аудитории
        file = "raspisaniyebyaudit.xlsx"
        bot.register_next_step_handler(
            message, todayOrNextDayOutput, file, next_day_bool)
    else:
        bot.send_message(message.from_user.id,
                         "Пожалуйста, введите верное значение, запустив функцию заново", reply_markup=telebot.types.ReplyKeyboardRemove())
        return 0


@bot.message_handler(commands=['today'])
def today_start(message):
    """Функция, передающая необходимые данные в функцию по выводу расписания на текущий или след день

    Args:
        message (string): Сообщение от пользователя
    """

    """Антифлуд """
    if message.from_user.id not in last_time:
        last_time[message.from_user.id] = time.time()
    else:
        if (time.time() - last_time[message.from_user.id]) * 1000 < 1500:
            return 0
        del last_time[message.from_user.id]
    if isUserSubscribedToBot(message) == False: 
        return False
    next_day_bool = 0
    # Переменная дающая понять, что нам нужно расписание на текущий день
    backend.PetroBot.scheduleType(message)
    bot.register_next_step_handler(message, today_sched_type, next_day_bool)


def today_sched_type(message, next_day_bool):
    """Получает тип расписания и перенаправляет на нужную функцию

    Args:
        message (string): Сообщение от пользователя
        next_day_bool (bool): Если переменная = 1, то расписание выводится на след день, если = 0, то на текущий

    """
    if message.text == "По номеру группы":
        # Вызов функции возвращающей список групп в виде клавиатуры для ввода
        bot.send_message(message.from_user.id,
                         parse.dateRasp, parse_mode="HTML")
        backend.PetroBot.groups(message)
        # Файл с расписанием по группе
        file = "raspisaniye.xlsx"
        bot.register_next_step_handler(
            message, todayOrNextDayOutput, file, next_day_bool)
    elif message.text == "По ФИО преподавателя":
        # Вызов функции предлагающей пользователю ввести ФИО преподавателя
        bot.send_message(message.from_user.id,
                         parse.dateRasp, parse_mode="HTML")
        backend.PetroBot.prepodSelect(message)
        # Файл с расписанием по преподавателю
        file = "raspisaniyebyprepod.xlsx"
        bot.register_next_step_handler(
            message, todayOrNextDayOutput, file, next_day_bool)
    elif message.text == "По номеру аудитории":
        # Вызов функции возвращающей список аудиторий в виде клавиатуры для ввода
        bot.send_message(message.from_user.id,
                         parse.dateRasp, parse_mode="HTML")
        backend.PetroBot.auditSelect(message)
        # Файл с расписанием по аудитории
        file = "raspisaniyebyaudit.xlsx"
        bot.register_next_step_handler(
            message, todayOrNextDayOutput, file, next_day_bool)
    else:
        bot.send_message(message.from_user.id,
                         "Пожалуйста, введите верное значение, запустив функцию заново", reply_markup=telebot.types.ReplyKeyboardRemove())
        return 0


def todayOrNextDayOutput(message, file, next_day_bool):
    """Вывод расписания на текущий или на следующий день

    Args:
        message (string): Сообщение от пользователя
        next_day_bool (bool): Если переменная = 1, то расписание выводится на след день, если = 0, то на текущий
        file(string): Название файла(тип нужного расписания)
    """
    try:
        backend.PetroBot.todayOrNextDayOutput(message, file, next_day_bool)
        #DonutMurkup = telebot.types.InlineKeyboardMarkup();
        #DonutMurkup.add(telebot.types.InlineKeyboardButton(text='Поддержать проект❤️', url='https://yoomoney.ru/to/4100117765250849'))
        #bot.send_message(message.from_user.id, "Поддержите проект (от этого может зависеть его судьба)", parse_mode="HTML", reply_markup=DonutMurkup)
    except:
        bot.send_message(message.from_user.id,
                         "Что-то пошло не так, пожалуйста попробуйте позже.\n Возможно портал сейчас не доступен или сейчас еще нет расписания.", reply_markup=telebot.types.ReplyKeyboardRemove())


@bot.message_handler(commands=['week'])
def sendWeekNumber(message):

    """Антифлуд """
    if message.from_user.id not in last_time:
        last_time[message.from_user.id] = time.time()
    else:
        if (time.time() - last_time[message.from_user.id]) * 1000 < 1500:
            return 0
        del last_time[message.from_user.id]
        
    if isUserSubscribedToBot(message) == False: 
        return False
    try:
        backend.PetroBot.sendWeekNumber(message)
        #DonutMurkup = telebot.types.InlineKeyboardMarkup();
        #DonutMurkup.add(telebot.types.InlineKeyboardButton(text='Поддержать проект❤️', url='https://yoomoney.ru/to/4100117765250849'))
        #bot.send_message(message.from_user.id, "Поддержите проект (от этого может зависеть его судьба)", parse_mode="HTML", reply_markup=DonutMurkup)
    except:
        bot.send_message(message.from_user.id,
                         "Что-то пошло не так, пожалуйста попробуйте позже.\n Возможно портал сейчас не доступен или сейчас еще нет расписания.", reply_markup=telebot.types.ReplyKeyboardRemove())


@bot.message_handler(commands=['by_week'])
def by_week_start(message):
    """Антифлуд """
    if message.from_user.id not in last_time:
        last_time[message.from_user.id] = time.time()
    else:
        if (time.time() - last_time[message.from_user.id]) * 1000 < 1500:
            return 0
        del last_time[message.from_user.id]
    if isUserSubscribedToBot(message) == False: 
        return False
    backend.PetroBot.scheduleType(message)
    bot.register_next_step_handler(message, by_week_sched_type)


def by_week_sched_type(message):
    if message.text == "По номеру группы":
        # Вызов функции возвращающей список групп в виде клавиатуры для ввода
        bot.send_message(message.from_user.id,
                         parse.dateRasp, parse_mode="HTML")
        backend.PetroBot.groups(message)
        # Файл с расписанием по группе
        file = "raspisaniye.xlsx"
        bot.register_next_step_handler(
            message, by_week_output, file)
    elif message.text == "По ФИО преподавателя":
        # Вызов функции предлагающей пользователю ввести ФИО преподавателя
        bot.send_message(message.from_user.id,
                         parse.dateRasp, parse_mode="HTML")
        backend.PetroBot.prepodSelect(message)
        # Файл с расписанием по преподавателю
        file = "raspisaniyebyprepod.xlsx"
        bot.register_next_step_handler(
            message, by_week_output, file)
    elif message.text == "По номеру аудитории":
        # Вызов функции возвращающей список аудиторий в виде клавиатуры для ввода
        bot.send_message(message.from_user.id,
                         parse.dateRasp, parse_mode="HTML")
        backend.PetroBot.auditSelect(message)
        # Файл с расписанием по аудитории
        file = "raspisaniyebyaudit.xlsx"
        bot.register_next_step_handler(
            message, by_week_output, file)
    else:
        bot.send_message(message.from_user.id,
                         "Пожалуйста, введите верное значение, запустив функцию заново", reply_markup=telebot.types.ReplyKeyboardRemove())
        return 0


def by_week_output(message, file):
    try:
        backend.PetroBot.by_week_output(message, file)
        #DonutMurkup = telebot.types.InlineKeyboardMarkup();
        #DonutMurkup.add(telebot.types.InlineKeyboardButton(text='Поддержать проект❤️', url='https://yoomoney.ru/to/4100117765250849'))
        #bot.send_message(message.from_user.id, "Поддержите проект (от этого может зависеть его судьба)", parse_mode="HTML", reply_markup=DonutMurkup)
    except:
        bot.send_message(message.from_user.id,
                         "Что-то пошло не так, пожалуйста попробуйте позже.\n Возможно портал сейчас не доступен или сейчас еще нет расписания.", reply_markup=telebot.types.ReplyKeyboardRemove())


"""    
#ЗАМЕНЫ#
"""


@bot.message_handler(commands=['all_changes'])
def send_all_changes(message):
    
    """Антифлуд """
    if message.from_user.id not in last_time:
        last_time[message.from_user.id] = time.time()
    else:
        if (time.time() - last_time[message.from_user.id]) * 1000 < 1500:
            return 0
        del last_time[message.from_user.id]
    if isUserSubscribedToBot(message) == False: 
        return False
    try:
        bot.send_message(message.from_user.id, "<strong>ВНИМАНИЕ!</strong> Если ваша группа в СДО весь день, то мониторьте это, так как эта информация <i>пока что</i> не берётся с сайта!", parse_mode="HTML")
        time.sleep(2)
        backend.PetroBot.send_all_changes(message)
        #DonutMurkup = telebot.types.InlineKeyboardMarkup();
        #DonutMurkup.add(telebot.types.InlineKeyboardButton(text='Поддержать проект❤️', url='https://yoomoney.ru/to/4100117765250849'))
        #bot.send_message(message.from_user.id, "Поддержите проект (от этого может зависеть его судьба)", parse_mode="HTML", reply_markup=DonutMurkup)
    except:
        bot.send_message(message.from_user.id,
                         "Что-то пошло не так, пожалуйста попробуйте позже.\n Возможно портал сейчас не доступен или сейчас еще нет расписания.", reply_markup=telebot.types.ReplyKeyboardRemove())


@bot.message_handler(commands=['changes'])
def changesByQueryStart(message):
    """Антифлуд """
    if message.from_user.id not in last_time:
        last_time[message.from_user.id] = time.time()
    else:
        if (time.time() - last_time[message.from_user.id]) * 1000 < 1500:
            return 0
        del last_time[message.from_user.id]
    if isUserSubscribedToBot(message) == False: 
        return False
    reply = telebot.types.ReplyKeyboardMarkup(
        resize_keyboard=True, one_time_keyboard=True, row_width=1)
    reply.add("Вчера")
    reply.add("Сегодня")
    reply.add("Завтра")
    bot.send_message(message.from_user.id,
                     "На какой день требуются изменения", reply_markup=reply)
    bot.register_next_step_handler(message, getChangesQuery)


def getChangesQuery(message):
    if message.text == "Вчера":
        date = datetime.datetime.today() + datetime.timedelta(days=-1)
        date_formatted = date.strftime('%d%m%Y')
    elif message.text == "Сегодня":
        date = datetime.datetime.today()
        date_formatted = date.strftime('%d%m%Y')
    elif message.text == "Завтра":
        date = datetime.datetime.today() + datetime.timedelta(days=1)
        date_formatted = date.strftime('%d%m%Y')
    else:
        bot.send_message(message.from_user.id,
                         "Вы ввели неправильное значение, запустите команду заново", reply_markup=telebot.types.ReplyKeyboardRemove())
        return 0

    bot.send_message(message.from_user.id, "Пожалуйста введите желаемый запрос для поиска, это может быть:  <strong>ФИО преподавателя</strong> (например: Иванов И.И. или просто Иванов), <strong>номер группы</strong>, <strong>название предмета</strong> (можно ввести первые буквы или же часть названия)", parse_mode='HTML')
    bot.register_next_step_handler(message, changesByQuery, date_formatted)


def changesByQuery(message, date_formatted):
    try:
        bot.send_message(message.from_user.id, "<strong>ВНИМАНИЕ!</strong> Если ваша группа в СДО весь день, то мониторьте это, так как эта информация <i>пока что</i> не берётся с сайта!", parse_mode="HTML")
        time.sleep(2)
        backend.PetroBot.changesByQuery(message, date_formatted)
        #DonutMurkup = telebot.types.InlineKeyboardMarkup();
        #DonutMurkup.add(telebot.types.InlineKeyboardButton(text='Поддержать проект❤️', url='https://yoomoney.ru/to/4100117765250849'))
        #bot.send_message(message.from_user.id, "Поддержите проект (от этого может зависеть его судьба)", parse_mode="HTML", reply_markup=DonutMurkup)
    except:
        bot.send_message(message.from_user.id,
                         "Что-то пошло не так, пожалуйста попробуйте позже.\n Возможно портал сейчас не доступен или сейчас еще нет расписания.", reply_markup=telebot.types.ReplyKeyboardRemove())


@bot.message_handler(commands=['subscribe'])
def subscribe_start(message):
    """Антифлуд """
    if message.from_user.id not in last_time:
        last_time[message.from_user.id] = time.time()
    else:
        if (time.time() - last_time[message.from_user.id]) * 1000 < 1500:
            return 0
        del last_time[message.from_user.id]
    if isUserSubscribedToBot(message) == False: 
        return False
    user = Subscribe().get_one_user_by_id(message.from_user.id)
    if user:
        Subscribe().delete_by_user_id(message.from_user.id)
        bot.send_message(message.from_user.id,
                         "Вы успешно отписаны от рассылки, чтобы подписаться снова используйте эту же команду - /subscribe")
        return 0
    else:
        bot.send_message(message.from_user.id,
                         "Чтобы подписаться на рассылку расписания, вам необходимо пройти процедуру выбора необходимого расписания. <strong>ВНИМАНИЕ</strong> расписание высылается на следующую неделю! Отправляется 1 раз в неделю в воскресенье 21:00.", parse_mode='HTML')
        backend.PetroBot.scheduleType(message)
        bot.register_next_step_handler(message, subscribe_schedule_type)


def subscribe_schedule_type(message):
    if message.text == "По номеру группы":
        # Вызов функции возвращающей список групп в виде клавиатуры для ввода
        bot.send_message(message.from_user.id,
                         parse.dateRasp, parse_mode="HTML")
        backend.PetroBot.groups(message)
        # Файл с расписанием по группе
        file = "raspisaniye.xlsx"
        bot.register_next_step_handler(
            message, subscribe_save_choice, file)
    elif message.text == "По ФИО преподавателя":
        # Вызов функции предлагающей пользователю ввести ФИО преподавателя
        bot.send_message(message.from_user.id,
                         parse.dateRasp, parse_mode="HTML")
        backend.PetroBot.prepodSelect(message)
        # Файл с расписанием по преподавателю
        file = "raspisaniyebyprepod.xlsx"
        bot.register_next_step_handler(
            message, subscribe_save_choice, file)
    elif message.text == "По номеру аудитории":
        # Вызов функции возвращающей список аудиторий в виде клавиатуры для ввода
        bot.send_message(message.from_user.id,
                         parse.dateRasp, parse_mode="HTML")
        backend.PetroBot.auditSelect(message)
        # Файл с расписанием по аудитории
        file = "raspisaniyebyaudit.xlsx"
        bot.register_next_step_handler(
            message, subscribe_save_choice, file)
    else:
        bot.send_message(message.from_user.id,
                         "Пожалуйста, введите верное значение, запустив функцию заново", reply_markup=telebot.types.ReplyKeyboardRemove())
        return 0


def subscribe_save_choice(message, file):
    try:
        backend.PetroBot.subscribeSaveChoice(message, file)
    except:
        bot.send_message(message.from_user.id,
                         "Не удалось сохранить выбор, пожалуйста попробуйте позже", reply_markup=telebot.types.ReplyKeyboardRemove())
        return 0


@bot.message_handler(commands=['send_something'])
def send_smth_start(message):
    """Антифлуд """
    if message.from_user.id not in last_time:
        last_time[message.from_user.id] = time.time()
    else:
        if (time.time() - last_time[message.from_user.id]) * 1000 < 1500:
            return 0
        del last_time[message.from_user.id]
    if message.from_user.id ==1459498902:
        bot.send_message('1459498902', 'Введи нужное сообщение')
        bot.register_next_step_handler(
            message, send_smth)
    else:
        return 0 

def send_smth(message):
    """Антифлуд """
    if message.from_user.id not in last_time:
        last_time[message.from_user.id] = time.time()
    else:
        if (time.time() - last_time[message.from_user.id]) * 1000 < 1500:
            return 0
        del last_time[message.from_user.id]
    if message.from_user.id ==1459498902:
        backend.PetroBot.sendSomethingToSubs(message.text)
        bot.send_message('1459498902', 'Рассылка закончена')
    else:
        return 0 

@bot.message_handler(commands=['pashalka'])
def pashalka(message):
    """Антифлуд """
    if message.from_user.id not in last_time:
        last_time[message.from_user.id] = time.time()
    else:
        if (time.time() - last_time[message.from_user.id]) * 1000 < 5000:
            return 0
        del last_time[message.from_user.id]

    if isUserSubscribedToBot(message) == False: 
        return False
    bot.send_message(message.from_user.id,
                         "Молодец! Ты нашел пасхалку! (=^-ω-^=)")
    #DonutMurkup = telebot.types.InlineKeyboardMarkup();
    #DonutMurkup.add(telebot.types.InlineKeyboardButton(text='Поддержать проект❤️', url='https://yoomoney.ru/to/4100117765250849'))
    #bot.send_message(message.from_user.id, "Поддержите проект (от этого может зависеть его судьба)", parse_mode="HTML", reply_markup=DonutMurkup)





if __name__ == '__main__':
    bot.infinity_polling()


# @server.route('/' + config_values['BOT_TOKEN'], methods=['POST'])
# def get_message():
#     json_string = request.get_data().decode('utf-8')
#     update = telebot.types.Update.de_json(json_string)
#     bot.process_new_updates([update])
#     return '!', 200

# @server.route('/'+'getPaymentInfo', methods=['POST'])
# def index():
#     response = request.get_data().decode('utf-8')
#     responseJson = json.loads(response)
#     successfulPayment(responseJson)
#     return '!', 200

# def successfulPayment(responseJson):
#     try:
#         secureUserId = (re.sub('<[^<]+?>', '', responseJson['nickname'])).replace(' ', '')
#         userId = int(secureUserId)
#     except:
#         logging.warning(f'\n\n Не удалось пропарсить никнейм {responseJson["nickname"]} в int \n\n')
#         bot.send_message(1459498902, f'\n\n Не удалось пропарсить никнейм {responseJson["nickname"]} в int \n\n')
#         return
#     userSubscribtion = BotSubscribtion().getOneUserById(userId)
#     if (not(userSubscribtion)):
#         BotSubscribtion().create(userId)
#     else:
#         #Если дата окончания подписки еще не настала, просто продляем подписку со дня конца, иначе с сегодняшнего дня
#         if userSubscribtion['expire_date'] > datetime.datetime.now():
#             BotSubscribtion().update(userId, userSubscribtion['expire_date'])
#         else:
#             BotSubscribtion().update(userId, datetime.datetime.now())        
#     bot.send_message(userId, 'Спасибо за подписку!!!❤❤❤')


# @server.route('/')
# def webhook():
#     bot.remove_webhook()
#     bot.set_webhook(url=config_values['https://bot.imsokserver70.keenetic.link/'] +
#                     config_values['BOT_TOKEN'])
#     return '!', 200

# @server.route('/'+'getStatusInfo')
# def statusInfo():
#     return 'ok', 200

# @server.route('/'+'getGroups')
# def getGroups():
#     #pprint.pprint(PetroBot.all_days_api('10-29','raspisaniye.xlsx'))
#     resp = make_response(backend.PetroBot.groups_api())
#     resp.headers['Access-Control-Allow-Origin'] = '*'
#     return resp

# @server.route('/'+'getByGroup')
# def getAllByGroup():
#     #pprint.pprint(PetroBot.all_days_api('10-29','raspisaniye.xlsx'))
#     group = request.args.get('group')
#     allschedule = backend.PetroBot.two_days_api(group)
#     resp = make_response(allschedule)
#     resp.headers['Access-Control-Allow-Origin'] = '*'
#     return resp


# def runHttps():
#     server.run(host="0.0.0.0", port=443)

# def runHttp():
#     server.run(host="0.0.0.0", port=12100)

# if __name__ == '__main__':
#     y = threading.Thread(target=runHttp)
#     x = threading.Thread(target=runHttps)
#     y.start()
#     time.sleep(0.5)
#     x.start()
