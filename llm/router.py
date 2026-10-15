"""
AnimusDialerEngine -- Multi-Provider LLM Router
Groq (fast) -> Mistral (structured) -> Gemini (long) -> OpenRouter (overflow)
"""
from __future__ import annotations
import json, time, logging, threading, urllib.request, urllib.error
from pathlib import Path
from typing import Optional

logger = logging.getLogger("dialer.llm_router")
_CFG = Path(__file__).parent.parent / "config" / "llm_keys.json"

def _cfg() -> dict:
    try: return json.loads(_CFG.read_text(encoding="utf-8"))["llm"]
    except: return {}

class _Tracker:
    def __init__(self): self._cd: dict[str,float]={};self._lk=threading.Lock()
    def ok(self, p): 
        with self._lk: return time.time() >= self._cd.get(p, 0)
    def limit(self, p, s=60.0):
        with self._lk: self._cd[p]=time.time()+s
        logger.warning(f"[LLM] {p} rate-limited {s}s")

_T = _Tracker()

def _post(url, payload, headers, timeout=20) -> Optional[str]:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise e
    except Exception as e:
        logger.error(f"[LLM] Request error: {e}")
        return None

def _groq(prompt, system="", model=None, max_tokens=512) -> Optional[str]:
    c = _cfg(); k = c.get("groq_api_key","")
    if not k or not _T.ok("groq"): return None
    mdl = model or c.get("groq_model","llama-3.3-70b-versatile")
    msgs = ([{"role":"system","content":system}] if system else []) + [{"role":"user","content":prompt}]
    try:
        d = _post("https://api.groq.com/openai/v1/chat/completions",
                  {"model":mdl,"messages":msgs,"max_tokens":max_tokens,"temperature":0.7},
                  {"Authorization":f"Bearer {k}","Content-Type":"application/json"})
        return d["choices"][0]["message"]["content"].strip() if d else None
    except urllib.error.HTTPError as e:
        if e.code==429: _T.limit("groq",60)
        return None

def _mistral(prompt, system="", max_tokens=512) -> Optional[str]:
    c = _cfg(); k = c.get("mistral_api_key","")
    if not k or not _T.ok("mistral"): return None
    mdl = c.get("mistral_model","ministral-8b-latest")
    msgs = ([{"role":"system","content":system}] if system else []) + [{"role":"user","content":prompt}]
    try:
        d = _post("https://api.mistral.ai/v1/chat/completions",
                  {"model":mdl,"messages":msgs,"max_tokens":max_tokens,"temperature":0.3},
                  {"Authorization":f"Bearer {k}","Content-Type":"application/json"})
        return d["choices"][0]["message"]["content"].strip() if d else None
    except urllib.error.HTTPError as e:
        if e.code==429: _T.limit("mistral",60)
        return None

def _gemini(prompt, system="", max_tokens=512) -> Optional[str]:
    c = _cfg(); k = c.get("gemini_api_key","")
    if not k or not _T.ok("gemini"): return None
    full = f"{system}\n\n{prompt}".strip() if system else prompt
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={k}"
    try:
        req = urllib.request.Request(url,
            data=json.dumps({"contents":[{"role":"user","parts":[{"text":full}]}],
                             "generationConfig":{"maxOutputTokens":max_tokens,"temperature":0.7}}).encode(),
            headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read())["candidates"][0]["content"]["parts"][0]["text"].strip()
    except urllib.error.HTTPError as e:
        if e.code==429: _T.limit("gemini",60)
        return None

def _openrouter(prompt, system="", max_tokens=512) -> Optional[str]:
    c = _cfg(); k = c.get("openrouter_api_key","")
    if not k or not _T.ok("openrouter"): return None
    msgs = ([{"role":"system","content":system}] if system else []) + [{"role":"user","content":prompt}]
    try:
        d = _post("https://openrouter.ai/api/v1/chat/completions",
                  {"model":"openrouter/auto","messages":msgs,"max_tokens":max_tokens},
                  {"Authorization":f"Bearer {k}","Content-Type":"application/json",
                   "HTTP-Referer":"https://github.com/AnimusDialerEngine","X-Title":"AnimusDialerEngine"})
        return d["choices"][0]["message"]["content"].strip() if d else None
    except urllib.error.HTTPError as e:
        if e.code==429: _T.limit("openrouter",120)
        return None

def complete(prompt: str, system: str="", task_type: str="fast", max_tokens: int=512) -> str:
    """
    task_type: fast | structured | long | overflow
    fast       -> Groq -> Mistral -> Gemini -> OpenRouter
    structured -> Mistral -> Groq -> Gemini -> OpenRouter  (JSON output)
    long       -> Gemini -> Groq -> Mistral -> OpenRouter  (big docs)
    overflow   -> OpenRouter -> all others
    """
    order = {
        "fast":       [_groq, _mistral, _gemini, _openrouter],
        "structured": [_mistral, _groq, _gemini, _openrouter],
        "long":       [_gemini, _groq, _mistral, _openrouter],
        "overflow":   [_openrouter, _groq, _mistral, _gemini],
    }.get(task_type, [_groq, _mistral, _gemini, _openrouter])

    for fn in order:
        result = fn(prompt, system, max_tokens=max_tokens)
        if result:
            logger.debug(f"[LLM] Served by {fn.__name__[1:]}")
            return result

    logger.error("[LLM] All providers exhausted!")
    return "I am temporarily unavailable. Please try again shortly."
