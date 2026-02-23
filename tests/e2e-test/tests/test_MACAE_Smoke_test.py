"""GP Test cases for MACAE."""

import logging
import time

import pytest

from pages.HomePage import BIABPage
from config.constants import HR_CLARIFICATION_TEXT, PROMPT_QUESTION1, RAI_PROMPT

logger = logging.getLogger(__name__)


@pytest.mark.gp
def test_macae_v4_gp_workflow(login_logout, request):
    """
    Validate Golden path for MACAE-v4 with all 5 teams.
    
    Steps:
    1. Validate home page elements are visible
    2. Select Retail Customer Success team
    3. Select quick task and create plan with all agents
    4. Validate all retail agents are displayed
    5. Approve the task plan
    6. Validate retail customer response
    7. Click on new task
    8. Select Product Marketing team
    9. Select quick task and create plan
    10. Validate all product marketing agents are displayed
    11. Approve the task plan
    12. Validate product marketing response
    13. Click on new task
    14. Select Human Resources team
    15. Select quick task and create plan
    16. Validate all HR agents are displayed
    17. Approve the task plan
    18. Send human clarification with employee details
    19. Validate HR response
    20. Click on new task
    21. Select RFP team
    22. Select quick task and create plan
    23. Validate all RFP agents are displayed
    24. Approve the task plan
    25. Validate RFP response
    26. Click on new task
    27. Select Contract Compliance team
    28. Select quick task and create plan
    29. Validate all Contract Compliance agents are displayed
    30. Approve the task plan
    31. Validate Contract Compliance response
    """
    page = login_logout
    biab_page = BIABPage(page)
    
    # Update test node ID for HTML report
    request.node._nodeid = "(MACAE V4) Golden Path - Test all 5 teams workflow"
    
    logger.info("=" * 80)
    logger.info("Starting Multi-Team Workflow Test")
    logger.info("=" * 80)
    
    start_time = time.time()
    
    try:
        # Reload home page before starting test
        biab_page.reload_home_page()
        
        # Step 1: Validate Home Page
        logger.info("\n" + "=" * 80)
        logger.info("STEP 1: Validating Home Page")
        logger.info("=" * 80)
        step1_start = time.time()
        biab_page.validate_home_page()
        step1_end = time.time()
        logger.info(f"Step 1 completed in {step1_end - step1_start:.2f} seconds")
        
        # Step 2: Select Retail Customer Success Team
        logger.info("\n" + "=" * 80)
        logger.info("STEP 2: Selecting Retail Customer Success Team")
        logger.info("=" * 80)
        step2_start = time.time()
        biab_page.select_retail_customer_success_team()
        step2_end = time.time()
        logger.info(f"Step 2 completed in {step2_end - step2_start:.2f} seconds")
        
        # Step 3: Select Quick Task and Create Plan
        logger.info("\n" + "=" * 80)
        logger.info("STEP 3: Selecting Quick Task and Creating Plan")
        logger.info("=" * 80)
        step3_start = time.time()
        biab_page.select_quick_task_and_create_plan()
        step3_end = time.time()
        logger.info(f"Step 3 completed in {step3_end - step3_start:.2f} seconds")
        
        # Step 4: Validate All Retail Agents Visible
        logger.info("\n" + "=" * 80)
        logger.info("STEP 4: Validating All Retail Agents Are Displayed")
        logger.info("=" * 80)
        step4_start = time.time()
        biab_page.validate_retail_agents_visible()
        step4_end = time.time()
        logger.info(f"Step 4 completed in {step4_end - step4_start:.2f} seconds")
        
        # Step 5: Approve Retail Task Plan (with retry logic)
        logger.info("\n" + "=" * 80)
        logger.info("STEP 5: Approving Retail Task Plan")
        logger.info("=" * 80)
        step5_start = time.time()
        step5_retry_attempted = False
        try:
            biab_page.approve_retail_task_plan()
            step5_end = time.time()
            logger.info(f"Step 5 completed in {step5_end - step5_start:.2f} seconds")
        except Exception as step5_error:
            logger.warning("\n" + "⚠" * 80)
            logger.warning(f"STEP 5 FAILED: {str(step5_error)}")
            logger.warning("Initiating retry logic: Step 7 (New Task) → Retry Steps 3, 4, 5")
            logger.warning("⚠" * 80)
            
            # Perform Step 7: Click New Task
            logger.info("\n" + "=" * 80)
            logger.info("STEP 7 (RETRY): Clicking New Task")
            logger.info("=" * 80)
            step7_retry_start = time.time()
            biab_page.click_new_task()
            biab_page.cancel_retail_task_plan()
            step7_retry_end = time.time()
            logger.info(f"Step 7 (Retry) completed in {step7_retry_end - step7_retry_start:.2f} seconds")
            
            # Retry Step 3: Select Quick Task and Create Plan
            logger.info("\n" + "=" * 80)
            logger.info("STEP 3 (RETRY): Selecting Quick Task and Creating Plan")
            logger.info("=" * 80)
            step3_retry_start = time.time()
            biab_page.select_quick_task_and_create_plan()
            step3_retry_end = time.time()
            logger.info(f"Step 3 (Retry) completed in {step3_retry_end - step3_retry_start:.2f} seconds")
            
            # Retry Step 4: Validate All Retail Agents Visible
            logger.info("\n" + "=" * 80)
            logger.info("STEP 4 (RETRY): Validating All Retail Agents Are Displayed")
            logger.info("=" * 80)
            step4_retry_start = time.time()
            biab_page.validate_retail_agents_visible()
            step4_retry_end = time.time()
            logger.info(f"Step 4 (Retry) completed in {step4_retry_end - step4_retry_start:.2f} seconds")
            
            # Retry Step 5: Approve Task Plan
            logger.info("\n" + "=" * 80)
            logger.info("STEP 5 (RETRY): Approving Retail Task Plan")
            logger.info("=" * 80)
            step5_retry_start = time.time()
            biab_page.approve_retail_task_plan()
            step5_end = time.time()
            logger.info(f"Step 5 (Retry) completed in {step5_end - step5_retry_start:.2f} seconds")
            logger.info("✓ Retry successful - continuing with test execution")
        
        # Step 6: Validate Retail Customer Response
        logger.info("\n" + "=" * 80)
        logger.info("STEP 6: Validating Retail Customer Response")
        logger.info("=" * 80)
        step6_start = time.time()
        biab_page.validate_retail_customer_response()
        step6_end = time.time()
        logger.info(f"Step 6 completed in {step6_end - step6_start:.2f} seconds")
        
        # Step 7: Click New Task
        logger.info("\n" + "=" * 80)
        logger.info("STEP 7: Clicking New Task")
        logger.info("=" * 80)
        step7_start = time.time()
        biab_page.click_new_task()
        step7_end = time.time()
        logger.info(f"Step 7 completed in {step7_end - step7_start:.2f} seconds")
        
        # Step 8: Select Product Marketing Team
        logger.info("\n" + "=" * 80)
        logger.info("STEP 8: Selecting Product Marketing Team")
        logger.info("=" * 80)
        step8_start = time.time()
        biab_page.select_product_marketing_team()
        step8_end = time.time()
        logger.info(f"Step 8 completed in {step8_end - step8_start:.2f} seconds")
        
        # Step 9: Select Quick Task and Create Plan (Product Marketing)
        logger.info("\n" + "=" * 80)
        logger.info("STEP 9: Selecting Quick Task and Creating Plan (Product Marketing)")
        logger.info("=" * 80)
        step9_start = time.time()
        biab_page.select_quick_task_and_create_plan()
        step9_end = time.time()
        logger.info(f"Step 9 completed in {step9_end - step9_start:.2f} seconds")
        
        # Step 10: Validate All Product Marketing Agents Visible
        logger.info("\n" + "=" * 80)
        logger.info("STEP 10: Validating All Product Marketing Agents Are Displayed")
        logger.info("=" * 80)
        step10_start = time.time()
        biab_page.validate_product_marketing_agents()
        step10_end = time.time()
        logger.info(f"Step 10 completed in {step10_end - step10_start:.2f} seconds")
        
        # Step 11: Approve Task Plan (Product Marketing)
        logger.info("\n" + "=" * 80)
        logger.info("STEP 11: Approving Task Plan (Product Marketing)")
        logger.info("=" * 80)
        step11_start = time.time()
        biab_page.approve_product_marketing_task_plan()
        step11_end = time.time()
        logger.info(f"Step 11 completed in {step11_end - step11_start:.2f} seconds")
        
        # Step 12: Validate Product Marketing Response
        logger.info("\n" + "=" * 80)
        logger.info("STEP 12: Validating Product Marketing Response")
        logger.info("=" * 80)
        step12_start = time.time()
        biab_page.validate_product_marketing_response()
        step12_end = time.time()
        logger.info(f"Step 12 completed in {step12_end - step12_start:.2f} seconds")
        
        # Step 13: Click New Task
        logger.info("\n" + "=" * 80)
        logger.info("STEP 13: Clicking New Task")
        logger.info("=" * 80)
        step13_start = time.time()
        biab_page.click_new_task()
        step13_end = time.time()
        logger.info(f"Step 13 completed in {step13_end - step13_start:.2f} seconds")
        
        # Step 14: Select Human Resources Team
        logger.info("\n" + "=" * 80)
        logger.info("STEP 14: Selecting Human Resources Team")
        logger.info("=" * 80)
        step14_start = time.time()
        biab_page.select_human_resources_team()
        step14_end = time.time()
        logger.info(f"Step 14 completed in {step14_end - step14_start:.2f} seconds")
        
        # Step 15: Select Quick Task and Create Plan (HR)
        logger.info("\n" + "=" * 80)
        logger.info("STEP 15: Selecting Quick Task and Creating Plan (HR)")
        logger.info("=" * 80)
        step15_start = time.time()
        biab_page.select_quick_task_and_create_plan()
        step15_end = time.time()
        logger.info(f"Step 15 completed in {step15_end - step15_start:.2f} seconds")
        
        # Step 16: Validate All HR Agents Visible
        logger.info("\n" + "=" * 80)
        logger.info("STEP 16: Validating All HR Agents Are Displayed")
        logger.info("=" * 80)
        step16_start = time.time()
        biab_page.validate_hr_agents()
        step16_end = time.time()
        logger.info(f"Step 16 completed in {step16_end - step16_start:.2f} seconds")
        
        # Step 17: Approve Task Plan (HR)
        logger.info("\n" + "=" * 80)
        logger.info("STEP 17: Approving HR Task Plan")
        logger.info("=" * 80)
        step17_start = time.time()
        biab_page.approve_task_plan()
        step17_end = time.time()
        logger.info(f"Step 17 completed in {step17_end - step17_start:.2f} seconds")
        
        # Step 18: Send Human Clarification with Employee Details
        logger.info("\n" + "=" * 80)
        logger.info("STEP 18: Sending Human Clarification with Employee Details")
        logger.info("=" * 80)
        step18_start = time.time()
        biab_page.input_clarification_and_send(HR_CLARIFICATION_TEXT)
        step18_end = time.time()
        logger.info(f"Step 18 completed in {step18_end - step18_start:.2f} seconds")
        
        # Step 19: Validate HR Response
        logger.info("\n" + "=" * 80)
        logger.info("STEP 19: Validating HR Response")
        logger.info("=" * 80)
        step19_start = time.time()
        biab_page.validate_hr_response()
        step19_end = time.time()
        logger.info(f"Step 19 completed in {step19_end - step19_start:.2f} seconds")
        
        # Step 20: Click New Task
        logger.info("\n" + "=" * 80)
        logger.info("STEP 20: Clicking New Task")
        logger.info("=" * 80)
        step20_start = time.time()
        biab_page.click_new_task()
        step20_end = time.time()
        logger.info(f"Step 20 completed in {step20_end - step20_start:.2f} seconds")
        
        # Step 21: Select RFP Team
        logger.info("\n" + "=" * 80)
        logger.info("STEP 21: Selecting RFP Team")
        logger.info("=" * 80)
        step21_start = time.time()
        biab_page.select_rfp_team()
        step21_end = time.time()
        logger.info(f"Step 21 completed in {step21_end - step21_start:.2f} seconds")
        
        # Step 22: Select Quick Task and Create Plan (RFP)
        logger.info("\n" + "=" * 80)
        logger.info("STEP 22: Selecting Quick Task and Creating Plan (RFP)")
        logger.info("=" * 80)
        step22_start = time.time()
        biab_page.select_quick_task_and_create_plan()
        step22_end = time.time()
        logger.info(f"Step 22 completed in {step22_end - step22_start:.2f} seconds")
        
        # Step 23: Validate All RFP Agents Visible
        logger.info("\n" + "=" * 80)
        logger.info("STEP 23: Validating All RFP Agents Are Displayed")
        logger.info("=" * 80)
        step23_start = time.time()
        biab_page.validate_rfp_agents_visible()
        step23_end = time.time()
        logger.info(f"Step 23 completed in {step23_end - step23_start:.2f} seconds")
        
        # Step 24: Approve RFP Task Plan
        logger.info("\n" + "=" * 80)
        logger.info("STEP 24: Approving RFP Task Plan")
        logger.info("=" * 80)
        step24_start = time.time()
        biab_page.approve_rfp_task_plan()
        step24_end = time.time()
        logger.info(f"Step 24 completed in {step24_end - step24_start:.2f} seconds")
        
        # Step 25: Validate RFP Response
        logger.info("\n" + "=" * 80)
        logger.info("STEP 25: Validating RFP Response")
        logger.info("=" * 80)
        step25_start = time.time()
        biab_page.validate_rfp_response()
        step25_end = time.time()
        logger.info(f"Step 25 completed in {step25_end - step25_start:.2f} seconds")
        
        # Step 26: Click New Task
        logger.info("\n" + "=" * 80)
        logger.info("STEP 26: Clicking New Task")
        logger.info("=" * 80)
        step26_start = time.time()
        biab_page.click_new_task()
        step26_end = time.time()
        logger.info(f"Step 26 completed in {step26_end - step26_start:.2f} seconds")
        
        # Step 27: Select Contract Compliance Team
        logger.info("\n" + "=" * 80)
        logger.info("STEP 27: Selecting Contract Compliance Team")
        logger.info("=" * 80)
        step27_start = time.time()
        biab_page.select_contract_compliance_team()
        step27_end = time.time()
        logger.info(f"Step 27 completed in {step27_end - step27_start:.2f} seconds")
        
        # Step 28: Select Quick Task and Create Plan (Contract Compliance)
        logger.info("\n" + "=" * 80)
        logger.info("STEP 28: Selecting Quick Task and Creating Plan (Contract Compliance)")
        logger.info("=" * 80)
        step28_start = time.time()
        biab_page.select_quick_task_and_create_plan()
        step28_end = time.time()
        logger.info(f"Step 28 completed in {step28_end - step28_start:.2f} seconds")
        
        # Step 29: Validate All Contract Compliance Agents Visible
        logger.info("\n" + "=" * 80)
        logger.info("STEP 29: Validating All Contract Compliance Agents Are Displayed")
        logger.info("=" * 80)
        step29_start = time.time()
        biab_page.validate_contract_compliance_agents_visible()
        step29_end = time.time()
        logger.info(f"Step 29 completed in {step29_end - step29_start:.2f} seconds")
        
        # Step 30: Approve Contract Compliance Task Plan
        logger.info("\n" + "=" * 80)
        logger.info("STEP 30: Approving Contract Compliance Task Plan")
        logger.info("=" * 80)
        step30_start = time.time()
        biab_page.approve_contract_compliance_task_plan()
        step30_end = time.time()
        logger.info(f"Step 30 completed in {step30_end - step30_start:.2f} seconds")
        
        # Step 31: Validate Contract Compliance Response
        logger.info("\n" + "=" * 80)
        logger.info("STEP 31: Validating Contract Compliance Response")
        logger.info("=" * 80)
        step31_start = time.time()
        biab_page.validate_contract_compliance_response()
        step31_end = time.time()
        logger.info(f"Step 31 completed in {step31_end - step31_start:.2f} seconds")
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        logger.info("\n" + "=" * 80)
        logger.info("TEST EXECUTION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Step 1 (Home Page Validation): {step1_end - step1_start:.2f}s")
        logger.info(f"Step 2 (Retail Team Selection): {step2_end - step2_start:.2f}s")
        logger.info(f"Step 3 (Retail Quick Task & Plan Creation): {step3_end - step3_start:.2f}s")
        logger.info(f"Step 4 (Retail Agents Validation): {step4_end - step4_start:.2f}s")
        logger.info(f"Step 5 (Retail Approve Task Plan): {step5_end - step5_start:.2f}s")
        logger.info(f"Step 6 (Retail Customer Response Validation): {step6_end - step6_start:.2f}s")
        logger.info(f"Step 7 (Click New Task): {step7_end - step7_start:.2f}s")
        logger.info(f"Step 8 (Product Marketing Team Selection): {step8_end - step8_start:.2f}s")
        logger.info(f"Step 9 (Product Marketing Quick Task & Plan): {step9_end - step9_start:.2f}s")
        logger.info(f"Step 10 (Product Marketing Agents Validation): {step10_end - step10_start:.2f}s")
        logger.info(f"Step 11 (Product Marketing Approve Task Plan): {step11_end - step11_start:.2f}s")
        logger.info(f"Step 12 (Product Marketing Response Validation): {step12_end - step12_start:.2f}s")
        logger.info(f"Step 13 (Click New Task): {step13_end - step13_start:.2f}s")
        logger.info(f"Step 14 (HR Team Selection): {step14_end - step14_start:.2f}s")
        logger.info(f"Step 15 (HR Quick Task & Plan): {step15_end - step15_start:.2f}s")
        logger.info(f"Step 16 (HR Agents Validation): {step16_end - step16_start:.2f}s")
        logger.info(f"Step 17 (HR Approve Task Plan): {step17_end - step17_start:.2f}s")
        logger.info(f"Step 18 (HR Human Clarification): {step18_end - step18_start:.2f}s")
        logger.info(f"Step 19 (HR Response Validation): {step19_end - step19_start:.2f}s")
        logger.info(f"Step 20 (Click New Task): {step20_end - step20_start:.2f}s")
        logger.info(f"Step 21 (RFP Team Selection): {step21_end - step21_start:.2f}s")
        logger.info(f"Step 22 (RFP Quick Task & Plan): {step22_end - step22_start:.2f}s")
        logger.info(f"Step 23 (RFP Agents Validation): {step23_end - step23_start:.2f}s")
        logger.info(f"Step 24 (RFP Approve Task Plan): {step24_end - step24_start:.2f}s")
        logger.info(f"Step 25 (RFP Response Validation): {step25_end - step25_start:.2f}s")
        logger.info(f"Step 26 (Click New Task): {step26_end - step26_start:.2f}s")
        logger.info(f"Step 27 (Contract Compliance Team Selection): {step27_end - step27_start:.2f}s")
        logger.info(f"Step 28 (Contract Compliance Quick Task & Plan): {step28_end - step28_start:.2f}s")
        logger.info(f"Step 29 (Contract Compliance Agents Validation): {step29_end - step29_start:.2f}s")
        logger.info(f"Step 30 (Contract Compliance Approve Task Plan): {step30_end - step30_start:.2f}s")
        logger.info(f"Step 31 (Contract Compliance Response Validation): {step31_end - step31_start:.2f}s")
        logger.info(f"Total Execution Time: {total_duration:.2f}s")
        logger.info("=" * 80)
        logger.info("✓ MACAE-v4 Multi-Team Workflow Test PASSED")
        logger.info("=" * 80)
        
        # Attach execution time to pytest report
        request.node._report_sections.append(
            ("call", "log", f"Total execution time: {total_duration:.2f}s")
        )
        
    except Exception as e:
        end_time = time.time()
        total_duration = end_time - start_time
        logger.error("\n" + "=" * 80)
        logger.error("TEST EXECUTION FAILED")
        logger.error("=" * 80)
        logger.error(f"Error: {str(e)}")
        logger.error(f"Execution time before failure: {total_duration:.2f}s")
        logger.error("=" * 80)
        raise


