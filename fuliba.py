# -*- coding:utf-8 -*-

import requests
import re
import yaml
import os
from lxml import etree

headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Cache-Control': 'max-age=0',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
}

need_to_update_url_error = "访问登录页失败"


def check_and_prepare_config_file() -> None:
    config_path = 'fuliba.yaml'
    if not os.path.exists(config_path):
        print("配置文件fuliba.yaml未找到，将尝试创建默认配置文件...")
        # 定义默认配置内容
        default_config = """
# 发布页地址
base_url: http://www.lao4g.com
# 当前bbs地址
current_bbs_url: https://www.wnflb2023.com
"""
        # 尝试写入默认配置内容
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(default_config)
            print("默认配置文件已创建。")
        except IOError as e:
            print(f"创建配置文件时发生错误: {e}")
            exit(1)  # 如果无法创建文件，则终止程序


def get_new_url(url: str) -> str:
    print("更新论坛地址")
    response = requests.get(url)
    if response.status_code == 200:
        response.encoding = 'UTF-16LE'
        res = etree.HTML(response.content)
        bbs_url = res.xpath(
            '/html/body/div[2]/div[3]/div/div[4]/div[1]/div/div[11]/div[2]/div[2]/div/a/@href')[0].strip()
        print("更新成功，当前论坛地址为%s" % bbs_url)
        return bbs_url
    else:
        print('Please check the network!')


def get_formhash(url: str, session: requests.Session) -> str:
    """访问登录页面并获取formhash"""
    login_page = session.get(url)
    res = etree.HTML(login_page.content)
    formhash_match = res.xpath(
        '/html/body/div[6]/div/div[1]/form/div/div/input[1]/@value')
    if formhash_match:
        return formhash_match[0]
    else:
        raise ValueError(need_to_update_url_error)


def checkin(url: str) -> None:
    print("自动登录")
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
    resp = session.post(login_url, data=data, headers=headers)
    if resp.status_code == 200:
        print("登录成功")
    else:
        return ValueError("登录失败,请检查账号密码")
    user_info = session.get(url + '/forum.php?mobile=no').text
    current_money = re.search(
        r'<a.*? id="extcreditmenu".*?>(.*?)</a>', user_info).group(1)
    if current_money:
        print("当前积分:", current_money)
    else:
        raise ValueError("无法获取当前积分")

def run() -> None:
    check_and_prepare_config_file()
    try:
        with open('fuliba.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            base_url = config['base_url']
            current_bbs_url = config['current_bbs_url']
    except yaml.scanner.ScannerError as e:
        print(f"无法读取配置文件!请检查文件格式")
        return

    try:
        print("当前bbs_url为%s" % current_bbs_url)
        checkin(current_bbs_url)
    except ValueError as e:
        print(f"登录失败,原因为:{e}")
        if str(e) == need_to_update_url_error:
            new_bbs_url = get_new_url(base_url)
            config['current_bbs_url'] = new_bbs_url
            with open('fuliba.yaml', 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True)
            # 再次尝试登录
            checkin(new_bbs_url)
        return

if __name__ == '__main__':
    run()
