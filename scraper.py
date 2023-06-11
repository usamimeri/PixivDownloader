import requests
from lxml import etree
import json
import os
import logging
from tqdm import tqdm_notebook
# from tqdm import tqdm
# from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from threading import Thread
import time
logging.captureWarnings(True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')


class Header:
    def __init__(self, Cookie=None, referer='https://www.pixiv.net/ranking.php?mode=daily_r18',
                 user_agent='Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_5_3; en-ca) AppleWebKit/525.18 (KHTML, like Gecko) Version/3.1.1 Safari/525.20', accept_language='zh-CN,zh;q=0.9'):
        """存储 HTTP 请求头信息"""
        self.__header = {
            'user-agent': user_agent,
            'accept-language': accept_language,
            'referer': referer,
            'Cookie': Cookie,
        }

    @property
    def header(self):
        '''返回header字典'''
        return self.__header

    def update(self, Cookie: str = None, referer: str = None, user_agent: str = None):
        '''更新请求头'''
        if isinstance(referer, str):
            self._header['referer'] = referer
        if isinstance(user_agent, str):
            self._header['user-agent'] = user_agent
        if Cookie:
            self._header['Cookie'] = Cookie


class RequestHtml:
    def __init__(self, Header: object) -> None:
        self.Header = Header

    def scrape_page(self, url) -> str:
        '''爬取一页，返回页面信息，可以是html或json'''
        try:
            session = requests.session()
            # max_retries=1 重试1次 后续再更改，因为很多时候三次都是失败的
            session.mount('http://', HTTPAdapter(max_retries=1))
            session.mount('https://', HTTPAdapter(max_retries=1))
            response = session.get(url, headers=self.Header.header)
            if response.status_code == requests.codes.OK:
                return response.text  # 成功就返回页面结果
            elif response.status_code==429 or str(429):
                raise '你爬太快了'
            else:
                logging.error(f'不正确的状态码{response.status_code},请检查{url}')

        except requests.RequestException:
            logging.error(f'爬取页面{url}时发生错误', exc_info=True)

    def save_image(self, info):
        '''根据传入的图片信息进行处理'''
        urls = info['urls']  # 一图或者多图的url

        for index, url in enumerate(urls):
            try:
                response = requests.get(url, headers=self.Header.header)
                if response.status_code == requests.codes.OK:
                    if not os.path.exists(DIR_NAME):
                        os.makedirs(DIR_NAME)
                    if len(info['urls']) > 1:
                        # 多图命名用title_id_1的格式
                        file_name = '_'.join(
                            [info['title'], info['id'], str(index+1)])
                    else:
                        file_name = '_'.join([info['title'], info['id']])
                    try:
                        # 注意要是写入模式,这里增加了扩展名
                        with open(os.path.join(DIR_NAME, file_name+os.path.splitext(url)[1]), 'wb') as f:
                            # 这里有个问题，有些作者标题起得不合法！
                            f.write(response.content)
                    except:
                        try:
                            file_name = '_'.join([info['id'], str(index+1)])
                            # 发生错误就只保存id了
                            with open(os.path.join(DIR_NAME, file_name+os.path.splitext(url)[1]), 'wb') as f:
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
        self.log=None #记录uid信息

    def artist_illust_uid(self, json_data):
        '''获取一个作者的所有作品的uid'''
        if json_data:
            uid_data = json.loads(json_data)
            try:
                uid_list = [uid for uid in uid_data['body']['illusts']]
            except:
                raise f'在读取uid时发生了错误，请检查{json_data}json文件的正确性'
            else:
                self.log = uid_list
                return uid_list
        else:
            logging.error('出现了空的json_data')

    def get_image_info(self, image_html, uid):
        '''返回图片详情'''
        html = etree.HTML(image_html)
        js = html.xpath('//meta[@name="preload-data"]/@content')[0]
        data = json.loads(js)['illust'][uid]
        url = data['urls']['original']
        # 构造urls列表
        urls = [f'p{i}'.join(url.split('p0'))
                for i in range(data['pageCount'])]  # 先按p0分离再按p页数结合
        info = dict(
            id=uid,  # 图片id
            userId=data['userIllusts'][uid]['userId'],  # 作者id
            userName=data['userIllusts'][uid]['userName'],  # 作者名
            tags=data['userIllusts'][uid]['tags'],  # tags标签
            urls=urls,  # 图片url
            title=data['title'],  # 图片标题
            bookmarkCount=data['bookmarkCount'],  # 收藏数
            likeCount=data['likeCount'],  # 点赞数
            viewCount=data['viewCount'],  # 观看数
            pageCount=data['pageCount'],  # 图片页数
            ugoira=('ugoira' in data['urls']['original']),  # 是否是动图
        )
        self.log.append(info)
        
        return info


class PixivDownloader:
    def __init__(self, Header) -> None:
        self.requesthtml = RequestHtml(Header=Header)
        self.pixivparser = PixivParser()

    def by_artist(self, uid,delay=0.5, thread_num=30 ,verify=True):
        '''下载单作者所有作品，可以指定是否断点续传，会先遍历指定文件夹，去除下好的uid，但不能保证因title本身数字导致误删'''
        ARTIST_URL = f'https://www.pixiv.net/ajax/user/{uid}/profile/all?lang=zh:'
        json_data = self.requesthtml.scrape_page(ARTIST_URL)  # 获取ajax的json
        uid_list = self.pixivparser.artist_illust_uid(json_data)  # 获取作者所有作品uid
        if verify:
            deleted = 0
            if os.path.exists(DIR_NAME):
                for uid in uid_list.copy():  # 必须copy 不然会出错
                    for file_name in os.listdir(DIR_NAME):
                        if uid in file_name:
                            uid_list.remove(uid)
                            deleted += 1
                            break
                logging.info(f'删除了下载好的{deleted}个uid')
                logging.info(f'目前任务长度{len(uid_list)}')
        
        def start_download(uid_chunk):
            for uid in uid_chunk:
                logging.info(f'正在下载uid为{uid}的作品')
                html = self.requesthtml.scrape_page(
                    f'https://www.pixiv.net/artworks/{uid}')  # 进入详情页
                image_info = self.pixivparser.get_image_info(
                    html, uid)  # 获取图片的下载信息
                self.requesthtml.save_image(image_info)  # 下载并保存图片

                time.sleep(delay)
        
        # threads=[Thread(target=start_download,args=(chunk,)) for chunk in self.split_task(uid_list,thread_num)] 
        threads=[Thread(target=start_download,args=([chunk],)) for chunk in uid_list] 
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    # def split_task(self,tasks, n_threads):
    #     """平均分割任务给线程池中的线程数"""
    #     if len(tasks)<=n_threads:
    #         n_threads=len(tasks)
    #     n_per_thread = len(tasks) // n_threads
    #     leftover = len(tasks) % n_threads

    #     starts = [n_per_thread * i for i in range(n_threads)] 

    #     ends = starts[1:] + [len(tasks)]
    #     ends[-1] += leftover

    #     chunks = []
    #     for i in range(n_threads):
    #         chunks.append(tasks[starts[i]:ends[i]])
    #     return chunks

if __name__ == '__main__':
    DIR_NAME = ''  # 改成放结果的文件夹名
    COOKIE = ''
    # cookie
    header = Header(COOKIE)
    downloader = PixivDownloader(header)
    downloader.by_artist('',0)
