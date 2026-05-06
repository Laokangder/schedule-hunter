import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ['PYTHONIOENCODING'] = 'utf-8'

from src.services.llm_service import LLMService
from src.services.parse_service import ParseService
from datetime import datetime


class TimeParserTest:
    def __init__(self):
        self.llm_service = LLMService()
        self.parse_service = ParseService()
        self.test_cases = [
            {
                "input": "28日晚上七点吃饭",
                "expected_times": ["19:00", "20:00"],
                "description": "晚上七点应提取为19:00"
            },
            {
                "input": "明天上午八点半开会",
                "expected_times": ["08:30", "09:30"],
                "description": "上午八点半应提取为08:30"
            },
            {
                "input": "去跑步",
                "expected_behavior": "no_time",
                "description": "无时间信息应标记needs_confirmation"
            },
            {
                "input": "下午三点去打球",
                "expected_times": ["15:00", "16:00"],
                "description": "下午三点应提取为15:00"
            },
            {
                "input": "明天中午十二点吃饭",
                "expected_times": ["12:00", "13:00"],
                "description": "中午十二点应提取为12:00"
            },
            {
                "input": "后天晚上九点开会",
                "expected_times": ["21:00", "22:00"],
                "description": "晚上九点应提取为21:00"
            }
        ]

    async def run_llm_test(self, test_input):
        print(f"\n{'='*60}")
        print(f"Test Input: {test_input['input']}")
        print(f"Expected: {test_input['description']}")

        try:
            result = await self.llm_service.parse_task(test_input['input'])
            print(f"\nParse Result:")
            print(f"  title: {result.get('title')}")
            print(f"  start_time: {result.get('start_time')}")
            print(f"  end_time: {result.get('end_time')}")
            print(f"  confidence: {result.get('confidence')}")
            print(f"  needs_confirmation: {result.get('needs_confirmation')}")
            print(f"  ai_fallback: {result.get('ai_fallback')}")

            if 'expected_times' in test_input:
                start_time = result.get('start_time', '')
                end_time = result.get('end_time', '')
                passed = any(exp in start_time for exp in test_input['expected_times'])
                print(f"\nResult: {'[PASS]' if passed else '[FAIL]'}")
                if not passed:
                    print(f"  Expected start_time to contain: {test_input['expected_times']}")
                    print(f"  Actual start_time: {start_time}")
            elif test_input.get('expected_behavior') == 'no_time':
                passed = result.get('needs_confirmation') == True or result.get('start_time') is None
                print(f"\nResult: {'[PASS]' if passed else '[FAIL]'}")
                if not passed:
                    print(f"  Expected: needs_confirmation=True or start_time=None")
                    print(f"  Actual: needs_confirmation={result.get('needs_confirmation')}, start_time={result.get('start_time')}")

            return result

        except Exception as e:
            print(f"\nException: {str(e)}")
            return None

    async def run_parse_service_test(self, test_input):
        print(f"\n{'='*60}")
        print(f"[ParseService] Test Input: {test_input['input']}")

        from src.models.request import ParseTaskRequest
        request = ParseTaskRequest(
            source_text=test_input['input'],
            context={},
            meta={}
        )

        try:
            result = await self.parse_service.parse(request, "test_trace")
            print(f"\nParse Result:")
            print(f"  title: {result.get('title')}")
            print(f"  start_time: {result.get('start_time')}")
            print(f"  end_time: {result.get('end_time')}")
            print(f"  confidence: {result.get('confidence')}")
            print(f"  needs_confirmation: {result.get('needs_confirmation')}")
            print(f"  ai_fallback: {result.get('ai_fallback')}")

            if 'expected_times' in test_input:
                start_time = result.get('start_time', '')
                passed = any(exp in start_time for exp in test_input['expected_times'])
                print(f"\nResult: {'[PASS]' if passed else '[FAIL]'}")
            elif test_input.get('expected_behavior') == 'no_time':
                passed = result.get('needs_confirmation') == True
                print(f"\nResult: {'[PASS]' if passed else '[FAIL]'}")

            return result

        except Exception as e:
            print(f"\nException: {str(e)}")
            return None

    async def run_all_tests(self):
        print("\n" + "="*60)
        print("Schedule Hunter - Time Parsing Test Suite")
        print("="*60)
        print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Test Cases: {len(self.test_cases)}")

        llm_passed = 0
        parse_passed = 0

        for i, test_case in enumerate(self.test_cases):
            print(f"\n{'#'*60}")
            print(f"## Test Case {i+1}/{len(self.test_cases)}")

            llm_result = await self.run_llm_test(test_case)
            if llm_result:
                if 'expected_times' in test_case:
                    start_time = llm_result.get('start_time', '')
                    if any(exp in start_time for exp in test_case['expected_times']):
                        llm_passed += 1
                elif test_case.get('expected_behavior') == 'no_time':
                    if llm_result.get('needs_confirmation') == True or llm_result.get('start_time') is None:
                        llm_passed += 1

            parse_result = await self.run_parse_service_test(test_case)
            if parse_result:
                if 'expected_times' in test_case:
                    start_time = parse_result.get('start_time', '')
                    if any(exp in start_time for exp in test_case['expected_times']):
                        parse_passed += 1
                elif test_case.get('expected_behavior') == 'no_time':
                    if parse_result.get('needs_confirmation') == True:
                        parse_passed += 1

        print(f"\n{'='*60}")
        print("Test Summary")
        print(f"{'='*60}")
        print(f"LLM Service: {llm_passed}/{len(self.test_cases)} passed")
        print(f"Parse Service: {parse_passed}/{len(self.test_cases)} passed")

        if llm_passed == len(self.test_cases) and parse_passed == len(self.test_cases):
            print(f"\n[SUCCESS] All tests passed!")
        else:
            print(f"\n[WARNING] Some tests failed, please check time extraction logic")


async def main():
    tester = TimeParserTest()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
