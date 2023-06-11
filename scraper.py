import requests
from lxml import etree
import json
import os
import logging
# from urllib.parse import urljoin
# from fake_useragent import UserAgent
from requests.adapters import HTTPAdapter

logging.captureWarnings(True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
class Header:
    def __init__(self,Cookie=None,referer='https://www.pixiv.net/ranking.php?mode=daily_r18',
                 user_agent='Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_5_3; en-ca) AppleWebKit/525.18 (KHTML, like Gecko) Version/3.1.1 Safari/525.20'
                 ,accept_language='zh-CN,zh;q=0.9'):
        
        """存储 HTTP 请求头信息"""
        self.__header={
            'user-agent': user_agent,
            'accept-language': accept_language,
            'referer': referer,
            'Cookie': Cookie,
        }
    
    @property
    def header(self):
        '''返回header字典'''
        return self.__header
    
    def update(self,Cookie:str=None,referer:str=None,user_agent:str=None):
        '''更新请求头'''
        if isinstance(referer, str):   
            self._header['referer'] = referer
        if isinstance(user_agent, str):        
            self._header['user-agent'] = user_agent
        if Cookie:
            self._header['Cookie'] = Cookie    
        

class RequestHtml:
    def __init__(self,Header:object) -> None:
        self.Header=Header
    
    def scrape_page(self,url)->str:
        '''爬取一页，返回页面信息，可以是html或json'''
        try:
            session = requests.session()
            # max_retries=3 重试3次
            session.mount('http://', HTTPAdapter(max_retries=3))
            session.mount('https://', HTTPAdapter(max_retries=3))
            response = session.get(url, headers=self.Header.header)
            if response.status_code == requests.codes.OK:
                return response.text  # 成功就返回页面结果
            else:
                logging.error(f'不正确的状态码{response.status_code},请检查{url}')

                
        except requests.RequestException:
            logging.error(f'爬取页面{url}时发生错误', exc_info=True)
    
    def save_image(self,info):
        '''根据传入的图片信息进行处理'''
        urls=info['urls'] #一图或者多图的url

        for index,url in enumerate(urls):
            try:
                response = requests.get(url, headers=self.Header.header)
                if response.status_code == requests.codes.OK:
                    if not os.path.exists(DIR_NAME):
                        os.makedirs(DIR_NAME)
                    if len(info['urls'])>1:
                        file_name='_'.join([info['title'],info['id'],str(index+1)]) #多图命名用title_id_1的格式 
                    else:
                        file_name='_'.join([info['title'],info['id']])
                    try:
                        with open(os.path.join(DIR_NAME,file_name+os.path.splitext(url)[1]),'wb') as f:  # 注意要是写入模式,这里增加了扩展名
                            #这里有个问题，有些作者标题起得不合法！
                            f.write(response.content)
                    except:
                        try:
                            file_name='_'.join([info['id'],str(index+1)])
                            with open(os.path.join(DIR_NAME,file_name+os.path.splitext(url)[1]),'wb') as f: #发生错误就只保存id了
                                f.write(response.content)
                        except Exception as e:
                            logging.error(f'保存图片发生错误,url:{url}', e)

                else:
                    logging.error(f'不正确的状态码{response.status_code}')
                    
            except requests.RequestException:
                logging.error(f'下载图片{url}时发生错误', exc_info=True)
    

class PixivParser:
    '''解析器'''
    def __init__(self) -> None:
        self.artist_illust_uid_cache=None 
        #临时存储单作者的作品列表，可以尝试记录下载了多少个，以便断点续传


    def artist_illust_uid(self,json_data):
        '''获取一个作者的所有作品的uid'''
        if json_data:
            uid_data=json.loads(json_data)
            try:
                uid_list=[uid for uid in uid_data['body']['illusts']]
            except:
                raise f'在读取uid时发生了错误，请检查{json_data}json文件的正确性'
            else:
                self.artist_illust_uid_cache=uid_list
                return uid_list
        else:
            logging.error('出现了空的json_data')

    def get_image_info(self,image_html,uid):
        '''返回图片详情'''
        html=etree.HTML(image_html)
        js=html.xpath('//meta[@name="preload-data"]/@content')[0]
        data=json.loads(js)['illust'][uid]
        url=data['urls']['original']
        #构造urls列表
        urls=[f'p{i}'.join(url.split('p0')) for i in range(data['pageCount'])] #先按p0分离再按p页数结合
        info=dict(
            id=uid, #图片id
            userId=data['userIllusts'][uid]['userId'], #作者id
            userName=data['userIllusts'][uid]['userName'], #作者名
            tags=data['userIllusts'][uid]['tags'], #tags标签
            urls=urls, #图片url
            title=data['title'], #图片标题
            bookmarkCount=data['bookmarkCount'], #收藏数
            likeCount=data['likeCount'], #点赞数
            viewCount=data['viewCount'], #观看数
            pageCount=data['pageCount'], #图片页数
            ugoira=('ugoira' in data['urls']['original']),#是否是动图
            )
        print(info)
        return info
        
class PixivDownloader:
    def __init__(self,Header) -> None:
        self.requesthtml=RequestHtml(Header=Header)
        self.pixivparser=PixivParser()
    def by_artist(self,uid,verify=True): 
        '''下载单作者所有作品，可以指定是否断点续传，会先遍历指定文件夹，去除下好的uid，但不能保证因title本身数字导致误删'''
        from tqdm import tqdm
        ARTIST_URL=f'https://www.pixiv.net/ajax/user/{uid}/profile/all?lang=zh:'
        json_data=self.requesthtml.scrape_page(ARTIST_URL) #获取ajax的json
        uid_list=self.pixivparser.artist_illust_uid(json_data) #获取作者所有作品uid
        if verify:
            deleted=0
            if os.path.exists(DIR_NAME):
                for uid in uid_list.copy(): #必须copy 不然会出错
                    for file_name in os.listdir(DIR_NAME):
                        if uid in file_name:
                            uid_list.remove(uid)
                            deleted+=1
                            break
                logging.info(f'删除了下载好的{deleted}个uid')
                logging.info(f'目前任务长度{len(uid_list)}')

        for uid in tqdm(uid_list):
            html=self.requesthtml.scrape_page(f'https://www.pixiv.net/artworks/{uid}') #进入详情页
            image_info=self.pixivparser.get_image_info(html,uid) #获取图片的下载信息
            self.requesthtml.save_image(image_info) #下载并保存图片
    

if __name__ == '__main__':
    DIR_NAME='yousei' #改成你想放结果的文件夹名
    COOKIE='first_visit_datetime_pc=2022-12-28+20%3A39%3A44; yuid_b=KShCQTE; p_ab_id=9; p_ab_id_2=2; p_ab_d_id=44044046; _fbp=fb.1.1672227586548.756303350; _im_vid=01GNC8G1S7PM4TDN0S4FWX4NH1; privacy_policy_agreement=5; privacy_policy_notification=0; a_type=0; b_type=1; adr_id=GtkcsQXhoeJmr8yWnkhrlsfAmDGyiOO9IETH7HwZZMyHMSDq; login_ever=yes; PHPSESSID=17255407_pJe3uT5CbqfpxiYg46omezBvwDJhaAiD; c_type=20; _im_uid.3929=i.LtnelIKXScCYpWMB2FgjiA; _ga_MZ1NL4PHH0=GS1.1.1682871015.3.1.1682871062.0.0.0; __utmv=235335808.|2=login%20ever=yes=1^3=plan=premium=1^5=gender=male=1^6=user_id=17255407=1^9=p_ab_id=9=1^10=p_ab_id_2=2=1^11=lang=zh=1; b-user-id=c230912d-a33b-14da-db6b-5b052d243c43; __utmz=235335808.1685720249.125.20.utmcsr=google|utmccn=(organic)|utmcmd=organic|utmctr=(not%20provided); _gcl_au=1.1.423243483.1685723202; _pubcid=20a08383-b991-4cb3-af72-c8632b5f59e8; __gads=ID=6b29979b8cff24b1:T=1679221868:RT=1685888986:S=ALNI_MbirPfvYyoIYvstlCcYFs3zRqdN_A; __gpi=UID=00000a2d93b33b28:T=1679221868:RT=1685888986:S=ALNI_MbsN_i-Y_usynP_GBMW9LICcPreXw; cto_bidid=pw4hsF9yWDJ6R1ZLZlRBJTJCSUt3SFRzOHM1YzJDJTJGRGVjR1hxY21NSVpjeXZLUlVpJTJCV2dKemJuWHlycDN4NkR4d01pUFpVUmJ2Q3NKcm5SRSUyQnFnS095Uk5ReG9leFY3TlpuNjRQUUY1T3JaNTh2QmM0JTNE; _ga_ZQEKG3EF2C=GS1.1.1685888985.3.0.1685889081.60.0.0; _gid=GA1.2.1157161106.1686227966; QSI_S_ZN_5hF4My7Ad6VNNAi=v:100:0; __utmc=235335808; __utma=235335808.1098950109.1672227586.1686397254.1686404627.135; howto_recent_view_history=108823710; __utmt=1; tag_view_ranking=0xsDLqCEW6~_EOd7bsGyl~ziiAzr_h04~5oPIfUbtd6~3mvlXxwzlR~_hSAdpN9rx~zIv0cf5VVk~Lt-oEicbBr~Ie2c51_4Sp~KN7uxuR89w~azESOjmQSV~RTJMXD26Ak~M0_oya2NVz~TJ2ipOtAVO~ZvexGYezEm~kffGOewQdf~Yv2C9XifX_~NHr56gvFVL~b_rY80S-DW~Q7cVAy8vED~q3eUobDMJW~CmMil8exOo~zjyzKriEtM~tgP8r-gOe_~UzD942ltHm~vx6lzF1fXS~IYclAM59kT~faHcYIP1U0~nmhKtIFWev~nofT_HAoUA~co0lRz54id~gEc5w6WHgC~Kw3rxm81BS~6RcLf9BQ-w~m3EJRa33xU~CiSfl_AE0h~AI_aJCDFn0~KhVXu5CuKx~2kSJBy_FeR~4QveACRzn3~7fCik7KLYi~HKYKqXebBi~yTfty1xk17~Oews_eiAFU~kGYw4gQ11Z~HLWLeyYOUF~hW_oUTwHGx~alQb7gJxOf~HY55MqmzzQ~jk9IzfjZ6n~48UjH62K37~BSlt10mdnm~yREQ8PVGHN~CkDjyRo6Vc~engSCj5XFq~U-RInt8VSZ~fAloiTkhNQ~TmShECZdw3~gCB7z_XWkp~3gc3uGrU1V~LcDbj1i54T~AXMsnOI1nG~ieRoksS1U_~vD3FEKC12p~GS5-ApVeYs~5URl6U6Xie~FbvXliFQRp~j4QDy2PP0o~v3nOtgG77A~Bd2L9ZBE8q~Ce-EdaHA-3~YXsA4N8tVW~M2vKPRxAge~jpIZPQ502H~AGF29gcJU3~bfM8xJ-4gy~wbvCWCYbkM~qWFESUmfEs~OUF2gvwPef~DlTwYHcEzf~uC2yUZfXDc~GHSY1lQ6BT~kjfJ5uXq4m~BVl7Vb2WNo~Bo1xMRD4DT~VJLFz2UuxX~1zrMwV1ffN~4fhov5mA8J~b8EPuiThxE~weJthAwEY_~ykcQDH70QN~3Sgz5yTKJd~WVrsHleeCL~lBcRAWFuPM~X6iWvDmD9W~yPNaP3JSNF~5mzv1EsHcE~y8GNntYHsi~pIHkJ2o7vI~81BOcT1ZAV; _ga_34B604LFFQ=GS1.1.1686404634.112.1.1686413252.10.0.0; _ga=GA1.2.957903919.1672227586; __utmb=235335808.38.9.1686413206182; _ga_75BBYNYN9J=GS1.1.1686404627.41.1.1686413277.0.0.0; __cf_bm=CGr4xZE6UMbqKJ0XZMvQzEdE785.sWyczlJA9WD0CUI-1686413278-0-AcHAUn80qeRUZDWafNONzy0Cl2G/6m97ZJqqzQa26Xx38YER8DhL+8n4ggxJYBht38TDMKaU+iIORlQflRVa8UwZ6dULQ1HU10jiBWY6PKfN; cto_bundle=bnZCvl9GUzN5UkwlMkJ0Y05wWmNFZnJvTjUwTEFPaGpmd0pOOHo0d1M0UTdHNFBTOVFDSFZZRlA0THR5a1ZEVWhlNlo5eFZSNzZFazRTbUZXRDNZeUNKQ2F3V2s1TDZDSGF5M1RPWHNwTWVSb0xBJTJGM1hac29SalkxZjZFZ2xKaSUyQkRoT0xXdUk0UFNPcDlKaWwyaGRZZm9YajJ5QWclM0QlM0Q'
    #改成你的cookie
    header=Header(COOKIE)
    downloader=PixivDownloader(header)
    downloader.by_artist('2864095')