def test_validate_source_text_not_visible(login_logout, request):
    """
    Validate that source text is not visible after retail customer response.
    
    Steps:
    1. Validate home page elements are visible
    2. Select Retail Customer Success team
    3. Select quick task and create plan
    4. Validate all retail agents are displayed
    5. Approve the task plan
    6. Validate retail customer response
    7. Validate source text is not visible
    """
    page = login_logout
    biab_page = BIABPage(page)
    
    # Update test node ID for HTML report
    request.node._nodeid = "(MACAE V3) Bug 23355: Bug - Agent output is showing citation sources that are not clickable or understandable"
    
    logger.info("=" * 80)
    logger.info("Starting Source Text Validation Test")
    logger.info("=" * 80)
    
    start_time = time.time()
    
    try:
        # Reload home page before starting test
        biab_page.reload_home_page()
        
        # Step 1: Validate Home Page
        logger.info("\n" + "=" * 80)
        logger.info("STEP 1: Validating Home Page")
        logger.info("=" * 80)
        step1_start = time.time()
        biab_page.validate_home_page()
        step1_end = time.time()
        logger.info(f"Step 1 completed in {step1_end - step1_start:.2f} seconds")
        
        # Step 2: Select Retail Customer Success Team
        logger.info("\n" + "=" * 80)
        logger.info("STEP 2: Selecting Retail Customer Success Team")
        logger.info("=" * 80)
        step2_start = time.time()
        biab_page.select_retail_customer_success_team()
        step2_end = time.time()
        logger.info(f"Step 2 completed in {step2_end - step2_start:.2f} seconds")
        
        # Step 3: Select Quick Task and Create Plan
        logger.info("\n" + "=" * 80)
        logger.info("STEP 3: Selecting Quick Task and Creating Plan")
        logger.info("=" * 80)
        step3_start = time.time()
        biab_page.select_quick_task_and_create_plan()
        step3_end = time.time()
        logger.info(f"Step 3 completed in {step3_end - step3_start:.2f} seconds")
        
        # Step 4: Validate All Retail Agents Visible
        logger.info("\n" + "=" * 80)
        logger.info("STEP 4: Validating All Retail Agents Are Displayed")
        logger.info("=" * 80)
        step4_start = time.time()
        biab_page.validate_retail_agents_visible()
        step4_end = time.time()
        logger.info(f"Step 4 completed in {step4_end - step4_start:.2f} seconds")
        
        # Step 5: Approve Retail Task Plan
        logger.info("\n" + "=" * 80)
        logger.info("STEP 5: Approving Retail Task Plan")
        logger.info("=" * 80)
        step5_start = time.time()
        biab_page.approve_retail_task_plan()
        step5_end = time.time()
        logger.info(f"Step 5 completed in {step5_end - step5_start:.2f} seconds")
        
        # Step 6: Validate Retail Customer Response
        logger.info("\n" + "=" * 80)
        logger.info("STEP 6: Validating Retail Customer Response")
        logger.info("=" * 80)
        step6_start = time.time()
        biab_page.validate_retail_customer_response()
        step6_end = time.time()
        logger.info(f"Step 6 completed in {step6_end - step6_start:.2f} seconds")
        
        # Step 7: Validate Source Text Not Visible
        logger.info("\n" + "=" * 80)
        logger.info("STEP 7: Validating Citation link Text Is Not Visible")
        logger.info("=" * 80)
        step7_start = time.time()
        biab_page.validate_source_text_not_visible()
        step7_end = time.time()
        logger.info(f"Step 7 completed in {step7_end - step7_start:.2f} seconds")
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        logger.info("\n" + "=" * 80)
        logger.info("TEST EXECUTION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Step 1 (Home Page Validation): {step1_end - step1_start:.2f}s")
        logger.info(f"Step 2 (Retail Team Selection): {step2_end - step2_start:.2f}s")
        logger.info(f"Step 3 (Quick Task & Plan Creation): {step3_end - step3_start:.2f}s")
        logger.info(f"Step 4 (Retail Agents Validation): {step4_end - step4_start:.2f}s")
        logger.info(f"Step 5 (Approve Task Plan): {step5_end - step5_start:.2f}s")
        logger.info(f"Step 6 (Retail Customer Response Validation): {step6_end - step6_start:.2f}s")
        logger.info(f"Step 7 (Source Text Not Visible Validation): {step7_end - step7_start:.2f}s")
        logger.info(f"Total Execution Time: {total_duration:.2f}s")
        logger.info("=" * 80)
        logger.info("✓ Source Text Validation Test PASSED")
        logger.info("=" * 80)
        
        # Attach execution time to pytest report
        request.node._report_sections.append(
            ("call", "log", f"Total execution time: {total_duration:.2f}s")
        )
        
    except Exception as e:
        end_time = time.time()
        total_duration = end_time - start_time
        logger.error("\n" + "=" * 80)
        logger.error("TEST EXECUTION FAILED")
        logger.error("=" * 80)
        logger.error(f"Error: {str(e)}")
        logger.error(f"Execution time before failure: {total_duration:.2f}s")
        logger.error("=" * 80)
        raise


