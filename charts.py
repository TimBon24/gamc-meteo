import os
from datetime import datetime, date, time, timedelta

from dotenv import load_dotenv
import requests
from requests.auth import HTTPBasicAuth

from apps import send_mail

load_dotenv()
PROXY = os.getenv('PROXY')
GAMC_LOGIN = os.getenv('GAMC_LOGIN')
GAMC_PASSWORD = os.getenv('GAMC_PASSWORD')
MAP_BASE_DIR = 'http://meteoinfo.gamc.ru/data/maps/'
HOME_BASE_DIR = '/home/tbondarenko/media/files/meteo/' #путь к пустой папке для хранения карт

def nearest(items, pivot):
    return min(items, key=lambda x: abs(x - pivot))


def get_sigwx_chart(id, etd, eta):
    # Input values for testing
    # id = '07.12.22 UUDD-URSS'
    # etd = '04:35'
    # eta = '07.12.2022 08:35'

    # Время и дата вылета
    id = id.split()
    id = id[1].split('.')
    day = int(id[0])
    month = int(id[1])
    year = 2000 + int(id[2])
    d = date(year, month, day)
    etd = etd.split(':')
    hour = int(etd[0])
    minutes = int(etd[1])
    t = time(hour, minutes)
    fulldata_etd = datetime.combine(d, t)

    # Время и дата прилёта
    eta = eta.split()
    date_eta = eta[0].split('.')
    d = date(int(date_eta[2]), int(date_eta[1]), int(date_eta[0]))
    time_eta = eta[1].split(':')
    t = time(int(time_eta[0]), int(time_eta[1]))
    fulldata_eta = datetime.combine(d, t)

    list_charts = [
        datetime(year, month, day, 0, 0),
        datetime(year, month, day, 6, 0),
        datetime(year, month, day, 12, 0),
        datetime(year, month, day, 18, 0),
        datetime(year, month, day, 0, 0) + timedelta(days=1),
    ]

    need_chart = nearest(list_charts, fulldata_etd)
    need_chart2 = nearest(list_charts, fulldata_eta)
    map_ident = datetime.strftime(need_chart - timedelta(days=1), '%d%H%M')
    map_ident2 = datetime.strftime(need_chart2 - timedelta(days=1), '%d%H%M')

    map_name = datetime.strftime(need_chart, '%d%H%M')
    map_name2 = datetime.strftime(need_chart2, '%d%H%M')

    proxies = {
        'http': PROXY,
        'https': PROXY,
    }
    auth = HTTPBasicAuth(GAMC_LOGIN, GAMC_PASSWORD)
    chart_types = [
        ('PGRE93RUMS', 'SIGWX'),
        ('PWCE30RUMS', 'WindFL300'),
        ('PWCE25RUMS', 'WindFL340'),
        ('PWCE20RUMS', 'WindFL390'),       
        ]
    if map_ident == map_ident2:
        result = []  
        for map_id, chart_name in chart_types:
            url = f'{HOME_BASE_DIR}{chart_name}_{map_name}.png'
            with open(url, 'wb') as file:
                query_url = (
                    f'{MAP_BASE_DIR}{map_id}_{map_ident}.png'
                )
                chart = requests.get(query_url, proxies=proxies, auth=auth)
                file.write(chart.content)
                sz = os.path.getsize(url)
                if sz > 10240:
                    result.append(url)
        return result
    else:
        result = []
        for map_id, chart_name in chart_types:
            url = f'{HOME_BASE_DIR}{chart_name}_{map_name}.png'
            url2 = f'{HOME_BASE_DIR}{chart_name}_{map_name2}.png'
            with open(url, 'wb') as file:
                query_url = (
                    f'{MAP_BASE_DIR}{map_id}_{map_ident}.png'
                )
                chart = requests.get(query_url, proxies=proxies, auth=auth)
                file.write(chart.content)
                sz = os.path.getsize(url)
                if sz > 10240:
                    result.append(url)
            with open(url2, 'wb') as file:
                query_url = (
                    f'{MAP_BASE_DIR}{map_id}_{map_ident2}.png'
                )
                chart = requests.get(query_url, proxies=proxies, auth=auth)
                file.write(chart.content)
                sz = os.path.getsize(url2)
                if sz > 10240:
                    result.append(url2)
        return result