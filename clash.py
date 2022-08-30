# __coding__:utf-8

from http import server
import requests
import base64
import re
import json
from http.server import BaseHTTPRequestHandler
from urllib import parse
from http.server import HTTPServer


# 将jms subscription转换为clash可用的订阅链接，并提供订阅更新服务。

# 处理ss://协议信息 [name, server, port, type, cipher, password]
def handleSS(data):
    data = data.replace('ss://','').split('#')
    enc = data[0]
    # base64 padding
    if len(enc)%4 != 0:
        enc = enc.ljust(len(enc)+4-len(enc)%4, '=')
    name = data[1].split('@')[1]
    dec = base64.b64decode(enc).decode('utf-8').split(':')
    cipher, port = dec[0], dec[2]
    [password, server] = dec[1].split('@')

    return {'name':name, 'server':server, 'port':port, 'type':'ss', 'cipher':cipher, 'password':password}

# 处理v2ray://协议信息 [name, server, port, type, uuid, alterId, cipher, tls]
def handleV2ray(data):
    enc = data.replace('vmess://','')
    if len(enc)%4 != 0:
        enc = enc.ljust(len(enc)+4-len(enc)%4, '=')
    dec = base64.b64decode(enc).decode('utf-8')
    conf = json.loads(dec)
    return {'name':conf['ps'].split('@')[1], 'server':conf['add'], 'port':conf['port'], 'type':'vmess', 'uuid':conf['id'], 'alterId':conf['aid'], 'cipher':'auto', 'tls':'false'}

# 下载jms订阅并提取出server、port、password、encrypt等
def getSubs(url):
    raw_config = requests.get(url)
    if raw_config.status_code == 200:
        print('success')
    else:
        print('invalid subscription url')
        return 0
    
    decode_config = base64.b64decode(raw_config.content).decode('utf-8')
    _config = decode_config.splitlines()
    config = []
    
    for d in _config:
        if d.startswith('ss://'):
            c = handleSS(d)
            config.append(c)
        elif d.startswith('vmess://'):
            c = handleV2ray(d)
            config.append(c)
    
    return config

# 根据server信息生成clash可用的config文件
def generateClashConfig(config):
    with open('Template.yaml', 'r') as fp:
        config_template = fp.read()
    count = 1
    for d in config:
        print(d)
        if d['type'] == 'ss':
            config_template = config_template.replace('NAME_'+str(count), d['name'])
            config_template = config_template.replace('SERVER_'+str(count), d['server'])
            config_template = config_template.replace('PORT_'+str(count), d['port'])
            config_template = config_template.replace('TYPE_'+str(count), d['type'])
            config_template = config_template.replace('CIPHER_'+str(count), d['cipher'])
            config_template = config_template.replace('PASSWORD_'+str(count), d['password'])
            count += 1
        elif d['type'] == 'vmess':
            config_template = config_template.replace('NAME_'+str(count), d['name'])
            config_template = config_template.replace('SERVER_'+str(count), d['server'])
            config_template = config_template.replace('PORT_'+str(count), d['port'])
            config_template = config_template.replace('TYPE_'+str(count), d['type'])
            config_template = config_template.replace('UUID_'+str(count), d['uuid'])
            config_template = config_template.replace('AID_'+str(count), str(d['alterId']))
            count += 1
    return config_template
    
class GetHandler(BaseHTTPRequestHandler):
    def __init__(self):
        self.secret = '' # 密钥
        self.url = '' # 订阅链接 Subscription

    def do_GET(self):
        parsed_path = parse.urlparse(self.path)
        message_parts = [
            'CLIENT VALUES:',
            'client_address={} ({})'.format(
                self.client_address,
                self.address_string()),
            'command={}'.format(self.command),
            'path={}'.format(self.path),
            'real path={}'.format(parsed_path.path),
            'query={}'.format(parsed_path.query),
            'request_version={}'.format(self.request_version),
            '',
            'SERVER VALUES:',
            'server_version={}'.format(self.server_version),
            'sys_version={}'.format(self.sys_version),
            'protocol_version={}'.format(self.protocol_version),
            '',
            'HEADERS RECEIVED:',
        ]
        path = parsed_path.path
        query = parsed_path.query
        print(path, query)
        if path == '/subccc' and query == self.secret:
            config = self.getConfig()
            self.send_response(200)
            self.send_header('Content-Type',
                            'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(config.encode('utf-8'))
        else:
            self.send_response_only(404)

    def getConfig(self):
        config = getSubs(self.url)
        return generateClashConfig(config)

# 提供clash订阅服务
def clashSubs():
    pass

if __name__ == '__main__':
    # http://127.0.0.1:8082/subccc?SECRET
    server = HTTPServer(('localhost', 8082), GetHandler)
    print('Starting server, use <Ctrl-C> to stop')
    server.serve_forever()
