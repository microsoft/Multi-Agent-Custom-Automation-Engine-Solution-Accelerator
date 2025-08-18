"""
Employee onboarding and other scenarios and test cases for the Magentic orchestration system.
Provides realistic use cases to demonstrate multi-agent collaboration.
"""

class MagenticScenarios:
    """Collection of employee onboarding scenarios for testing and demonstration."""
    
    # Basic onboarding scenarios
    WELCOME_NEW_HIRE = """
    A new software engineer named Sarah is starting at our tech company next Monday. 
    Help create a comprehensive first-week onboarding plan that includes:
    - Welcome activities and team introductions
    - Required training modules and timeline
    - Equipment setup and access provisioning
    - Key company policies to review
    - First-week goals and expectations
    
    Research current best practices for remote software engineer onboarding in 2025.
    """
    
    ONBOARDING_METRICS_ANALYSIS = """
    Analyze our employee onboarding effectiveness using this sample data:
    - Average time to first meaningful contribution: 45 days
    - 90-day retention rate: 85%
    - Employee satisfaction score (1-10): 7.2
    - Training completion rate: 78%
    - Manager feedback score: 8.1
    
    Compare these metrics to industry benchmarks and recommend improvements.
    Create visualizations showing our performance vs. industry standards.
    """
    
    COMPLIANCE_RESEARCH = """
    Research the latest compliance requirements for employee onboarding in the technology sector for 2025.
    Focus on:
    - Data privacy and security training requirements
    - Remote work compliance considerations
    - Diversity, equity, and inclusion training mandates
    - Industry-specific certifications needed
    
    Provide a comprehensive compliance checklist with implementation timeline.
    """
    
    REMOTE_ONBOARDING_OPTIMIZATION = """
    Our company is transitioning to a fully remote workforce. Design an optimized remote onboarding experience that addresses:
    - Virtual team integration strategies
    - Digital tool training and setup
    - Remote culture building activities
    - Asynchronous learning paths
    - Virtual mentorship programs
    
    Research the most effective remote onboarding tools and platforms available in 2025.
    """
    
    ONBOARDING_COST_ANALYSIS = """
    Calculate the total cost of our current onboarding program and identify optimization opportunities:
    - HR staff time allocation (40 hours per new hire)
    - Training material costs ($500 per hire)
    - Technology setup and licensing ($1,200 per hire)
    - Manager mentoring time (20 hours per hire)
    - Lost productivity during ramp-up period
    
    Research cost-effective alternatives and calculate potential ROI improvements.
    """
    
    MANAGER_TRAINING_PROGRAM = """
    Design a comprehensive training program for managers who will be onboarding new team members:
    - Essential management skills for onboarding
    - Communication best practices for new hires
    - Goal setting and expectation management
    - Cultural integration techniques
    - Performance tracking during probation period
    
    Include current research on effective management practices for Gen Z employees entering the workforce.
    """
    
    TECH_STACK_ONBOARDING = """
    Create a detailed technical onboarding plan for a new developer joining our team that uses:
    - React/TypeScript frontend
    - Python/Django backend
    - PostgreSQL database
    - AWS cloud infrastructure
    - Docker containerization
    - Git/GitHub workflow
    
    Include learning resources, hands-on exercises, and milestone checkpoints for each technology.
    Research the latest learning resources and tutorials for 2025.
    """
    
    FEEDBACK_ANALYSIS = """
    Analyze this employee feedback from our recent onboarding survey and recommend improvements:
    
    Positive feedback:
    - "Great team culture and welcoming environment"
    - "Clear initial project assignments"
    - "Excellent technical mentorship"
    
    Areas for improvement:
    - "Administrative processes were confusing"
    - "Too much information in first week"
    - "Unclear long-term career path discussion"
    - "Limited social interaction opportunities"
    
    Provide specific, actionable recommendations with implementation priorities.
    """

    OFFICIAL_DEMO = """
    I am preparing a report on the energy efficiency of different machine learning model architectures. 
    Compare the estimated training and inference energy consumption of ResNet-50, BERT-base, and GPT-2 
    on standard datasets (e.g., ImageNet for ResNet, GLUE for BERT, WebText for GPT-2). 
    Then, estimate the CO2 emissions associated with each, assuming training on an Azure Standard_NC6s_v3 VM 
    for 24 hours. Provide tables for clarity, and recommend the most energy-efficient model 
    per task type (image classification, text classification, and text generation).
    """

    @classmethod
    def get_all_scenarios(cls):
        """Get all onboarding scenarios as a dictionary."""
        return {
            "welcome_new_hire": cls.WELCOME_NEW_HIRE,
            "metrics_analysis": cls.ONBOARDING_METRICS_ANALYSIS,
            "compliance_research": cls.COMPLIANCE_RESEARCH,
            "remote_optimization": cls.REMOTE_ONBOARDING_OPTIMIZATION,
            "cost_analysis": cls.ONBOARDING_COST_ANALYSIS,
            "manager_training": cls.MANAGER_TRAINING_PROGRAM,
            "tech_stack": cls.TECH_STACK_ONBOARDING,
            "feedback_analysis": cls.FEEDBACK_ANALYSIS,
            "official_demo": cls.OFFICIAL_DEMO,
        }
    
    @classmethod
    def get_scenario_names(cls):
        """Get list of available scenario names."""
        return list(cls.get_all_scenarios().keys())
    
    @classmethod
    def get_scenario(cls, name: str):
        """Get a specific scenario by name."""
        scenarios = cls.get_all_scenarios()
        return scenarios.get(name, None)