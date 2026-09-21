import time
from django.core.cache import cache
from django.http import JsonResponse
class RateLimitMiddleware:
    WINDOW=60; LIMIT=60
    def __init__(self,get_response): self.get_response=get_response
    def __call__(self,request):
        if request.path in {"/login/","/admin/login/"}:
            ip=request.META.get("REMOTE_ADDR") or "unknown"
            key=f"rl:{ip}:{int(time.time()//self.WINDOW)}"
            try:
                count=cache.get(key,0)+1; cache.set(key,count,timeout=self.WINDOW)
                if count>self.LIMIT: return JsonResponse({"detail":"rate limit exceeded"},status=429)
            except Exception: pass
        return self.get_response(request)
