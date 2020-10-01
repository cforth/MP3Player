import re
import os


# 将歌词时间戳字符串转为秒数，字符串格式为 01:56.43
def get_lyric_seconds(lyric_time_str):
    fen = int(lyric_time_str[0:2])
    secs = int(lyric_time_str[3:5])
    return fen * 60 + secs


# 获得歌词所在秒数列表和对应的歌词字符串字典
def read_lyric(lyric_path):
    if not os.path.exists(lyric_path):
        return {}

    lyric_str_dirt = {}
    with open(lyric_path, "r", encoding="utf-8") as f:
        lyric_list = f.readlines()
    for l in lyric_list:
        lyric_str = l[10:].replace("\n", "")
        if re.match(r'\[\d\d:\d\d\.\d\d]*', l):
            if lyric_str:
                lyric_str_dirt[get_lyric_seconds(l[1:9])] = lyric_str
    return lyric_str_dirt


# print(read_lyric("./lyric/展展与罗罗 - 沙漠骆驼.lrc"))
