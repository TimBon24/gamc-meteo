import hashlib
import json
import os
import re
from imap_tools import MailBox
import requests
from requests.auth import HTTPBasicAuth

from dotenv import load_dotenv
from fpdf import FPDF

from apps import send_mail
from charts import get_sigwx_chart

load_dotenv()
EMAIL_WORK = os.getenv('EMAIL_WORK')
EMAIL_ALERT = os.getenv('EMAIL_ALERT').split()
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD').strip('"')
EMAIL_SERVER = os.getenv('EMAIL_SERVER')
EMAIL_RECIPIENT = os.getenv('EMAIL_RECIPIENT').split()
API_LOGIN = os.getenv('API_LOGIN')
API_PASSWORD = os.getenv('API_PASSWORD')
API_URL = os.getenv('API_URL')
PROXY = os.getenv('PROXY')
FONTS_PATH = '/home/tbondarenko/media/fonts/' #путь к шрифтам
HOME_BASE_DIR = '/home/tbondarenko/media/files/' #путь к пустой папке для хранения файлов


def Get_request_param(cfp_file, sign):
    result = {}
    with open(cfp_file, 'rb') as f:
        for line in f:
            decoded_line = line.decode(errors='ignore')
            if 'APT:' in decoded_line:
                items = decoded_line.split(',')
                result['AP'] = [
                    item.replace('             APT: ', '').replace(' ', '').replace('\r\n', '')
                    for item in items
                ]
            elif 'FIR:' in decoded_line:
                items = decoded_line.split(',')
                result['FIR'] = [
                    item.replace('             FIR: ', '').replace(' ', '').replace('\r\n', '')
                    for item in items
                ]
            elif 'ETD:' in decoded_line:
                items = decoded_line.split(',')
                result['ETD'] = items[0].replace('             ETD: ', '').replace('\r\n', '')
            elif 'ETA:' in decoded_line:
                items = decoded_line.split(',')
                result['ETA'] = items[0].replace('             ETA: ', '').replace('\r\n', '')
    
    return result.get(sign)


def Get_subject(cfp_file):
    with open(cfp_file, 'rb') as f:
        subject = 'no subject'
        for line in f:
            if 'ID:' in line.decode(errors='ignore'):
                subject_temp = line.decode(errors='ignore').split(':')
                subject = subject_temp[1]
                break
    return subject


def main():
    with MailBox(EMAIL_SERVER).login(
        EMAIL_WORK, EMAIL_PASSWORD
    ) as mailbox:
        for msg in mailbox.fetch():
            for att in msg.attachments:
                name = att.filename
                cfp_url = f'{HOME_BASE_DIR}{name}'
                f = open(cfp_url, 'wb')
                f.write(att.payload)
                f.close()

                airports = Get_request_param(cfp_url, 'AP')
                firs = Get_request_param(cfp_url, 'FIR')
                etd = Get_request_param(cfp_url, 'ETD')
                eta = Get_request_param(cfp_url, 'ETA')

                subject = Get_subject(cfp_url)

                Weather_url = f'{HOME_BASE_DIR}meteo/Meteo.pdf'
                Sigmet_url = f'{HOME_BASE_DIR}meteo/Sigmet.pdf'

                try:
                    Get_weather_API(airports)
                    Get_sigmet(firs)
                    send_mail(
                        EMAIL_WORK,
                        EMAIL_RECIPIENT,
                        f'METEO {subject}',
                        'METEO INFORMATION',
                        files=[Weather_url, Sigmet_url]
                    )
                except Exception:
                    pass

                try:
                    SigWX_charts_url = get_sigwx_chart(subject, etd, eta)
                    send_mail(
                        EMAIL_WORK,
                        EMAIL_RECIPIENT,
                        f'CHARTS {subject}',
                        'METEO CHARTS',
                        files=SigWX_charts_url
                    )
                except Exception:
                    pass
                    
            mailbox.delete(msg.uid)
    print('Ready')