def test_rai_validation_unable_to_create_plan(login_logout, request):
    """
    Validate RAI (Responsible AI) validation for 'Unable to create plan' message across all 5 teams.
    
    Steps:
    1. Validate home page elements are visible
    2. Test Retail Customer Success Team:
       - Select Retail Customer Success team
       - Enter RAI prompt
       - Validate 'Unable to create plan' message appears
       - Click new task
    3. Test Product Marketing Team:
       - Select Product Marketing team
       - Enter RAI prompt
       - Validate 'Unable to create plan' message appears
       - Click new task
    4. Test Human Resources Team:
       - Select Human Resources team
       - Enter RAI prompt
       - Validate 'Unable to create plan' message appears
       - Click new task
    5. Test RFP Team:
       - Select RFP team
       - Enter RAI prompt
       - Validate 'Unable to create plan' message appears
       - Click new task
    6. Test Contract Compliance Team:
       - Select Contract Compliance team
       - Enter RAI prompt
       - Validate 'Unable to create plan' message appears
    """
    page = login_logout
    biab_page = BIABPage(page)
    
    # Update test node ID for HTML report
    request.node._nodeid = "(MACAE V4) - Test RAI prompts for all 5 default teams"
    
    logger.info("=" * 80)
    logger.info("Starting RAI Validation Test - Unable to Create Plan")
    logger.info("=" * 80)
    
    start_time = time.time()
    
    try:
        # Reload home page before starting test
        biab_page.reload_home_page()
        
        # Step 1: Validate Home Page
        logger.info("\n" + "=" * 80)
        logger.info("STEP 1: Validating Home Page")
        logger.info("=" * 80)
        step1_start = time.time()
        biab_page.validate_home_page()
        step1_end = time.time()
        logger.info(f"Step 1 completed in {step1_end - step1_start:.2f} seconds")
        
        # Step 2: Test Retail Customer Success Team
        logger.info("\n" + "=" * 80)
        logger.info("STEP 2: Testing RAI Validation - Retail Customer Success Team")
        logger.info("=" * 80)
        step2_start = time.time()
        
        logger.info("Selecting Retail Customer Success Team...")
        biab_page.select_retail_customer_success_team()
        
        logger.info(f"Entering RAI prompt: {RAI_PROMPT}")
        biab_page.input_RAI_PROMPT_and_send(RAI_PROMPT)
        
        logger.info("Validating 'Unable to create plan' message is visible...")
        biab_page.validate_rai_error_message()
        
        logger.info("Clicking New Task...")
        biab_page.click_new_task()
        
        step2_end = time.time()
        logger.info(f"Step 2 (Retail Team RAI Validation) completed in {step2_end - step2_start:.2f} seconds")
        
        # Step 3: Test Product Marketing Team
        logger.info("\n" + "=" * 80)
        logger.info("STEP 3: Testing RAI Validation - Product Marketing Team")
        logger.info("=" * 80)
        step3_start = time.time()
        
        logger.info("Selecting Product Marketing Team...")
        biab_page.select_product_marketing_team()
        
        logger.info(f"Entering RAI prompt: {RAI_PROMPT}")
        biab_page.input_RAI_PROMPT_and_send(RAI_PROMPT)
        
        logger.info("Validating 'Unable to create plan' message is visible...")
        biab_page.validate_rai_error_message()
        
        logger.info("Clicking New Task...")
        biab_page.click_new_task()
        
        step3_end = time.time()
        logger.info(f"Step 3 (Product Marketing Team RAI Validation) completed in {step3_end - step3_start:.2f} seconds")
        
        # Step 4: Test Human Resources Team
        logger.info("\n" + "=" * 80)
        logger.info("STEP 4: Testing RAI Validation - Human Resources Team")
        logger.info("=" * 80)
        step4_start = time.time()
        
        logger.info("Selecting Human Resources Team...")
        biab_page.select_human_resources_team()
        
        logger.info(f"Entering RAI prompt: {RAI_PROMPT}")
        biab_page.input_RAI_PROMPT_and_send(RAI_PROMPT)
        
        logger.info("Validating 'Unable to create plan' message is visible...")
        biab_page.validate_rai_error_message()
        
        step4_end = time.time()
        logger.info(f"Step 4 (Human Resources Team RAI Validation) completed in {step4_end - step4_start:.2f} seconds")
        
        # Step 5: Test RFP Team
        logger.info("\n" + "=" * 80)
        logger.info("STEP 5: Testing RAI Validation - RFP Team")
        logger.info("=" * 80)
        step5_start = time.time()
        
        logger.info("Clicking New Task...")
        biab_page.click_new_task()
        
        logger.info("Selecting RFP Team...")
        biab_page.select_rfp_team()
        
        logger.info(f"Entering RAI prompt: {RAI_PROMPT}")
        biab_page.input_RAI_PROMPT_and_send(RAI_PROMPT)
        
        logger.info("Validating 'Unable to create plan' message is visible...")
        biab_page.validate_rai_error_message()
        
        step5_end = time.time()
        logger.info(f"Step 5 (RFP Team RAI Validation) completed in {step5_end - step5_start:.2f} seconds")
        
        # Step 6: Test Contract Compliance Team
        logger.info("\n" + "=" * 80)
        logger.info("STEP 6: Testing RAI Validation - Contract Compliance Team")
        logger.info("=" * 80)
        step6_start = time.time()
        
        logger.info("Clicking New Task...")
        biab_page.click_new_task()
        
        logger.info("Selecting Contract Compliance Team...")
        biab_page.select_contract_compliance_team()
        
        logger.info(f"Entering RAI prompt: {RAI_PROMPT}")
        biab_page.input_RAI_PROMPT_and_send(RAI_PROMPT)
        
        logger.info("Validating 'Unable to create plan' message is visible...")
        biab_page.validate_rai_error_message()
        
        step6_end = time.time()
        logger.info(f"Step 6 (Contract Compliance Team RAI Validation) completed in {step6_end - step6_start:.2f} seconds")
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        logger.info("\n" + "=" * 80)
        logger.info("TEST EXECUTION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Step 1 (Home Page Validation): {step1_end - step1_start:.2f}s")
        logger.info(f"Step 2 (Retail Team RAI Validation): {step2_end - step2_start:.2f}s")
        logger.info(f"Step 3 (Product Marketing Team RAI Validation): {step3_end - step3_start:.2f}s")
        logger.info(f"Step 4 (Human Resources Team RAI Validation): {step4_end - step4_start:.2f}s")
        logger.info(f"Step 5 (RFP Team RAI Validation): {step5_end - step5_start:.2f}s")
        logger.info(f"Step 6 (Contract Compliance Team RAI Validation): {step6_end - step6_start:.2f}s")
        logger.info(f"Total Execution Time: {total_duration:.2f}s")
        logger.info("=" * 80)
        logger.info("✓ RAI Validation Test PASSED - All 5 teams correctly blocked harmful prompts")
        logger.info("=" * 80)
        
        # Attach execution time to pytest report
        request.node._report_sections.append(
            ("call", "log", f"Total execution time: {total_duration:.2f}s")
        )
        
    except Exception as e:
        end_time = time.time()
        total_duration = end_time - start_time
        logger.error("\n" + "=" * 80)
        logger.error("TEST EXECUTION FAILED")
        logger.error("=" * 80)
        logger.error(f"Error: {str(e)}")
        logger.error(f"Execution time before failure: {total_duration:.2f}s")
        logger.error("=" * 80)
        raise


