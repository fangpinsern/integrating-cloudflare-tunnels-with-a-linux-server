#!/usr/bin/env python3

import argparse
import requests
import getpass
import json

Constant_TYPE_GET = 'GET'
Constant_TYPE_DELETE = 'DELETE'

Constant_CONFIG_CREATE = 'CREATE'
Constant_CONFIG_REMOVE = 'REMOVE'

parser = argparse.ArgumentParser()

parser.add_argument("--type", help="GET | DELETE", required=True)
parser.add_argument("-p", "--port", help="Port is used as identification", required=True)
args = parser.parse_args()
API_KEY = <INSERT_API_KEY>

args_TYPE=args.type
args_PORT=args.port

def is_valid_type(type_arg):
  return type_arg == Constant_TYPE_GET or type_arg == Constant_TYPE_DELETE

HEADERS = {
  'Authorization': f'Bearer {API_KEY}',
  'Content-Type': 'application/json'
}

# REQUEST_LINK = 'https://api.cloudflare.com/client/v4/user/tokens/verify'

# response = requests.get(REQUEST_LINK, headers=HEADERS)
# response_code = response.status_code
# response_json = response.json()
# print(response_json['result'])

# print(args)
# print("helloworld")

ACCOUNT_IDENTIFIER=<INSERT_ACCOUNT_IDENTIFIER>
TUNNEL_ID=<INSERT_TUNNEL_ID>
ZONE_IDENTIFIER=<INSERT_ZONE_IDENTIFIER>
TUNNEL_DNS_LINK=f'{TUNNEL_ID}.cfargotunnel.com'

def get_tunnel_config():
  GET_CONFIG_LINK = f'https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_IDENTIFIER}/cfd_tunnel/{TUNNEL_ID}/configurations'
  get_response = requests.get(GET_CONFIG_LINK, headers=HEADERS)
  get_response_STATUS = get_response.status_code
  
  if not get_response.ok:
    return {}

  get_response_JSON = get_response.json()

  # print(get_response_JSON['result']['config']['ingress'][0])
  return get_response_JSON['result']['config'] 

def filter_tunnel_config(tunnel_config, port):
  SERVICE_NAME = f'http://localhost:{port}'

  if 'ingress' not in tunnel_config:
    return {}
  ingress_config = tunnel_config['ingress']
  
  for record in ingress_config:
    if record['service'] == SERVICE_NAME:
      return record

  return {} 

def get_hostname(port_config):
  if 'hostname' in port_config:
    return port_config["hostname"]
  return ''

def is_valid_ingress_config(config):
  if 'service' not in config:
    print('invalid ingress config. no service key')
    return False
  if 'hostname' not in config:
    print('invalid ingress config. no hostname key')
    return False
  if 'originRequest' not in config:
    print('invalid ingress config. no originRequest key')
    return False
  return True

def new_ingress_config(port, hostname, originRequest={}):
  return {
    'service': f'http://localhost:{port}',
    'hostname': hostname,
    'originRequest': originRequest
  }

def build_ingress_config(existing_config, change_config, action=""):
    config_valid = is_valid_ingress_config(change_config)
    if not config_valid:
      return existing_config

    if action == Constant_CONFIG_CREATE:
      old_ingress = []
      if 'ingress' in existing_config:
        old_ingress = existing_config['ingress']

      old_ingress.insert(len(old_ingress) - 1,change_config)
      existing_config['ingress'] = old_ingress
      return existing_config
    
    if action == Constant_CONFIG_REMOVE:
      if 'ingress' not in existing_config:
        print('No config to remove')
        return existing_config
      existing_config['ingress'] = [config for config in existing_config['ingress'] if config['service'] != change_config['service']]
      print(existing_config['ingress'])

    return existing_config

def put_tunnel_config(new_config):
  PUT_CONFIG_LINK = f'https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_IDENTIFIER}/cfd_tunnel/{TUNNEL_ID}/configurations'

  put_response = requests.put(PUT_CONFIG_LINK, data=json.dumps({'config':new_config}), headers=HEADERS)

  if not put_response.ok:
    print('Error occured when updating configs.')
    print(put_response.json())
    return {}

  put_response_JSON = put_response.json()

  print('tunnel config updated')
  return put_response_JSON['result']['config']

