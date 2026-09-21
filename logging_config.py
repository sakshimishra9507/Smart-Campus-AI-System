import json,logging,os,sys,time
class JsonFormatter(logging.Formatter):
    def format(self,record):
        return json.dumps({"timestamp":time.time(),"level":record.levelname,"logger":record.name,"message":record.getMessage()},ensure_ascii=False)
def configure_logging():
    handler=logging.StreamHandler(sys.stdout); handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=os.getenv("LOG_LEVEL","INFO").upper(),handlers=[handler],force=True)
