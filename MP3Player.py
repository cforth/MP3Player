import time
import threading
import pygame
import os
import random
import tkinter.filedialog as filedialog
from json2gui import *


# 音乐播放器类，使用pygame实现
class Player(threading.Thread):
    def __init__(self, file_path, volume=1.0, master=None):
        threading.Thread.__init__(self)
        # 传入主窗口的指针，用于触发主窗口事件(若有)
        self.master = master
        self.file_path = file_path
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
            self.track.play()  # 开始播放
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
        # 保存音乐播放的文件夹
        self.music_dir_path = None
        # 初始化音乐播放列表
        self.music_play_list = []
        # 保存当前正在播放的音乐地址
        self.current_music_path = None
        # 初始化控制按钮图片属性
        self.init_control_button_img()
        # 设置其他按钮图片属性
        self.__dict__["fileFromButton"]["image"] = self.folder_img
        self.__dict__["prevMusicButton"]["image"] = self.prev_play_img
        self.__dict__["nextMusicButton"]["image"] = self.next_play_img
        self.__dict__["volumeOnOffButton"]["image"] = self.volume_on_img
        self.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(3, weight=1)
        # 读取配置文件
        self.read_config("./config.json")

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

    def file_from_button_callback(self, event=None):
        self.music_dir_path = filedialog.askdirectory()
        self.init_music_list(self.music_dir_path)

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

    def read_config(self, config_path):
        if not os.path.exists(config_path):
            return
        with open(config_path, "r") as f:
            configs = json.load(f)
            if configs:
                self.init_music_list(configs["music_dir_path"], configs["current_music_path"])
                self.__dict__["playOption"].set(configs["playOption"])

    def save_config(self, config_path):
        if self.music_dir_path:
            configs = dict()
            configs["music_dir_path"] = self.music_dir_path
            configs["current_music_path"] = self.current_music_path
            configs["playOption"] = self.__dict__["playOption"].get()
            with open(config_path, "w") as f:
                json.dump(configs, f)

    # 在顶层窗口关闭时，先结束音乐播放线程
    def close_event(self, event=None):
        self.music_stop()
        self.save_config("./config.json")
        self.master.destroy()

    def init_control_button_img(self, event=None):
        # 设置按钮的图片和文字属性
        self.__dict__["startButton"]["image"] = self.play_img
        self.__dict__["startButton"]["text"] = "播放"
        self.__dict__["stopButton"]["image"] = self.stop_img
        self.__dict__["stopButton"]["text"] = "停止"

    def music_start(self, event=None):
        # 设置正在播放的音乐信息
        music_path = self.current_music_path
        # 如果不存在这个路径，则退出播放
        if not music_path or not os.path.exists(music_path):
            self.__dict__["musicPath"].set("")
            return

        music_name = os.path.basename(music_path)
        self.__dict__["info"].set(music_name)
        # 中文路径必须编码后才可以
        if self.__dict__["volumeOnOffButton"]["text"] == "音量开":
            now_volume = self.__dict__["musicVolumeScale"].get() / 100.0
        else:
            now_volume = 0.0

        if self.__dict__["startButton"]["text"] == "播放":
            self.__dict__["startButton"]["image"] = self.pause_img
            self.__dict__["startButton"]["text"] = "暂停"
            self.__dict__["musicProgressBar"].stop()
            if self.player:
                self.player.stop_state = True
                self.player = None
                time.sleep(1)
            self.player = Player(self.__dict__["musicPath"].get().encode('utf-8'), now_volume, self)
            # 启动进度条
            self.__dict__["musicProgressBar"].start()
            self.player.start()
        else:
            self.music_pause_restore()

    def next_music(self, event=None):
        if self.__dict__["playOption"].get() == "随机播放":
            self.random_music()
        else:
            old_music_path = self.current_music_path
            index = self.music_play_list.index(old_music_path)
            if not self.music_play_list or index == len(self.music_play_list) - 1:
                return
            else:
                self.init_control_button_img()
                new_music_path = self.music_play_list[index + 1]
                self.__dict__["musicPath"].set(new_music_path)
                self.current_music_path = new_music_path
                self.music_start()
                self.set_music_list_window_selection(index + 1)

    def prev_music(self, event=None):
        if self.__dict__["playOption"].get() == "随机播放":
            self.random_music()
        else:
            old_music_path = self.current_music_path
            index = self.music_play_list.index(old_music_path)
            if not self.music_play_list or index == 0:
                return
            else:
                self.init_control_button_img()
                new_music_path = self.music_play_list[index - 1]
                self.__dict__["musicPath"].set(new_music_path)
                self.current_music_path = new_music_path
                self.music_start()
                self.set_music_list_window_selection(index - 1)

    def random_music(self, event=None):
        music_play_list_length = len(self.music_play_list)
        index = random.randint(0, music_play_list_length)
        if not self.music_play_list:
            return
        else:
            new_music_path = self.music_play_list[index]
            self.__dict__["musicPath"].set(new_music_path)
            self.current_music_path = new_music_path
            self.init_control_button_img()
            self.music_start()
            self.set_music_list_window_selection(index)

    def music_stop(self, event=None):
        self.init_control_button_img()
        self.__dict__["musicProgressBar"].stop()
        if self.player:
            self.player.stop_state = True
            self.player = None

    def could_music_stop(self, event=None):
        self.music_stop()
        if self.__dict__["playOption"].get() == "顺序播放":
            self.next_music()
        elif self.__dict__["playOption"].get() == "随机播放":
            self.random_music()

    def music_pause_restore(self, event=None):
        # 暂停和恢复切换事件
        if self.player and self.player.pause_state:
            self.__dict__["startButton"]["text"] = "暂停"
            self.__dict__["startButton"]["image"] = self.pause_img
            self.__dict__["musicProgressBar"].start()
            self.player.pause_state = False
        elif self.player and not self.player.pause_state:
            self.__dict__["startButton"]["text"] = "恢复"
            self.__dict__["startButton"]["image"] = self.play_img
            self.__dict__["musicProgressBar"].stop()
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
        music_list.column("b", width=700, anchor="w")
        music_list.heading("a", text="序号")
        music_list.heading("b", text="音乐名称")

    # 清空表格
    def clear_music_list_window(self):
        # 找到musicListTreeview控件的引用
        music_list = getattr(self, "musicListTreeview")
        # 删除原节点
        for _ in map(music_list.delete, music_list.get_children("")):
            pass
        self.music_play_list = []

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
            # 根据iid插入到TreeView中
            music_list.insert("", "end", iid=tree_view_id, values=(i + 1, music_name_list[i]))

    # 音乐列表双击事件处理
    def double_click_music_callback(self, event=None):
        if not event.widget.item(event.widget.selection(), 'values'):
            return
        new_music_name = event.widget.item(event.widget.selection(), 'values')[1]
        old_music_path = self.__dict__["musicPath"].get()
        new_music_path = os.path.join(os.path.dirname(old_music_path), new_music_name).replace("\\", "/")
        self.__dict__["musicPath"].set(new_music_path)
        self.current_music_path = new_music_path
        self.init_control_button_img()
        self.music_start()

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

