import time
import math
import datetime
import threading
import pygame
import os
import random
import eyed3
import hashlib
import operator
from eyed3 import mp3
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox
import tkinter.simpledialog
from json2gui import *
from LyricUtils import read_lyric


# 字符串MD5生成
def get_str_md5(string):
    my_hash = hashlib.md5()
    my_hash.update(string.encode('utf-8'))
    return my_hash.hexdigest()


# 音乐播放器类，使用pygame实现
class Player(threading.Thread):
    def __init__(self, file_path, volume=1.0, start_time=0.0, master=None):
        threading.Thread.__init__(self)
        # 传入主窗口的指针，用于触发主窗口事件(若有)
        self.master = master
        self.file_path = file_path
        # 音乐播放起点
        self.start_time = start_time
        # 用于控制音乐播放与停止
        self.stop_state = False
        # 用于控制音乐的暂停和恢复
        self.pause_state = False
        # 控制默认音量
        self.volume = volume
        # 初始化mixer
        pygame.mixer.init()  # 初始化音频
        self.track = pygame.mixer.music

    def set_volume(self, volume):
        self.volume = volume
        self.track.set_volume(self.volume)

    def get_volume(self):
        return self.volume

    def run(self):
        try:
            file = self.file_path
            self.track.load(file)  # 载入音乐文件
            self.track.set_volume(self.volume)  # 设置音量
            self.track.play(start=self.start_time)  # 开始播放
        except Exception as e:
            logging.warning(e)
            if self.master:
                self.master.event_generate("<<MusicError>>", when="tail")

        while True:
            time.sleep(1)
            # 若停止播放或播放结束，则结束这个线程
            if self.stop_state:
                self.track.stop()  # 停止播放
                return
            elif not self.track.get_busy():
                if self.master:
                    self.master.event_generate("<<CouldMusicStop>>", when="tail")
                return
            elif not self.stop_state and self.pause_state:
                self.track.pause()  # 暂停播放
            elif not self.stop_state and not self.pause_state:
                self.track.unpause()  # 恢复播放


