"""
demo.py - Ollama 없이도 에이전트 루프 동작 방식을 확인하는 데모

실제 LLM 없이 "mock" 응답으로 에이전트 패턴을 시각화합니다.
Claude Code / Codex 내부에서 일어나는 일을 단계별로 보여줍니다.
"""

import json
import time
from tools import execute_tool


# ──────────────────────────────────────────────
# Mock LLM: 실제 Ollama 대신 미리 짜둔 시나리오로 시뮬레이션
# ──────────────────────────────────────────────

SCENARIO = [
    # Step 1: LLM이 먼저 파일 목록을 확인
    """현재 디렉토리를 먼저 확인해보겠습니다.

<tool_call>
{"name": "list_files", "arguments": {"directory": "."}}
</tool_call>""",

    # Step 2: 파일 목록 확인 후 코드 작성
    r"""파일 목록을 확인했습니다. 이제 피보나치 함수를 작성하겠습니다.

<tool_call>
{"name": "write_file", "arguments": {"path": "fibonacci.py", "content": "def fibonacci(n):\n    if n <= 1:\n        return n\n    a, b = 0, 1\n    for _ in range(2, n+1):\n        a, b = b, a+b\n    return b\n\nfor i in range(10):\n    print(f'fibonacci({i}) = {fibonacci(i)}')\n"}}
</tool_call>""",

    # Step 3: 작성한 코드 실행해서 테스트
    r"""코드를 저장했습니다. 이제 실행해서 테스트해보겠습니다.

<tool_call>
{"name": "run_python", "arguments": {"code": "exec(open('fibonacci.py').read())"}}
</tool_call>""",

    # Step 4: 결과 확인 후 완료
    """테스트 결과가 정상입니다!

fibonacci.py 파일을 생성했습니다:
- 반복문을 사용한 효율적인 구현 (O(n) 시간복잡도)
- 0~9까지의 피보나치 수열을 출력하는 테스트 포함

<done>"""
]


def simulate_llm(step: int, context: str = "") -> str:
    """실제 LLM 호출을 흉내내는 함수"""
    time.sleep(0.5)  # LLM 처리 시간 시뮬레이션
    if step < len(SCENARIO):
        return SCENARIO[step]
    return "작업이 완료되었습니다. <done>"


def extract_tool_call(text: str) -> dict | None:
    import re
    match = re.search(r'<tool_call>\s*(.*?)\s*</tool_call>', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    return None


# ──────────────────────────────────────────────
# 에이전트 루프 시각화
# ──────────────────────────────────────────────

def run_demo():
    print("\n" + "=" * 60)
    print("  AI 코딩 에이전트 동작 방식 데모")
    print("  (Claude Code / Codex 내부 메커니즘 시뮬레이션)")
    print("=" * 60)

    user_request = "피보나치 수열을 계산하는 Python 파일을 만들고 테스트해줘"
    print(f"\n[사용자 요청]: {user_request}")
    print("\n" + "─" * 60)

    messages = []
    messages.append({"role": "user", "content": user_request})

    print("""
┌─────────────────────────────────────────────────────┐
│               에이전트 루프 시작                        │
│                                                     │
│  while not done:                                    │
│    1. LLM 호출  (현재 대화 히스토리 전달)               │
│    2. 응답 파싱 (도구 호출 여부 확인)                   │
│    3. 도구 실행 (파일 읽기/쓰기, 코드 실행 등)           │
│    4. 결과 저장 (다음 LLM 호출을 위해 히스토리에 추가)    │
└─────────────────────────────────────────────────────┘
""")

    for iteration in range(10):
        print(f"\n{'━' * 60}")
        print(f"  LOOP #{iteration + 1}")
        print(f"{'━' * 60}")

        # ── 1. LLM 호출 ──────────────────────────────
        print(f"\n  [1] LLM 호출")
        print(f"      → 현재 대화 히스토리: {len(messages)}개 메시지")
        print(f"      → LLM이 맥락을 이해하고 다음 행동 결정 중...")

        llm_response = simulate_llm(iteration)
        messages.append({"role": "assistant", "content": llm_response})

        # 응답에서 실제 내용만 (tool_call 태그 제외) 요약 출력
        clean_response = llm_response.replace('\n', ' ')[:80]
        print(f"      ← LLM 응답: \"{clean_response}...\"")

        # ── 2. 완료 체크 ──────────────────────────────
        if "<done>" in llm_response:
            print(f"\n  [완료 감지] '<done>' 태그 확인 → 루프 종료")
            break

        # ── 3. 도구 호출 파싱 ─────────────────────────
        tool_call = extract_tool_call(llm_response)
        if not tool_call:
            print(f"\n  [도구 호출 없음] 텍스트 응답만 있음 → 루프 종료")
            break

        tool_name = tool_call["name"]
        tool_args = tool_call.get("arguments", {})

        print(f"\n  [2] 도구 호출 감지")
        print(f"      도구: {tool_name}")
        print(f"      인자: {json.dumps(tool_args, ensure_ascii=False)[:100]}")

        # ── 4. 도구 실행 ──────────────────────────────
        print(f"\n  [3] 도구 실행 중...")
        result = execute_tool(tool_name, tool_args)
        result_data = json.loads(result)

        if result_data.get("success"):
            print(f"      ✓ 성공")
            # 결과 요약 출력
            if "entries" in result_data:
                print(f"        파일 {result_data['count']}개 발견")
            elif "message" in result_data:
                print(f"        {result_data['message']}")
            elif "stdout" in result_data:
                output = result_data["stdout"][:100]
                print(f"        출력: {output}")
        else:
            print(f"      ✗ 실패: {result_data.get('error', '알 수 없는 오류')}")

        # ── 5. 결과를 히스토리에 추가 ──────────────────
        print(f"\n  [4] 결과를 대화 히스토리에 저장")
        print(f"      → 다음 LLM 호출 시 이 결과를 참고하여 계속 작업")

        messages.append({
            "role": "user",
            "content": f"<tool_result>\n{result}\n</tool_result>"
        })

    print(f"\n\n{'=' * 60}")
    print("  데모 완료!")
    print(f"{'=' * 60}")
    print(f"\n총 {len(messages)}개의 메시지가 대화 히스토리에 쌓였습니다.")
    print("\n이것이 Claude Code / Codex 같은 AI 코딩 도구의 핵심 원리입니다:")
    print("  - LLM은 '도구를 쓸지 말지' 와 '어떤 도구를 쓸지' 를 결정")
    print("  - 실제 파일 조작, 코드 실행은 도구(Tool)가 담당")
    print("  - 대화 히스토리로 맥락을 유지하며 반복")
    print("  - 작업 완료 신호(<done>)가 오면 루프 종료\n")


if __name__ == "__main__":
    run_demo()
