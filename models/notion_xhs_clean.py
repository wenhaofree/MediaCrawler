from notion_client import Client


class notion_client:
    def __init__(self):
        global global_notion
        global global_database_id
        global_token = "secret_SGSgYlUHk8knQRLcwJr1alzjzVTwXFwrr0UDBawy0Sw"
        global_database_id = "71a27ce80d274ff5ba0637dbca1ed766"
        global_notion = Client(auth=global_token)
        print('开始Notion自动化获取数据...')

    """
    获取所有页面
    """

    def get_all_pages(self, database_id):
        results = []
        start_cursor = None
        while True:
            response = global_notion.databases.query(
                database_id=database_id,
                start_cursor=start_cursor,
                page_size=100,  # Maximum page size
            )
            results.extend(response['results'])
            # temp 处理重复数据
            self.delete_duplicate_page(results, "Node_id")
            start_cursor = response.get('next_cursor')
            if not start_cursor:
                break
        return results

    """
    删除页面内容
    """

    def delete_page_content(self, page_id):
        del_block = global_notion.blocks.delete(block_id=page_id)
        # print('delete:' + del_block['id'])

    """
    删除重复的页面-保留最新的页面
    """

    def delete_duplicate_page(self, page_list, property_name):
        property_name_set = set()
        for page in page_list:
            if page["object"] == "page":
                for key, value in page["properties"].items():
                    if key == property_name:
                        # 获取富文本类型的值
                        text_value = value['rich_text'][0]['text']['content']
                        if text_value in property_name_set:
                            print('delete:' + text_value)
                            try:
                                self.delete_page_content(page["id"])
                            except Exception as e:
                                print(f'删除异常: {e}')
                        else:
                            property_name_set.add(text_value)


if __name__ == '__main__':
    """
    1. 清理冗余重复数据 头条数据
    """
    client = notion_client()
    client.get_all_pages(global_database_id)
