import os
import time
import setup
from custom_modules import loadEnv
import threading
import subprocess
import web_app
import datetime
from custom_modules import dbManeger
import pyperclip

banner = r"""
  ___________________  _____  _________ ___________.___ ___________   _________  ________   ________ __________ 
 /   _____/\______   \/  _  \ \_   ___ \\_   _____/|   |\      \   \ /   /  _  \ \______ \  \_____  \\______   \
 \_____  \  |     ___/  /_\  \/    \  \/ |    __)_ |   |/   |   \   Y   /  /_\  \ |    |  \  /   |   \|       _/
 /        \ |    |  /    |    \     \____|        \|   /    |    \     /    |    \|    `   \/    |    \    |   \
/_______  / |____|  \____|__  /\______  /_______  /|___\____|__  /\___/\____|__  /_______  /\_______  /____|_  /
        \/                  \/        \/        \/             \/              \/        \/         \/       \/ 

"""
print(banner)

printed_servers = []

if not os.path.exists('.env'):
    setup.setup()
    print("Setup complete, please restart the program")

env = loadEnv.load()


def help_cmd(args=None):
    string = "Commands:\n"
    for command in commands:
        string += f"  {command}: \n    Description: {commands[command]['description']} \n    Usage: {commands[command]['usage']}\n"
    print(string)


def scan_cmd(args=None):
    print("Scanning for new servers...\n")
    subprocess.Popen(f'python scan.py', shell=False)


def webApp_cmd(args=None):
    print("Starting web app...\n")
    subprocess.Popen(f'python web_app.py', shell=False)

def server_cmd(args=None):
    minutes = 5
    version = None
    online_players = False
    number = 1
    copy_to_clipboard = False
    ensure_no_whitelist = False

    if args:
        for i in args:
            if i.startswith("v"):
                version = i.split(" ")[1]
            if i.startswith("o"):
                online_players = True
            if i.startswith("m"):
                minutes = int(i.split(" ")[1])
            if i.startswith("n"):
                number = i.split(" ")[1]
                if number == "all":
                    number = 999999
                else:
                    number = int(number)
            if i == "c":
                copy_to_clipboard = True
            if i.startswith("w"):
                ensure_no_whitelist = True

    db = dbManeger.dbManeger(env['DB_TYPE'], env['DB'])
    print(f"Getting servers online in the last {minutes} minutes...")
    current_time = datetime.datetime.now()

    sql = f"SELECT * FROM ip WHERE whitelist IS NOT true"

    if online_players and version:
        sql += f" AND onlinePlayers > 0 AND version = '{version}'"
    elif online_players:
        sql += " AND onlinePlayers > 0"
    elif version:
        sql += f" AND version = '{version}'"

    servers = db.execute(sql)

    if len(servers) == 0:
        print("No servers found")
        return

    server_count = 1
    for i, data in enumerate(servers):
        if i == number:
            break

        if number != "all" and data[0] in printed_servers:
            number += 1
            continue

        last_scan_time_str = data[12]
        if last_scan_time_str is None:
            number += 1
            continue
        try:
            last_scan_time = datetime.datetime.strptime(last_scan_time_str, "%d %b %Y %H:%M:%S")
        except ValueError:
            number += 1
            continue
        time_diff = (current_time - last_scan_time).total_seconds() // 60
        if time_diff >= minutes:
            number += 1
            continue
        if ensure_no_whitelist and data[10] is None:
            number += 1
            continue
        print(
            f"Server {server_count}: {data[1]}:{data[2]} ({data[5]})    ID: {data[0]}    Last Scan: {abs(time_diff)} minutes ago", end="")
        if data[10] is None:
            print(f"   ⚠ No whitelist scan data available", end="")
        print()

        if copy_to_clipboard and server_count == 1:
            ip_port = f"{data[1]}:{data[2]}"
            pyperclip.copy(ip_port)
            print(f"IP:Port copied to clipboard: {ip_port}")

        printed_servers.append(data[0])
        server_count += 1


def run_command(cmd, args=None):
    if cmd in commands:
        if cmd == "stop":
            stop_flag.set()
        else:
            if commands[cmd].get("run_in_thread", False):
                thread = threading.Thread(target=commands[cmd]["function"], args=(args,))
                thread.start()
            else:
                commands[cmd]["function"](args)


commands = {
    "help": {
        "description": "Show this help message",
        "usage": "help",
        "function": help_cmd,
        "run_in_thread": False,
    },
    "scan": {
        "description": "Scan for new Minecraft servers",
        "usage": "scan",
        "function": scan_cmd,
        "run_in_thread": True,
    },
    "webApp": {
        "description": "Start the web app",
        "usage": "webApp",
        "function": webApp_cmd,
        "run_in_thread": False,
    },
    "stop": {
        "description": "Stop threads",
        "usage": "stop",
        "function": lambda: None,
        "run_in_thread": False,
    },
    "server": {
        "description": "Returns a joinable server",
        "usage": "server [-v Version] [-o (should people be online) -m minutes (how long ago the server was online)] -n int/all (number of servers to return) -c (copy to clipboard) -w (ensure server has no whitelist)",
        "function": server_cmd,
        "run_in_thread": False,
    },
    "exit": {
        "description": "Exit the program",
        "usage": "exit",
        "function": lambda: exit(0),
        "run_in_thread": False,
    },
}

while True:
    user_input = input(">>> ")
    parts = user_input.split(maxsplit=1)
    cmd = parts[0]
    args = parts[1].split('-')[1:] if len(parts) > 1 else None

    if cmd in commands:
        run_command(cmd, args)
