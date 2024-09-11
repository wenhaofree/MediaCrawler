from notion_client import Client
import datetime
import json
import os
import re
# import config


def time_fromat(timestamp):
    timestamp = timestamp / 1000
    dt = datetime.datetime.fromtimestamp(timestamp)
    formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S")
    return formatted_date


class NotionClient:
    def __init__(self):
        """
        初始化
        """
        global global_notion
        global global_database_id
        global_token = "secret_SGSgYlUHk8knQRLcwJr1alzjzVTwXFwrr0UDBawy0Sw"
        global_database_id = "71a27ce80d274ff5ba0637dbca1ed766"
        global_notion = Client(auth=global_token)
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
                                'content': page['title']
                            }
                        }
                    ]
                },
                '正文内容': {
                    'rich_text': [
                        {
                            'text': {
                                'content': page['desc']
                            }
                        }
                    ]
                },
                '作者': {
                    'rich_text': [
                        {
                            'text': {
                                'content': page['nickname']
                            }
                        }
                    ]
                },
                '图文地址集': {
                    'rich_text': [
                        {
                            'text': {
                                'content': page['image_list'][:1900]
                            }
                        }
                    ]
                },
                "视频URL": {
                    'url': page['video_url'] if page['video_url'] != "" else None
                },
                'Node_id': {
                    'rich_text': [
                        {
                            'text': {
                                'content': page['note_id']
                            }
                        }
                    ]
                },
                'Type': {
                    'select': {
                        'name': page['type']
                    }
                },
                "点赞数": {
                    "number": int(page['liked_count'])
                },
                "收藏数": {
                    "number": int(page['collected_count'])
                },
                "评论数": {
                    "number": int(page['comment_count'])
                },
                "转发数": {
                    "number": int(page['share_count'])
                },
                '发布地': {
                    'select': {
                        'name': page['ip_location'] if page['ip_location'] != "" else "未知"
                    }
                },
                "作者头像": {
                    'url': page['avatar']
                },
                "笔记URL": {
                    'url': page['note_url']
                },
                "创建时间": {
                    "date": {
                        "start": page['time']
                    }
                },
                "更新时间": {
                    "date": {
                        "start": page['last_update_time']
                    }
                },
                "上次修改时间": {
                    "date": {
                        "start": page['last_modify_ts'],
                    }
                },
                '关键词': {
                    'select': {
                        'name': page['keyword']
                    }
                },
                "标签": {
                    "multi_select": page['tags']
                },
            }
        )
        return new_page

    """
    删除页面内容
    """

    def delete_page_content(self, page_id):
        del_block = global_notion.blocks.delete(block_id=page_id)
        print(del_block)

    """
    删除重复的页面-保留最新的页面
    """

    def delete_duplicate_page(self, page_list, property_name):
        property_name_set = set()
        for page in page_list:
            if page["object"] == "page":
                for key, value in page["properties"].items():
                    if key == property_name:
                        text_value = value['rich_text'][0]['text']['content']
                        if text_value in property_name_set:
                            self.delete_page_content(page["id"])
                        else:
                            # todo-fwh-获取富文本类型
                            property_name_set.add(value['rich_text'][0]['text']['content'])

    """
    获取页面指定属性的值，入参为属性名
    """

    def get_page_properties(self, page_list, property_name):
        property_name_set = set()
        for page in page_list:
            if page["object"] == "page":
                for key, value in page["properties"].items():
                    if key == property_name:
                        # todo-fwh-获取富文本类型
                        property_name_set.add(value['rich_text'][0]['text']['content'])
        print(property_name_set)
        return property_name_set


