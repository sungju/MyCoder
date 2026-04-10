"""
tools.py - AI 코딩 에이전트가 사용하는 도구 모음

Claude Code / Codex 같은 AI 코딩 도구들은
LLM이 직접 코드를 실행하거나 파일을 다루는 게 아니라,
"도구(Tool)"라는 인터페이스를 통해 환경과 상호작용합니다.
"""

import os
import subprocess
import json
from pathlib import Path
from typing import Any


# ──────────────────────────────────────────────
# 도구 정의 (LLM에게 전달할 스키마)
# LLM은 이 스키마를 보고 "어떤 도구를, 어떤 인자로 쓸지" 결정합니다.
# ──────────────────────────────────────────────

TOOLS = [
    {
        "name": "read_file",
        "description": "파일 내용을 읽습니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "읽을 파일 경로"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "파일에 내용을 씁니다 (없으면 생성, 있으면 덮어씀).",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "쓸 파일 경로"},
                "content": {"type": "string", "description": "파일에 쓸 내용"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "list_files",
        "description": "디렉토리의 파일 목록을 가져옵니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "조회할 디렉토리 (기본: 현재 디렉토리)"}
            },
            "required": []
        }
    },
    {
        "name": "run_python",
        "description": "Python 코드를 실행하고 출력 결과를 반환합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "실행할 Python 코드"},
                "timeout": {"type": "integer", "description": "타임아웃 (초, 기본: 10)"}
            },
            "required": ["code"]
        }
    },
    {
        "name": "search_code",
        "description": "파일들에서 특정 패턴/키워드를 검색합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "검색할 패턴"},
                "directory": {"type": "string", "description": "검색할 디렉토리 (기본: 현재)"},
                "file_pattern": {"type": "string", "description": "파일 패턴 (예: '*.py')"}
            },
            "required": ["pattern"]
        }
    }
]


# ──────────────────────────────────────────────
# 도구 실행 함수들 (실제 환경과 상호작용)
# ──────────────────────────────────────────────

def read_file(path: str) -> dict[str, Any]:
    try:
        content = Path(path).read_text(encoding="utf-8")
        return {"success": True, "content": content, "lines": content.count("\n") + 1}
    except FileNotFoundError:
        return {"success": False, "error": f"파일을 찾을 수 없습니다: {path}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def write_file(path: str, content: str) -> dict[str, Any]:
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"success": True, "message": f"파일 저장 완료: {path} ({len(content)} bytes)"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_files(directory: str = ".") -> dict[str, Any]:
    try:
        entries = []
        for item in sorted(Path(directory).iterdir()):
            entries.append({
                "name": item.name,
                "type": "dir" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None
            })
        return {"success": True, "entries": entries, "count": len(entries)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_python(code: str, timeout: int = 10) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["python3", "-c", code],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"타임아웃 ({timeout}초 초과)"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def search_code(pattern: str, directory: str = ".", file_pattern: str = "*.py") -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["grep", "-rn", "--include", file_pattern, pattern, directory],
            capture_output=True, text=True
        )
        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
        return {
            "success": True,
            "matches": lines,
            "count": len(lines)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# 도구 이름 → 함수 매핑
TOOL_REGISTRY = {
    "read_file": read_file,
    "write_file": write_file,
    "list_files": list_files,
    "run_python": run_python,
    "search_code": search_code,
}


def execute_tool(name: str, arguments: dict) -> str:
    """도구를 실행하고 결과를 JSON 문자열로 반환"""
    if name not in TOOL_REGISTRY:
        return json.dumps({"success": False, "error": f"알 수 없는 도구: {name}"})

    result = TOOL_REGISTRY[name](**arguments)
    return json.dumps(result, ensure_ascii=False, indent=2)
