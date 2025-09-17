from enum import Enum

class Engine(str, Enum):
    sync = "sync"
    async_ = "async"   # name can't be 'async' in Python, value stays "async"

class Output(str, Enum):
    table = "table"
    json = "json"
    yaml = "yaml"