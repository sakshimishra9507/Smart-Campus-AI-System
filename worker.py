import os,time,redis
REDIS_URL=os.environ["REDIS_URL"]
INTERVAL=max(5,int(os.getenv("WORKER_HEARTBEAT_SECONDS","15")))
def main():
    client=redis.Redis.from_url(REDIS_URL,socket_connect_timeout=3,socket_timeout=3)
    while True:
        client.ping(); client.set("worker:heartbeat",str(time.time()),ex=INTERVAL*2); time.sleep(INTERVAL)
if __name__=="__main__": main()
