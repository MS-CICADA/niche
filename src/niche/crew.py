import os
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from niche.tools.DataForSEOTools import KeywordExpansionTool, GoogleTrendsDataForSEOTool, DataForSEOClient
from niche.tools.TavilyTools import AIWebSearch
from niche.tools.SerperDevTools import SerperDevScraper

@CrewBase
class BlogContentResearchCrew:
    """Blog Content Research Crew"""
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL_NAME"),
        base_url=os.getenv("OPENAI_API_BASE"),
        api_key=os.getenv("OPENAI_API_KEY")
    )
 
    def __init__(self):
        self.dataforseo_client = DataForSEOClient()
        self.keyword_expansion_tool = KeywordExpansionTool(client=self.dataforseo_client)
        self.google_trends_tool = GoogleTrendsDataForSEOTool(client=self.dataforseo_client)
        self.ai_web_search = AIWebSearch()
        self.serper_dev_scraper = SerperDevScraper()
        super().__init__()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _execute_task_with_retry(self, task: Task) -> str:
        try:
            return task.execute()
        except Exception as e:
            print(f"Error executing task: {str(e)}")
            raise

    def manager_agent(self) -> Agent:
        return Agent(
            llm=self.llm,
            config=self.agents_config['manager_agent'],
            verbose=True
        )

    @agent
    def keyword_research_agent(self) -> Agent:
        return Agent(
            llm=self.llm,
            config=self.agents_config['keyword_research_agent'],
            tools=[self.keyword_expansion_tool, self.google_trends_tool, self.ai_web_search, self.serper_dev_scraper],
            verbose=True
        )

    @agent
    def content_ideation_agent(self) -> Agent:
        return Agent(
            llm=self.llm,
            config=self.agents_config['content_ideation_agent'],
            tools=[self.ai_web_search],
            verbose=True
        )

    @agent
    def trend_analysis_agent(self) -> Agent:
        return Agent(
            llm=self.llm,
            config=self.agents_config['trend_analysis_agent'],
            tools=[self.ai_web_search],
            verbose=True
        )

    @agent
    def report_generation_agent(self) -> Agent:
        return Agent(
            llm=self.llm,
            config=self.agents_config['report_generation_agent'],
            verbose=True
        )

    @task
    def generate_initial_keywords(self) -> Task:
        return Task(config=self.tasks_config['generate_initial_keywords'])

    @task
    def expand_and_analyze_keywords(self) -> Task:
        return Task(config=self.tasks_config['expand_and_analyze_keywords'])

    @task
    def perform_deep_dive_analysis(self) -> Task:
        return Task(config=self.tasks_config['perform_deep_dive_analysis'])

    @task
    def generate_blog_content_ideas(self) -> Task:
        return Task(config=self.tasks_config['generate_blog_content_ideas'])

    @task
    def identify_blog_content_trends(self) -> Task:
        return Task(config=self.tasks_config['identify_blog_content_trends'])

    @task
    def compile_comprehensive_blog_strategy_report(self) -> Task:
        return Task(config=self.tasks_config['compile_comprehensive_blog_strategy_report'])

    @crew
    def crew(self) -> Crew:
        """Creates the Blog Content Research Crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.hierarchical,
            manager_agent=self.manager_agent(),
            verbose=True,
        )

if __name__ == "__main__":
    blog_content_research = BlogContentResearchCrew()
    result = blog_content_research.crew.kickoff()
    with open('final_blog_strategy_report.md', 'w') as f:
        f.write(result)
    print("Report generated: final_blog_strategy_report.md")