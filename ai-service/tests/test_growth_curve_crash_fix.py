# -*- coding: utf-8 -*-
"""
Bug Condition Exploration Test for Growth Curve Crash Fix

**CRITICAL**: This test MUST FAIL on unfixed code with NameError: name 'datetime' is not defined
The failure confirms the bug exists at line 433 in build_dual_track_report function.

**Validates: Requirements 1.1, 1.2, 1.3**
**Property 1: Bug Condition - Datetime Availability in Report Generation**

Test Strategy:
- Directly call build_dual_track_report with valid parameters
- Expected on UNFIXED code: NameError when reaching line 433 (datetime.now().strftime())
- Expected on FIXED code: Test passes, report contains formatted timestamp
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import pig_agent
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from pig_rag.pig_agent import build_dual_track_report


# ============================================================
# Test Data Generators
# ============================================================

@st.composite
def valid_pig_report_data(draw):
    """
    Generate valid input data for build_dual_track_report function.
    
    This generator creates realistic pig growth report parameters that would
    trigger the datetime.now() call at line 433.
    """
    pig_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    breed = draw(st.sampled_from(["两头乌", "杜洛克", "长白猪", "大白猪"]))
    current_day_age = draw(st.integers(min_value=30, max_value=300))
    current_weight = draw(st.floats(min_value=10.0, max_value=150.0, allow_nan=False, allow_infinity=False))
    
    # Generate predicted curve with at least one data point
    num_points = draw(st.integers(min_value=1, max_value=10))
    predicted_curve = []
    for i in range(num_points):
        day_age = current_day_age + (i + 1) * 30
        weight_kg = current_weight + draw(st.floats(min_value=5.0, max_value=30.0, allow_nan=False, allow_infinity=False))
        predicted_curve.append({
            "day_age": day_age,
            "weight_kg": weight_kg
        })
    
    deviation_summary = draw(st.sampled_from([
        "生长速率符合预期",
        "生长速率略低于标准",
        "生长速率显著偏低",
        "生长速率超出预期"
    ]))
    deviation_percent = draw(st.floats(min_value=-30.0, max_value=30.0, allow_nan=False, allow_infinity=False))
    
    # Generate match summary with at least one match
    num_matches = draw(st.integers(min_value=1, max_value=5))
    match_summary = []
    for i in range(num_matches):
        match_summary.append({
            "pig_id": f"HIST_{draw(st.integers(min_value=1000, max_value=9999))}",
            "dtw_distance": draw(st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)),
            "final_weight": draw(st.floats(min_value=80.0, max_value=120.0, allow_nan=False, allow_infinity=False))
        })
    
    diagnosis_text = draw(st.text(min_size=10, max_size=500))
    
    return {
        "pig_id": pig_id,
        "breed": breed,
        "current_day_age": current_day_age,
        "current_weight": current_weight,
        "predicted_curve": predicted_curve,
        "deviation_summary": deviation_summary,
        "deviation_percent": deviation_percent,
        "match_summary": match_summary,
        "diagnosis_text": diagnosis_text
    }


# ============================================================
# Bug Condition Exploration Tests
# ============================================================

@given(data=valid_pig_report_data())
@settings(
    max_examples=50,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None
)
def test_build_dual_track_report_datetime_availability(data):
    """
    **Property 1: Bug Condition - Datetime Availability in Report Generation**
    
    **Validates: Requirements 2.1, 2.3**
    
    For any execution of build_dual_track_report function where the code reaches 
    line 433 to generate the timestamp, the function SHALL successfully access 
    datetime.now() and format it as '%Y-%m-%d %H:%M:%S' without raising NameError.
    
    **EXPECTED OUTCOME ON UNFIXED CODE**: 
    Test FAILS with NameError: name 'datetime' is not defined at line 433
    
    **EXPECTED OUTCOME ON FIXED CODE**: 
    Test PASSES - report contains formatted timestamp matching pattern YYYY-MM-DD HH:MM:SS
    
    **Counterexample Documentation**:
    If this test fails on unfixed code, it confirms:
    - Bug exists: datetime is not accessible in build_dual_track_report's namespace at line 433
    - Root cause: Despite import at line 26, datetime name is undefined when strftime is called
    - Impact: Complete report generation flow crashes, preventing user from getting inspection results
    """
    # Call the function that should trigger datetime.now() at line 433
    # On unfixed code: This will raise NameError
    # On fixed code: This will succeed and return a report with timestamp
    report = build_dual_track_report(
        pig_id=data["pig_id"],
        breed=data["breed"],
        current_day_age=data["current_day_age"],
        current_weight=data["current_weight"],
        predicted_curve=data["predicted_curve"],
        deviation_summary=data["deviation_summary"],
        deviation_percent=data["deviation_percent"],
        match_summary=data["match_summary"],
        diagnosis_text=data["diagnosis_text"]
    )
    
    # Verify the report is a string
    assert isinstance(report, str), f"Expected report to be string, got {type(report)}"
    
    # Verify the report is not empty
    assert len(report) > 0, "Report should not be empty"
    
    # Verify the report contains the timestamp line
    # The timestamp should be at the end of the report in format: *报告生成时间：YYYY-MM-DD HH:MM:SS*
    assert "*报告生成时间：" in report, "Report should contain timestamp marker"
    
    # Extract and verify timestamp format
    import re
    timestamp_pattern = r'\*报告生成时间：(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\*'
    match = re.search(timestamp_pattern, report)
    
    assert match is not None, f"Report should contain timestamp in format YYYY-MM-DD HH:MM:SS, but got: {report[-200:]}"
    
    timestamp_str = match.group(1)
    
    # Verify the timestamp can be parsed (validates format correctness)
    from datetime import datetime as dt
    try:
        parsed_time = dt.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        assert parsed_time is not None, "Timestamp should be parseable"
    except ValueError as e:
        pytest.fail(f"Timestamp format is invalid: {timestamp_str}, error: {e}")


def test_build_dual_track_report_concrete_case():
    """
    Concrete test case to explicitly demonstrate the bug condition.
    
    This test uses a specific, minimal example to trigger the datetime.now() call.
    Easier to debug than property-based test when investigating root cause.
    
    **EXPECTED ON UNFIXED CODE**: NameError at line 433
    **EXPECTED ON FIXED CODE**: Report with valid timestamp
    """
    # Minimal valid input
    pig_id = "TEST001"
    breed = "两头乌"
    current_day_age = 90
    current_weight = 35.5
    predicted_curve = [
        {"day_age": 120, "weight_kg": 45.0},
        {"day_age": 150, "weight_kg": 55.0}
    ]
    deviation_summary = "生长速率符合预期"
    deviation_percent = 2.5
    match_summary = [
        {"pig_id": "HIST_1234", "dtw_distance": 1.23, "final_weight": 95.0}
    ]
    diagnosis_text = "### 风险评估\n- 生长正常\n\n### 干预建议\n- 继续观察"
    
    # This call should trigger the bug on unfixed code
    report = build_dual_track_report(
        pig_id=pig_id,
        breed=breed,
        current_day_age=current_day_age,
        current_weight=current_weight,
        predicted_curve=predicted_curve,
        deviation_summary=deviation_summary,
        deviation_percent=deviation_percent,
        match_summary=match_summary,
        diagnosis_text=diagnosis_text
    )
    
    # Verify report structure
    assert "## 生猪个体生长趋势分析报告" in report
    assert f"**猪只ID**：`{pig_id}`" in report
    assert "*报告生成时间：" in report
    
    # Verify timestamp exists and is properly formatted
    import re
    timestamp_pattern = r'\*报告生成时间：\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\*'
    assert re.search(timestamp_pattern, report), "Report must contain properly formatted timestamp"


if __name__ == "__main__":
    print("=" * 80)
    print("Bug Condition Exploration Test for Growth Curve Crash Fix")
    print("=" * 80)
    print("\n**CRITICAL**: This test MUST FAIL on unfixed code!")
    print("Expected error: NameError: name 'datetime' is not defined at line 433\n")
    
    # Run concrete test first for easier debugging
    print("Running concrete test case...")
    try:
        test_build_dual_track_report_concrete_case()
        print("✓ Concrete test PASSED - Bug appears to be fixed!")
    except NameError as e:
        print(f"✗ Concrete test FAILED with NameError (EXPECTED on unfixed code): {e}")
        print("   This confirms the bug exists: datetime is not defined at line 433")
    except Exception as e:
        print(f"✗ Concrete test FAILED with unexpected error: {e}")
    
    print("\n" + "=" * 80)
    print("Run full property-based tests with: pytest test_growth_curve_crash_fix.py -v")
    print("=" * 80)