def Get_weather_API(airports:list):
    login = API_LOGIN
    login64 = login.encode('utf-8')

    pw = API_PASSWORD
    pw64 = hashlib.md5(pw.encode()).hexdigest()
    pw64 = pw64.encode('utf-8')

    alternate_list = ''
    for i in airports[2:]:
        alternate_list = alternate_list + i + '+' + i + '2' + '+' + i + '3' + '+'
    alternate_list = alternate_list[:-1]

    dep_weather = json_request(f'{API_URL}opmet', login64, pw64, airports[0])
    arr_weather = json_request(f'{API_URL}opmet', login64, pw64, airports[1])
    alt_weather = ''
    for i in airports[2:]:
        if alt_weather == '':
            alt_weather = json_request(f'{API_URL}opmet', login64, pw64, i)
        else:
            temp = json_request(f'{API_URL}opmet', login64, pw64, i)
            alt_weather.update(temp)

    create_pdf(dep_weather, arr_weather, alt_weather)

    return airports


def json_request(url, login, pw, airport):
    proxies = {
        'http': PROXY,
    }
    metar_temp_url = f'{HOME_BASE_DIR}meteo/m_temp.json'
    taf_temp_url = f'{HOME_BASE_DIR}meteo/t_temp.json'

    request = {
        "dep": f'{airport}+{airport}2+{airport}3',
        "METAR": True,
        "TAF": False
    }

    response = requests.post(
        url,
        auth=HTTPBasicAuth(login, pw),
        json=request,
        proxies=proxies
    )

    with open(metar_temp_url, 'w') as f:
        f.write(response.text)

    with open(metar_temp_url, 'r') as j:
        json_data_M = json.load(j)
        result_M = json_data_M['message']
        result_M = re.sub(r'(<HDR>).*(</HDR>)', '', result_M)
        result_M = re.sub(r'.*(NIL=)', 'sep', result_M)
        result_M = result_M.replace('\u003d\r\nsep', '').replace(
            '\r\nsep', '').replace('sep', '')

    result_M = result_M.split('\r\n')
    i = 0
    p = 0
    start_del = 0
    end_del = 0
    for item in result_M:
        i += 1
        if 'SIGMET' in item:
            start_del = i
            break
    for item in result_M:
        p += 1
        if 'METAR' in item and start_del != 0 and p > start_del:
            end_del = p
            break

    del result_M[start_del - 1:end_del - 1]

    k = 0
    for item in result_M:
        k += 1
        if 'SWX ADVISORY' in item:
            start_del = k

    del result_M[start_del - 1:]

    result_M = '\n'.join(result_M).replace('\n    ', ' ')
    if result_M == '':
        send_mail(
            EMAIL_WORK,
            EMAIL_ALERT,
            f'ОТСУТСВУЕТ METAR ДЛЯ АЭРОПОРТА {airport}',
            f'''НЕ УДАЛОСЬ ЗАПРОСИТЬ METAR ДЛЯ {airport}, ИСПОЛЬЗУЙ ДРУГОЙ
         ИСТОЧНИК ДАННЫХ И ДОБАВЬ В БРИФИНГ'''
        )

    request2 = {
        "dep": f'{airport}+{airport}2+{airport}3',
        "METAR": False,
        "TAF": True
    }

    response2 = requests.post(
        url,
        auth=HTTPBasicAuth(login, pw),
        json=request2,
        proxies=proxies
    )

    with open(taf_temp_url, 'w') as f:
        f.write(response2.text)

    with open(taf_temp_url, 'r') as j:
        json_data_T = json.load(j)
        result_T = json_data_T['message']
        result_T = re.sub(r'(<HDR>).*(</HDR>)', '', result_T)
        result_T = re.sub(r'.*(NIL=)', 'sep', result_T)
        result_T = result_T.replace('\u003d\r\nsep', '').replace(
            '\r\nsep', '').replace('sep', '').replace(' FM', '\rFM')

    result_T = result_T.split('\r\n')
    i = 0
    start_del = 0
    end_del = 0
    for item in result_T:
        i += 1
        if 'SIGMET' in item:
            start_del = i
            break
    for item in result_T:
        p += 1
        if 'TAF' in item and start_del != 0 and p > start_del:
            end_del = p
            break

    del result_T[start_del - 1:end_del - 1]

    k = 0
    for item in result_T:
        k += 1
        if 'SWX ADVISORY' in item:
            start_del = k

    del result_T[start_del - 1:]

    result_T = '\n'.join(result_T).replace('\n    ', ' ')
    if result_T == '':
        send_mail(
            EMAIL_WORK,
            EMAIL_ALERT,
            f'ОТСУТСВУЕТ TAF ДЛЯ АЭРОПОРТА {airport}',
            f'''НЕ УДАЛОСЬ ЗАПРОСИТЬ TAF ДЛЯ {airport}, ИСПОЛЬЗУЙ ДРУГОЙ
         ИСТОЧНИК ДАННЫХ И ДОБАВЬ В БРИФИНГ'''
        )

    result = {
        f'metar{airport}': result_M.replace('\n', ''),
        f'taf{airport}': result_T.replace('\n', '')
    }

    return result


