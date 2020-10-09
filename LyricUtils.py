import re
import os
import chardet


# 判断文件编码
def get_txt_encoding(txt_path):
    with open(txt_path, 'rb') as f:
        str_bytes = f.read()
        encoding = chardet.detect(str_bytes)['encoding']
    return encoding


# 将歌词时间戳字符串转为秒数，歌词文件要符合lrc格式
def get_lyric_seconds(lyric_time_str):
    fen = int(lyric_time_str[0:2])
    secs = int(lyric_time_str[3:5])
    return fen * 60 + secs


# 获得歌词所在秒数列表和对应的歌词字符串字典
def read_lyric(lyric_path):
    if not os.path.exists(lyric_path):
        return {}

    lyric_str_dirt = {}
    txt_encoding = get_txt_encoding(lyric_path)
    with open(lyric_path, "r", encoding=txt_encoding) as f:
        lyric_list = f.readlines()
    for lyric_line in lyric_list:
        lyric_line = lyric_line.replace("\r", "")
        lyric_line = lyric_line.replace("\n", "")
        times = re.findall(r'(\d{2}:\d{2}[:|.]\d{2})+', lyric_line)
        times = re.findall(r'(\d{2}:\d{2})+', lyric_line) if not times else times
        if times:
            lyric_str = lyric_line[lyric_line.rindex("]")+1:]
            if lyric_str:
                for t in times:
                    lyric_str_dirt[get_lyric_seconds(t)] = lyric_str

    return lyric_str_dirt
