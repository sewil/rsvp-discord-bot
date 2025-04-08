import redis
import variables

def connect():
    r = redis.Redis(host=variables.REDIS_HOST, port=variables.REDIS_PORT, decode_responses=True, password=variables.REDIS_PASS)
    return r

def get_online_count(r: redis.Redis, world: int, channel: int):
    return r.get(f'online-players-{world}-{channel}')