def create_pdf(dep, arr, alt):

    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_font(
        'Tahoma', '', f'{FONTS_PATH}Tahoma.ttf', uni=True)
    pdf.add_font(
        'Tahoma', 'B', f'{FONTS_PATH}Tahoma-Bold.ttf', uni=True)
    pdf.add_page()

    # Departure
    pdf.set_font("Tahoma", size=8, style='B')
    pdf.set_fill_color(255, 250, 205)
    pdf.set_draw_color(255, 222, 205)
    result_keys = list(dep.keys())
    pdf.cell(
        0, 3.5, txt=result_keys[0][5:], border=1, ln=1, align="L", fill=True)
    pdf.ln(1)
    for key in dep:
        if 'metar' in key:
            metars = dep[key].split('METAR')
        if 'taf' in key:
            tafs = dep[key].split('TAF')
    pdf.set_fill_color(240, 255, 240)
    pdf.set_draw_color(204, 204, 153)
    pdf.set_font("Tahoma", size=8)
    for metar in metars:
        if metar != '\n ' and metar != ' ':
            if metar == '':
                pdf.multi_cell(
                    0, 3.5, txt='METAR NOT AVAILABLE',
                    border=1, fill=True, align='L'
                )
            else:
                pdf.multi_cell(
                    0, 3.5, txt='METAR ' + metar,
                    border=1, fill=True, align='L'
                )
                pdf.ln(1)
    pdf.set_draw_color(242, 153, 42)
    for taf in tafs:
        if taf != '\n ' and taf != ' ':
            if taf == '':
                pdf.multi_cell(
                    0, 3.5, txt='TAF  NOT AVAILABLE',
                    border=1, fill=False, align='L'
                )
            else:
                pdf.multi_cell(
                    0, 3.5, txt='TAF ' + taf,
                    border=1, fill=False, align='L'
                )
                pdf.ln(1)
    # Arrival
    pdf.set_font("Tahoma", size=8, style='B')
    pdf.set_fill_color(255, 250, 205)
    pdf.set_draw_color(255, 222, 205)
    result_keys = list(arr.keys())
    pdf.cell(
        0, 3.5, txt=result_keys[0][5:], border=1, ln=1, align="L", fill=True)
    pdf.ln(1)
    for key in arr:
        if 'metar' in key:
            metars = arr[key].split('METAR')
        if 'taf' in key:
            tafs = arr[key].split('TAF')
    pdf.set_fill_color(240, 255, 240)
    pdf.set_draw_color(204, 204, 153)
    pdf.set_font("Tahoma", size=8)
    for metar in metars:
        if metar != '\n ' and metar != ' ':
            if metar == '':
                pdf.multi_cell(
                    0, 3.5, txt='METAR NOT AVAILABLE',
                    border=1, fill=True, align='L'
                )
            else:
                pdf.multi_cell(
                    0, 3.5, txt='METAR ' + metar,
                    border=1, fill=True, align='L'
                )
                pdf.ln(1)
    pdf.set_draw_color(242, 153, 42)
    for taf in tafs:
        if taf != '\n ' and taf != ' ':
            if taf == '':
                pdf.multi_cell(
                    0, 3.5, txt='TAF  NOT AVAILABLE',
                    border=1, fill=False, align='L'
                )
            else:
                pdf.multi_cell(
                    0, 3.5, txt='TAF ' + taf,
                    border=1, fill=False, align='L'
                )
                pdf.ln(1)

    # Alternates
    for key in alt:
        if 'metar' in key:
            pdf.set_fill_color(255, 250, 205)
            pdf.set_draw_color(255, 222, 205)
            pdf.set_font("Tahoma", size=8, style='B')
            pdf.cell(
                0, 3.5, txt=key[5:], border=1, ln=1, align="L", fill=True)
            pdf.ln(1)
            metars = alt[key].split('METAR')
            pdf.set_fill_color(240, 255, 240)
            pdf.set_draw_color(204, 204, 153)
            pdf.set_font("Tahoma", size=8)
            for metar in metars:
                if metar != '\n ' and metar != ' ':
                    if metar == '':
                        pdf.multi_cell(
                            0, 3.5, txt='METAR NOT AVAILABLE',
                            border=1, fill=True, align='L'
                        )
                    else:
                        pdf.multi_cell(
                            0, 3.5, txt='METAR ' + metar,
                            border=1, fill=True, align='L'
                        )
                        pdf.ln(1)
        if 'taf' in key:
            tafs = alt[key].split('TAF')
            pdf.set_draw_color(242, 153, 42)
            pdf.set_font("Tahoma", size=8)
            for taf in tafs:
                if taf != '\n ' and taf != ' ':
                    if taf == '':
                        pdf.multi_cell(
                            0, 3.5, txt='TAF  NOT AVAILABLE',
                            border=1, fill=False, align='L'
                        )
                    else:
                        pdf.multi_cell(
                            0, 3.5, txt='TAF ' + taf,
                            border=1, fill=False, align='L'
                        )
                        pdf.ln(1)

    output_url = f'{HOME_BASE_DIR}meteo/Meteo.pdf'
    pdf.output(output_url)

    return output_url


