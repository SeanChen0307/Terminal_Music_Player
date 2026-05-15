#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
终端音乐播放器 v9.0 - 终极稳健版
修复：交互模式闪退、找不到歌曲静默退出、Python 3.10 语法冲突
"""

import os
import sys
import glob
import json
import time
import random
import threading
import subprocess
import argparse
import unicodedata

# 强制输出编码修复 (针对 Windows PowerShell)
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ── 基础配置 ──
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "player_config.json")
DEFAULT_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "手机音乐")
SUPPORTED_EXT = ('.mp3', '.flac', '.aac', '.ape', '.wav', '.m4a')

settings = {
    "music_dir": DEFAULT_DIR,
    "volume": 50,
    "play_mode": 0, 
    "last_song": "",
    "last_pos": 0,
    "start_timestamp": 0,
    "is_paused": False
}

current_proc = None

# ── 状态管理 ──

def load_settings():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                settings.update(json.load(f))
        except: pass

def save_settings():
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
    except: pass

def get_current_elapsed():
    if settings.get("is_paused"): return settings.get("last_pos", 0)
    start = settings.get("start_timestamp", 0)
    if start == 0: return 0
    return settings.get("last_pos", 0) + (time.time() - start)

# ── 播放核心逻辑 ──

def get_songs():
    path = settings.get("music_dir", DEFAULT_DIR)
    if not os.path.isdir(path): return []
    songs = []
    for ext in SUPPORTED_EXT:
        songs.extend(glob.glob(os.path.join(path, f'*{ext}')))
        songs.extend(glob.glob(os.path.join(path, f'*{ext.upper()}')))
    return sorted(list(set(songs)))

def kill_existing_ffplay():
    global current_proc
    if os.name == 'nt':
        subprocess.run(["taskkill", "/F", "/IM", "ffplay.exe", "/T"], 
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    current_proc = None

def play_song(path, start_pos=0):
    global current_proc
    kill_existing_ffplay()
    if not path or not os.path.exists(path): return
    
    settings["last_song"] = os.path.abspath(path)
    settings["last_pos"] = start_pos
    settings["start_timestamp"] = time.time()
    settings["is_paused"] = False
    save_settings()
    
    vol = settings.get("volume", 50)
    try:
        # 使用 CREATE_NO_WINDOW (0x08000000) 隐藏子进程窗口
        current_proc = subprocess.Popen(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-volume", str(vol), "-ss", str(start_pos), path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=0x08000000 if os.name == 'nt' else 0
        )
    except Exception as e:
        print(f"播放失败: {e}")

def action_next(manual=False):
    songs = get_songs()
    if not songs: return None
    mode = settings.get("play_mode", 0)
    curr = settings.get("last_song", "")
    try: curr_idx = songs.index(curr) if curr in songs else -1
    except: curr_idx = -1

    if mode == 2 and not manual:
        target = curr if curr_idx != -1 else songs[0]
    elif mode == 1:
        target = random.choice(songs)
    else:
        next_idx = (curr_idx + 1) % len(songs)
        target = songs[next_idx]
    
    play_song(target)
    return target

def auto_next_monitor():
    while True:
        if current_proc and current_proc.poll() is not None:
            if not settings.get("is_paused"):
                action_next(manual=False)
        time.sleep(1)

# ── UI 渲染 (100% 兼容 3.10) ──

def get_display_width(text):
    width = 0
    for char in text:
        if unicodedata.east_asian_width(char) in ('W', 'F', 'A'): width += 2
        else: width += 1
    return width

def align_line(content, total_width):
    return content + " " * max(0, total_width - get_display_width(content))

def show_ui(current_song_path="无"):
    os.system('cls' if os.name == 'nt' else 'clear')
    song_basename = os.path.basename(current_song_path) if current_song_path and current_song_path != "无" else "等待播放..."
    status_text = "▶ 播放中" if not settings.get("is_paused") else "⏸ 已暂停"
    modes_list = ["🔁 顺序播放", "🔀 随机播放", "🔂 单曲循环"]
    m_idx = settings.get("play_mode", 0)
    mode_text = modes_list[m_idx] if 0 <= m_idx < 3 else modes_list[0]
    vol_val = settings.get("volume", 50)
    
    W = 52
    # 采用极其稳健的预变量渲染，避开 f-string 陷阱
    row_title = "🎵 终端音乐播放器 v9.0 (Win)"
    row_status = "状态: " + status_text
    row_song = "当前: " + song_basename
    row_info = "音量: " + str(vol_val) + "%  │  模式: " + mode_text
    row_cmd1 = "n: 下一首 │ p: 暂停/继续 │ m: 切换模式 │ l: 点歌"
    row_cmd2 = "+: 音量+  │ -: 音量-     │ q: 退出播放器"

    print("╔" + "═" * W + "╗")
    print("║ " + align_line(row_title, W-2) + " ║")
    print("╠" + "═" * W + "╣")
    print("║ " + align_line(row_status, W-2) + " ║")
    print("║ " + align_line(row_song, W-2) + " ║")
    print("║ " + align_line(row_info, W-2) + " ║")
    print("╠" + "═" * W + "╣")
    print("║ " + align_line(row_cmd1, W-2) + " ║")
    print("║ " + align_line(row_cmd2, W-2) + " ║")
    print("╚" + "═" * W + "╝")

# ── 交互指令 ──

def action_list_paged(songs, current_song):
    page_size = 15 
    total_songs = len(songs)
    for i in range(0, total_songs, page_size):
        show_ui(current_song)
        chunk = songs[i:i + page_size]
        print("\n--- 📂 歌单列表 (第 " + str(i//page_size + 1) + " 页 / 共 " + str((total_songs-1)//page_size + 1) + " 页) ---")
        for j, s in enumerate(chunk):
            print(" [" + str(i + j + 1) + "] " + os.path.basename(s))
        
        choice = input("\n[回车] 下一页 | [数字] 点播序号 | [q] 返回: ").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < total_songs: return songs[idx]
        if choice.lower() == 'q': break
    return None

# ── 主入口 ──

def main():
    load_settings()
    parser = argparse.ArgumentParser()
    parser.add_argument('--next', action='store_true')
    parser.add_argument('--stop', action='store_true')
    parser.add_argument('--pause', action='store_true')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--index', type=int)
    parser.add_argument('--vol', type=int)
    parser.add_argument('--mode', type=int, choices=[0, 1, 2])
    parser.add_argument('--dir', type=str)
    
    args = parser.parse_args()
    # 无论何种模式都启动监控线程
    threading.Thread(target=auto_next_monitor, daemon=True).start()

    cli_triggered = any([args.next, args.stop, args.pause, args.resume, 
                         args.list, args.index is not None, 
                         args.vol is not None, args.mode is not None, 
                         args.dir is not None])

    if cli_triggered:
        # CLI 模式逻辑 (此处保持 8.9 的稳定逻辑)
        if args.dir and os.path.isdir(args.dir):
            settings["music_dir"] = args.dir; save_settings()
        if args.mode is not None:
            settings["play_mode"] = args.mode; save_settings()
        if args.vol is not None:
            pos = get_current_elapsed(); settings["volume"] = max(0, min(100, args.vol)); save_settings()
            if not settings.get("is_paused") and settings.get("last_song"): play_song(settings["last_song"], start_pos=pos)

        songs = get_songs()
        if args.stop: kill_existing_ffplay(); return
        if args.pause: settings["last_pos"] = get_current_elapsed(); settings["is_paused"] = True; kill_existing_ffplay(); save_settings(); return
        if args.resume:
            last = settings.get("last_song")
            if last and os.path.exists(last): play_song(last, start_pos=settings.get("last_pos", 0))
        if args.index and songs:
            if 1 <= args.index <= len(songs): play_song(songs[args.index-1])
        if args.next: action_next(manual=True)
        if args.list:
            for i, s in enumerate(songs): print("[" + str(i+1) + "] " + os.path.basename(s), flush=True)

        if current_proc:
            try:
                while True:
                    if current_proc.poll() is not None: break
                    time.sleep(1)
            except KeyboardInterrupt: pass
        return

    # ── 交互模式入口 ──
    interactive_loop()

def interactive_loop():
    songs = get_songs()
    if not songs:
        print("\n❌ 错误：在目录 " + settings.get("music_dir") + " 下没找到音乐文件！")
        new_path = input("👉 请手动输入包含音乐的文件夹路径：").strip().strip('"')
        if os.path.isdir(new_path):
            settings["music_dir"] = new_path; save_settings()
            songs = get_songs()
        else:
            print("路径依然无效，请检查后再运行。")
            return

    # 初始化播放
    current_song = settings.get("last_song", "")
    if not current_song or not os.path.exists(current_song):
        mode = settings.get("play_mode", 0)
        current_song = random.choice(songs) if mode == 1 else songs[0]
        play_song(current_song)
    else:
        if not settings.get("is_paused"):
            play_song(current_song, start_pos=settings.get("last_pos", 0))

    while True:
        actual_song = settings.get("last_song", "")
        show_ui(actual_song)
        try:
            cmd = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            kill_existing_ffplay(); break

        if cmd in ("n", ""):
            action_next(manual=True)
        elif cmd == "p":
            if not settings.get("is_paused"):
                settings["last_pos"] = get_current_elapsed(); settings["is_paused"] = True
                kill_existing_ffplay(); save_settings()
            else:
                play_song(actual_song, start_pos=settings.get("last_pos", 0))
        elif cmd == "m":
            settings["play_mode"] = (settings.get("play_mode", 0) + 1) % 3; save_settings()
        elif cmd == "l":
            # 刷新歌曲列表
            songs = get_songs()
            selected = action_list_paged(songs, actual_song)
            if selected: play_song(selected)
        elif cmd in ("+", "="):
            pos = get_current_elapsed(); settings["volume"] = min(100, settings.get("volume", 50) + 10); save_settings()
            play_song(actual_song, start_pos=pos)
        elif cmd in ("-", "_"):
            pos = get_current_elapsed(); settings["volume"] = max(0, settings.get("volume", 50) - 10); save_settings()
            play_song(actual_song, start_pos=pos)
        elif cmd in ("q", "exit"):
            kill_existing_ffplay(); break

if __name__ == "__main__":
    main()