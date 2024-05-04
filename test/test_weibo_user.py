import requests

def getUserInfo():
    # 设置参数
    params = {'luicode': '10000011', 'lfid': '231583', 'type': 'uid', 'value': '2705169595', 'containerid': '1076032705169595','page':1}

    # 设置请求头
    headers = {'User-Agent': 'Mozilla/5.0'}

    # 设置请求Cookie
    cookies = {'XSRF-TOKEN': '360c84', 'SSOLoginState': '1710920189'}

    # 发送带有参数、请求头和请求Cookie的GET请求
    response = requests.get('https://m.weibo.cn/api/container/getIndex', params=params, headers=headers, cookies=cookies)

    # 打印响应内容
    print(response.text)

def main():
    getUserInfo()
if __name__ == '__main__':
    main()
