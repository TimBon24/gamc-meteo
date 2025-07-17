![YAML](https://img.shields.io/badge/YAML-2.0-blue?logo=yaml&logoColor=white)

## Описание проекта

Автоматизированная система обработки метеорологической информации для планирования полетов.
Проверяет почтовый ящик, забирает *txt файл во вложении, удаляет письмо. При каждом запуске- одно письмо.
Получает данные METAR, TAF и SIGMET для указанных аэропортов и погодные карты по РФ,
формирует отчеты в PDF и отправляет их по электронной почте.

## Необходимые переменные окружения
```bash
EMAIL_WORK= <почтовый ящик для получения CFP и отправки PDF>
EMAIL_PASSWORD= <пароль от почтового ящика>
EMAIL_SERVER= <почтовый сервер>
EMAIL_PORT= <порт почтового сервера>
EMAIL_ALERT= <список почтовых адресов для отправки предупреждений о сбое через пробел>
EMAIL_RECIPIENT= <список получателей метео через пробел>
API_LOGIN= <логин от ГАМЦ API>
API_PASSWORD= <пароль от ГАМЦ API>
API_URL= <точка доступа к ГАМЦ API/тоннель>
PROXY= <внутренний прокси>
GAMC_LOGIN= <логин от meteoinfo.gamc.ru>
GAMC_PASSWORD= <пароль от meteoinfo.gamc.ru>
```
## Необходимый блок в *txt формате CFP
```bash
             APT: UUDD, URSS, URML, URMM, URWA
             FIR: UUWV, UWWW, URRV
             
             ID: AFL1033 15.07.25 UUDD-URSS
             ETD: 15:00
             ETA: 15.07.2025 18:28
```

## Установка
```bash
git clone https://github.com/TimBon24/gamc-meteo.git
cd gamc-meteo
#создание файла c переменными окружения
nano .env
pip install -r requirements.txt
#создание директории для файлов
mkdir -p media/files/meteo/
#виртуальное окружение
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt 
```
## Запуск
```bash
В файле main.py изменить HOME_BASE_DIR, FONTS_PATH
В файле charts.py изменить HOME_BASE_DIR
python main.py
```

## Запуск через crontab для постоянной проверки почтового ящика
```bash
crontab -e 
* * * * * /путь/до/вашего/проекта/venv/bin/python /путь/до/вашего/проекта/main.py
```

## Автор
Бондаренко Тимофей https://github.com/TimBon24/
