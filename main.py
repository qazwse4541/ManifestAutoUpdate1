import json
import logging
import os
import re
import argparse
from reptile import ManifestAutoUpdate, result_data, dlc
from steam.utils.tools import upload_aliyun
from steam.client.cdn import temp, CDNClient


def write_to_file(file_path, content, mode='a+', encoding='utf-8'):
    # 将文件当前内容读取到集合中，以便于判断新内容是否存在
    existing_lines = set()
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding=encoding) as fr:
            existing_lines = set(fr.readlines())

    with open(file_path, mode, encoding=encoding) as fw:
        for line in content:
            # 检查line是否存在，如果不存在再写入
            if f"{line}\n" not in existing_lines or f"{line}" not in existing_lines:
                fw.write(f"{line}\n")


def read_vdf_config(config_path, pattern=r'"(\d+)"\s+{\s+"DecryptionKey"\s+"([\da-f]+)"\s+}'):
    if not os.path.exists(config_path):
        return []

    with open(config_path, 'r', encoding='utf-8') as fr:
        return re.findall(pattern, fr.read())


def upload_file(local_path, remote_path):
    try:
        upload_aliyun(remote_path, local_path)
        log.info(f"Upload successful: {local_path}")
    except Exception as e:
        log.error(f"Upload failed for {local_path}. Error: {str(e)}")


def cleanup_temp_files(files):
    for file in files:
        os.remove(file)
        log.info(f"Temporary file removed: {file}")


def end(app_id, json_data):
    if json_data is None:
        return

    result_path = f"data/depots/{app_id}/{app_id}.txt"
    config_path = f"data/depots/{app_id}/config.vdf"
    app_id_cache_path = f"data/depots/{app_id}/{app_id}_cache.txt"

    # 将数据写入app_id.txt
    write_to_file(result_path, json_data['iuser'])

    # 如果 config.vdf 存在，则添加解密密钥和票证数据
    matches = read_vdf_config(config_path)
    if matches:
        write_to_file(result_path, [f"{match[0]}----{match[1]}" for match in matches] + json_data["ticket"])

    logging.info(f"{app_id}.txt written successfully")

    # 写入app_id_cache.txt并上传文件
    with open(app_id_cache_path, 'a+', encoding='utf-8') as fc:
        for root, dirs, files in os.walk(f"data/depots/{app_id}"):
            for file in files:
                if file.endswith(".manifest"):
                    manifest_path = os.path.join(root, file)
                    upload_file(manifest_path, f"depotcache/{app_id}/{file}")
                    fc.write(file.replace(".manifest", "") + "\n")

    logging.info(f"{app_id}_cache.txt written successfully")

    # 上传结果文件
    upload_file(result_path, f"gKeyConfig/{app_id}.txt")
    upload_file(app_id_cache_path, f"depotcache/{app_id}/{app_id}.txt")

    # 清理临时文件
    cleanup_temp_files([app_id_cache_path])


# 初始化日志记录器
log = logging.getLogger('ManifestAutoUpdate')

# Assume CDNClient.temp_json already contains the required JSON data
# end('123456', CDNClient.temp_json)  # Replace with actual app_id and JSON data

