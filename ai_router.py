#!/usr/bin/env python3
"""
ai-router v0.1.0 - Ultra-light AI API Router
=============================================
Aggregate multiple AI sources into one OpenAI-compatible API.
Zero dependencies, single file, automatic failover.
"""
import http.server, json, os, sys, time, urllib.request, urllib.error
import uuid, argparse, threading, logging
from dataclasses import dataclass, field

DEFAULT_CONFIG = {
    "host": "0.0.0.0", "port": 8080,
    "providers": [
        {"name": "deepseek", "type": "openai", "base_url": "https://api.deepseek.com/v1",
         "api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
         "models": ["deepseek-chat", "deepseek-v4-pro", "deepseek-reasoner"],
         "priority": 1, "rate_limit": 100, "timeout": 60},
        {"name": "openclaw", "type": "openai", "base_url": "https://api.openclaw.ai/v1",
         "api_key": os.environ.get("OPENCLAW_API_KEY", ""),
         "models": ["openclaw-zero-token"],
         "priority": 2, "rate_limit": 50, "timeout": 120},
    ],
    "models": {"default": "deepseek-chat",
        "aliases": {"gpt-4o-mini": "deepseek-chat", "o3-mini": "deepseek-reasoner", "free": "openclaw-zero-token"}},
    "fallback": {"enabled": True, "max_retries": 2, "retry_delay": 0.5},
    "log_level": "INFO",
}

@dataclass
class Provider:
    name: str; ptype: str; base_url: str; api_key: str
    models: list; priority: int; rate_limit: int; timeout: int
    healthy: bool = True; _calls: int = 0; _last_reset: float = field(default_factory=time.time)

class ModelRouter:
    def __init__(self, config=None):
        self.config = config or DEFAULT_CONFIG
        self.providers = []
        for p in self.config.get("providers", []):
            self.providers.append(Provider(name=p["name"], ptype=p.get("type","openai"),
                base_url=p["base_url"], api_key=p.get("api_key",""), models=p.get("models",[]),
                priority=p.get("priority",999), rate_limit=p.get("rate_limit",100), timeout=p.get("timeout",60)))
        self.providers.sort(key=lambda p: p.priority)
        level = getattr(logging, self.config.get("log_level","INFO").upper(), logging.INFO)
        logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=level)
        self.log = logging.getLogger("ai-router")

    def resolve_model(self, m):
        return self.config.get("models",{}).get("aliases",{}).get(m, m)

    def find_providers(self, model):
        resolved = self.resolve_model(model)
        candidates = []
        for p in self.providers:
            if not p.healthy: continue
            if resolved in p.models or "*" in p.models:
                now = time.time()
                if now - p._last_reset > 60: p._calls = 0; p._last_reset = now
                if p._calls < p.rate_limit: candidates.append(p)
        candidates.sort(key=lambda p: (p.priority, p.name))
        return candidates

    def chat_completion(self, request):
        candidates = self.find_providers(request.model)
        if not candidates:
            return self._error(f"No healthy provider for: {request.model}")
        last_error = None
        fc = self.config.get("fallback",{})
        for attempt in range(fc.get("max_retries",2)+1):
            for p in candidates:
                if attempt > 0: time.sleep(fc.get("retry_delay",0.5))
                try:
                    p._calls += 1
                    if request.stream: return self._stream(p, request)
                    return self._single(p, request)
                except Exception as e:
                    last_error = str(e)
                    self.log.warning(f"{p.name} failed: {last_error}")
                    p.healthy = False
                    threading.Timer(30.0, lambda pp=p: setattr(pp,"healthy",True)).start()
        return self._error(f"All providers failed: {last_error}")

    def _single(self, p, req):
        url = f"{p.base_url.rstrip('/')}/chat/completions"
        body = {"model": self.resolve_model(req.model),
                "messages": [{"role":m.role,"content":m.content} for m in req.messages],
                "temperature": req.temperature, "max_tokens": req.max_tokens, "stream": False}
        r = urllib.request.Request(url, data=json.dumps(body).encode(),
            headers={"Content-Type":"application/json","Authorization":f"Bearer {p.api_key}"}, method="POST")
        result = json.loads(urllib.request.urlopen(r, timeout=p.timeout).read().decode())
        return {"id":f"chatcmpl-{uuid.uuid4().hex[:12]}","object":"chat.completion",
                "created":int(time.time()),"model":req.model,"provider":p.name,
                "choices":[{"index":0,"message":{"role":"assistant","content":result["choices"][0]["message"]["content"]},
                            "finish_reason":result["choices"][0].get("finish_reason","stop")}],
                "usage":result.get("usage",{})}

    def _stream(self, p, req):
        url = f"{p.base_url.rstrip('/')}/chat/completions"
        body = {"model": self.resolve_model(req.model),
                "messages": [{"role":m.role,"content":m.content} for m in req.messages],
                "temperature": req.temperature, "max_tokens": req.max_tokens, "stream": True}
        r = urllib.request.Request(url, data=json.dumps(body).encode(),
            headers={"Content-Type":"application/json","Authorization":f"Bearer {p.api_key}"}, method="POST")
        resp = urllib.request.urlopen(r, timeout=p.timeout)
        def gen():
            buf = ""
            for b in iter(lambda: resp.read(1), b""):
                buf += b.decode()
                if buf.endswith("\n"):
                    line = buf.strip(); buf = ""
                    if line.startswith("data: "):
                        d = line[6:]
                        if d == "[DONE]": yield "data: [DONE]\n\n"; return
                        try: json.loads(d); yield f"data: {d}\n\n"
                        except: pass
            resp.close()
        return gen()

    def _error(self, msg):
        return {"id":f"chatcmpl-{uuid.uuid4().hex[:12]}","object":"chat.completion",
                "created":int(time.time()),"model":"error",
                "choices":[{"index":0,"message":{"role":"assistant","content":f"[ai-router] {msg}"},"finish_reason":"error"}],"usage":{}}

