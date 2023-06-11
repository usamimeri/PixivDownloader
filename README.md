# PixivDownloader
简易的pixiv下载器，正在边学爬虫边完善

# 支持功能
1. 根据单作者uid下载所有作品，支持单静图和多静图
```
    DIR_NAME='#改成你想放结果的文件夹名
    COOKIE=#改成你的cookie
    header=Header(COOKIE)
    downloader=PixivDownloader(header)
    downloader.by_artist('作者的uid')
```
2. 断点续传，会先检测已经下好的内容并去除
3. 自动提取信息，可以设置获得每个图片的信息
    * 图片id
    * 作者id
    * 作者名
    * 图片标题
    * 图片tags
    * 图片的收藏数，喜欢数，观看数
    * 图片是否是动图
 
# 目标
1. 多进程/线程加快
2. 过滤器类的实现
3. 将其他信息存入数据库以便数据分析用