def test_rai_validation_in_clarification(login_logout, request):
    """
    Validate RAI (Responsible AI) validation for 'Unable to create plan' message in clarification input.
    
    Steps:
    1. Validate home page elements are visible
    2. Select Human Resources team
    3. Input prompt and send
    4. Validate all HR agents are displayed
    5. Approve the task plan
    6. Send RAI prompt in clarification input
    7. Validate 'Unable to create plan' error message appears
    """
    page = login_logout
    biab_page = BIABPage(page)
    
    # Update test node ID for HTML report
    request.node._nodeid = "(MACAE V3)  - Test RAI prompt in user clarification step"
    
    logger.info("=" * 80)
    logger.info("Starting RAI Validation Test in Clarification Input")
    logger.info("=" * 80)
    
    start_time = time.time()
    
    try:
        # Reload home page before starting test
        biab_page.reload_home_page()
        
        # Step 1: Validate Home Page
        logger.info("\n" + "=" * 80)
        logger.info("STEP 1: Validating Home Page")
        logger.info("=" * 80)
        step1_start = time.time()
        biab_page.validate_home_page()
        step1_end = time.time()
        logger.info(f"Step 1 completed in {step1_end - step1_start:.2f} seconds")
        
        # Step 2: Select Human Resources Team
        logger.info("\n" + "=" * 80)
        logger.info("STEP 2: Selecting Human Resources Team")
        logger.info("=" * 80)
        step2_start = time.time()
        biab_page.select_human_resources_team()
        step2_end = time.time()
        logger.info(f"Step 2 completed in {step2_end - step2_start:.2f} seconds")
        
        # Step 3: Select Quick Task and Create Plan (HR)
        logger.info("\n" + "=" * 80)
        logger.info("STEP 3: Selecting Quick Task and Creating Plan (HR)")
        logger.info("=" * 80)
        step3_start = time.time()
        biab_page.select_quick_task_and_create_plan()
        step3_end = time.time()
        logger.info(f"Step 3 completed in {step3_end - step3_start:.2f} seconds")
        
        # Step 4: Validate All HR Agents Visible
        logger.info("\n" + "=" * 80)
        logger.info("STEP 4: Validating All HR Agents Are Displayed")
        logger.info("=" * 80)
        step4_start = time.time()
        biab_page.validate_hr_agents()
        step4_end = time.time()
        logger.info(f"Step 4 completed in {step4_end - step4_start:.2f} seconds")
        
        # Step 5: Approve Task Plan
        logger.info("\n" + "=" * 80)
        logger.info("STEP 5: Approving HR Task Plan")
        logger.info("=" * 80)
        step5_start = time.time()
        biab_page.approve_task_plan()
        step5_end = time.time()
        logger.info(f"Step 5 completed in {step5_end - step5_start:.2f} seconds")
        
        # Step 6: Send RAI Prompt in Clarification Input
        logger.info("\n" + "=" * 80)
        logger.info("STEP 6: Sending RAI Prompt in Clarification Input")
        logger.info("=" * 80)
        step6_start = time.time()
        
        logger.info(f"Entering RAI prompt in clarification: {RAI_PROMPT}")
        logger.info("Typing RAI prompt in clarification input...")
        page.locator(biab_page.INPUT_CLARIFICATION).fill(RAI_PROMPT)
        page.wait_for_timeout(1000)
        logger.info("✓ RAI prompt entered in clarification input")
        
        logger.info("Clicking Send button for clarification...")
        page.locator(biab_page.SEND_BUTTON_CLARIFICATION).click()
        page.wait_for_timeout(1000)
        logger.info("✓ Clarification send button clicked")
        
        step6_end = time.time()
        logger.info(f"Step 6 completed in {step6_end - step6_start:.2f} seconds")
        
        # Step 7: Validate RAI Error Message
        logger.info("\n" + "=" * 80)
        logger.info("STEP 7: Validating 'Unable to create plan' Error Message")
        logger.info("=" * 80)
        step7_start = time.time()
        biab_page.validate_rai_clarification_error_message()
        step7_end = time.time()
        logger.info(f"Step 7 completed in {step7_end - step7_start:.2f} seconds")
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        logger.info("\n" + "=" * 80)
        logger.info("TEST EXECUTION SUMMARY - RAI CLARIFICATION INPUT TEST")
        logger.info("=" * 80)
        logger.info(f"✓ Test completed successfully for Human Resources team")
        logger.info(f"Total test execution time: {total_duration:.2f} seconds")
        logger.info("=" * 80)
        
    except Exception as e:
        end_time = time.time()
        total_duration = end_time - start_time
        logger.error("\n" + "=" * 80)
        logger.error("TEST EXECUTION FAILED - RAI CLARIFICATION INPUT TEST")
        logger.error("=" * 80)
        logger.error(f"✗ Error occurred: {str(e)}")
        logger.error(f"Total time before failure: {total_duration:.2f} seconds")
        logger.error("=" * 80)
        raise