def notion_data_save(client, pages,global_config_keyword):
    # 插入notion的数据保存文件中
    file_path = os.path.join(os.path.dirname(__file__), "notion-xhs.json")
    with open(file_path, 'a') as f:
        for page in pages:
            if page is not None:
                # 时间格式化
                page['time'] = time_fromat(page['time'])
                page['last_modify_ts'] = time_fromat(page['last_modify_ts'])
                page['last_update_time'] = time_fromat(page['last_update_time'])
                # page['keyword'] = config.KEYWORDS
                page['keyword'] = global_config_keyword
                # 标签处理
                tag_list_array = page['tag_list'].split(',')
                data = {"multi_select": []}
                if len(tag_list_array) == 1:
                    data["multi_select"].append({"name": 'default'})
                else:
                    for item in tag_list_array:
                        data["multi_select"].append({"name": item})

                page['tags'] = data["multi_select"]
                # 保存Notion
                new_page = client.create_page(page)

                page_id = new_page["id"]
                node_id = page['note_id']
                insert_notion_data = {'page_id': page_id, 'node_id': node_id}
                json.dump(insert_notion_data, f)
                f.write('\n')
                print(f'记录Notion.Json node_id:{node_id}')
        # 关闭文件
        f.close()


# 读取文件中Notion已保存的数据
def get_message_ids():
    message_ids = set()
    file_name = "notion-xhs.json"
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


def get_json_files():
    # 获取上一级目录同级目录的json文件
    current_file_path = os.path.abspath(__file__)
    parent_dir_path = os.path.dirname(current_file_path)
    grandparent_dir_path = os.path.dirname(parent_dir_path)
    data_dir_path = os.path.join(grandparent_dir_path, "data/xhs/json")
    json_files = [os.path.join(data_dir_path, f) for f in os.listdir(data_dir_path) if f.endswith('.json')]
    # 打印找到的所有 JSON 文件路径
    file_paths = []
    for json_file in json_files:
        file_paths.append(json_file)
    return file_paths


def parse_json_files(exist_ids, filename):
    # 文件是否存在
    if not os.path.exists(filename):
        return
    pages = []
    with open(filename) as f:
        rows = json.load(f)
        # for line in f:
        #     rows = json.loads(line)
        for row in rows:
            # 唯一ID
            note_id = row['note_id']
            # 判断数据是否存在
            if note_id in exist_ids:
                continue
            page = {
                'note_id': note_id,
                'type': row['type'],
                'title': row['title'],
                'desc': row['desc'],
                'video_url': row['video_url'],
                'time': row['time'],
                'last_update_time': row['last_update_time'],
                'user_id': row['user_id'],
                'nickname': row['nickname'],
                'avatar': row['avatar'],
                'liked_count': convert_to_integer(row['liked_count']),
                'collected_count': convert_to_integer(row['collected_count']),
                'comment_count': convert_to_integer(row['comment_count']),
                'share_count': convert_to_integer(row['share_count']),
                'ip_location': row['ip_location'],
                'image_list': row['image_list'],
                'tag_list': row['tag_list'],
                'tag_list': row['tag_list'],
                'last_modify_ts': row['last_modify_ts'],
                'note_url': row['note_url'],
            }
            pages.append(page)
    return pages

def convert_to_integer(s):
    """数字转化"""
    if '万' in s:
        # 去掉 '万' 并转换为浮点数，然后乘以 10000
        number = float(s.replace('万', '')) * 10000
    else:
        number = float(s)
    return int(number)

def main(keyword:None):
    '''
    1. 加载Json数据
    2. 解析Json数据
    3. 数据存储Notion-xhs中
    4. 存储完毕,删除Json文件
    '''
    client = NotionClient()
    json_files = get_json_files()
    exist_ids = get_message_ids()
    for file_path in json_files:
        if "contents" in file_path:
            # 正文
            pages = parse_json_files(exist_ids, file_path)
            notion_data_save(client, pages, keyword)
        elif "comments" in file_path:
            print('评论')
        # 删除文件
        os.remove(file_path)
        print(f'[文件删除:{file_path}]')


if __name__ == '__main__':
    main('英语资料')
