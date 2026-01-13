#!/usr/bin/env python3

"""
Logging and text interface related code.
"""


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    
    # Advanced
    NEON_GREEN = "\033[38;5;82m"
    NEON_CYAN = "\033[38;5;51m"
    NEON_RED = "\033[38;5;196m"
    NEON_PURPLE = "\033[38;5;201m" 
    NERD_YELLOW = "\033[38;5;226m"
    GRAY = "\033[38;5;245m"


class loglevel:
    INFO = ("✚", bcolors.NEON_GREEN)
    WARN = ("⚠", bcolors.NERD_YELLOW)
    INPUT = ("➤", bcolors.NEON_CYAN)
    DEBUG = ("⚙", bcolors.OKBLUE)
    ERROR = ("✖", bcolors.NEON_RED)


def color_print(color: str, msg: str):
    print(f"{color}{msg}{bcolors.ENDC}")


def log(level: tuple, msg: str):
    """
    Print a string with the selected log level.
    """
    # Format: [SYMBOL] Message
    # Only color the symbol
    print(f"{bcolors.GRAY}[{level[1]}{level[0]}{bcolors.GRAY}] {bcolors.ENDC}{msg}")


def log_info(msg: str):
    log(loglevel.INFO, msg)


def log_warn(msg: str):
    log(loglevel.WARN, msg)

def log_error(msg: str):
    log(loglevel.ERROR, msg)

def input_yn(msg: str) -> bool:
    log(loglevel.INPUT, msg)
    option = input(f"{bcolors.GRAY}   [Y/n] >> {bcolors.ENDC}") or "y"
    return option.lower() in ("y", "yes")

def box_print(msg: str, color=bcolors.NEON_CYAN):
    lines = msg.split('\n')
    width = max(len(line) for line in lines) + 4
    print(f"{color}╔{'═' * width}╗{bcolors.ENDC}")
    for line in lines:
        print(f"{color}║  {bcolors.ENDC}{line.ljust(width-4)}{color}  ║{bcolors.ENDC}")
    print(f"{color}╚{'═' * width}╝{bcolors.ENDC}")