def test_cancel_button_all_teams(login_logout, request):
    """
    Validate cancel button functionality across all 5 teams.
    
    Steps:
    1. Validate home page elements are visible
    2. Test Retail Customer Success Team:
       - Select Retail Customer Success team
       - Select quick task and create plan
       - Click Cancel button
       - Validate home page
    3. Test Product Marketing Team:
       - Select Product Marketing team
       - Select quick task and create plan
       - Click Cancel button
       - Validate home page
    4. Test Human Resources Team:
       - Select Human Resources team
       - Input custom prompt
       - Click Cancel button
       - Validate home page
    5. Test RFP Team:
       - Select RFP team
       - Select quick task and create plan
       - Click Cancel button
       - Validate home page
    6. Test Contract Compliance Team:
       - Select Contract Compliance team
       - Select quick task and create plan
       - Click Cancel button
       - Validate home page
    """
    page = login_logout
    biab_page = BIABPage(page)
    
    # Update test node ID for HTML report
    request.node._nodeid = "(MACAE V4) - Test Cancel functionality in the Plan Approval step for all 5 teams"
    
    logger.info("=" * 80)
    logger.info("Starting Cancel Button Validation Test - All Teams")
    logger.info("=" * 80)
    
    start_time = time.time()
    
    try:
        # Reload home page before starting test
        biab_page.reload_home_page()
        
        # Step 1: Validate Home Page
        logger.info("\n" + "=" * 80)
        logger.info("STEP 1: Validating Home Page")
        logger.info("=" * 80)
        step1_start = time.time()
        biab_page.validate_home_page()
        step1_end = time.time()
        logger.info(f"Step 1 completed in {step1_end - step1_start:.2f} seconds")
        
        # Step 2: Test Retail Customer Success Team
        logger.info("\n" + "=" * 80)
        logger.info("STEP 2: Testing Cancel Button - Retail Customer Success Team")
        logger.info("=" * 80)
        step2_start = time.time()
        
        logger.info("Selecting Retail Customer Success Team...")
        biab_page.select_retail_customer_success_team()
        
        logger.info("Selecting Quick Task and Creating Plan...")
        biab_page.select_quick_task_and_create_plan()
        
        logger.info("Clicking Cancel button...")
        biab_page.click_cancel_button()
        
        logger.info("Validating Home Page after cancel...")
        biab_page.validate_home_page()
        
        step2_end = time.time()
        logger.info(f"Step 2 (Retail Team Cancel) completed in {step2_end - step2_start:.2f} seconds")
        
        # Step 3: Test Product Marketing Team
        logger.info("\n" + "=" * 80)
        logger.info("STEP 3: Testing Cancel Button - Product Marketing Team")
        logger.info("=" * 80)
        step3_start = time.time()
        
        logger.info("Selecting Product Marketing Team...")
        biab_page.select_product_marketing_team()
        
        logger.info("Selecting Quick Task and Creating Plan...")
        biab_page.select_quick_task_and_create_plan()
        
        logger.info("Clicking Cancel button...")
        biab_page.click_cancel_button()
        
        logger.info("Validating Home Page after cancel...")
        biab_page.validate_home_page()
        
        step3_end = time.time()
        logger.info(f"Step 3 (Product Marketing Team Cancel) completed in {step3_end - step3_start:.2f} seconds")
        
        # Step 4: Test Human Resources Team
        logger.info("\n" + "=" * 80)
        logger.info("STEP 4: Testing Cancel Button - Human Resources Team")
        logger.info("=" * 80)
        step4_start = time.time()
        
        logger.info("Selecting Human Resources Team...")
        biab_page.select_human_resources_team()
        
        logger.info("Inputting Custom Prompt...")
        biab_page.input_prompt_and_send(PROMPT_QUESTION1)
        
        logger.info("Clicking Cancel button...")
        biab_page.click_cancel_button()
        
        logger.info("Validating Home Page after cancel...")
        biab_page.validate_home_page()
        
        step4_end = time.time()
        logger.info(f"Step 4 (Human Resources Team Cancel) completed in {step4_end - step4_start:.2f} seconds")
        
        # Step 5: Test RFP Team
        logger.info("\n" + "=" * 80)
        logger.info("STEP 5: Testing Cancel Button - RFP Team")
        logger.info("=" * 80)
        step5_start = time.time()
        
        logger.info("Selecting RFP Team...")
        biab_page.select_rfp_team()
        
        logger.info("Selecting Quick Task and Creating Plan...")
        biab_page.select_quick_task_and_create_plan()
        
        logger.info("Clicking Cancel button...")
        biab_page.click_cancel_button()
        
        logger.info("Validating Home Page after cancel...")
        biab_page.validate_home_page()
        
        step5_end = time.time()
        logger.info(f"Step 5 (RFP Team Cancel) completed in {step5_end - step5_start:.2f} seconds")
        
        # Step 6: Test Contract Compliance Team
        logger.info("\n" + "=" * 80)
        logger.info("STEP 6: Testing Cancel Button - Contract Compliance Team")
        logger.info("=" * 80)
        step6_start = time.time()
        
        logger.info("Selecting Contract Compliance Team...")
        biab_page.select_contract_compliance_team()
        
        logger.info("Selecting Quick Task and Creating Plan...")
        biab_page.select_quick_task_and_create_plan()
        
        logger.info("Clicking Cancel button...")
        biab_page.click_cancel_button()
        
        logger.info("Validating Home Page after cancel...")
        biab_page.validate_home_page()
        
        step6_end = time.time()
        logger.info(f"Step 6 (Contract Compliance Team Cancel) completed in {step6_end - step6_start:.2f} seconds")
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        logger.info("\n" + "=" * 80)
        logger.info("TEST EXECUTION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Step 1 (Home Page Validation): {step1_end - step1_start:.2f}s")
        logger.info(f"Step 2 (Retail Team Cancel): {step2_end - step2_start:.2f}s")
        logger.info(f"Step 3 (Product Marketing Team Cancel): {step3_end - step3_start:.2f}s")
        logger.info(f"Step 4 (Human Resources Team Cancel): {step4_end - step4_start:.2f}s")
        logger.info(f"Step 5 (RFP Team Cancel): {step5_end - step5_start:.2f}s")
        logger.info(f"Step 6 (Contract Compliance Team Cancel): {step6_end - step6_start:.2f}s")
        logger.info(f"Total Execution Time: {total_duration:.2f}s")
        logger.info("=" * 80)
        logger.info("✓ Cancel Button Test PASSED - All 5 teams successfully returned to home page")
        logger.info("=" * 80)
        
        # Attach execution time to pytest report
        request.node._report_sections.append(
            ("call", "log", f"Total execution time: {total_duration:.2f}s")
        )
        
    except Exception as e:
        end_time = time.time()
        total_duration = end_time - start_time
        logger.error("\n" + "=" * 80)
        logger.error("TEST EXECUTION FAILED")
        logger.error("=" * 80)
        logger.error(f"Error: {str(e)}")
        logger.error(f"Execution time before failure: {total_duration:.2f}s")
        logger.error("=" * 80)
        raise


