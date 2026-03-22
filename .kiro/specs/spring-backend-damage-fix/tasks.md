# Implementation Plan

- [ ] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Maven编译失败验证
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: For deterministic bugs, scope the property to the concrete failing case(s) to ensure reproducibility
  - Test that Maven compilation fails when CameraService interface does not exist in com.liangtouwu.business.service package
  - Test that Maven compilation fails when DailyBriefingService imports com.liangtouwu.business.entity.DailyBriefing (wrong path)
  - Execute `mvn clean compile -pl liangtouwu-business` on UNFIXED code
  - **EXPECTED OUTCOME**: Compilation FAILS with "cannot find symbol: class CameraService" and "package com.liangtouwu.business.entity does not exist"
  - Document counterexamples found to understand root cause
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 1.3_

- [ ] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - 现有功能保持不变
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-buggy inputs
  - Test that MonitorService.getCameras() continues to work correctly
  - Test that CameraMapper.findAll() continues to work correctly
  - Test that Camera and DailyBriefing entities remain in domain layer (com.liangtouwu.domain.entity)
  - Test that other Service interfaces and implementations are unaffected
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ] 3. Fix for Spring Backend编译错误

  - [x] 3.1 Create CameraService interface
    - Create file: `两头乌后端/liangtouwu-business/src/main/java/com/liangtouwu/business/service/CameraService.java`
    - Define getCameras() method returning List<Map<String, Object>>
    - Follow MonitorService interface design pattern
    - Use standard Java interface declaration
    - _Bug_Condition: isBugCondition(input) where NOT exists("com.liangtouwu.business.service.CameraService")_
    - _Expected_Behavior: Maven compilation succeeds, CameraController can inject CameraService_
    - _Preservation: MonitorService, CameraMapper, entity locations remain unchanged_
    - _Requirements: 2.1, 2.3_

  - [x] 3.2 Create CameraServiceImpl implementation
    - Create file: `两头乌后端/liangtouwu-business/src/main/java/com/liangtouwu/business/service/impl/CameraServiceImpl.java`
    - Use @Service annotation to mark as Spring Bean
    - Inject CameraMapper via @Autowired
    - Implement getCameras() method calling CameraMapper.findAll() and converting to Map format
    - Follow MonitorServiceImpl implementation pattern
    - _Bug_Condition: isBugCondition(input) where CameraService has no implementation_
    - _Expected_Behavior: Spring container can instantiate CameraService bean_
    - _Preservation: Service implementation patterns remain consistent_
    - _Requirements: 2.1, 2.3_

  - [x] 3.3 Fix DailyBriefingService import path
    - Modify file: `两头乌后端/liangtouwu-business/src/main/java/com/liangtouwu/business/service/DailyBriefingService.java`
    - Change line 3 import statement from `import com.liangtouwu.business.entity.DailyBriefing;`
    - To: `import com.liangtouwu.domain.entity.DailyBriefing;`
    - Ensure import path follows Maven multi-module architecture layering principles
    - _Bug_Condition: isBugCondition(input) where imports("com.liangtouwu.business.entity.DailyBriefing")_
    - _Expected_Behavior: Maven compilation succeeds, DailyBriefingService can use DailyBriefing entity_
    - _Preservation: DailyBriefing entity remains in domain layer_
    - _Requirements: 2.2, 2.3_

  - [ ] 3.4 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Maven编译成功
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Execute `mvn clean compile -pl liangtouwu-business` on FIXED code
    - **EXPECTED OUTCOME**: Compilation PASSES with no errors
    - _Requirements: 2.1, 2.2, 2.3_

  - [ ] 3.5 Verify preservation tests still pass
    - **Property 2: Preservation** - 现有功能保持不变
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fix (no regressions)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 4. Checkpoint - Ensure all tests pass
  - Run full Maven build: `mvn clean install`
  - Test Spring Boot application startup: `mvn spring-boot:run`
  - Verify CameraController /camera/list endpoint responds correctly
  - Verify DailyBriefingService methods work correctly
  - Ensure all tests pass, ask the user if questions arise