# 窗口类
class Window(ttk.Frame):
    def __init__(self, ui_json, master=None):
        super().__init__(master, padding=2)
        # 初始化音乐播放器对象的引用
        self.player = None
        # 初始化按钮的图片
        self.play_img = tk.PhotoImage(file="./resources/play.png")
        self.stop_img = tk.PhotoImage(file="./resources/stop.png")
        self.pause_img = tk.PhotoImage(file="./resources/pause.png")
        self.folder_img = tk.PhotoImage(file="./resources/folder.png")
        self.next_play_img = tk.PhotoImage(file="./resources/next_play.png")
        self.prev_play_img = tk.PhotoImage(file="./resources/prev_play.png")
        self.volume_on_img = tk.PhotoImage(file="./resources/volume_on.png")
        self.volume_off_img = tk.PhotoImage(file="./resources/volume_off.png")
        self.music_search_img = tk.PhotoImage(file="./resources/search.png")
        # 从json自动设置UI控件
        create_ui(self, ui_json)
        # 从json自动绑定事件
        create_all_binds(self, ui_json)
        # 顶层窗口事件绑定
        self.bind_window_event()
        # 初始化音乐循环下拉列表，设置默认的音量值
        self.init_default_play_option()
        # 初始化音乐播放列表窗口
        self.init_music_list_window()
        self.init_menu()
        # 保存音乐播放的文件夹
        self.music_dir_path = None
        # 初始化音乐播放列表
        self.music_play_list = []
        # 保存当前正在播放的音乐地址
        self.current_music_path = None
        # 保存收藏的音乐行号
        self.star_music_index_list = []
        self.star_music_path_list = []
        # 初始化控制按钮图片属性
        self.init_control_button_img()
        # 初始化音乐播放时间
        self.__dict__["playTime"].set("00:00")
        # 初始化音乐时长
        self.music_duration = 0
        self.__dict__["musicTime"].set("00:00")
        # 初始化音乐播放开始时间
        self.start_seconds = 0.0
        # 初始化音乐播放时间戳
        self._play_current_time = datetime.datetime.now()
        # 音乐播放时间定时器
        self._play_time_count_timer = None
        self._player_running = False
        # 设置其他按钮图片属性
        self.__dict__["fileFromButton"]["image"] = self.folder_img
        self.__dict__["prevMusicButton"]["image"] = self.prev_play_img
        self.__dict__["nextMusicButton"]["image"] = self.next_play_img
        self.__dict__["volumeOnOffButton"]["image"] = self.volume_on_img
        self.__dict__["searchButton"]["image"] = self.music_search_img
        self.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(4, weight=1)
        # 记录歌曲播放次数的字典
        self.music_play_times_dict = {}
        # 记录热度播放顺序的列表
        self.favor_music_list = []
        # 读取配置文件
        self.read_config("./configs/config.json")
        # 记录播放过的音乐行号
        self.music_play_history_ids = []
        # 记录歌词字典
        self.lyric_dict = {}
        # 记录等待播放的列表
        self.wait_play_list = []

    def init_menu(self):
        # 音乐列表窗口右键菜单
        self.muisc_list_menu = tk.Menu(self, tearoff=0)
        self.muisc_list_menu.add_command(label="添加收藏", command=self.on_add_star_music)
        self.muisc_list_menu.add_command(label="取消收藏", command=self.on_del_star_music)
        self.muisc_list_menu.add_command(label="下一首播放", command=self.add_wait_play_list)
        self.muisc_list_menu.add_separator()
        self.muisc_list_menu.add_command(label="复制名称", command=self.on_copy_music_name)
        music_list = getattr(self, "musicListTreeview")
        music_list.bind("<Button-3>", self.pop_menu)

    def pop_menu(self, event):
        self.muisc_list_menu.post(event.x_root, event.y_root)

    # 初始化音乐循环下拉列表，设置默认的音量值
    def init_default_play_option(self):
        set_combobox_item(self.__dict__["playOptionCombobox"], "单曲播放", True)
        self.__dict__["musicVolumeScale"].set(60)

    # 顶层窗口事件绑定
    def bind_window_event(self):
        # 音乐读取错误或播放完毕时，触发自定义事件
        self.bind("<<MusicError>>", self.music_stop)
        self.bind("<<MusicStop>>", self.music_stop)
        self.bind("<<CouldMusicStop>>", self.could_music_stop)
        # 绑定关闭事件
        self.master.protocol("WM_DELETE_WINDOW", self.close_event)
        # 绑定键盘事件
        self.master.bind("<Key>", self.key_event)
        # 绑定选择播放顺序控件的事件
        self.__dict__["playOptionCombobox"].bind("<Button-1>", self.clear_music_play_history)

    def file_from_button_callback(self, event=None):
        self.save_config("./configs/config.json")
        self.music_play_times_dict = {}
        self.music_dir_path = filedialog.askdirectory()
        self.read_music_play_times(self.music_dir_path)
        self.init_music_list(self.music_dir_path)
        self.read_star_config(self.music_dir_path)
        self.clear_music_play_history()

    def key_event(self, event=None):
        # 摁空格键暂停或恢复音乐播放
        if event.char == " ":
            self.music_pause_restore()
        # 右方向键下一首
        elif event.keycode == 39:
            self.next_music()
        # 左方向键上一首
        elif event.keycode == 37:
            self.prev_music()

    def read_music_play_times(self, music_dir_path):
        self.music_play_times_dict = {}
        # 读取音乐文件夹的收藏列表
        current_music_dir = music_dir_path
        star_music_config_path = os.path.join('./configs', get_str_md5(current_music_dir) + ".json")
        if os.path.exists(star_music_config_path):
            with open(star_music_config_path, "r") as sf:
                star_configs = json.load(sf)
                if star_configs.get("music_play_times_dict") and star_configs["music_play_times_dict"]:
                    for k, v in star_configs["music_play_times_dict"].items():
                        self.music_play_times_dict[self.music_dir_path+'/'+k] = v

    def read_star_config(self, music_dir_path):
        self.star_music_path_list = []
        # 读取音乐文件夹的收藏列表
        current_music_dir = music_dir_path
        star_music_config_path = os.path.join('./configs', get_str_md5(current_music_dir) + ".json")
        if os.path.exists(star_music_config_path):
            with open(star_music_config_path, "r") as sf:
                star_configs = json.load(sf)
                if star_configs.get("star_index_path_list") and star_configs["star_index_path_list"]:
                    for s in star_configs["star_index_path_list"]:
                        self.star_music_path_list.append(self.music_dir_path + '/' + s)
                    for x in self.star_music_path_list:
                        if x in self.music_play_list:
                            star_music_index = self.music_play_list.index(x)
                            self.star_music_index_list.append(star_music_index)
                    self.set_star_music(self.star_music_index_list)

    def read_config(self, config_path):
        if not os.path.exists(config_path):
            return
        with open(config_path, "r") as f:
            configs = json.load(f)
            if configs:
                if configs["music_dir_path"]:
                    self.music_dir_path = configs["music_dir_path"]
                self.read_music_play_times(configs["music_dir_path"])
                self.init_music_list(configs["music_dir_path"], configs["current_music_path"])
                self.__dict__["playOption"].set(configs["playOption"])
                if configs["current_music_path"] in self.music_play_list:
                    current_music_id = self.music_play_list.index(configs["current_music_path"])
                    self.set_music_list_window_selection(current_music_id)
                    self.read_star_config(configs["music_dir_path"])

    def save_config(self, config_path):
        if not os.path.exists("./configs"):
            os.mkdir("./configs")

        if self.music_dir_path:
            configs = dict()
            configs["music_dir_path"] = self.music_dir_path
            configs["current_music_path"] = self.current_music_path
            configs["playOption"] = self.__dict__["playOption"].get()
            star_index_list = sorted(self.star_music_index_list)
            star_index_path_list = []
            for i in star_index_list:
                star_index_path_list.append(os.path.basename(self.music_play_list[i]))
            star_configs = dict()
            star_configs["star_index_path_list"] = star_index_path_list
            music_play_times_dict = dict()
            for k, v in self.music_play_times_dict.items():
                music_play_times_dict[os.path.basename(k)] = v
            star_configs["music_play_times_dict"] = music_play_times_dict
            star_music_config_path = os.path.join('./configs', get_str_md5(self.music_dir_path) + ".json")
            with open(star_music_config_path, "w") as f:
                json.dump(star_configs, f)
            with open(config_path, "w") as f:
                json.dump(configs, f)

    # 记录音乐播放的次数
    def count_music_play_times(self, music_path):
        if self.music_play_times_dict.get(music_path):
            self.music_play_times_dict[music_path] += 1
        else:
            self.music_play_times_dict[music_path] = 1
        self.update_music_play_times(music_path, self.music_play_list)

    # 在顶层窗口关闭时，先结束音乐播放线程
    def close_event(self, event=None):
        quit_result = messagebox.askokcancel('提示', '真的要退出吗？')
        if quit_result:
            self.music_stop()
            self.save_config("./configs/config.json")
            self.master.destroy()

    def init_control_button_img(self, event=None):
        # 设置按钮的图片和文字属性
        self.__dict__["startButton"]["image"] = self.play_img
        self.__dict__["startButton"]["text"] = "播放"
        self.__dict__["stopButton"]["image"] = self.stop_img
        self.__dict__["stopButton"]["text"] = "停止"

    def _format_time(self, all_time):
        min = 60
        if all_time < 60:
            return "00:%.2d" % math.ceil(all_time)
        else:
            mins = divmod(all_time, min)
            return "%.2d:%.2d" % (int(mins[0]), math.ceil(mins[1]))

    def _de_format_time(self, time_str):
        mins = int(time_str[:time_str.index(":")])
        secs = int(time_str[time_str.index(":")+1:])
        return mins * 60 + secs

    # 计算歌曲正在播放的秒数
    def _get_play_time(self):
        current_time = datetime.datetime.now()
        time_obj = current_time - self._play_current_time
        secs = time_obj.seconds + self.start_seconds
        milliseconds = secs * 1000 + time_obj.microseconds / 1000
        return secs, milliseconds

    # 获得当前毫秒数正在播放的歌词
    def _get_current_lyric_str(self, secs):
        if self.lyric_dict.get(secs):
            return self.lyric_dict[secs]
        else:
            return ""

    # 更新内部的定时器
    def _update_timer(self):
        secs, milliseconds = self._get_play_time()
        # 更新进度条
        self.__dict__["music_progress_scale_value"].set(milliseconds/(self.music_duration*10))
        self.__dict__["playTime"].set(self._format_time(secs))
        if self._player_running:
            self._play_time_count_timer = self.after(1000, self._update_timer)
        # 更新歌词
        lyric_str = self._get_current_lyric_str(int(secs))
        if lyric_str:
            self.__dict__["lyric"].set(lyric_str)

    # 启动计时器
    def play_time_count_start(self, event=None, start_seconds=0.0):
        self.start_seconds = start_seconds
        self._play_current_time = datetime.datetime.now()
        self.__dict__["playTime"].set(self._format_time(self.start_seconds))
        self._player_running = True
        # 设置定时器，更新播放时长
        self._play_time_count_timer = self.after(1000, self._update_timer)

    # 停止计时器
    def play_time_count_stop(self, event=None):
        # 停止进度条
        self.start_seconds = 0.0
        self.__dict__["music_progress_scale_value"].set(0.0)
        self.__dict__["playTime"].set(self._format_time(0))
        self._player_running = False
        if self._play_time_count_timer:
            self.after_cancel(self._play_time_count_timer)
        self._play_time_count_timer = None

    # 调整进度条时停止计时器
    def adjust_time_count_stop(self, event=None):
        # 停止进度条
        self.start_seconds = 0.0
        self._player_running = False
        if self._play_time_count_timer:
            self.after_cancel(self._play_time_count_timer)
        self._play_time_count_timer = None

    # 暂停计时器
    def play_time_count_pause(self, event=None):
        self._player_running = False
        if self._play_time_count_timer:
            self.after_cancel(self._play_time_count_timer)
        self.play_pause_time = datetime.datetime.now()

    # 恢复计时器
    def play_time_count_restore(self, event=None):
        self._player_running = True
        self._play_current_time += datetime.datetime.now() - self.play_pause_time
        self._play_time_count_timer = self.after(1000, self._update_timer)

    # 根据进度条拖动的位置，修改音乐正在播放的时间
    def set_music_start_time(self, event=None):
        music_progress_value = self.__dict__["music_progress_scale_value"].get()
        music_play_start_time = music_progress_value * self.music_duration / 100
        self.__dict__["playTime"].set(self._format_time(music_play_start_time))
        return music_play_start_time

    # 设置音乐从指定进度点播放
    def set_music_progress(self, event=None):
        music_play_start_time = self.set_music_start_time()
        self.music_start(start_seconds=music_play_start_time)

    # 播放音乐
    def music_start(self, event=None, start_seconds=0.0):
        # 设置正在播放的音乐信息
        music_path = self.current_music_path
        # 如果不存在这个路径，则退出播放
        if not music_path or not os.path.exists(music_path):
            self.__dict__["musicPath"].set("")
            return

        # 获取歌词字典，如果有的话
        self.__dict__["lyric"].set("")
        self.lyric_dict = read_lyric(os.path.join(self.music_dir_path, os.path.basename(self.current_music_path)[:-3]+"lrc"))

        # 设置音乐时长
        music_file = mp3.Mp3AudioFile(music_path)
        try:
            music_name_info = music_file.tag.artist + " - " + music_file.tag.title + "\n专辑:" + music_file.tag.album
        except Exception as e:
            logging.warning(e)
            music_name_info = os.path.basename(music_path)
        self.__dict__["info"].set(music_name_info)
        self.music_duration = music_file.info.time_secs
        self.__dict__["musicTime"].set(self._format_time(self.music_duration))
        # 中文路径必须编码后才可以
        if self.__dict__["volumeOnOffButton"]["text"] == "音量开":
            now_volume = self.__dict__["musicVolumeScale"].get() / 100.0
        else:
            now_volume = 0.0

        # 如果是新播放音乐或者从指定时间播放
        if self.__dict__["startButton"]["text"] == "播放" or start_seconds != 0.0:
            self.__dict__["startButton"]["image"] = self.pause_img
            self.__dict__["startButton"]["text"] = "暂停"
            if start_seconds != 0.0:
                self.adjust_time_count_stop()
            else:
                self.play_time_count_stop()
            if self.player:
                self.player.stop_state = True
                self.player = None
                time.sleep(1)
            self.player = Player(self.__dict__["musicPath"].get().encode('utf-8'), now_volume, start_seconds, self)
            self.player.start()
            self.play_time_count_start(start_seconds=start_seconds)
            self.count_music_play_times(music_path)
        else:
            self.music_pause_restore()

    def list_next_music_play(self, music_list, restart=False):
        old_music_path = self.current_music_path
        if not restart:
            if old_music_path not in music_list:
                index = -1
            else:
                index = music_list.index(old_music_path)
        else:
            index = -1
        if not music_list or index == len(music_list) - 1:
            return
        else:
            self.init_control_button_img()
            new_music_path = music_list[index + 1]
            self.__dict__["musicPath"].set(new_music_path)
            self.current_music_path = new_music_path
            self.music_start()
            sel_index = self.music_play_list.index(new_music_path)
            self.set_music_list_window_selection(sel_index)

    def list_prev_music_play(self, music_list):
        old_music_path = self.current_music_path
        if old_music_path not in music_list:
            index = len(music_list)
        else:
            index = music_list.index(old_music_path)
        if not music_list or index == 0:
            return
        else:
            self.init_control_button_img()
            new_music_path = music_list[index - 1]
            self.__dict__["musicPath"].set(new_music_path)
            self.current_music_path = new_music_path
            self.music_start()
            sel_index = self.music_play_list.index(new_music_path)
            self.set_music_list_window_selection(sel_index)

    def list_next_random_music_play(self, music_list):
        if not music_list:
            return
        else:
            music_play_list_length = len(music_list)
            index = random.randint(0, music_play_list_length - 1)
            new_music_path = music_list[index]
            self.music_play_preparation(new_music_path)
            self.music_start()

    def list_prev_random_music_play(self, music_list):
        if not music_list or not self.music_play_history_ids:
            return
        else:
            if self.current_music_path not in music_list:
                return
            else:
                old_index = music_list.index(self.current_music_path)
            # 如果从正常随机播放第一次点击上一次播放，抛弃正在播放的音乐行号
            if old_index == self.music_play_history_ids[-1]:
                self.music_play_history_ids.pop()
            # 播放前一首随机音乐
            index = self.music_play_history_ids.pop()
            new_music_path = music_list[index]
            self.music_play_preparation(new_music_path)
            self.music_start()

    def clear_music_play_history(self, event=None):
        self.music_play_history_ids.clear()

    # 播放音乐之前的准备工作
    def music_play_preparation(self, music_path):
        self.__dict__["musicPath"].set(music_path)
        self.current_music_path = music_path
        self.init_control_button_img()
        sel_index = self.music_play_list.index(music_path)
        self.set_music_list_window_selection(sel_index)
        # 记录播放过的音乐行号
        self.music_play_history_ids.append(sel_index)

    def next_music(self, event=None):
        # 先判断有没有等待播放列表
        if self.wait_play_list:
            new_music_path = self.wait_play_list.pop()
            self.music_play_preparation(new_music_path)
            self.music_start()
        else:
            if self.__dict__["playOption"].get() == "单曲播放":
                self.music_start()
            elif self.__dict__["playOption"].get() == "随机播放":
                self.list_next_random_music_play(self.music_play_list)
            elif self.__dict__["playOption"].get() == "顺序播放":
                self.list_next_music_play(self.music_play_list)
            elif self.__dict__["playOption"].get() == "收藏顺序":
                self.list_next_music_play(self.star_music_path_list)
            elif self.__dict__["playOption"].get() == "收藏随机":
                self.list_next_random_music_play(self.star_music_path_list)
            elif self.__dict__["playOption"].get() == "热度播放":
                if not self.favor_music_list:
                    favor_musics = sorted(self.music_play_times_dict.items(), key=operator.itemgetter(1), reverse=True)
                    self.favor_music_list = [item[0] for item in favor_musics]
                    self.list_next_music_play(self.favor_music_list, restart=True)
                else:
                    self.list_next_music_play(self.favor_music_list)

    def prev_music(self, event=None):
        if self.__dict__["playOption"].get() == "随机播放":
            self.list_prev_random_music_play(self.music_play_list)
        elif self.__dict__["playOption"].get() == "顺序播放":
            self.list_prev_music_play(self.music_play_list)
        elif self.__dict__["playOption"].get() == "收藏顺序":
            self.list_prev_music_play(self.star_music_path_list)
        elif self.__dict__["playOption"].get() == "收藏随机":
            self.list_prev_random_music_play(self.star_music_path_list)

    def music_stop(self, event=None):
        self.init_control_button_img()
        if self.player:
            self.play_time_count_stop()
            self.player.stop_state = True
            self.player = None

    def could_music_stop(self, event=None):
        self.music_stop()
        self.next_music()

    def music_pause_restore(self, event=None):
        # 暂停和恢复切换事件
        if self.player and self.player.pause_state:
            self.__dict__["startButton"]["text"] = "暂停"
            self.__dict__["startButton"]["image"] = self.pause_img
            self.play_time_count_restore()
            self.player.pause_state = False
        elif self.player and not self.player.pause_state:
            self.__dict__["startButton"]["text"] = "恢复"
            self.__dict__["startButton"]["image"] = self.play_img
            self.play_time_count_pause()
            self.player.pause_state = True

    # 根据Scale条设置播放音乐的音量
    def set_music_scale_volume(self, event=None):
        if self.__dict__["volumeOnOffButton"]["text"] == "音量开":
            # 获取Player类需要的音量值，在0到1之间
            now_volume = self.__dict__["musicVolumeScale"].get() / 100.0
            self.set_volume(now_volume)

    # 设置音乐的音量
    def set_volume(self, volume):
        if self.player:
            self.player.set_volume(volume)

    def volume_on_off(self, event=None):
        if self.__dict__["volumeOnOffButton"]["text"] == "音量开":
            self.__dict__["volumeOnOffButton"]["text"] = "音量关"
            self.__dict__["volumeOnOffButton"]["image"] = self.volume_off_img
            self.set_volume(0.0)
        else:
            self.__dict__["volumeOnOffButton"]["text"] = "音量开"
            self.__dict__["volumeOnOffButton"]["image"] = self.volume_on_img
            self.set_music_scale_volume()

    # 初始化音乐播放列表窗口
    def init_music_list_window(self):
        # 找到musicListTreeview控件和的musicListVbar控件的引用
        music_list = getattr(self, "musicListTreeview")
        music_list_vbar = getattr(self, "musicListVbar")
        music_list_vbar["command"] = music_list.yview
        # 定义树形结构与滚动条
        music_list.configure(yscrollcommand=music_list_vbar.set)
        # 表格的标题
        music_list.column("a", width=50, anchor="center")
        music_list.column("b", width=10, anchor="center")
        music_list.column("c", width=600, anchor="w")
        music_list.column("d", width=50, anchor="center")
        music_list.heading("a", text="序号")
        music_list.heading("b", text=" ")
        music_list.heading("c", text="音乐名称")
        music_list.heading("d", text="播放热度")

    # 清空表格
    def clear_music_list_window(self):
        # 找到musicListTreeview控件的引用
        music_list = getattr(self, "musicListTreeview")
        # 删除原节点
        for _ in map(music_list.delete, music_list.get_children("")):
            pass
        self.music_play_list = []
        self.star_music_index_list = []
        self.star_music_path_list = []

    # 初始化音乐播放列表
    def init_music_list(self, music_dir_path, current_music_path=None):
        self.music_dir_path = music_dir_path
        if music_dir_path and os.path.exists(music_dir_path):
            self.clear_music_list_window()
            music_play_list = []
            for m in os.listdir(music_dir_path):
                if m.endswith(".MP3") or m.endswith(".mp3"):
                    music_play_list.append(os.path.join(music_dir_path, m).replace("\\", "/"))
            self.music_play_list = music_play_list
            if self.music_play_list:
                if current_music_path and current_music_path in self.music_play_list:
                    self.current_music_path = current_music_path
                else:
                    self.current_music_path = self.music_play_list[0]
            self.__dict__["musicPath"].set(self.current_music_path)
            self.insert_music_list(music_dir_path)

    # 表格内容插入
    def insert_music_list(self, dir_path):
        # 找到musicListTreeview控件的引用
        music_list = getattr(self, "musicListTreeview")
        # 获取音乐播放列表
        music_name_list = [f for f in os.listdir(dir_path) if f.endswith(".MP3") or f.endswith(".mp3")]
        # 更新插入新节点
        for i in range(0, len(music_name_list)):
            tree_view_id = self.get_tree_view_iid(i)
            music_path = os.path.join(os.path.dirname(self.current_music_path), music_name_list[i]).replace('\\', '/')
            if self.music_play_times_dict.get(music_path):
                play_times = self.music_play_times_dict[music_path]
            else:
                play_times = 0
            # 根据iid插入到TreeView中
            music_list.insert("", "end", iid=tree_view_id, values=(i + 1, " ", music_name_list[i], play_times), tags=["normal"])

    # 音乐列表双击事件处理
    def double_click_music_callback(self, event=None):
        if not event.widget.item(event.widget.selection(), 'values'):
            return
        new_music_name = event.widget.item(event.widget.selection(), 'values')[2]
        old_music_path = self.__dict__["musicPath"].get()
        new_music_path = os.path.join(os.path.dirname(old_music_path), new_music_name).replace("\\", "/")
        self.__dict__["musicPath"].set(new_music_path)
        self.current_music_path = new_music_path
        self.init_control_button_img()
        self.music_start()

    # 根据音乐列表窗口已选择行获得行号
    def get_music_list_window_selection(self):
        # 找到musicListTreeview控件的引用
        music_list_widget = getattr(self, "musicListTreeview")
        iid = music_list_widget.selection()[0] if music_list_widget.selection() else "I0001"
        # 十六进制字符串转十进制数
        return int(iid[1:], 16) - 1

    # 根据行号设置音乐列表窗口的已选择行
    def set_music_list_window_selection(self, index):
        # 找到musicListTreeview控件的引用
        music_list_widget = getattr(self, "musicListTreeview")
        sel_index = self.get_tree_view_iid(index)
        music_list_widget.selection_set((sel_index,))
        # 使选中的行可见
        music_list_widget.see((sel_index,))

    # 根据list中的序号，计算出Treeview中的iid
    def get_tree_view_iid(self, index):
        widget_index = index + 1
        hex_index = hex(widget_index)[2:].upper()
        length = len(hex_index)
        return "I000"[0:4 - length] + hex_index

    # 右键菜单添加收藏
    def on_add_star_music(self, event=None):
        sel_index = self.get_music_list_window_selection()
        if sel_index not in self.star_music_index_list:
            self.star_music_index_list.append(sel_index)
            self.star_music_path_list.append(self.music_play_list[sel_index])
            music_list_widget = getattr(self, "musicListTreeview")
            children = music_list_widget.get_children()
            music_list_widget.item(children[sel_index], tags=["star"])
            music_list_widget.set(children[sel_index], column=1, value="★")

    # 右键菜单取消收藏
    def on_del_star_music(self, event=None):
        sel_index = self.get_music_list_window_selection()
        if sel_index in self.star_music_index_list:
            self.star_music_index_list.remove(sel_index)
            self.star_music_path_list.remove(self.music_play_list[sel_index])
            music_list_widget = getattr(self, "musicListTreeview")
            children = music_list_widget.get_children()
            music_list_widget.item(children[sel_index], tags=["normal"])
            music_list_widget.set(children[sel_index], column=1, value="")

    # 右键菜单复制歌曲名称
    def on_copy_music_name(self, event=None):
        music_list = getattr(self, "musicListTreeview")
        item_values = music_list.item(music_list.selection()[0])['values']
        music_name = item_values[2] if item_values else ""
        self.clipboard_clear()
        self.clipboard_append(music_name)

    # 右键菜单增加到等待播放列表
    def add_wait_play_list(self, event=None):
        sel_index = self.get_music_list_window_selection()
        self.wait_play_list.append(self.music_play_list[sel_index])

    # 根据音乐行号列表将音乐播放列表中收藏歌曲标注
    def set_star_music(self, star_music_index_list):
        music_list_widget = getattr(self, "musicListTreeview")
        children = music_list_widget.get_children()
        for i in star_music_index_list:
            music_list_widget.item(children[i], tags=["star"])
            music_list_widget.set(children[i], column=1, value="★")

    # 更新在音乐列表中的音乐播放次数
    def update_music_play_times(self, music_path, music_path_list):
        if music_path not in music_path_list:
            return
        if self.music_play_times_dict and self.music_play_times_dict.get(music_path):
            play_times = self.music_play_times_dict[music_path]
        else:
            play_times = 0
        index = music_path_list.index(music_path)
        # 找到musicListTreeview控件的引用
        music_list_widget = getattr(self, "musicListTreeview")
        children = music_list_widget.get_children()
        music_list_widget.set(children[index], column=3, value=play_times)

    # 在播放列表中搜索歌曲
    def music_search(self, event=None):
        music_word = tkinter.simpledialog.askstring(title='搜索歌曲', prompt='请输入歌名关键词：', initialvalue='')
        if music_word:
            for name in self.music_play_list:
                if music_word.lower() in name.lower():
                    sel_index = self.music_play_list.index(name)
                    self.set_music_list_window_selection(sel_index)
                    return


if __name__ == '__main__':
    app = Window("UI.json")
    # 设置窗口标题:
    app.master.title("音乐播放器")
    try:
        # 设置窗口图标
        app.master.iconbitmap('./resources/music.ico')
    except Exception as e:
        # 忽略图片设置的错误
        pass
    # 主消息循环:
    app.mainloop()