@pytest.mark.cancel
def test_cancel_functionality_all_teams(login_logout, request):
    """
    Test Case ID 29007: Test Cancel functionality in the Plan Approval step.
    
    Tests the cancel button across all 5 teams:
    - Human Resources Team
    - Product Marketing Team
    - Retail Customer Success Team
    - RFP Team
    - Contract Compliance Review Team
    """
    page = login_logout
    biab_page = BIABPage(page)
    
    request.node._nodeid = "(MACAE V4) Test Cancel functionality in the Plan Approval step"
    
    logger.info("=" * 80)
    logger.info("Starting Cancel Functionality Test for All Teams")
    logger.info("=" * 80)
    
    start_time = time.time()
    
    try:
        # Reload home page before starting test
        biab_page.reload_home_page()
        
        # Step 1-2: Validate Home Page
        logger.info("\n" + "=" * 80)
        logger.info("STEP 1-2: Validating Home Page and Authentication")
        logger.info("=" * 80)
        step1_start = time.time()
        biab_page.validate_home_page()
        step1_end = time.time()
        logger.info(f"Steps 1-2 completed in {step1_end - step1_start:.2f} seconds")
        
        # Step 3-5: Test Cancel - Human Resources Team
        logger.info("\n" + "=" * 80)
        logger.info("STEPS 3-5: Testing Cancel Button - Human Resources Team")
        logger.info("=" * 80)
        step2_start = time.time()
        
        logger.info("Selecting Human Resources Team...")
        biab_page.select_human_resources_team()
        
        logger.info("Selecting Quick Task and Creating Plan...")
        biab_page.select_quick_task_and_create_plan()
        
        logger.info("Clicking Cancel button...")
        biab_page.click_cancel_button()
        
        logger.info("Validating redirect to Home Screen...")
        biab_page.validate_home_input_visible()
        
        step2_end = time.time()
        logger.info(f"Steps 3-5 (HR Team Cancel) completed in {step2_end - step2_start:.2f} seconds")
        
        # Step 6-8: Test Cancel - Product Marketing Team
        logger.info("\n" + "=" * 80)
        logger.info("STEPS 6-8: Testing Cancel Button - Product Marketing Team")
        logger.info("=" * 80)
        step3_start = time.time()
        
        logger.info("Selecting Product Marketing Team...")
        biab_page.select_product_marketing_team()
        
        logger.info("Selecting Quick Task and Creating Plan...")
        biab_page.select_quick_task_and_create_plan()
        
        logger.info("Clicking Cancel button...")
        biab_page.click_cancel_button()
        
        logger.info("Validating redirect to Home Screen...")
        biab_page.validate_home_input_visible()
        
        step3_end = time.time()
        logger.info(f"Steps 6-8 (Product Marketing Cancel) completed in {step3_end - step3_start:.2f} seconds")
        
        # Step 9-11: Test Cancel - Retail Customer Success Team
        logger.info("\n" + "=" * 80)
        logger.info("STEPS 9-11: Testing Cancel Button - Retail Customer Success Team")
        logger.info("=" * 80)
        step4_start = time.time()
        
        logger.info("Selecting Retail Customer Success Team...")
        biab_page.select_retail_customer_success_team()
        
        logger.info("Selecting Quick Task and Creating Plan...")
        biab_page.select_quick_task_and_create_plan()
        
        logger.info("Clicking Cancel button...")
        biab_page.click_cancel_button()
        
        logger.info("Validating redirect to Home Screen...")
        biab_page.validate_home_input_visible()
        
        step4_end = time.time()
        logger.info(f"Steps 9-11 (Retail Team Cancel) completed in {step4_end - step4_start:.2f} seconds")
        
        # Step 12-14: Test Cancel - RFP Team
        logger.info("\n" + "=" * 80)
        logger.info("STEPS 12-14: Testing Cancel Button - RFP Team")
        logger.info("=" * 80)
        step5_start = time.time()
        
        logger.info("Selecting RFP Team...")
        biab_page.select_rfp_team()
        
        logger.info("Selecting Quick Task and Creating Plan...")
        biab_page.select_quick_task_and_create_plan()
        
        logger.info("Clicking Cancel button...")
        biab_page.click_cancel_button()
        
        logger.info("Validating redirect to Home Screen...")
        biab_page.validate_home_input_visible()
        
        step5_end = time.time()
        logger.info(f"Steps 12-14 (RFP Team Cancel) completed in {step5_end - step5_start:.2f} seconds")
        
        # Step 15-17: Test Cancel - Contract Compliance Review Team
        logger.info("\n" + "=" * 80)
        logger.info("STEPS 15-17: Testing Cancel Button - Contract Compliance Review Team")
        logger.info("=" * 80)
        step6_start = time.time()
        
        logger.info("Selecting Contract Compliance Review Team...")
        biab_page.select_contract_compliance_team()
        
        logger.info("Selecting Quick Task and Creating Plan...")
        biab_page.select_quick_task_and_create_plan()
        
        logger.info("Clicking Cancel button...")
        biab_page.click_cancel_button()
        
        logger.info("Validating redirect to Home Screen...")
        biab_page.validate_home_input_visible()
        
        step6_end = time.time()
        logger.info(f"Steps 15-17 (Contract Compliance Cancel) completed in {step6_end - step6_start:.2f} seconds")
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        logger.info("\n" + "=" * 80)
        logger.info("TEST EXECUTION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Steps 1-2 (Home Page Validation): {step1_end - step1_start:.2f}s")
        logger.info(f"Steps 3-5 (HR Team Cancel): {step2_end - step2_start:.2f}s")
        logger.info(f"Steps 6-8 (Product Marketing Cancel): {step3_end - step3_start:.2f}s")
        logger.info(f"Steps 9-11 (Retail Team Cancel): {step4_end - step4_start:.2f}s")
        logger.info(f"Steps 12-14 (RFP Team Cancel): {step5_end - step5_start:.2f}s")
        logger.info(f"Steps 15-17 (Contract Compliance Cancel): {step6_end - step6_start:.2f}s")
        logger.info(f"Total Execution Time: {total_duration:.2f}s")
        logger.info("=" * 80)
        logger.info("✓ Cancel Functionality Test PASSED")
        logger.info("=" * 80)
        
    except Exception as e:
        end_time = time.time()
        total_duration = end_time - start_time
        logger.error("\n" + "=" * 80)
        logger.error("TEST EXECUTION FAILED")
        logger.error("=" * 80)
        logger.error(f"Error: {str(e)}")
        logger.error(f"Execution time before failure: {total_duration:.2f}s")
        logger.error("=" * 80)
        raise


@pytest.mark.rai
def test_rai_prompt_in_clarification(login_logout, request):
    """
    Test Case ID 29009: Test RAI prompt in user clarification step.
    
    Validates that harmful/RAI prompts are blocked during the clarification step.
    """
    page = login_logout
    biab_page = BIABPage(page)
    
    request.node._nodeid = "(MACAE V4) Test RAI prompt in user clarification step"
    
    logger.info("=" * 80)
    logger.info("Starting RAI Prompt in Clarification Test")
    logger.info("=" * 80)
    
    start_time = time.time()
    
    try:
        # Reload home page
        biab_page.reload_home_page()
        
        # Steps 1-2: Validate Home Page
        logger.info("\n" + "=" * 80)
        logger.info("STEPS 1-2: Validating Home Page and Authentication")
        logger.info("=" * 80)
        step1_start = time.time()
        biab_page.validate_home_page()
        step1_end = time.time()
        logger.info(f"Steps 1-2 completed in {step1_end - step1_start:.2f} seconds")
        
        # Step 3: Select HR Team
        logger.info("\n" + "=" * 80)
        logger.info("STEP 3: Selecting Human Resources Team")
        logger.info("=" * 80)
        step2_start = time.time()
        biab_page.select_human_resources_team()
        step2_end = time.time()
        logger.info(f"Step 3 completed in {step2_end - step2_start:.2f} seconds")
        
        # Step 4: Select Quick Task
        logger.info("\n" + "=" * 80)
        logger.info("STEP 4: Selecting Quick Task and Creating Plan")
        logger.info("=" * 80)
        step3_start = time.time()
        biab_page.select_quick_task_and_create_plan()
        step3_end = time.time()
        logger.info(f"Step 4 completed in {step3_end - step3_start:.2f} seconds")
        
        # Step 5: Approve Task Plan
        logger.info("\n" + "=" * 80)
        logger.info("STEP 5: Approving Task Plan")
        logger.info("=" * 80)
        step4_start = time.time()
        biab_page.approve_task_plan()
        step4_end = time.time()
        logger.info(f"Step 5 completed in {step4_end - step4_start:.2f} seconds")
        
        # Step 6: Input RAI prompt in clarification
        logger.info("\n" + "=" * 80)
        logger.info("STEP 6: Inputting RAI Prompt in Clarification")
        logger.info("=" * 80)
        step5_start = time.time()
        
        logger.info(f"Entering RAI prompt: {RAI_PROMPT}")
        biab_page.input_rai_clarification_and_send(RAI_PROMPT)
        
        logger.info("Validating RAI error message...")
        biab_page.validate_rai_clarification_error_message()
        
        step5_end = time.time()
        logger.info(f"Step 6 completed in {step5_end - step5_start:.2f} seconds")
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        logger.info("\n" + "=" * 80)
        logger.info("TEST EXECUTION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Steps 1-2 (Home Page Validation): {step1_end - step1_start:.2f}s")
        logger.info(f"Step 3 (HR Team Selection): {step2_end - step2_start:.2f}s")
        logger.info(f"Step 4 (Quick Task Selection): {step3_end - step3_start:.2f}s")
        logger.info(f"Step 5 (Approve Task Plan): {step4_end - step4_start:.2f}s")
        logger.info(f"Step 6 (RAI Prompt in Clarification): {step5_end - step5_start:.2f}s")
        logger.info(f"Total Execution Time: {total_duration:.2f}s")
        logger.info("=" * 80)
        logger.info("✓ RAI Prompt in Clarification Test PASSED")
        logger.info("=" * 80)
        
    except Exception as e:
        end_time = time.time()
        total_duration = end_time - start_time
        logger.error("\n" + "=" * 80)
        logger.error("TEST EXECUTION FAILED")
        logger.error("=" * 80)
        logger.error(f"Error: {str(e)}")
        logger.error(f"Execution time before failure: {total_duration:.2f}s")
        logger.error("=" * 80)
        raise


