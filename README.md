# PixivDownloader
简易的pixiv下载器，正在边学爬虫边完善

# 支持功能
1. 根据单作者uid下载所有作品
```
    DIR_NAME='#改成你想放结果的文件夹名
    COOKIE=#改成你的cookie
    header=Header(COOKIE)
    downloader=PixivDownloader(header)
    downloader.by_artist('作者的uid')
```

# 目标
1. 多进程加快
2. 断点续传功能
3. 过滤器类的实现
4. 实现图片命名格式规范化
