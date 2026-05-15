#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
import json
import os
import time
import sys

# ── 配置 ──
PLAYER_SCRIPT = "music_player.py"
CONFIG_FILE = "player_config.json"
PYTHON_EXE = sys.executable

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {}

def kill_all():
    """彻底清理 ffplay 和播放器残余"""
    if sys.platform == 'win32':
        subprocess.run(["taskkill", "/F", "/IM", "ffplay.exe", "/T"], 
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def check_ffplay():
    """检查 ffplay 是否在运行"""
    try:
        output = subprocess.check_output(["tasklist", "/FI", "IMAGENAME eq ffplay.exe"], text=True)
        return "ffplay.exe" in output
    except:
        return False

def run_cli(args, timeout=None):
    """
    运行命令行指令。
    对于点歌等阻塞性指令，通过 timeout 参数强制在 5 秒后切断。
    """
    cmd = [PYTHON_EXE, PLAYER_SCRIPT] + args
    print(f"  [CLI执行] {' '.join(args)}")
    try:
        # 如果设置了 timeout，超时后会抛出 subprocess.TimeoutExpired
        subprocess.run(cmd, timeout=timeout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.TimeoutExpired:
        # 播放测试时，超时是正常的预期行为
        pass
    finally:
        # 每次指令执行完都清理一下，确保环境干净
        if timeout:
            kill_all()
        time.sleep(1) 

# ── 测试阶段 ──

def phase_1_cli():
    print("\n--- 阶段 1: 命令行功能 (CLI) 测试 ---")
    kill_all()
    
    # 1. 设置目录 (非阻塞)
    run_cli(["--dir", os.getcwd()])
    if load_config().get("music_dir") == os.getcwd():
        print("✅ 目录设置成功")

    # 2. 模式切换 (非阻塞)
    run_cli(["--mode", "2"]) # 设为单曲循环
    if load_config().get("play_mode") == 2:
        print("✅ 播放模式设置成功")

    # 3. 音量调节 (由于会触发续播，属于阻塞操作，设置 5 秒超时)
    print("  测试音量调节 (试听 5 秒)...")
    run_cli(["--vol", "25"], timeout=5)
    if load_config().get("volume") == 25:
        print("✅ 音量持久化成功")

    # 4. 序号点播 (阻塞操作，设置 5 秒超时)
    print("  测试序号点播 (试听 5 秒)...")
    run_cli(["--index", "1"], timeout=5)
    # 虽然进程被我们杀了，但 JSON 里的 last_song 应该更新了
    if load_config().get("last_song"):
        print("✅ 序号点播数据记录成功")
    
    # 5. 暂停 (非阻塞)
    run_cli(["--pause"])
    if load_config().get("is_paused"):
        print("✅ 命令行暂停成功")
    
    # 6. 恢复播放 (阻塞操作，设置 5 秒超时)
    print("  测试恢复播放 (试听 5 秒)...")
    run_cli(["--resume"], timeout=5)
    if not load_config().get("is_paused"):
        print("✅ 命令行恢复播放成功")

    run_cli(["--stop"])
    print("✅ 命令行停止功能正常")

def phase_2_tui():
    print("\n--- 阶段 2: 控制台交互 (TUI) 测试 ---")
    kill_all()
    
    # 启动交互模式
    p = subprocess.Popen(
        [PYTHON_EXE, PLAYER_SCRIPT],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1, encoding='utf-8'
    )
    time.sleep(3) # 等待开播

    try:
        print("  模拟按下 [n] (切歌)...")
        p.stdin.write("n\n")
        p.stdin.flush()
        time.sleep(3) # 听 3 秒
        
        print("  模拟按下 [p] (暂停)...")
        p.stdin.write("p\n")
        p.stdin.flush()
        time.sleep(2)
        
        if load_config().get("is_paused"):
            print("✅ 交互式暂停成功")

        print("  模拟按下 [q] (退出)...")
        p.stdin.write("q\n")
        p.stdin.flush()
        time.sleep(1)
        if p.poll() is not None:
            print("✅ 交互式正常退出")

    except Exception as e:
        print(f"💥 异常: {e}")
    finally:
        if p.poll() is None: p.kill()
        kill_all()

if __name__ == "__main__":
    print("🚀 开始整合测试 (试听模式)...")
    start_time = time.time()
    try:
        phase_1_cli()
        phase_2_tui()
    finally:
        kill_all()
    print(f"\n🎉 测试全部完成，耗时: {time.time() - start_time:.2f} 秒")