@pytest.mark.rai
def test_rai_prompts_all_teams(login_logout, request):
    """
    Test Case ID 29011: Test RAI prompts for all 5 default teams.
    
    Validates that RAI prompts are blocked at initial task input for all teams.
    """
    page = login_logout
    biab_page = BIABPage(page)
    
    request.node._nodeid = "(MACAE V4) Test RAI prompts for all 5 default teams"
    
    logger.info("=" * 80)
    logger.info("Starting RAI Prompts for All Teams Test")
    logger.info("=" * 80)
    
    start_time = time.time()
    
    try:
        # Reload home page
        biab_page.reload_home_page()
        
        # Steps 1-2: Validate Home Page
        logger.info("\n" + "=" * 80)
        logger.info("STEPS 1-2: Validating Home Page and Authentication")
        logger.info("=" * 80)
        step1_start = time.time()
        biab_page.validate_home_page()
        step1_end = time.time()
        logger.info(f"Steps 1-2 completed in {step1_end - step1_start:.2f} seconds")
        
        # Steps 3-4: Test RAI - Human Resources Team
        logger.info("\n" + "=" * 80)
        logger.info("STEPS 3-4: Testing RAI Prompt - Human Resources Team")
        logger.info("=" * 80)
        step2_start = time.time()
        
        biab_page.select_human_resources_team()
        biab_page.input_RAI_PROMPT_and_send(RAI_PROMPT)
        biab_page.validate_rai_error_message()
        
        step2_end = time.time()
        logger.info(f"Steps 3-4 (HR Team RAI) completed in {step2_end - step2_start:.2f} seconds")
        
        # Steps 5-6: Test RAI - Product Marketing Team
        logger.info("\n" + "=" * 80)
        logger.info("STEPS 5-6: Testing RAI Prompt - Product Marketing Team")
        logger.info("=" * 80)
        step3_start = time.time()
        
        biab_page.select_product_marketing_team()
        biab_page.input_RAI_PROMPT_and_send(RAI_PROMPT)
        biab_page.validate_rai_error_message()
        
        step3_end = time.time()
        logger.info(f"Steps 5-6 (Product Marketing RAI) completed in {step3_end - step3_start:.2f} seconds")
        
        # Steps 7-8: Test RAI - Retail Customer Success Team
        logger.info("\n" + "=" * 80)
        logger.info("STEPS 7-8: Testing RAI Prompt - Retail Customer Success Team")
        logger.info("=" * 80)
        step4_start = time.time()
        
        biab_page.select_retail_customer_success_team()
        biab_page.input_RAI_PROMPT_and_send(RAI_PROMPT)
        biab_page.validate_rai_error_message()
        
        step4_end = time.time()
        logger.info(f"Steps 7-8 (Retail Team RAI) completed in {step4_end - step4_start:.2f} seconds")
        
        # Steps 9-10: Test RAI - RFP Team
        logger.info("\n" + "=" * 80)
        logger.info("STEPS 9-10: Testing RAI Prompt - RFP Team")
        logger.info("=" * 80)
        step5_start = time.time()
        
        biab_page.select_rfp_team()
        biab_page.input_RAI_PROMPT_and_send(RAI_PROMPT)
        biab_page.validate_rai_error_message()
        
        step5_end = time.time()
        logger.info(f"Steps 9-10 (RFP Team RAI) completed in {step5_end - step5_start:.2f} seconds")
        
        # Steps 11-12: Test RAI - Contract Compliance Review Team
        logger.info("\n" + "=" * 80)
        logger.info("STEPS 11-12: Testing RAI Prompt - Contract Compliance Review Team")
        logger.info("=" * 80)
        step6_start = time.time()
        
        biab_page.select_contract_compliance_team()
        biab_page.input_RAI_PROMPT_and_send(RAI_PROMPT)
        biab_page.validate_rai_error_message()
        
        step6_end = time.time()
        logger.info(f"Steps 11-12 (Contract Compliance RAI) completed in {step6_end - step6_start:.2f} seconds")
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        logger.info("\n" + "=" * 80)
        logger.info("TEST EXECUTION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Steps 1-2 (Home Page Validation): {step1_end - step1_start:.2f}s")
        logger.info(f"Steps 3-4 (HR Team RAI): {step2_end - step2_start:.2f}s")
        logger.info(f"Steps 5-6 (Product Marketing RAI): {step3_end - step3_start:.2f}s")
        logger.info(f"Steps 7-8 (Retail Team RAI): {step4_end - step4_start:.2f}s")
        logger.info(f"Steps 9-10 (RFP Team RAI): {step5_end - step5_start:.2f}s")
        logger.info(f"Steps 11-12 (Contract Compliance RAI): {step6_end - step6_start:.2f}s")
        logger.info(f"Total Execution Time: {total_duration:.2f}s")
        logger.info("=" * 80)
        logger.info("✓ RAI Prompts for All Teams Test PASSED")
        logger.info("=" * 80)
        
    except Exception as e:
        end_time = time.time()
        total_duration = end_time - start_time
        logger.error("\n" + "=" * 80)
        logger.error("TEST EXECUTION FAILED")
        logger.error("=" * 80)
        logger.error(f"Error: {str(e)}")
        logger.error(f"Execution time before failure: {total_duration:.2f}s")
        logger.error("=" * 80)
        raise


@pytest.mark.input_validation
def test_chat_input_validation(login_logout, request):
    """
    Test Case ID 29014: Validate chat input handling for Empty/only-spaces and Excessively long queries.
    
    Tests edge cases for chat input validation.
    """
    page = login_logout
    biab_page = BIABPage(page)
    
    request.node._nodeid = "(MACAE V4) Validate chat input handling"
    
    logger.info("=" * 80)
    logger.info("Starting Chat Input Validation Test")
    logger.info("=" * 80)
    
    start_time = time.time()
    
    try:
        # Step 1: Go to application URL
        logger.info("\n" + "=" * 80)
        logger.info("STEP 1: Opening Application URL")
        logger.info("=" * 80)
        step1_start = time.time()
        biab_page.reload_home_page()
        step1_end = time.time()
        logger.info(f"Step 1 completed in {step1_end - step1_start:.2f} seconds")
        
        # Step 2: Select HR Team
        logger.info("\n" + "=" * 80)
        logger.info("STEP 2: Selecting Human Resources Team")
        logger.info("=" * 80)
        step2_start = time.time()
        biab_page.select_human_resources_team()
        step2_end = time.time()
        logger.info(f"Step 2 completed in {step2_end - step2_start:.2f} seconds")
        
        # Step 3: Test empty input
        logger.info("\n" + "=" * 80)
        logger.info("STEP 3: Testing Empty Input")
        logger.info("=" * 80)
        step3_start = time.time()
        
        biab_page.input_text_only("")
        biab_page.validate_send_button_disabled()
        
        step3_end = time.time()
        logger.info(f"Step 3 completed in {step3_end - step3_start:.2f} seconds")
        
        # Step 4: Test spaces-only input
        logger.info("\n" + "=" * 80)
        logger.info("STEP 4: Testing Spaces-Only Input")
        logger.info("=" * 80)
        step4_start = time.time()
        
        biab_page.input_text_only("     ")
        biab_page.validate_send_button_disabled()
        
        step4_end = time.time()
        logger.info(f"Step 4 completed in {step4_end - step4_start:.2f} seconds")
        
        # Step 5: Test excessively long query
        logger.info("\n" + "=" * 80)
        logger.info("STEP 5: Testing Excessively Long Query")
        logger.info("=" * 80)
        step5_start = time.time()
        
        # Create a long query (>5000 characters)
        long_query = "a" * 5001
        biab_page.input_RAI_PROMPT_and_send(long_query)
        biab_page.validate_rai_error_message()
        
        step5_end = time.time()
        logger.info(f"Step 5 completed in {step5_end - step5_start:.2f} seconds")
        
        # Step 6: Test valid short query
        logger.info("\n" + "=" * 80)
        logger.info("STEP 6: Testing Valid Short Query")
        logger.info("=" * 80)
        step6_start = time.time()
        
        biab_page.input_prompt_and_send(PROMPT_QUESTION1)
        logger.info("✓ Valid query processed successfully")
        
        step6_end = time.time()
        logger.info(f"Step 6 completed in {step6_end - step6_start:.2f} seconds")
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        logger.info("\n" + "=" * 80)
        logger.info("TEST EXECUTION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Step 1 (Open Application): {step1_end - step1_start:.2f}s")
        logger.info(f"Step 2 (Select HR Team): {step2_end - step2_start:.2f}s")
        logger.info(f"Step 3 (Empty Input Test): {step3_end - step3_start:.2f}s")
        logger.info(f"Step 4 (Spaces-Only Test): {step4_end - step4_start:.2f}s")
        logger.info(f"Step 5 (Long Query Test): {step5_end - step5_start:.2f}s")
        logger.info(f"Step 6 (Valid Query Test): {step6_end - step6_start:.2f}s")
        logger.info(f"Total Execution Time: {total_duration:.2f}s")
        logger.info("=" * 80)
        logger.info("✓ Chat Input Validation Test PASSED")
        logger.info("=" * 80)
        
    except Exception as e:
        end_time = time.time()
        total_duration = end_time - start_time
        logger.error("\n" + "=" * 80)
        logger.error("TEST EXECUTION FAILED")
        logger.error("=" * 80)
        logger.error(f"Error: {str(e)}")
        logger.error(f"Execution time before failure: {total_duration:.2f}s")
        logger.error("=" * 80)
        raise


@pytest.mark.duplicate_teams
def test_duplicate_team_entries(login_logout, request):
    """
    Test Case ID 29016: Validate Duplicated Team Entries in Team Selection List.
    
    Validates that no duplicate team entries appear in the team selection list.
    """
    page = login_logout
    biab_page = BIABPage(page)
    
    request.node._nodeid = "(MACAE V4) Validate Duplicated Team Entries"
    
    logger.info("=" * 80)
    logger.info("Starting Duplicate Team Entries Test")
    logger.info("=" * 80)
    
    start_time = time.time()
    
    try:
        # Step 1: Open application
        logger.info("\n" + "=" * 80)
        logger.info("STEP 1: Opening Application")
        logger.info("=" * 80)
        step1_start = time.time()
        biab_page.reload_home_page()
        step1_end = time.time()
        logger.info(f"Step 1 completed in {step1_end - step1_start:.2f} seconds")
        
        # Step 2-5: Validate unique team entries
        logger.info("\n" + "=" * 80)
        logger.info("STEPS 2-5: Validating Unique Team Entries")
        logger.info("=" * 80)
        step2_start = time.time()
        
        # Open team selection
        biab_page.open_team_selection()
        
        # Check for duplicate teams
        teams_to_check = [
            "Product Marketing Team",
            "Human Resources Team",
            "Retail Customer Success Team",
            "RFP Team",
            "Contract Compliance Review Team"
        ]
        
        duplicate_found = False
        for team in teams_to_check:
            count = biab_page.get_team_list_count(team)
            if count > 1:
                logger.error(f"❌ Duplicate entries found for '{team}': {count} entries")
                duplicate_found = True
            else:
                logger.info(f"✓ '{team}' has unique entry: {count} entry")
        
        if duplicate_found:
            raise AssertionError("Duplicate team entries found in team selection list")
        
        step2_end = time.time()
        logger.info(f"Steps 2-5 completed in {step2_end - step2_start:.2f} seconds")
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        logger.info("\n" + "=" * 80)
        logger.info("TEST EXECUTION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Step 1 (Open Application): {step1_end - step1_start:.2f}s")
        logger.info(f"Steps 2-5 (Validate Unique Teams): {step2_end - step2_start:.2f}s")
        logger.info(f"Total Execution Time: {total_duration:.2f}s")
        logger.info("=" * 80)
        logger.info("✓ Duplicate Team Entries Test PASSED - All teams are unique")
        logger.info("=" * 80)
        
    except Exception as e:
        end_time = time.time()
        total_duration = end_time - start_time
        logger.error("\n" + "=" * 80)
        logger.error("TEST EXECUTION FAILED")
        logger.error("=" * 80)
        logger.error(f"Error: {str(e)}")
        logger.error(f"Execution time before failure: {total_duration:.2f}s")
        logger.error("=" * 80)
        raise


