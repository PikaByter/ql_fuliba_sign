# !/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
new Env('fuliba签到');
0 3 * * * fuliba.py
'''
import requests
import re
import yaml
import os
import logging
from lxml import etree

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

NEED_TO_UPDATE_URL_ERROR = "访问登录页失败"
HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Cache-Control': 'max-age=0',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
}
CONFIG_PATH = 'fuliba.yaml'

def check_and_prepare_config_file() -> None:
    if not os.path.exists(CONFIG_PATH):
        logging.info("配置文件fuliba.yaml未找到，将尝试创建默认配置文件...")
        # 定义默认配置内容
        default_config = """
# 发布页地址
base_url: http://www.lao4g.com
# 当前bbs地址
current_bbs_url: https://www.wnflb2023.com
"""
        # 尝试写入默认配置内容
        try:
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                f.write(default_config)
            logging.info("默认配置文件已创建")
        except IOError as e:
            raise e

def get_new_url(url: str) -> str:
    logging.info("更新论坛地址")
    response = requests.get(url)
    if response.status_code == 200:
        response.encoding = 'UTF-16LE'
        res = etree.HTML(response.content)
        bbs_url = res.xpath(
            '/html/body/div[2]/div[3]/div/div[4]/div[1]/div/div[11]/div[2]/div[2]/div/a/@href')[0].strip()
        logging.info("更新成功，当前论坛地址为%s" % bbs_url)
        return bbs_url
    else:
        raise ValueError("更新论坛地址出错!")


def get_formhash(url: str, session: requests.Session) -> str:
    """访问登录页面并获取formhash"""
    login_page = session.get(url)
    res = etree.HTML(login_page.content)
    formhash_match = res.xpath(
        '/html/body/div[6]/div/div[1]/form/div/div/input[1]/@value')
    if formhash_match:
        return formhash_match[0]
    else:
        raise ValueError(NEED_TO_UPDATE_URL_ERROR)


def checkin(url: str) -> str:
    logging.info("自动登录")
    session = requests.session()
    formhash = get_formhash(url, session)
    data = {
        'username': os.getenv('FULIBA_USERNAME'),
        'password': os.getenv('FULIBA_PASSWORD'),
        'formhash': formhash,  # 使用获取到的formhash
        'quickforward': 'yes',
        'handlekey': 'ls'
    }
    login_url = url + '/member.php?mod=logging&action=login&loginsubmit=yes&infloat=yes&lssubmit=yes&inajax=1'
    resp = session.post(login_url, data=data, headers=HEADERS)
    if resp.status_code != 200:
        return ValueError("登录失败,请检查账号密码")
    user_info = session.get(url + '/forum.php?mobile=no').text
    current_money = re.search(
        r'<a.*? id="extcreditmenu".*?>(.*?)</a>', user_info).group(1)
    if current_money:
        return "签到成功！当前积分为: %s" % current_money
    else:
        raise ValueError("无法获取当前积分")

def notify(msg: str) -> None:
    if os.getenv("FULIBA_SEND_MSG") == "true":
        try:
            import notify
        except Exception as e:
            print(f"导入通知模块失败，原因为: {e}")
            return
        notify.send("fuliba每日签到", msg)


def log_and_notify(ifsuccess: bool, result: str) -> None:
    if ifsuccess:
        logging.info(result)
    else:
        logging.error(result)
    notify(result)


def run() -> None:
    try:
        check_and_prepare_config_file()
    except Exception as e:
        log_and_notify(ifsuccess=False, result=f"创建默认配置文件错误，原因为：{e}")

    try:
        with open('fuliba.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            base_url = config['base_url']
            current_bbs_url = config['current_bbs_url']
            logging.info("当前bbs_url为%s" % current_bbs_url)
    except yaml.scanner.ScannerError as e:
        log_and_notify(ifsuccess=False, result="配置文件格式错误!请检查文件格式")

    try:
        log_and_notify(ifsuccess=True, result=checkin(current_bbs_url))
    except ValueError as e:
        RESULT=f"登录失败,原因为:{e}"
        logging.error(RESULT)
        if str(e) == NEED_TO_UPDATE_URL_ERROR:
            new_bbs_url = get_new_url(base_url)
            config['current_bbs_url'] = new_bbs_url
            with open('fuliba.yaml', 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True)
            # 再次尝试登录
            try:
                RESULT = checkin(new_bbs_url)
                log_and_notify(ifsuccess=True, result=RESULT)
            except ValueError as e:
                RESULT=f"登录失败,原因为:{e}"
                log_and_notify(ifsuccess=False, result=RESULT)
        else:
            notify(RESULT)


if __name__ == '__main__':
    run()
