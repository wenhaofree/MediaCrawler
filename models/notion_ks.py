from notion_client import Client

class Page:
    def __init__(self,keywords,title,content,video_id,user_id,liked_count,viewd_count,video_url,video_cover_url,video_play_url,create_time,video_type,nick_name,avatar):
        self.keywords = keywords
        self.title = title
        self.content = content
        self.video_id = video_id
        self.user_id = user_id
        self.liked_count = liked_count
        self.viewd_count = viewd_count
        self.video_url = video_url
        self.video_cover_url = video_cover_url
        self.video_play_url = video_play_url
        self.create_time = create_time
        self.video_type=video_type
        self.nick_name = nick_name
        self.avatar = avatar

class NotionClient:
    def __init__(self):
        """
        初始化
        """
        global global_query_results
        global global_notion
        global global_database_id
        global_token = "secret_SGSgYlUHk8knQRLcwJr1alzjzVTwXFwrr0UDBawy0Sw"
        global_database_id = "775760b5d5c04fda88e05d1d2cb5e46a"
        global_notion = Client(auth=global_token)
        global_query_results = global_notion.databases.query(database_id=global_database_id)
        print('开始Notion自动化处理数据...')

    """
    创建新的页面
    1. 属性名字和字段个数要对应上
    2. 不同的属性用不同的构参方式
    """
    def create_page(self, page):
        new_page = global_notion.pages.create(
            parent={
                'database_id': global_database_id
            },
            properties={
                'Name': {
                    'title': [
                        {
                            'text': {
                                'content': "title"
                            }
                        }
                    ]
                },
                '正文内容': {
                    'rich_text': [
                        {
                            'text': {
                                'content': page.content
                            }
                        }
                    ]
                },
                'Video_id': {
                    'rich_text': [
                        {
                            'text': {
                                'content': page.video_id
                            }
                        }
                    ]
                },
                'User_id': {
                    'rich_text': [
                        {
                            'text': {
                                'content': page.user_id
                            }
                        }
                    ]
                },
                'nick_name': {
                    'rich_text': [
                        {
                            'text': {
                                'content': page.nick_name
                            }
                        }
                    ]
                },
                'Video_type': {
                    'select':{
                        'name': page.video_type
                    }
                },
                '关键词': {
                    'select':{
                        'name': page.keywords
                    }
                },
                "点赞数": {
                    "number": int(page.liked_count) if page.liked_count is not None else 0
                },
                "播放数": {
                    "number": int(page.viewd_count) if page.viewd_count is not None else 0
                },
                "avatar_url": {
                    'url': page.avatar
                },
                "Video_url": {
                    'url': page.video_url
                },
                "Video_cover_url": {
                    'url': page.video_cover_url
                },
                "Video_play_url": {
                    'url': page.video_play_url
                },

                "创建时间": {
                    "date": {
                        "start": page.create_time,
                    }
                }
            }
        )
        return new_page


    """
    更新页面内容
    """
    def update_page_content(self, page_id, properties_params):
        page = global_notion.pages.retrieve(page_id)
        #更新属性是URL内容
        for key, value in page["properties"].items():
            if key == "URL":
                page["properties"][key]["url"] = properties_params[key]
        update_page=global_notion.pages.update(page_id=page_id, properties=page["properties"])
        print(update_page)
    def update_page_content_test(self, page_id, properties_params):
        page = global_notion.pages.retrieve(page_id)
        #更新属性是URL内容
        # 更新页面的属性
        update_payload = {
            "properties": {
                "点赞数": {
                    "number": 456
                },
                # 其他属性更新
            }
        }
        # 执行更新操作
        update_page=global_notion.pages.update(page_id=page_id, **update_payload)
        print(update_page)

    #

    """
    删除页面内容
    """
    def delete_page_content(self, page_id):
        del_block = global_notion.blocks.delete(block_id=page_id)
        print(del_block)

    """
    删除重复的页面-保留最新的页面
    """
    def delete_duplicate_page(self,page_list,property_name):
        property_name_set=set()
        for page in page_list:
            if page["object"] == "page":
                for key, value in page["properties"].items():
                    if key == property_name:
                        text_value=value['rich_text'][0]['text']['content']
                        if text_value in property_name_set:
                            self.delete_page_content(page["id"])
                        else:
                            # todo-fwh-获取富文本类型
                            property_name_set.add(value['rich_text'][0]['text']['content'])
    
    

    """
    获取页面指定属性的值，入参为属性名
    """
    def get_page_properties(self,page_list,property_name):
        property_name_set=set()
        for page in page_list:
            if page["object"] == "page":
                for key, value in page["properties"].items():
                    if key == property_name:
                        # todo-fwh-获取富文本类型
                        property_name_set.add(value['rich_text'][0]['text']['content'])
        print(property_name_set)
        return property_name_set

import json
import os
def notion_handler(page):
    node_id=page.video_id
    node_ids = notion_data_read()
    if node_id not in node_ids:
        notion_data_save(page)
    else:
        print(f'[notion.json已存在:{node_id}]')
def notion_data_save(page):
    client = NotionClient()
    insert_notion_list=[]
    if page is not None:
        if page.create_time is None:
            page.create_time = "2021-01-01 00:00:00"
        else:
            page.create_time = time_fromat(page.create_time)
        new_page=client.create_page(page)

        page_id=new_page["id"]
        node_id = new_page["properties"]["Video_id"]["rich_text"][0]["text"]["content"]
        insert_notion_data = {'page_id': page_id, 'node_id': node_id}
        insert_notion_list.append(insert_notion_data)
    
    # 插入notion的数据保存文件中
    file_name="notion-ks.json"
    file_path = os.path.join(os.path.dirname(__file__), file_name)
    with open(file_path, 'a') as f:
        for i in insert_notion_list:
            json.dump(i, f)
            f.write('\n')
        f.close()
        print(f'[notion.json保存:{len(insert_notion_list)}条数据完成]')
        

# 读取文件中Notion已保存的数据
def notion_data_read():
    message_ids = set()
    file_name="notion-ks.json"
    file_path = os.path.join(os.path.dirname(__file__), file_name)
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    json_data = json.loads(line)
                    node_id = json_data['node_id']
                    message_ids.add(node_id)
        except Exception as e:
            print(f'打开文件异常更新异常:{e}')
            pass
    return message_ids
    


# 将时间戳转换为datetime对象
import datetime
def time_fromat(timestamp):
    timestamp=timestamp/1000
    dt = datetime.datetime.fromtimestamp(timestamp)
    formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S")
    return formatted_date

def test():
    client = NotionClient()
    create_time=time_fromat(1625110200)
    page=Page(
        "123","title","content","video_id","user_id","3000","333","video_url","video_cover_url","video_play_url",create_time,"video_type","nick_name","avatar"
    )
    client.create_page(page)


if __name__ == '__main__':
    test()
    