@pytest.mark.cross_team
def test_cross_team_agent_validation(login_logout, request):
    """
    Test Case ID 29986: Multi-agent cross team error.
    
    Validates that agents don't mix between teams - ensures agents are specific to their teams.
    First completes full RFP workflow, then switches to HR and completes full HR workflow.
    
    Steps:
    1. Validate home page elements are visible
    2. Select RFP Team
    3. Select Quick Task and Create Plan (RFP)
    4. Validate All RFP Agents Visible
    5. Approve RFP Task Plan
    6. Validate RFP Response
    7. Click New Task
    8. Select Human Resources Team
    9. Select Quick Task and Create Plan (HR)
    10. Validate All HR Agents Visible
    11. Approve HR Task Plan
    12. Send Human Clarification with Employee Details
    13. Validate HR Response
    """
    page = login_logout
    biab_page = BIABPage(page)
    
    request.node._nodeid = "(MACAE V4) Multi-agent cross team error"
    
    logger.info("=" * 80)
    logger.info("Starting Cross Team Agent Validation Test")
    logger.info("=" * 80)
    
    start_time = time.time()
    
    try:
        # Step 1: Validate Home Page
        logger.info("\n" + "=" * 80)
        logger.info("STEP 1: Validating Home Page")
        logger.info("=" * 80)
        step1_start = time.time()
        biab_page.reload_home_page()
        biab_page.validate_home_page()
        step1_end = time.time()
        logger.info(f"Step 1 completed in {step1_end - step1_start:.2f} seconds")
        
        # Step 2: Select RFP Team
        logger.info("\n" + "=" * 80)
        logger.info("STEP 2: Selecting RFP Team")
        logger.info("=" * 80)
        step2_start = time.time()
        biab_page.select_rfp_team()
        step2_end = time.time()
        logger.info(f"Step 2 completed in {step2_end - step2_start:.2f} seconds")
        
        # Step 3: Select Quick Task and Create Plan (RFP)
        logger.info("\n" + "=" * 80)
        logger.info("STEP 3: Selecting Quick Task and Creating Plan (RFP)")
        logger.info("=" * 80)
        step3_start = time.time()
        biab_page.select_quick_task_and_create_plan()
        step3_end = time.time()
        logger.info(f"Step 3 completed in {step3_end - step3_start:.2f} seconds")
        
        # Step 4: Validate All RFP Agents Visible
        logger.info("\n" + "=" * 80)
        logger.info("STEP 4: Validating All RFP Agents Are Displayed")
        logger.info("=" * 80)
        step4_start = time.time()
        biab_page.validate_rfp_agents_visible()
        step4_end = time.time()
        logger.info(f"Step 4 completed in {step4_end - step4_start:.2f} seconds")
        
        # Step 5: Approve RFP Task Plan
        logger.info("\n" + "=" * 80)
        logger.info("STEP 5: Approving RFP Task Plan")
        logger.info("=" * 80)
        step5_start = time.time()
        biab_page.approve_rfp_task_plan()
        step5_end = time.time()
        logger.info(f"Step 5 completed in {step5_end - step5_start:.2f} seconds")
        
        # Step 6: Validate RFP Response
        logger.info("\n" + "=" * 80)
        logger.info("STEP 6: Validating RFP Response")
        logger.info("=" * 80)
        step6_start = time.time()
        biab_page.validate_rfp_response()
        step6_end = time.time()
        logger.info(f"Step 6 completed in {step6_end - step6_start:.2f} seconds")
        
        logger.info("✓ RFP Team workflow completed successfully")
        logger.info("=" * 80)
        
        # Step 7: Click New Task
        logger.info("\n" + "=" * 80)
        logger.info("STEP 7: Clicking New Task")
        logger.info("=" * 80)
        step7_start = time.time()
        biab_page.click_new_task()
        step7_end = time.time()
        logger.info(f"Step 7 completed in {step7_end - step7_start:.2f} seconds")
        
        # Step 8: Select Human Resources Team
        logger.info("\n" + "=" * 80)
        logger.info("STEP 8: Selecting Human Resources Team")
        logger.info("=" * 80)
        step8_start = time.time()
        biab_page.select_human_resources_team()
        step8_end = time.time()
        logger.info(f"Step 8 completed in {step8_end - step8_start:.2f} seconds")
        
        # Step 9: Select Quick Task and Create Plan (HR)
        logger.info("\n" + "=" * 80)
        logger.info("STEP 9: Selecting Quick Task and Creating Plan (HR)")
        logger.info("=" * 80)
        step9_start = time.time()
        biab_page.select_quick_task_and_create_plan()
        step9_end = time.time()
        logger.info(f"Step 9 completed in {step9_end - step9_start:.2f} seconds")
        
        # Step 10: Validate All HR Agents Visible
        logger.info("\n" + "=" * 80)
        logger.info("STEP 10: Validating All HR Agents Are Displayed")
        logger.info("=" * 80)
        step10_start = time.time()
        biab_page.validate_hr_agents()
        step10_end = time.time()
        logger.info(f"Step 10 completed in {step10_end - step10_start:.2f} seconds")
        logger.info("✓ HR-specific agents validated successfully")
        logger.info("✓ No cross-contamination from RFP team detected")
        
        # Step 11: Approve HR Task Plan
        logger.info("\n" + "=" * 80)
        logger.info("STEP 11: Approving HR Task Plan")
        logger.info("=" * 80)
        step11_start = time.time()
        biab_page.approve_task_plan()
        step11_end = time.time()
        logger.info(f"Step 11 completed in {step11_end - step11_start:.2f} seconds")
        
        # Step 12: Send Human Clarification with Employee Details
        logger.info("\n" + "=" * 80)
        logger.info("STEP 12: Sending Human Clarification with Employee Details")
        logger.info("=" * 80)
        step12_start = time.time()
        biab_page.input_clarification_and_send(HR_CLARIFICATION_TEXT)
        step12_end = time.time()
        logger.info(f"Step 12 completed in {step12_end - step12_start:.2f} seconds")
        
        # Step 13: Validate HR Response
        logger.info("\n" + "=" * 80)
        logger.info("STEP 13: Validating HR Response")
        logger.info("=" * 80)
        step13_start = time.time()
        biab_page.validate_hr_response()
        step13_end = time.time()
        logger.info(f"Step 13 completed in {step13_end - step13_start:.2f} seconds")
        
        logger.info("✓ HR Team workflow completed successfully")
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        logger.info("\n" + "=" * 80)
        logger.info("TEST EXECUTION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Step 1 (Home Page Validation): {step1_end - step1_start:.2f}s")
        logger.info(f"Step 2 (RFP Team Selection): {step2_end - step2_start:.2f}s")
        logger.info(f"Step 3 (RFP Quick Task & Plan): {step3_end - step3_start:.2f}s")
        logger.info(f"Step 4 (RFP Agents Validation): {step4_end - step4_start:.2f}s")
        logger.info(f"Step 5 (RFP Approve Task Plan): {step5_end - step5_start:.2f}s")
        logger.info(f"Step 6 (RFP Response Validation): {step6_end - step6_start:.2f}s")
        logger.info(f"Step 7 (Click New Task): {step7_end - step7_start:.2f}s")
        logger.info(f"Step 8 (HR Team Selection): {step8_end - step8_start:.2f}s")
        logger.info(f"Step 9 (HR Quick Task & Plan): {step9_end - step9_start:.2f}s")
        logger.info(f"Step 10 (HR Agents Validation): {step10_end - step10_start:.2f}s")
        logger.info(f"Step 11 (HR Approve Task Plan): {step11_end - step11_start:.2f}s")
        logger.info(f"Step 12 (HR Human Clarification): {step12_end - step12_start:.2f}s")
        logger.info(f"Step 13 (HR Response Validation): {step13_end - step13_start:.2f}s")
        logger.info(f"Total Execution Time: {total_duration:.2f}s")
        logger.info("=" * 80)
        logger.info("✓ Cross Team Agent Validation Test PASSED")
        logger.info("=" * 80)
        
    except Exception as e:
        end_time = time.time()
        total_duration = end_time - start_time
        logger.error("\n" + "=" * 80)
        logger.error("TEST EXECUTION FAILED")
        logger.error("=" * 80)
        logger.error(f"Error: {str(e)}")
        logger.error(f"Execution time before failure: {total_duration:.2f}s")
        logger.error("=" * 80)
        raise