def build_dns_record(record_name, record_content, record_type="CNAME"):
  return {
    "type": record_type,
    "name": record_name,
    "content": record_content,
    "ttl": 1,
    "comment": f'{record_name} specific domain',
    "proxied": True
  }

def get_dns_record(record_name, record_type="CNAME"):
  GET_DNS_RECORD_LINK = f'https://api.cloudflare.com/client/v4/zones/{ZONE_IDENTIFIER}/dns_records'
  GET_PARAMS = {
    "type": record_type,
    "name": record_name
  }

  get_response = requests.get(GET_DNS_RECORD_LINK, params=GET_PARAMS, headers=HEADERS)
  if not get_response.ok:
    print('Error occured when getting dns record.')
    print(get_response.json())
    return []

  get_response_JSON = get_response.json()
  return get_response_JSON['result']

def create_dns_record(dns_record):
  CREATE_DNS_RECORD_LINK = f'https://api.cloudflare.com/client/v4/zones/{ZONE_IDENTIFIER}/dns_records'
  post_response = requests.post(CREATE_DNS_RECORD_LINK, data=json.dumps(dns_record), headers=HEADERS)
  if not post_response.ok:
    print('error occured when creating dns record. no dns record created')
    print(post_response.json())
    return {}

  post_response_JSON = post_response.json()
  print('new config added')
  return post_response_JSON['result']

def delete_dns_record(dns_identifier_id):
  DELETE_DNS_RECORD_LINK = f'https://api.cloudflare.com/client/v4/zones/{ZONE_IDENTIFIER}/dns_records/{dns_identifier_id}'
  delete_response = requests.delete(DELETE_DNS_RECORD_LINK, headers=HEADERS)
  if not delete_response.ok:
    print('error occured when creating dns record. no dns record created')
    print(delete_response.json())
    return {}
  delete_response_JSON = delete_response.json()
  print(f'deleted dns record {delete_response_JSON["result"]["id"]}')
  return delete_response_JSON["result"]

if args_TYPE == Constant_TYPE_GET:
  HOSTNAME=''
  TUNNEL_CONFIG = get_tunnel_config()
  PORT_CONFIG = filter_tunnel_config(TUNNEL_CONFIG, args_PORT)
  if bool(PORT_CONFIG):
    print("config for port exists. do nothing")
    HOSTNAME = get_hostname(PORT_CONFIG)
    # print(HOSTNAME)
  else:
    # port config does not exist
    new_hostname = f'{getpass.getuser()}.pinsern.com'
    new_config = new_ingress_config(args_PORT, new_hostname)
    # print(new_config)
    put_body = build_ingress_config(TUNNEL_CONFIG, new_config, Constant_CONFIG_CREATE)
    updated_tunnel_config = put_tunnel_config(put_body)
    PORT_CONFIG = filter_tunnel_config(updated_tunnel_config, args_PORT)
    HOSTNAME = get_hostname(PORT_CONFIG)

  # CREATE NEW DNS RECORD
  check_dns_records = get_dns_record(HOSTNAME)
  if len(check_dns_records) == 0:
    print("no dns record")
    new_dns_record = build_dns_record(HOSTNAME, TUNNEL_DNS_LINK)
    result = create_dns_record(new_dns_record)
  
  print(f'https://{HOSTNAME}')

if args_TYPE == Constant_TYPE_DELETE:
  TUNNEL_CONFIG = get_tunnel_config()
  CONFIG_TO_REMOVE = filter_tunnel_config(TUNNEL_CONFIG, args_PORT)
  if not bool(CONFIG_TO_REMOVE):
    print("port does not have configs. do nothing")
  else:
    put_body = build_ingress_config(TUNNEL_CONFIG, CONFIG_TO_REMOVE, Constant_CONFIG_REMOVE)
    updated_tunnel_config = put_tunnel_config(put_body)
    if bool(updated_tunnel_config):
      HOSTNAME_TO_REMOVE = CONFIG_TO_REMOVE["hostname"]
      print(f'{HOSTNAME_TO_REMOVE} has been removed')

      # DELETE DNS RECORD
      check_dns_records = get_dns_record(HOSTNAME_TO_REMOVE)
      print(HOSTNAME_TO_REMOVE)
      if len(check_dns_records) == 0:
        print("no dns record to delete")
      else:
        record_id = check_dns_records[0]['id']
        deleted_dns_record = delete_dns_record(record_id)
