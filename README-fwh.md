## 个人注意事项:
1. 搜索信息关键词,都在config目录的base_config里.  新增:executable_path=config.EXECUTABLE_PATH 
2. 抖音登录需要二维码还有短信验证码登录. 需要接通安卓手机操作
3. 小红书登录,二维码不回显有问题
4. B站顺利
5. 快手二维码扫码无法登录
6. 解决方式采用cooker形式登录获取数据
7. 数据限制20条,但是重新开始会出现重复采集的情况,需要用去重逻辑,根据node_id唯一值
8. 增加Notion存储数据

## 本地使用方法

1. 创建 python 虚拟环境
   ```shell
   python3 -m venv venv
   ```

2. 安装依赖库

   ```shell
   pip install -r requirements.txt
   ```

3. 安装playwright浏览器驱动

   ```shell
   pip install playwright
   playwright install
   ```

4. 是否保存数据到DB中

   如果选择开启，则需要配置数据库连接信息，`config/db_config.py` 中的 `IS_SAVED_DATABASED`和`RELATION_DB_URL` 变量。然后执行以下命令初始化数据库信息，生成相关的数据库表结构：

   ```shell
   python db.py
   ```

5. 运行爬虫程序

   ```shell
   # 从配置文件中读取关键词搜索相关的帖子并爬去帖子信息与评论
   python main.py --platform xhs --lt qrcode --type search
   
   # 从配置文件中读取指定的帖子ID列表获取指定帖子的信息与评论信息
   python main.py --platform xhs --lt qrcode --type detail
   
   # 其他平台爬虫使用示例, 执行下面的命令查看
    python3 main.py --help

    options:
         -h, --help            show this help message and exit
         --platform {xhs,dy,ks,bili}
                                 Media platform select (xhs | dy | ks | bili)
         --lt {qrcode,phone,cookie}
                                 Login type (qrcode | phone | cookie)
         --type {search,detail}
                                 crawler type (search | detail)
    
   ```

6. 打开对应APP扫二维码登录

7. 等待爬虫程序执行完毕，数据会保存到 `data/xhs` 目录下
