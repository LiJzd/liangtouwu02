# Implementation Plan

- [ ] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Datetime Availability in Report Generation
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: Scope the property to the concrete failing case - calling `build_dual_track_report` function at line 282 where `datetime.now()` is invoked
  - Test that `build_dual_track_report` function successfully accesses `datetime.now()` and formats it as `'%Y-%m-%d %H:%M:%S'` without raising NameError
  - Create test file: `两头乌ai端/tests/test_growth_curve_crash_fix.py`
  - Test implementation details from Bug Condition in design: execution reaches line 282, attempts `datetime.now().strftime()`, and datetime is not in local or global namespace
  - The test assertions should match the Expected Behavior Properties from design: datetime.now() call succeeds and returns formatted timestamp string
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS with `NameError: name 'datetime' is not defined` (this is correct - it proves the bug exists)
  - Document counterexamples found to understand root cause (e.g., "build_dual_track_report execution at line 282 raises NameError instead of returning formatted timestamp")
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 1.3_

- [ ] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Other Datetime Usage
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-buggy inputs: other functions in `pig_agent.py` that use datetime (e.g., `run_farm_daily_briefing`, `_analyze_log_trends`)
  - Write property-based tests capturing observed behavior patterns from Preservation Requirements
  - Test that `run_farm_daily_briefing` function's `datetime.now().date()` call continues to work normally
  - Test that `_analyze_log_trends` function's `str(datetime.now().date())` usage remains unchanged
  - Test that report generation's other parts (基础档案、预测曲线数据表格、数值引擎推演、AI专家诊断) maintain identical format and content
  - Property-based testing generates many test cases for stronger guarantees
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [ ] 3. Fix for datetime import issue in build_dual_track_report

  - [ ] 3.1 Implement the fix
    - Verify import statement at line 26: `from datetime import datetime` exists and is not modified
    - Check for variable name conflicts: ensure no local variables or parameters named `datetime` in the file
    - Add function-level import in `build_dual_track_report` function if global import is unreliable: add `from datetime import datetime` at the beginning of the function
    - Verify module path operations in `run_dual_track_inspection` function: ensure `sys.path.insert(0, ...)` does not affect datetime import
    - Optional: Add defensive check before using datetime for better error messages
    - _Bug_Condition: isBugCondition(execution_context) where execution_context.function_name == 'build_dual_track_report' AND execution_context.line_number == 282 AND 'datetime' NOT IN execution_context.local_namespace AND 'datetime' NOT IN execution_context.global_namespace_
    - _Expected_Behavior: For any execution of build_dual_track_report function where the code reaches line 282, the fixed function SHALL successfully access datetime.now() and format it as '%Y-%m-%d %H:%M:%S' without raising NameError_
    - _Preservation: For any function in pig_agent.py that is NOT build_dual_track_report, the fixed code SHALL produce exactly the same behavior as the original code when using datetime functions_
    - _Requirements: 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.4_

  - [ ] 3.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Datetime Availability in Report Generation
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed - datetime.now() call succeeds and returns formatted timestamp)
    - _Requirements: Expected Behavior Properties from design - 2.1, 2.3_

  - [ ] 3.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Other Datetime Usage
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions - other datetime usage remains unchanged)
    - Confirm all tests still pass after fix (no regressions in run_farm_daily_briefing, _analyze_log_trends, and report format)

- [ ] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
