import requests
import re
import os
import time
import logging
from urllib.parse import urljoin
from fake_useragent import UserAgent
from multiprocessing import Pool
logging.captureWarnings(True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# RANK_URL='https://www.pixiv.net/ranking.php' #今日排行榜
RANK_URL = 'https://www.pixiv.net/ranking.php?mode=daily_r18'  # 今日排行榜
BASE_URL = "https://www.pixiv.net/"  # 主页url
headers = {
    'user-agent': UserAgent().random,  # 未知原因用下面那个就会出问题
    # 'user-agent':'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36',
    'accept-language': 'zh-CN,zh;q=0.9',
    'referer': RANK_URL,
    # 由于pixiv设置了图片防盗链，故需请求头添加Referer，作用为告诉服务器【本次访问通过主页发起】，防止访问被拒绝
    'Cookie': 'first_visit_datetime_pc=2022-12-28+20%3A39%3A44; yuid_b=KShCQTE; p_ab_id=9; p_ab_id_2=2; p_ab_d_id=44044046; _fbp=fb.1.1672227586548.756303350; _im_vid=01GNC8G1S7PM4TDN0S4FWX4NH1; privacy_policy_agreement=5; privacy_policy_notification=0; a_type=0; b_type=1; adr_id=GtkcsQXhoeJmr8yWnkhrlsfAmDGyiOO9IETH7HwZZMyHMSDq; login_ever=yes; PHPSESSID=17255407_pJe3uT5CbqfpxiYg46omezBvwDJhaAiD; c_type=20; _im_uid.3929=i.LtnelIKXScCYpWMB2FgjiA; _ga_MZ1NL4PHH0=GS1.1.1682871015.3.1.1682871062.0.0.0; __utmv=235335808.|2=login%20ever=yes=1^3=plan=premium=1^5=gender=male=1^6=user_id=17255407=1^9=p_ab_id=9=1^10=p_ab_id_2=2=1^11=lang=zh=1; b-user-id=c230912d-a33b-14da-db6b-5b052d243c43; __utmz=235335808.1685720249.125.20.utmcsr=google|utmccn=(organic)|utmcmd=organic|utmctr=(not%20provided); _gcl_au=1.1.423243483.1685723202; _pubcid=20a08383-b991-4cb3-af72-c8632b5f59e8; __gads=ID=6b29979b8cff24b1:T=1679221868:RT=1685888986:S=ALNI_MbirPfvYyoIYvstlCcYFs3zRqdN_A; __gpi=UID=00000a2d93b33b28:T=1679221868:RT=1685888986:S=ALNI_MbsN_i-Y_usynP_GBMW9LICcPreXw; cto_bidid=pw4hsF9yWDJ6R1ZLZlRBJTJCSUt3SFRzOHM1YzJDJTJGRGVjR1hxY21NSVpjeXZLUlVpJTJCV2dKemJuWHlycDN4NkR4d01pUFpVUmJ2Q3NKcm5SRSUyQnFnS095Uk5ReG9leFY3TlpuNjRQUUY1T3JaNTh2QmM0JTNE; _ga_ZQEKG3EF2C=GS1.1.1685888985.3.0.1685889081.60.0.0; _gid=GA1.2.1157161106.1686227966; QSI_S_ZN_5hF4My7Ad6VNNAi=v:100:0; __utmc=235335808; __utma=235335808.1098950109.1672227586.1686397254.1686404627.135; howto_recent_view_history=108823710; __utmt=1; tag_view_ranking=0xsDLqCEW6~_EOd7bsGyl~ziiAzr_h04~5oPIfUbtd6~3mvlXxwzlR~_hSAdpN9rx~zIv0cf5VVk~Lt-oEicbBr~Ie2c51_4Sp~KN7uxuR89w~azESOjmQSV~RTJMXD26Ak~M0_oya2NVz~TJ2ipOtAVO~ZvexGYezEm~kffGOewQdf~Yv2C9XifX_~NHr56gvFVL~b_rY80S-DW~Q7cVAy8vED~q3eUobDMJW~CmMil8exOo~zjyzKriEtM~tgP8r-gOe_~UzD942ltHm~vx6lzF1fXS~IYclAM59kT~faHcYIP1U0~nmhKtIFWev~nofT_HAoUA~co0lRz54id~gEc5w6WHgC~Kw3rxm81BS~6RcLf9BQ-w~m3EJRa33xU~CiSfl_AE0h~AI_aJCDFn0~KhVXu5CuKx~2kSJBy_FeR~4QveACRzn3~7fCik7KLYi~HKYKqXebBi~yTfty1xk17~Oews_eiAFU~kGYw4gQ11Z~HLWLeyYOUF~hW_oUTwHGx~alQb7gJxOf~HY55MqmzzQ~jk9IzfjZ6n~48UjH62K37~BSlt10mdnm~yREQ8PVGHN~CkDjyRo6Vc~engSCj5XFq~U-RInt8VSZ~fAloiTkhNQ~TmShECZdw3~gCB7z_XWkp~3gc3uGrU1V~LcDbj1i54T~AXMsnOI1nG~ieRoksS1U_~vD3FEKC12p~GS5-ApVeYs~5URl6U6Xie~FbvXliFQRp~j4QDy2PP0o~v3nOtgG77A~Bd2L9ZBE8q~Ce-EdaHA-3~YXsA4N8tVW~M2vKPRxAge~jpIZPQ502H~AGF29gcJU3~bfM8xJ-4gy~wbvCWCYbkM~qWFESUmfEs~OUF2gvwPef~DlTwYHcEzf~uC2yUZfXDc~GHSY1lQ6BT~kjfJ5uXq4m~BVl7Vb2WNo~Bo1xMRD4DT~VJLFz2UuxX~1zrMwV1ffN~4fhov5mA8J~b8EPuiThxE~weJthAwEY_~ykcQDH70QN~3Sgz5yTKJd~WVrsHleeCL~lBcRAWFuPM~X6iWvDmD9W~yPNaP3JSNF~5mzv1EsHcE~y8GNntYHsi~pIHkJ2o7vI~81BOcT1ZAV; _ga_34B604LFFQ=GS1.1.1686404634.112.1.1686413252.10.0.0; _ga=GA1.2.957903919.1672227586; __utmb=235335808.38.9.1686413206182; _ga_75BBYNYN9J=GS1.1.1686404627.41.1.1686413277.0.0.0; __cf_bm=CGr4xZE6UMbqKJ0XZMvQzEdE785.sWyczlJA9WD0CUI-1686413278-0-AcHAUn80qeRUZDWafNONzy0Cl2G/6m97ZJqqzQa26Xx38YER8DhL+8n4ggxJYBht38TDMKaU+iIORlQflRVa8UwZ6dULQ1HU10jiBWY6PKfN; cto_bundle=bnZCvl9GUzN5UkwlMkJ0Y05wWmNFZnJvTjUwTEFPaGpmd0pOOHo0d1M0UTdHNFBTOVFDSFZZRlA0THR5a1ZEVWhlNlo5eFZSNzZFazRTbUZXRDNZeUNKQ2F3V2s1TDZDSGF5M1RPWHNwTWVSb0xBJTJGM1hac29SalkxZjZFZ2xKaSUyQkRoT0xXdUk0UFNPcDlKaWwyaGRZZm9YajJ5QWclM0QlM0Q'
}
DIR_NAME = 'pixiv'


def scrape_page(url):
    '''接受url,返回页面信息'''
    logging.info(f'正在爬取页面{url}')
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == requests.codes.OK:
            return response.text  # 成功就返回页面结果
        else:
            logging.error(f'不正确的状态码{response.status_code},请检查{url}')
            
    except requests.RequestException:
        logging.error(f'爬取页面{url}时发生错误', exc_info=True)


def parse_image_list(html):
    '''返回一个含每个图片链接的列表，点进去可以获取图片详情以备image_url'''
    pattern = r'<a href="(?P<image_url>/artworks/\d+)"\s?class="work  _work.*?"\s*?target="_blank">'
    image_urls = re.finditer(pattern=pattern, string=html)  # 这样必须得指出哪组
    detail_url_list = [urljoin(BASE_URL, url.group('image_url'))
                       for url in image_urls]
    return detail_url_list


def parse_image_url(html, nsfw=True):
    '''根据详情页，返回图片url'''
    # pattern=r'<img.*?src="(.*?)".*?class="sc-1qpw8k9-1 jOmqKq".*?>'
    # 返回的竟然是JavaScript生成页面
    pattern = '<link rel="preload" as="image" href="(?P<image>.*?)">'
    if nsfw:
        pattern = r'"regular":"(?P<image>.*?)"'
    try:
        url = re.search(pattern=pattern, string=html).group('image')
    except Exception as e:
        print(f'在尝试根据详情页返回图片下载地址时出错,检查html', e)
    else:
        return url


def save_image(url):
    response = requests.get(url, headers=headers)
    logging.info(f'正在下载图片:{url}')
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == requests.codes.OK:
            if not os.path.exists(DIR_NAME):
                os.makedirs(DIR_NAME)
            with open(os.path.join(DIR_NAME, os.path.basename(url)), 'wb') as f:  # 注意要是写入模式
                try:
                    f.write(response.content)
                except Exception as e:
                    print(f'保存图片发生错误,url:{url}', e)

        else:
            logging.error(f'不正确的状态码{response.status_code}')
            
    except requests.RequestException:
        logging.error(f'下载图片{url}时发生错误', exc_info=True)



page_html = scrape_page(RANK_URL)
image_url_list = parse_image_list(page_html)# 返回例如https://www.pixiv.net/artworks/108826801的链接

def main(url):
    html = scrape_page(url)  # 获取详情页的html
    image_url = parse_image_url(html)  # 解析详情页的html，返回图片下载地址
    save_image(image_url)  # 根据下载地址下载图片
   

def run():
    from threading import Thread
    threads=[Thread(target=main,args=(url,)) for url in image_url_list ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    
if __name__ == '__main__':
    run()