# def end(app_id):
#     json_data = CDNClient.temp_json
#     if json_data is not None:
#         # 创建app_id.txt并追加数据
#         result_path = f"data/depots/{app_id}/{app_id}.txt"
#         fw = open(result_path, 'a+', encoding='utf-8')
#         for iuser in json_data['iuser']:
#             fw.write(f"{iuser}\n")
#             fw.flush()  # 刷新文件缓冲区
#         # 如果data/depots/{app_id}/config.vdf存在,则打开,转为json格式,并追加数据
#         """
#         这块代码是为了获取config.vdf中的DecryptionKey
#         """
#         config_path = f"data/depots/{app_id}/config.vdf"
#         if os.path.exists(config_path):
#             fr = open(config_path, 'r', encoding='utf-8')
#             # 定义一个正则表达式模式
#             pattern = r'"(\d+)"\s+{\s+"DecryptionKey"\s+"([\da-f]+)"\s+}'
#             # 在 VDF 数据中查找匹配的键值对
#             matches = re.findall(pattern, fr.read())
#
#             for match in matches:
#                 fw.write(f"{match[0]}----{match[1]}\n")
#                 fw.flush()  # 刷新文件缓冲区
#             # 结尾添加 ticket
#             for ticket in json_data["ticket"]:
#                 fw.write(f"{ticket}\n")
#                 fw.flush()  # 刷新文件缓冲区
#             log.info(f"END {match[0]}.txt written successfully")
#             fw.close()
#             # 开始将data 字典中的 dlc 和 manifest_gid_list 写入到app_id_cache.txt中
#             # log.info(f"dep_gid_data: {dep_gid_data}")
#             app_id_cache_path = f"data/depots/{app_id}/{app_id}_cache.txt"
#             fc = open(app_id_cache_path, 'a+', encoding='utf-8')
#             # 遍历目录下的文件和子目录
#             for root, dirs, files in os.walk(f"data/depots/{app_id}"):
#                 for file in files:
#                     # 检查文件后缀名是否为 .manifest
#                     if file.endswith(".manifest"):
#                         upload_aliyun(f"depotcache/{app_id}/{file}", f"data/depots/{app_id}/{file}")
#                         log.info(f"Done,{file} upload success")
#                         fc.write(file.replace(".manifest", "") + "\n")
#             # 继续遍历
#             fc.flush()
#             fc.close()
#             log.info(f"END {app_id}_cache.txt written successfully")
#             try:
#                 upload_aliyun(f"gKeyConfig/{app_id}.txt", result_path)
#                 upload_aliyun(f"depotcache/{app_id}/{app_id}.txt", app_id_cache_path)
#                 log.info(f"Done,data uploaded successfully")
#             except Exception as e:
#                 log.error(f"Completed,{app_id}_cache.txt upload failed. Error: {str(e)}")
#
#             # 清理临时文件
#             os.remove(app_id_cache_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--credential-location', default=None)
    parser.add_argument('-l', '--level', default='INFO')
    parser.add_argument('-p', '--pool-num', type=int, default=8)
    parser.add_argument('-r', '--retry-num', type=int, default=3)
    parser.add_argument('-t', '--update-wait-time', type=int, default=86400)
    parser.add_argument('-k', '--key', default=None)
    parser.add_argument('-x', '--x', default=None)
    parser.add_argument('-i', '--init-only', action='store_true', default=False)
    parser.add_argument('-C', '--cli', action='store_true', default=False)
    parser.add_argument('-P', '--no-push', action='store_true', default=False)
    parser.add_argument('-u', '--update', action='store_true', default=False)
    parser.add_argument('-a', '--app-id', dest='app_id_list', action='extend', nargs='*')
    parser.add_argument('-U', '--users', dest='user_list', action='extend', nargs='*')
    args = parser.parse_args()
    temp["temp_id"].append(args.app_id_list[0])  # 将app_id赋给cdn.py
    log.info(args)
    ManifestAutoUpdate(args.credential_location, level=args.level, pool_num=args.pool_num, retry_num=args.retry_num,
                       update_wait_time=args.update_wait_time, key=args.key, init_only=args.init_only,
                       cli=args.cli, app_id_list=args.app_id_list, user_list=args.user_list).run(update=args.update)
    format_url_list = [
        "https://gh-proxy.com/https://raw.githubusercontent.com/heyong5454/ManifestAutoUpdate/{sha}/{path}",
        "https://github.moeyy.xyz/https://raw.githubusercontent.com/heyong5454/ManifestAutoUpdate/{sha}/{path}",
        "https://ghproxy.com/https://raw.githubusercontent.com/heyong5454/ManifestAutoUpdate/{sha}/{path}",
        "https://hub.fgit.ml/heyong5454/ManifestAutoUpdate/raw/{sha}/{path}",
        "https://hub.yzuu.cf/heyong5454/ManifestAutoUpdate/raw/{sha}/{path}",
        "https://raw.kgithub.com/heyong5454/ManifestAutoUpdate/{sha}/{path}",
        "https://hub.nuaa.cf/heyong5454/ManifestAutoUpdate/raw/{sha}/{path}"
    ]
    data = {}
    for _app_id in result_data:
        depot_id_list = []
        manifest_gid_list = []
        data[_app_id] = {
            "app_id": _app_id,
            "depot_id_list": [],
            "dlc": [],
            "format_url_list": format_url_list,
            "manifest_gid_list": [],
            "show": True
        }

        for depot_id, gid_set in result_data[_app_id].items():
            for gid in gid_set:
                depot_id_list.append(depot_id)
                manifest_gid_list.append(gid)
        data[_app_id]["depot_id_list"] = depot_id_list
        data[_app_id]["manifest_gid_list"] = manifest_gid_list

        log.info(f"manifest_gid_list: {manifest_gid_list}")
        if _app_id in dlc:
            data[_app_id]["dlc"] = dlc[_app_id]
    log.info(json.dumps(data, sort_keys=True, indent=4, separators=(',', ': ')))

    # 爬虫进程结束,开始处理数据
    end(args.app_id_list[0], CDNClient.temp_json)
