# coding=utf-8
from urlparse import urlparse, parse_qs
from bs4 import BeautifulSoup

import requests
import configparser
import table2csv

LOGIN_URL = 'https://ww2.capsim.com/login/logincheck.cfm'
DASHBOARD_URL = 'http://ww2.capsim.com/menuApp/studentMain.cfm?simid=%s'
APP_LOGIN_URL = 'http://ww3.capsim.com/login/loginCode.cfm?studentkey=%s&token=%s'
COURIER_URL = 'http://ww3.capsim.com/cgi-bin/ShowCourier.cfm?round=%s&simid=%s'

CONFIG_FILE = 'config.ini'
CONFIG_SECTION = 'DEFAULT'

FIRST_PASS_OUTPUT_FILE = 'output_first_pass.csv'
SECOND_PASS_OUTPUT_FILE = 'output_second_pass.csv'

# Read config
config = configparser.ConfigParser()
config.read(CONFIG_FILE)

sim_id = config[CONFIG_SECTION]['sim_id']
student_key = config[CONFIG_SECTION]['student_key']
username = config[CONFIG_SECTION]['username']
password = config[CONFIG_SECTION]['password']
try:
    proxy = config[CONFIG_SECTION]['proxy']
except KeyError:
    proxy = None

# Proxy settings
proxies = None if proxy is None else {
    'http': 'http://%s' % proxy,
    'https': 'https://%s' % proxy,
}


def download_courier(round_number, sim_id, student_key, username, password, proxy):
    # Persistent cookie jar
    with requests.Session() as s:
        # Login
        payload = {
            'username': username,
            'password': password
        }
        global_login = s.post(
            LOGIN_URL,
            data=payload,
            proxies=proxies,
            allow_redirects=False
        )

        dashboard_redirect = s.get(
            DASHBOARD_URL % sim_id,
            proxies=proxies,
            allow_redirects=False
        )

        token_url = dashboard_redirect.headers.get('location')
        parsed_url = urlparse(token_url)
        query = parse_qs(parsed_url.query)
        token = query['token'][0]

        app_login = s.post(
            APP_LOGIN_URL % (student_key, token),
            data=payload,
            proxies=proxies,
            allow_redirects=False
        )

        # Fetch courier
        courier_response = s.get(
            COURIER_URL % (round_number, sim_id),
            proxies=proxies,
            allow_redirects=False
        )

        html = courier_response.content
        soup = BeautifulSoup(html, features="html.parser")

        tables = table2csv.find_all_tables(soup)

        return tables


def write_first_pass_csv(tables):
    with open(FIRST_PASS_OUTPUT_FILE, 'wb') as csv_file:
        csv_file.write('')
    with open(FIRST_PASS_OUTPUT_FILE, 'a') as csv_file:
        for table in tables:
            try:
                df = table2csv.to_dataframe(table)
                df.dropna(how='all', axis=1)
                df.to_csv(csv_file, sep=',', index=False, encoding='utf-8')
            except AttributeError:
                pass


def write_second_pass_csv():
    with open(SECOND_PASS_OUTPUT_FILE, 'wb') as output_csv_file:
        with open(FIRST_PASS_OUTPUT_FILE, 'rb') as input_csv_file:
            for line in input_csv_file.readlines():
                if not line.startswith('CAPSTONE®') and \
                        not line.startswith('0') and \
                        not line.startswith('Page') and \
                        len(line) > 1:
                    output_csv_file.write(line)


tables = download_courier(0, sim_id, student_key, username, password, proxy)
write_first_pass_csv(tables)
write_second_pass_csv()
