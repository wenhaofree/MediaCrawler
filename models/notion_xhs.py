from notion_client import Client

class Page:
    def __init__(self, content,type,liked_count,collected_count,comment_count,share_count,ip_location,author,author_avatar,image_list,title,create_time,update_time,last_modify_ts,note_url,node_id):
        self.content = content
        self.type = type
        self.liked_count = liked_count
        self.collected_count = collected_count
        self.comment_count = comment_count
        self.share_count = share_count
        self.ip_location = ip_location
        self.author = author
        self.author_avatar = author_avatar
        self.image_list = image_list
        self.title = title
        self.create_time = create_time
        self.update_time = update_time
        self.last_modify_ts = last_modify_ts
        self.note_url = note_url
        self.node_id = node_id
    

class NotionClient:
    def __init__(self):
        """
        初始化
        """
        global global_query_results
        global global_notion
        global global_database_id
        global_token = "secret_SGSgYlUHk8knQRLcwJr1alzjzVTwXFwrr0UDBawy0Sw"
        global_database_id = "71a27ce80d274ff5ba0637dbca1ed766"
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
                                'content': page.title
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
                '作者': {
                    'rich_text': [
                        {
                            'text': {
                                'content': page.author
                            }
                        }
                    ]
                },
                '图文地址集': {
                    'rich_text': [
                        {
                            'text': {
                                'content': page.image_list
                            }
                        }
                    ]
                },
                'Node_id': {
                    'rich_text': [
                        {
                            'text': {
                                'content': page.node_id
                            }
                        }
                    ]
                },
                'Type': {
                    'select':{
                        'name': page.type
                    }
                },
                "点赞数": {
                    "number": int(page.liked_count)
                },
                "收藏数": {
                    "number": int(page.collected_count)
                },
                "评论数": {
                    "number": int(page.comment_count)
                },
                "转发数": {
                    "number": int(page.share_count)
                },
                '发布地': {
                    'select':{
                        'name': page.ip_location if page.ip_location != "" else "未知"
                    }
                },
                "作者头像": {
                    'url': page.author_avatar
                },
                "笔记URL": {
                    'url': page.note_url
                },
                "创建时间": {
                    "date": {
                        "start": page.create_time,
                    }
                },
                "更新时间": {
                    "date": {
                        "start": page.update_time,
                    }
                },
                "上次修改时间": {
                    "date": {
                        "start": page.last_modify_ts,
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
def notion_handler(page):
    client = NotionClient()
    insert_notion_list=[]
    if page is not None:
        page.create_time = time_fromat(page.create_time)
        page.last_modify_ts = time_fromat(page.last_modify_ts)
        page.update_time = time_fromat(page.update_time)
        new_page=client.create_page(page)

        page_id=new_page["id"]
        node_id = new_page["properties"]["Node_id"]["rich_text"][0]["text"]["content"]
        insert_notion_data = {'page_id': page_id, 'node_id': node_id}
        insert_notion_list.append(insert_notion_data)
    
    # 插入notion的数据保存文件中
    file_path="notion-xhs.json"
    with open(file_path, 'a') as f:
        for i in insert_notion_list:
            json.dump(i, f)
            f.write('\n')
        f.close()
        print(f'[notion.json保存:{len(insert_notion_list)}条数据完成]')
        
# def notion_data_read():
#     # 打开已经保存的文件
#         message_ids = {}
#         file_name = f'{search}-noiton.json'
#         file_path = os.path.join(os.path.dirname(__file__), file_name)
#         if os.path.exists(file_path):
#             try:
#                 with open(file_path, 'r', encoding='utf-8') as f:
#                     for line in f:
#                         json_data = json.loads(line)
#                         node_id = json_data['node_id']
#                         page_id = json_data['page_id']
#                         message_ids[node_id] = page_id
#             except Exception as e:
#                 print(f'更新异常:{e}')
#                 pass
        


# 将时间戳转换为datetime对象
import datetime
def time_fromat(timestamp):
    timestamp=timestamp/1000
    dt = datetime.datetime.fromtimestamp(timestamp)
    formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S")
    return formatted_date

def main():
    client = NotionClient()
    client.create_page("page")

if __name__ == '__main__':
    main()
    
