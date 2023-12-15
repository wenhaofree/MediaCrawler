from notion_client import Client

class Page:
    def __init__(self,keywords,title,content,liked_count,collected_count,comment_count,share_count,aweme_url,create_time,aweme_type,ip_location,aweme_id,user_id,sec_uid,short_user_id,user_unique_id,user_signature,nick_name,avatar):
        self.keywords = keywords
        self.title = title
        self.content = content
        self.liked_count = liked_count
        self.collected_count = collected_count
        self.comment_count = comment_count
        self.share_count = share_count
        self.aweme_url = aweme_url
        self.create_time = create_time
        self.aweme_type = aweme_type
        self.ip_location = ip_location
        self.aweme_id = aweme_id
        self.user_id = user_id
        self.sec_uid = sec_uid
        self.short_user_id = short_user_id
        self.user_unique_id = user_unique_id
        self.user_signature = user_signature
        self.nick_name = nick_name
        self.avatar = avatar
        
    # def __init__(self, content,type,liked_count,collected_count,comment_count,share_count,ip_location,author,author_avatar,image_list,title,create_time,update_time,last_modify_ts,note_url,node_id):
    #     self.content = content
    #     self.type = type
    #     self.liked_count = liked_count
    #     self.collected_count = collected_count
    #     self.comment_count = comment_count
    #     self.share_count = share_count
    #     self.ip_location = ip_location
    #     self.author = author
    #     self.author_avatar = author_avatar
    #     self.image_list = image_list
    #     self.title = title
    #     self.create_time = create_time
    #     self.update_time = update_time
    #     self.last_modify_ts = last_modify_ts
    #     self.note_url = note_url
    #     self.node_id = node_id
    

class NotionClient:
    def __init__(self):
        """
        初始化
        """
        global global_query_results
        global global_notion
        global global_database_id
        global_token = "secret_SGSgYlUHk8knQRLcwJr1alzjzVTwXFwrr0UDBawy0Sw"
        global_database_id = "04bbd91c482548b1be8aefd6f7977695"
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
                'nick_name': {
                    'rich_text': [
                        {
                            'text': {
                                'content': page.nick_name
                            }
                        }
                    ]
                },
                'Aweme_id': {
                    'rich_text': [
                        {
                            'text': {
                                'content': page.aweme_id
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
                'Sec_uid': {
                    'rich_text': [
                        {
                            'text': {
                                'content': page.sec_uid
                            }
                        }
                    ]
                },
                'Short_user_id': {
                    'rich_text': [
                        {
                            'text': {
                                'content': page.short_user_id
                            }
                        }
                    ]
                },
                'User_unique_id': {
                    'rich_text': [
                        {
                            'text': {
                                'content': page.user_unique_id if page.user_unique_id is not None else ""
                            }
                        }
                    ]
                },
                'User_signature': {
                    'rich_text': [
                        {
                            'text': {
                                'content': page.user_signature if page.user_signature is not None else ""
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
                'Aweme_type': {
                    'select':{
                        'name': page.aweme_type
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
                "收藏数": {
                    "number": int(page.collected_count) if page.collected_count is not None else 0
                },
                "评论数": {
                    "number": int(page.comment_count) if page.comment_count is not None else 0
                },
                "转发数": {
                    "number": int(page.share_count) if page.share_count is not None else 0
                },
                '发布地': {
                    'select':{
                        'name': page.ip_location if page.ip_location != "" else "未知"
                    }
                },
                "avatar_url": {
                    'url': page.avatar
                },
                "aweme_url": {
                    'url': page.aweme_url
                },
                "创建时间": {
                    "date": {
                        "start": page.create_time,
                    }
                }
            }
        )
        # print(new_page)
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
    node_id=page.aweme_id
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
        node_id = new_page["properties"]["Aweme_id"]["rich_text"][0]["text"]["content"]
        insert_notion_data = {'page_id': page_id, 'node_id': node_id}
        insert_notion_list.append(insert_notion_data)
    
    # 插入notion的数据保存文件中
    file_name="notion-dy.json"
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
    file_name="notion-dy.json"
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
    # timestamp=timestamp/1000
    dt = datetime.datetime.fromtimestamp(timestamp)
    formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S")
    return formatted_date

def test():
    client = NotionClient()
    create_time=time_fromat(1625110200)
    page=Page(
        title="title",
        content="content",
        liked_count=1,
        collected_count=1,
        comment_count=1,
        share_count=1,
        aweme_url="aweme_url",
        create_time=create_time,
        aweme_type="aweme_type",
        ip_location="ip_location",
        author_avatar="author_avatar",
        aweme_id="aweme_id",
        user_id="user_id",
        sec_uid="sec_uid",
        short_user_id="short_user_id",
        user_unique_id="user_unique_id",
        user_signature="user_signature",
        nick_name="nick_name",
        avatar="avatar"
    )
    client.create_page(page)


if __name__ == '__main__':
    test()
    