def Get_sigmet(firs):
    proxies = {
        'http': PROXY,
    }
    sigmet_temp_url = f'{HOME_BASE_DIR}meteo/s_temp.json'
    login = API_LOGIN
    login64 = login.encode('utf-8')

    pw = API_PASSWORD
    pw64 = hashlib.md5(pw.encode()).hexdigest()
    pw64 = pw64.encode('utf-8')

    request = {
        "fir": firs
    }

    response = requests.post(
        f'{API_URL}sigmet',
        auth=HTTPBasicAuth(login64, pw64),
        json=request,
        proxies=proxies
    )

    with open(sigmet_temp_url, 'w') as f:
        f.write(response.text)

    with open(sigmet_temp_url, 'r') as j:
        json_data_M = json.load(j)
        result_M = json_data_M['message']
        result_M = re.sub(r'(<HDR>).*(</HDR>)', '', result_M)
        result_M = re.sub(r'.*(NIL=)', '', result_M)

    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_font(
        'Tahoma', '', f'{FONTS_PATH}Tahoma.ttf', uni=True)
    pdf.add_font(
        'Tahoma', 'B', f'{FONTS_PATH}Tahoma-Bold.ttf', uni=True)
    pdf.add_page()
    pdf.set_draw_color(204, 204, 153)
    pdf.set_font("Tahoma", size=8)
    pdf.multi_cell(
        0, 3.5, txt=result_M, border=1, align='L'
    )

    output_url = f'{HOME_BASE_DIR}meteo/Sigmet.pdf'
    pdf.output(output_url)


if __name__ == '__main__':
    main()