"""
agent.py - AI 코딩 에이전트의 핵심 루프

Claude Code / Codex 같은 도구들이 실제로 하는 일:

  1. 사용자 요청을 받는다
  2. LLM이 "어떤 도구를 써야 할지" 결정한다  ← Think
  3. 도구를 실제로 실행한다                   ← Act
  4. 결과를 LLM에게 돌려준다                  ← Observe
  5. 2~4를 작업 완료까지 반복한다             ← Loop

이걸 "ReAct (Reasoning + Acting)" 패턴 또는
"Agentic Loop" 라고 부릅니다.
"""

import json
import re
from typing import Generator
import ollama
from tools import TOOLS, execute_tool


# ──────────────────────────────────────────────
# 시스템 프롬프트: LLM에게 "역할"과 "도구 사용법"을 알려줌
# ──────────────────────────────────────────────

SYSTEM_PROMPT = """당신은 Python 코딩을 도와주는 AI 에이전트입니다.

다음 도구들을 사용해 파일 시스템과 상호작용할 수 있습니다:
- read_file: 파일 읽기
- write_file: 파일 쓰기
- list_files: 파일 목록 조회
- run_python: Python 코드 실행
- search_code: 코드 검색

도구를 사용하려면 다음 형식으로 응답하세요:

<tool_call>
{"name": "도구이름", "arguments": {"인자명": "값"}}
</tool_call>

도구 결과를 받은 후 계속 작업하거나 최종 답변을 제공하세요.
작업 완료 시 <done>을 출력하세요.

중요:
- 코드를 작성할 때는 항상 write_file로 저장하세요
- 코드 실행 전 run_python으로 테스트하세요
- 한국어로 친절하게 설명하세요
"""


class CodingAgent:
    """
    Ollama 기반 AI 코딩 에이전트

    핵심 구조:
    - messages: 대화 히스토리 (LLM은 이걸 보고 문맥을 이해)
    - agentic_loop: 도구 호출이 끝날 때까지 반복하는 루프
    """

    def __init__(self, model: str = "qwen2.5-coder:7b", verbose: bool = True):
        self.model = model
        self.verbose = verbose
        self.messages: list[dict] = []
        self.max_iterations = 10  # 무한루프 방지

    def reset(self):
        """대화 히스토리 초기화"""
        self.messages = []

    def _build_tools_description(self) -> str:
        """도구 목록을 프롬프트용 텍스트로 변환"""
        lines = []
        for tool in TOOLS:
            params = tool["parameters"].get("properties", {})
            param_desc = ", ".join(
                f"{k}: {v.get('description', '')}"
                for k, v in params.items()
            )
            lines.append(f"- {tool['name']}({param_desc}): {tool['description']}")
        return "\n".join(lines)

    def _extract_tool_call(self, text: str) -> dict | None:
        """LLM 응답에서 도구 호출 파싱"""
        match = re.search(r'<tool_call>\s*(.*?)\s*</tool_call>', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                return None
        return None

    def _is_done(self, text: str) -> bool:
        """작업 완료 여부 확인"""
        return "<done>" in text.lower()

    def run(self, user_request: str) -> Generator[str, None, None]:
        """
        에이전트 실행 - 제너레이터로 진행 상황을 스트리밍

        에이전트 루프:
        while not done:
            1. LLM 호출 (현재 메시지 히스토리 전달)
            2. 응답에서 도구 호출 파싱
            3. 도구 실행
            4. 결과를 히스토리에 추가
        """
        # 사용자 메시지 추가
        self.messages.append({"role": "user", "content": user_request})

        yield f"\n[사용자]: {user_request}\n"
        yield "─" * 50 + "\n"

        for iteration in range(self.max_iterations):
            yield f"\n[에이전트 루프 #{iteration + 1}]\n"

            # ── Step 1: LLM 호출 ──────────────────────
            yield "  LLM thinking...\n"

            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    *self.messages
                ],
                stream=False
            )

            assistant_message = response["message"]["content"]
            self.messages.append({"role": "assistant", "content": assistant_message})

            # LLM 응답 출력
            yield f"\n[LLM 응답]:\n{assistant_message}\n"

            # ── Step 2: 완료 체크 ─────────────────────
            if self._is_done(assistant_message):
                yield "\n[완료] 에이전트가 작업을 마쳤습니다.\n"
                break

            # ── Step 3: 도구 호출 파싱 ────────────────
            tool_call = self._extract_tool_call(assistant_message)

            if not tool_call:
                # 도구 호출 없이 텍스트만 응답 → 작업 완료로 간주
                yield "\n[완료] 최종 응답을 받았습니다.\n"
                break

            tool_name = tool_call.get("name", "")
            tool_args = tool_call.get("arguments", {})

            yield f"\n[도구 실행]: {tool_name}\n"
            yield f"  인자: {json.dumps(tool_args, ensure_ascii=False)}\n"

            # ── Step 4: 도구 실행 ─────────────────────
            tool_result = execute_tool(tool_name, tool_args)
            yield f"  결과: {tool_result[:200]}{'...' if len(tool_result) > 200 else ''}\n"

            # ── Step 5: 결과를 히스토리에 추가 ──────────
            # LLM이 다음 턴에 도구 결과를 "기억"하게 함
            self.messages.append({
                "role": "user",
                "content": f"<tool_result>\n도구: {tool_name}\n결과:\n{tool_result}\n</tool_result>\n\n위 결과를 바탕으로 계속 진행해주세요."
            })

        else:
            yield f"\n[경고] 최대 반복 횟수({self.max_iterations})에 도달했습니다.\n"

        yield "\n" + "─" * 50 + "\n"


def main():
    """대화형 에이전트 실행"""
    print("=" * 60)
    print("  MyCoder - Ollama 기반 AI 코딩 에이전트")
    print("  (Claude Code / Codex 동작 방식 데모)")
    print("=" * 60)
    print("\n사용 가능한 모델: qwen2.5-coder:7b, codellama:7b, llama3.1:8b")
    print("종료: 'exit' 또는 'quit' 입력\n")

    # 모델 선택
    model = input("모델 선택 (기본: qwen2.5-coder:7b): ").strip()
    if not model:
        model = "qwen2.5-coder:7b"

    agent = CodingAgent(model=model)

    print(f"\n모델 '{model}'로 에이전트를 시작합니다.\n")
    print("예시 요청:")
    print("  - 'hello.py 파일을 만들고 Hello World를 출력해줘'")
    print("  - '피보나치 수열을 계산하는 함수를 작성하고 테스트해줘'")
    print("  - '현재 디렉토리의 파일들을 보여줘'\n")

    while True:
        try:
            user_input = input("[사용자] > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n에이전트를 종료합니다.")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "종료"):
            print("에이전트를 종료합니다.")
            break

        if user_input.lower() in ("reset", "초기화"):
            agent.reset()
            print("대화 히스토리를 초기화했습니다.\n")
            continue

        # 에이전트 실행 (스트리밍)
        for chunk in agent.run(user_input):
            print(chunk, end="", flush=True)
        print()


if __name__ == "__main__":
    main()