class Handler(http.server.BaseHTTPRequestHandler):
    router = None
    def do_GET(self):
        if self.path=="/v1/models": self._json(200,{"object":"list","data":[{"id":m,"object":"model"} for m in sorted(set(m for p in self.router.providers for m in p.models))]})
        elif self.path=="/health": self._json(200,{"status":"ok","providers":len(self.router.providers),"healthy":sum(1 for p in self.router.providers if p.healthy)})
        else: self._json(404,{"error":"Not found"})
    def do_POST(self):
        if self.path=="/v1/chat/completions":
            try:
                length=int(self.headers.get("Content-Length",0))
                body=json.loads(self.rfile.read(length).decode())
            except Exception as e: return self._json(400,{"error":f"Bad request: {e}"})
            msgs=[type("M",(),{"role":m["role"],"content":m["content"]})() for m in body.get("messages",[])]
            req=type("R",(),{"model":body.get("model",self.router.config.get("models",{}).get("default","deepseek-chat")),"messages":msgs,"stream":body.get("stream",False),"temperature":body.get("temperature",1.0),"max_tokens":body.get("max_tokens",4096)})()
            if req.stream: self._stream_resp(req)
            else: self._json(200,self.router.chat_completion(req))
        else: self._json(404,{"error":"Not found"})
    def _stream_resp(self, req):
        self.send_response(200)
        self.send_header("Content-Type","text/event-stream"); self.send_header("Cache-Control","no-cache"); self.send_header("Connection","keep-alive"); self.end_headers()
        try:
            for c in self.router.chat_completion(req): self.wfile.write(c.encode()); self.wfile.flush()
        except Exception as e: self.wfile.write(f"data: {json.dumps({'error':str(e)})}\n\n".encode()); self.wfile.flush()
    def _json(self,s,d): self.send_response(s); self.send_header("Content-Type","application/json"); self.end_headers(); self.wfile.write(json.dumps(d,ensure_ascii=False).encode())
    def log_message(self,f,*a): logging.getLogger("ai-router").info(f"{self.client_address[0]} - {f%a}")

def serve(cfg_path=None):
    cfg=DEFAULT_CONFIG
    if cfg_path and os.path.exists(cfg_path):
        with open(cfg_path) as f: uc=json.load(f)
        def m(a,b):
            r=a.copy()
            for k,v in b.items():
                if k in r and isinstance(r[k],dict) and isinstance(v,dict): r[k]=m(r[k],v)
                else: r[k]=v
            return r
        cfg=m(DEFAULT_CONFIG,uc)
    router=ModelRouter(cfg); Handler.router=router
    sv=http.server.HTTPServer((cfg["host"],cfg["port"]),Handler)
    router.log.info(f"ai-router v0.1.0 at http://{cfg['host']}:{cfg['port']}")
    try: sv.serve_forever()
    except KeyboardInterrupt: router.log.info("Bye."); sv.shutdown()

def cli():
    p=argparse.ArgumentParser(description="ai-router",epilog="Commands: serve, chat, list")
    sp=p.add_subparsers(dest="command")
    sp.add_parser("serve").add_argument("--host",default=DEFAULT_CONFIG["host"]).add_argument("--port",type=int,default=DEFAULT_CONFIG["port"]).add_argument("--config")
    sp.add_parser("chat").add_argument("message",nargs="?").add_argument("-m","--model",default=DEFAULT_CONFIG["models"]["default"]).add_argument("--config").add_argument("-i","--interactive",action="store_true")
    sp.add_parser("list")
    args=p.parse_args()
    cfg=DEFAULT_CONFIG
    if hasattr(args,"config") and args.config and os.path.exists(args.config):
        with open(args.config) as f: cfg=json.load(f)
    if args.command=="list":
        router=ModelRouter(cfg)
        for p in router.providers: print(f"  {chr(10003) if p.healthy else chr(10007)} {p.name}")
        for a,t in cfg.get("models",{}).get("aliases",{}).items(): print(f"  alias: {a} -> {t}")
    elif args.command=="chat":
        router=ModelRouter(cfg)
        if args.interactive:
            print(f"ai-router chat [{args.model}]")
            msgs=[]
            while True:
                try: ui=input(">>> ").strip()
                except: break
                if not ui or ui=="/quit": break
                msgs.append(type("M",(),{"role":"user","content":ui})())
                req=type("R",(),{"model":args.model,"messages":msgs,"stream":False,"temperature":1.0,"max_tokens":4096})()
                r=router.chat_completion(req); c=r.get("choices",[{}])[0].get("message",{}).get("content","")
                print(f"AI [{r.get('provider','?')}]: {c}\n")
                msgs.append(type("M",(),{"role":"assistant","content":c})())
        elif args.message:
            msgs=[type("M",(),{"role":"user","content":args.message})()]
            req=type("R",(),{"model":args.model,"messages":msgs,"stream":False,"temperature":1.0,"max_tokens":4096})()
            r=router.chat_completion(req); c=r.get("choices",[{}])[0].get("message",{}).get("content","")
            print(f"AI [{r.get('provider','?')}]: {c}")
    else: serve(getattr(args,"config",None))

if __name__=="__main__": cli()