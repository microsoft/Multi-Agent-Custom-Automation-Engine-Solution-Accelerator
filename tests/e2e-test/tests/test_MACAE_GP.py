"""GP Test cases for MACAE."""

import logging
import time

import pytest

from pages.HomePage import BIABPage
from config.constants import hr_clarification_text, prompt_question1

logger = logging.getLogger(__name__)


def test_retail_customer_success_workflow(login_logout, request):
    """
    Validate Golden path for MACAE-v3.
    
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
    15. Input custom prompt "Onboard new employee"
    16. Validate all HR agents are displayed
    17. Approve the task plan
    18. Send human clarification with employee details
    19. Validate HR response
    """
    page = login_logout
    biab_page = BIABPage(page)
    
    # Update test node ID for HTML report
    request.node._nodeid = "Golden Path - MACAE-v3- test golden path works properly"
    
    logger.info("=" * 80)
    logger.info("Starting Multi-Team Workflow Test")
    logger.info("=" * 80)
    
    start_time = time.time()
    
    try:
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
            step5_retry_attempted = True
            
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
        
        # Step 15: Input Custom Prompt "Onboard new employee"
        logger.info("\n" + "=" * 80)
        logger.info("STEP 15: Inputting Custom Prompt - Onboard new employee")
        logger.info("=" * 80)
        step15_start = time.time()
        biab_page.input_prompt_and_send(prompt_question1)
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
        biab_page.input_clarification_and_send(hr_clarification_text)
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
        logger.info(f"Step 15 (HR Input Custom Prompt): {step15_end - step15_start:.2f}s")
        logger.info(f"Step 16 (HR Agents Validation): {step16_end - step16_start:.2f}s")
        logger.info(f"Step 17 (HR Approve Task Plan): {step17_end - step17_start:.2f}s")
        logger.info(f"Step 18 (HR Human Clarification): {step18_end - step18_start:.2f}s")
        logger.info(f"Step 19 (HR Response Validation): {step19_end - step19_start:.2f}s")
        logger.info(f"Total Execution Time: {total_duration:.2f}s")
        logger.info("=" * 80)
        logger.info("✓ Multi-Team Workflow Test PASSED")
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




