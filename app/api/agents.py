# Llamaindex imports
from llama_index.llms.openai import OpenAI
from llama_index.llms.openrouter import OpenRouter
from llama_index.agent.openai import OpenAIAgent
from llama_index.tools.exa import ExaToolSpec
from llama_index.core.workflow import (
    Event,
    StartEvent,
    StopEvent,
    Workflow,
    step,
    Context
)
from llama_index.core.tools import FunctionTool
from app.api import prompts
from app.core.config import get_settings
from app.api import tools
from datetime import datetime
from llama_index.core.llms import ChatMessage
from pydantic import Field
from llama_index.core.agent.workflow import AgentWorkflow
import re

class SEO_Platform_Strategist(Event):
    input: str

class Content_Strategist_Prompt_Weaver(Event):
    input: str

class Target_Audience_Trend_Alchemist(Event):
    input: str


class IdeationFlow(Workflow):
    llm = OpenAI(api_key=get_settings().OPENAI_API_KEY, model=get_settings().RESEARCH_LLM_NAME)
    
    chat_history = []
    report = {}

    @step()
    async def start_agent_flow(self, ev: StartEvent) -> Target_Audience_Trend_Alchemist:
        if ev.provider == "openai":
            self.llm = OpenAI(api_key=get_settings().OPENAI_API_KEY, model=ev.model)
        elif ev.provider == "openrouter":
            self.llm = OpenRouter(api_key=get_settings().OPENROUTER_API_KEY, model=ev.model, max_tokens=1000)

        initial_input = ev.input
        self.chat_history = ev.chat_history
        prompt = f"Here is the initial topic I need youtube ideas on - {initial_input}. \n\n The chat history with the brainstorming agent is: {self.chat_history}"
        
        return Target_Audience_Trend_Alchemist(input=str(prompt))

    @step()
    async def trend_analysis(self, ev: Target_Audience_Trend_Alchemist) -> SEO_Platform_Strategist:
        input = ev.input
        
        system_prompt= prompts.Target_Audience_Trend_Alchemist_Prompt

        exa_tool = ExaToolSpec(
            api_key=get_settings().EXA_API_KEY
        )

        tool_list = [FunctionTool.from_defaults(tools.perplexity_ai_search, 
                        name="perplexity_ai_search", 
                        description="You can use this tool, to understand concepts or search for certain queries for elaboration. Useful when conducting research using Perplexity AI online model."
                        ),

                    FunctionTool.from_defaults(tools.youtube_search, 
                        name="youtube_search", 
                        description="Use this tool for searching YouTube videos for related topics. Make sure to pay attention to views and views to subscriber ratios."
                        ),
                    
                    FunctionTool.from_defaults(tools.channel_details_tool, 
                        name="channel_details_tool", 
                        description="Use this tool to retrieve details of a specific YouTube channel, like the subscriber count and channel description."
                        ),

                    FunctionTool.from_defaults(tools.youtube_video_details, 
                        name="youtube_video_details", 
                        description="Use this tool for retrieving detailed information about a youtube video, like the views, publish date, like count, channel id."
                        ),

                    FunctionTool.from_defaults(tools.transcribe_video, 
                        name="transcribe_video", 
                        description="Transcribe a YouTube video using Youtube Transcriptor RapidAPI."
                        ),

                    FunctionTool.from_defaults(tools.avatar_information, 
                        name="Avatar", 
                        description="use it to find out more about our target audience, our avatars. Their information about interests, age, employment and other information about them."
                        )
        ]

        tool_list.extend(exa_tool.to_tool_list())

        # agent = OpenAIAgent.from_tools(tool_list, verbose=True, system_prompt=system_prompt, llm=self.llm)
        # response = agent.chat(input)

        workflow = AgentWorkflow.from_tools_or_functions(
            tool_list,
            llm=self.llm,
            system_prompt=str(system_prompt),
        )
        response = await workflow.run(user_msg=str(input))

        tools.save_outputs_in_notion(str(response), f"Trend And Audience Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        self.report["Trend_And_Audience_Analysis"] = str(response)

        return SEO_Platform_Strategist(input=str(response))
        # return StopEvent(result=str(response))

    @step()
    async def seo_optimization(self, ev: SEO_Platform_Strategist) -> Content_Strategist_Prompt_Weaver:

        input = f"Here is the output of the Target Audience Trend Alchemist: {ev.input}. I need you to validate the topics, titles, and thumbnails for search optimization.  \n\n The chat history with the brainstorming agent is: {self.chat_history}"

        system_prompt= prompts.SEO_Platform_Strategist_Prompt

        exa_tool = ExaToolSpec(
            api_key=get_settings().EXA_API_KEY
        )

        tool_list = [FunctionTool.from_defaults(tools.google_promise, 
                        name="google_promise", 
                        description="Google Promise Keyword Tool used via RapidAPI, that should be used whenever you need to find information about current search volumes and popularity on any topic and keyword or phrase. It runs both dedicated global search for English language. You can also do dedicated location research by specifying country, like US or GB. Purpose: Fetches keyword data, including search volume, competition, and related keywords, from Google Keyword Planner via RapidAPI. Make sure that the input is no longer than 1-2 words"
                        )
        ]

        tool_list.extend(exa_tool.to_tool_list())

        # agent = OpenAIAgent.from_tools(tool_list, verbose=True, system_prompt=system_prompt, llm=self.llm)

        # response = agent.chat(input)

        workflow = AgentWorkflow.from_tools_or_functions(
            tool_list,
            llm=self.llm,
            system_prompt=str(system_prompt),
        )
        response = await workflow.run(user_msg=str(input))
        

        tools.save_outputs_in_notion(str(response), f"SEO Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        self.report["SEO_Analysis"] = str(response)

        return Content_Strategist_Prompt_Weaver(input=str(response))
        

    @step()
    async def content_strategy(self, ev: Content_Strategist_Prompt_Weaver) -> StopEvent:

        input = f"This is the output of the Target_Audience_Trend_Alchemist: {self.report["Trend_And_Audience_Analysis"]}. \n\n This is the output of the SEO_Platform_Strategist:  {self.report["SEO_Analysis"]}   \n\n The chat history with the brainstorming agent is: {self.chat_history}"

        system_prompt= prompts.Content_Strategist_Prompt_Weaver_Prompt

        tool_list = [
                    FunctionTool.from_defaults(tools.ultimatebrain_information, 
                        name="scripting_brain", 
                        description="This is the scripting_brain that contains a lot of curated distilled knowledge about scripting, content creation, AI and optimal way to write youtube video scripts. It contains a lot of viable useful crucial key information for perfect youtube video masterpiece creation process. Especially titles, thumbnails, hooks, payoffs, cognitive bias, retention methods etc."
                        ),

                    FunctionTool.from_defaults(tools.avatar_information, 
                        name="Avatar", 
                        description="use it to find out more about our target audience, our avatars. Their information about interests, age, employment and other information about them."
                        )
            ]
        # agent = OpenAIAgent.from_tools(tool_list, verbose=True, system_prompt=system_prompt, llm=self.llm)

        # response = agent.chat(input)

        workflow = AgentWorkflow.from_tools_or_functions(
            tool_list,
            llm=self.llm,
            system_prompt=str(system_prompt),
        )
        response = await workflow.run(user_msg=str(input))
        

        tools.save_outputs_in_notion(str(response), f"Content Strategist - {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        self.report["Content_Strategist_Prompt_Weaver"] = str(response)

        return StopEvent(result=str(response))



class Research_Navigator(Event):
    input: str

class Knowledge_Curator_Fact_Checker(Event):
    input: str


class ResearchFlow(Workflow):
    llm = OpenAI(api_key=get_settings().OPENAI_API_KEY, model=get_settings().RESEARCH_LLM_NAME)
    
    report = {}
    chat_history = []

    @step()
    async def start_agent_flow(self, ev: StartEvent) -> Research_Navigator:

        if ev.provider == "openai":
            self.llm = OpenAI(api_key=get_settings().OPENAI_API_KEY, model=ev.model)
        elif ev.provider == "openrouter":
            self.llm = OpenRouter(api_key=get_settings().OPENROUTER_API_KEY, model=ev.model, max_tokens=1000)
        
        initial_input = ev.input
        ideation_output = ev.ideation
        self.chat_history = ev.chat_history
        prompt = f"Here is the initial topic - {initial_input}. \n I need you to find statistics, studies, examples from reputable scientific sources and store properly. \n\n Here are the 3 idea sets finalized: {ideation_output}.  \n\n The chat history with the brainstorming agent is: {self.chat_history}"
        
        return Research_Navigator(input=str(prompt))

    @step()
    async def research_navigator(self, ev: Research_Navigator) -> Knowledge_Curator_Fact_Checker:
        input = str(ev.input)
        
        system_prompt= prompts.Research_Navigator_Prompt

        tool_list = [FunctionTool.from_defaults(tools.Med_Articles_PMC, 
                        name="Med_Articles_PMC", 
                        description="Fetches medical literature data from the Europe PMC API. Use it to find scientific news - new research, letters, case reports and reviews from medical world."
                        ),

                    FunctionTool.from_defaults(tools.Semantic_Scholar_Tool, 
                        name="Semantic_Scholar_Tool", 
                        description="Use this tool to access a free, AI-powered research tool for scientific literature."
                        ),
                    
                    FunctionTool.from_defaults(tools.PubMed_Tool, 
                        name="PubMed_Tool", 
                        description="Searches PubMed NCBI Database for medical publications and research papers."
                        ),

                    FunctionTool.from_defaults(tools.Google_Scholar_Tool, 
                        name="Google_Scholar_Tool", 
                        description="Fetches scholarly articles from Google Scholar using SerpAPI"
                        )
        ]

        # agent = OpenAIAgent.from_tools(tool_list, verbose=True, system_prompt=system_prompt, llm=self.llm)

        # response = await agent.achat(input)
        workflow = AgentWorkflow.from_tools_or_functions(
            tool_list,
            llm=self.llm,
            system_prompt=str(system_prompt),
        )
        response = await workflow.run(user_msg=str(input))
        

        tools.save_outputs_in_notion(str(response), f"Research Navigator - {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        self.report["Research_Navigator"] = str(response)

        return Knowledge_Curator_Fact_Checker(input=str(response))

    @step()
    async def knowledge_curator(self, ev: Knowledge_Curator_Fact_Checker) -> StopEvent:

        input = f"Here is the output of the Research_Navigator: {ev.input}.  \n\n The chat history with the brainstorming agent is: {self.chat_history}"

        system_prompt= prompts.Knowledge_Curator_Fact_Checker_Prompt

        exa_tool = ExaToolSpec(
            api_key=get_settings().EXA_API_KEY
        )

        tool_list = [FunctionTool.from_defaults(tools.perplexity_ai_search, 
                        name="perplexity_ai_search", 
                        description="You can use this tool, to understand concepts or search for certain queries for elaboration. Useful when conducting research using Perplexity AI online model. You can also use this to fetch the content from the urls returns by Research_Navigator"
                        ),

                    FunctionTool.from_defaults(tools.save_in_notion, 
                        name="save_in_notion", 
                        description="Use this to save research to Notion database. It accepts the content, title and list of DOIs of the research articles in the content like this DOI1, DOI2, DOI3..."
                        ),

                    FunctionTool.from_defaults(tools.upsert_to_qdrant, 
                        name="upsert_to_qdrant", 
                        description="Use this to upsert the notion page's data into Qdrant Vector Store. Example input: page_id: 3c8babb6-0666-48e6-a584-444ddf7a008f"
                        )

        ]

        tool_list.extend(exa_tool.to_tool_list())

        # agent = OpenAIAgent.from_tools(tool_list, verbose=True, system_prompt=system_prompt, llm=self.llm)

        # response = await agent.achat(input)
        workflow = AgentWorkflow.from_tools_or_functions(
            tool_list,
            llm=self.llm,
            system_prompt=str(system_prompt),
        )
        response = await workflow.run(user_msg=str(input))
        

        tools.save_outputs_in_notion(str(response), f"Knowledge Curator Fact Checker - {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        self.report["Knowledge_Curator_Fact_Checker"] = str(response)

        return StopEvent(result=str(response))
        
class Lead_Scriptwriter_Engagement_Maestro(Event):
    input: str

class GEORGE_BLACKMAN_EVALUATOR(Event):
    input: str

class MR_BEAST_EVALUATOR(Event):
    input: str

class Evaluate_Score(Event):
    input: str

# class ScriptingFlow(Workflow):
#     llm = OpenAI(api_key=get_settings().OPENAI_API_KEY, model=get_settings().RESEARCH_LLM_NAME)
    
#     report = {}
#     chat_history = []

#     scripting_prompt = prompts.Scriptwriter_Prompt

#     @step()
#     async def start_agent_flow(self, ev: StartEvent) -> Lead_Scriptwriter_Engagement_Maestro:
#         if ev.provider == "openai":
#             self.llm = OpenAI(api_key=get_settings().OPENAI_API_KEY, model=ev.model)
#         elif ev.provider == "openrouter":
#             self.llm = OpenRouter(api_key=get_settings().OPENROUTER_API_KEY, model=ev.model, max_tokens=1000)

#         if ev.scripting_prompt:
#             self.scripting_prompt = ev.scripting_prompt

#         ideation_output = ev.ideation
#         research_output = ev.research

#         self.chat_history = ev.chat_history
#         self.report["ideation_output"] = ideation_output
#         self.report["research_output"] = research_output

#         prompt = f"Here is the chosen set from output of Team 1 (Ideation Workflow): {ideation_output}. \n\n Here is the output of Team 2 (Medical Researcher): {research_output}  \n\n The chat history is: {self.chat_history}"
        
#         return Lead_Scriptwriter_Engagement_Maestro(input=str(prompt))

#     @step()
#     async def scriptwriter(self, ev: Lead_Scriptwriter_Engagement_Maestro) -> GEORGE_BLACKMAN_EVALUATOR | MR_BEAST_EVALUATOR:
#         input = ev.input
        
#         system_prompt= self.scripting_prompt

#         tool_list = [FunctionTool.from_defaults(tools.avatar_information, 
#                         name="Avatar", 
#                         description="use it to find out more about our target audience, our avatars. Their information about interests, age, employment and other information about them."
#                         ),

#                     FunctionTool.from_defaults(tools.sugarbrain_information, 
#                         name="Ultimate_Brain", 
#                         description="Use it to retrieve all the important information for current script in terms of scientific knowledge. It contains research papers, notes, insights, conclusions, scientific review articles and much more relating to current problem we are trying to tackle in the video. Use it always."
#                         ),
#                     FunctionTool.from_defaults(tools.ultimatebrain_information, 
#                         name="scripting_brain", 
#                         description="This is a database that contains a lot of curated distilled knowledge about scripting, content creation and optimal way to write youtube video scripts. It contains a lot of viable, useful, crucial, key information for perfect, masterpiece youtube video content creation process."
#                         ),
#                     FunctionTool.from_defaults(tools.search_notion_pages, 
#                         name="search_notion_pages", 
#                         description="Use this to search for relevent research articles to add references in the script."
#                         ),
#                     FunctionTool.from_defaults(tools.extract_notion_page_content, 
#                         name="extract_notion_page_content", 
#                         description="Use this to extract the page content from notion"
#                         )
#         ]

#         # agent = OpenAIAgent.from_tools(tool_list, verbose=True, system_prompt=system_prompt, llm=self.llm)

#         # response = agent.chat(input)

#         workflow = AgentWorkflow.from_tools_or_functions(
#             tool_list,
#             llm=self.llm,
#             system_prompt=str(system_prompt),
#         )
#         response = await workflow.run(user_msg=str(input))
        

#         self.report["Final_Script"] = str(response)
        
#         tools.save_outputs_in_notion(str(response), f"Final Script - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
#         self.send_event(GEORGE_BLACKMAN_EVALUATOR(input=str(response)))
#         self.send_event(MR_BEAST_EVALUATOR(input=str(response)))

#     @step()
#     async def mr_beast_evaluator(self, ev: MR_BEAST_EVALUATOR) -> Evaluate_Score:
#         input = ev.input
        
#         system_prompt= prompts.MR_BEAST_EVALUATOR

#         tool_list = []

#         # agent = OpenAIAgent.from_tools(tool_list, verbose=True, system_prompt=system_prompt, llm=self.llm)

#         # response = agent.chat(input)
#         workflow = AgentWorkflow.from_tools_or_functions(
#             tool_list,
#             llm=self.llm,
#             system_prompt=str(system_prompt),
#         )
#         response = await workflow.run(user_msg=str(input))
        

#         self.report["MR_BEAST_SCORE"] = str(response)

#         return Evaluate_Score(input="")

#     @step()
#     async def gorge_blackman_evaluator(self, ev: GEORGE_BLACKMAN_EVALUATOR) -> Evaluate_Score:
#         input = ev.input
        
#         system_prompt= prompts.GEORGE_BLACKMAN_EVALUATOR

#         tool_list = []

#         # agent = OpenAIAgent.from_tools(tool_list, verbose=True, system_prompt=system_prompt, llm=self.llm)

#         # response = agent.chat(input)

#         workflow = AgentWorkflow.from_tools_or_functions(
#             tool_list,
#             llm=self.llm,
#             system_prompt=str(system_prompt),
#         )
#         response = await workflow.run(user_msg=str(input))
        

#         self.report["GEORGE_BLACKMAN_SCORE"] = str(response)

#         return Evaluate_Score(input="")

#     @step()
#     async def evaluate_score(self, ctx: Context, ev: Evaluate_Score) -> StopEvent | Lead_Scriptwriter_Engagement_Maestro | None:
        
#         ready = ctx.collect_events(ev, [Evaluate_Score] * 2)
#         if ready is None:
#             return None

#         print(self.report["GEORGE_BLACKMAN_SCORE"])
#         print(self.report["MR_BEAST_SCORE"])

#         GEORGE_BLACKMAN_SCORE = self.report["GEORGE_BLACKMAN_SCORE"]
#         MR_BEAST_SCORE = self.report["MR_BEAST_SCORE"]

#         if check_total_mb_score(GEORGE_BLACKMAN_SCORE) or check_total_mb_score(MR_BEAST_SCORE):
#             input = f'''This is the final script that was generated: {self.report["Final_Script"]}. 
#             Here is the chosen set from output of Team 1 (Ideation Workflow): {ideation_output}. 
#             Here is the output of Team 2 (Medical Researcher): {research_output}. 
#             Current date & time: {datetime.now().strftime("%Y-%m-%d %H:%M")}
#             The score given to the final script by gorge blackman & Mr Beast is as following:
#             GEORGE_BLACKMAN_SCORE: {self.report["GEORGE_BLACKMAN_SCORE"]}
#             MR_BEAST_SCORE: {self.report["MR_BEAST_SCORE"]}

#             The score wasn't up to mark. Please recreate the script again.
#             '''
#             return Lead_Scriptwriter_Engagement_Maestro(input=input)
#         else:
#             return StopEvent(result=self.report)


class ScriptCEO(Event):
    input: str

class ContextResearchExtraction(Event):
    input: str

class StoryNarrativeStructureDevelopment(Event):
    input: str

class ContentStructureProductionBlueprint(Event):
    input: str

class HookIntroduction(Event):
    input: str

class Segment1(Event):
    input: str

class Segment2(Event):
    input: str

class Segment3(Event):
    input: str

class Segment4(Event):
    input: str

class ConclusionCTA(Event):
    input: str

class FinalCompilation(Event):
    input: str

class ScriptingWorkflow(Workflow):

    responses = {}
    initial_input = " "
    index = 0
    llm = OpenAI(model = "gpt-4o-mini", api_key = get_settings().OPENAI_API_KEY)
    ideation_output = ""
    research_output = ""
    chat_history = ""


    @step
    async def ceo(self, ctx: Context, ev: StartEvent) -> ContextResearchExtraction | StoryNarrativeStructureDevelopment | ContentStructureProductionBlueprint | Segment1 | Segment2 | Segment3 | Segment4 | ConclusionCTA | HookIntroduction:

        system_prompt = prompts.ScriptCEO_Prompt
        
        input = ev.input

        self.index = self.index + 1
        
        if self.index == 1:
            # self.initial_input = ev.input
            if ev.provider == "openai":
                self.llm = OpenAI(api_key=get_settings().OPENAI_API_KEY, model=ev.model)
            elif ev.provider == "openrouter":
                self.llm = OpenRouter(api_key=get_settings().OPENROUTER_API_KEY, model=ev.model, max_tokens=1000)

            self.ideation_output = ev.ideation
            self.research_output = ev.research
            self.chat_history = ev.chat_history
            input = f"Here is the chosen set from output of Team 1 (Ideation Workflow): {self.ideation_output}. \n\n Here is the output of Team 2 (Medical Researcher): {self.research_output}  \n\n The chat history is: {ev.chat_history}."
            self.initial_input = ev.input

        # if ev.scripting_prompt is not None:
        #     system_prompt = ev.scripting_prompt


        agent = OpenAIAgent.from_tools([], verbose=True, system_prompt=system_prompt, llm=self.llm)

        response = agent.chat(input).response

        print("response is:" + response)

        next_agent = re.search(r'Next Agent:\s*(.+)', response)

        if next_agent:
            next_agent = next_agent.group(1).strip()
            print("next agent is:" + next_agent)
       
        if "ContextResearchExtraction" in next_agent:
            return ContextResearchExtraction(input=response)
        elif "StoryNarrativeStructureDevelopment" in next_agent:
            return StoryNarrativeStructureDevelopment(input=response)
        elif "ContentStructureProductionBlueprint" in next_agent:
            return ContentStructureProductionBlueprint(input=response)
        elif "Segment1" in next_agent or "Segment2" in next_agent or "Segment3" in next_agent or "Segment4" in next_agent or "ConclusionCTA" in next_agent or "HookIntroduction":
            ctx.send_event(HookIntroduction(input=response))
            ctx.send_event(Segment1(input=response))
            ctx.send_event(Segment2(input=response))
            ctx.send_event(Segment3(input=response))
            ctx.send_event(Segment4(input=response))
            ctx.send_event(ConclusionCTA(input=response))

    @step
    async def researchExtraction(self, ctx: Context, ev: ContextResearchExtraction) -> StartEvent:

        input = ev.input

        exa_tool = ExaToolSpec(
            api_key=get_settings().EXA_API_KEY
        )
        
        tool_list = [FunctionTool.from_defaults(tools.avatar_information, 
                        name="Avatar", 
                        description="use it to find out more about our target audience, our avatars. Their information about interests, age, employment and other information about them."
                        ),

                    FunctionTool.from_defaults(tools.sugarbrain_information, 
                        name="Ultimate_Brain", 
                        description="Use it to retrieve all the important information for current script in terms of scientific knowledge. It contains research papers, notes, insights, conclusions, scientific review articles and much more relating to current problem we are trying to tackle in the video. Use it always."
                        ),
                    FunctionTool.from_defaults(tools.ultimatebrain_information, 
                        name="scripting_brain", 
                        description="This is a database that contains a lot of curated distilled knowledge about scripting, content creation and optimal way to write youtube video scripts. It contains a lot of viable, useful, crucial, key information for perfect, masterpiece youtube video content creation process."
                        ),
                    FunctionTool.from_defaults(tools.search_notion_pages, 
                        name="search_notion_pages", 
                        description="Use this to search for relevent research articles to add references in the script."
                        ),
                    FunctionTool.from_defaults(tools.extract_notion_page_content, 
                        name="extract_notion_page_content", 
                        description="Use this to extract the page content from notion"
                        ),
                    FunctionTool.from_defaults(tools.perplexity_ai_search,
                        name="perplexity_ai_search",
                        description="You can use this tool, to understand concepts or search for certain queries for elaboration. Useful when conducting research using Perplexity AI online model."),
                    # exa_tool.to_tool_list()
        ]

        agent = OpenAIAgent.from_tools(tool_list, verbose=True, system_prompt=prompts.ContextResearchExtraction_Prompt, llm=self.llm)

        response = agent.chat(f'Here is the initial input buy the user: {self.initial_input} and here are the instructions of the ScriptWriter Oschestrator: {input}').response

        self.responses["ContextResearchExtraction"] = response

        return StartEvent(input=f'I have completed ContextResearchExtraction task. Here is my output: {response}')

    @step
    async def storyNarrativeStructureDevelopment(self, ctx: Context, ev: StoryNarrativeStructureDevelopment) -> StartEvent:

        exa_tool = ExaToolSpec(
            api_key=get_settings().EXA_API_KEY
        )

        input = ev.input

        tool_list = [FunctionTool.from_defaults(tools.avatar_information, 
                        name="Avatar", 
                        description="use it to find out more about our target audience, our avatars. Their information about interests, age, employment and other information about them."
                        ),
                        FunctionTool.from_defaults(tools.perplexity_ai_search,
                        name="perplexity_ai_search",
                        description="You can use this tool, to understand concepts or search for certain queries for elaboration. Useful when conducting research using Perplexity AI online model."),
                        # exa_tool.to_tool_list()
        ]

        agent = OpenAIAgent.from_tools(tool_list, verbose=True, system_prompt=prompts.StoryNarrativeStructureDevelopment_Prompt, llm=self.llm)

        response = agent.chat(f'Here is the initial input buy the user: {self.initial_input}. \n\n Here is the output of the other agents: {self.responses}. \n\n Here is the chat history while brainstorming the idea: {self.chat_history} \n\n Here are the instructions of the ScriptWriter Oschestrator: {input}').response

        self.responses["StoryNarrativeStructureDevelopment"] = str(response)

        return StartEvent(input=f'I have completed StoryNarrativeStructureDevelopment task. Here is my output: {response}')

    @step
    async def contentStructureProductionBlueprint(self, ctx: Context, ev: ContentStructureProductionBlueprint) -> StartEvent:

        input = ev.input
        tool_list = [FunctionTool.from_defaults(tools.avatar_information, 
                                name="Avatar", 
                                description="use it to find out more about our target audience, our avatars. Their information about interests, age, employment and other information about them."
                                )
                                            
                    ]
        agent = OpenAIAgent.from_tools(tool_list, verbose=True, system_prompt=prompts.ContentStructureProductionBlueprint_Prompt, llm=self.llm)

        response = agent.chat(f'Here is the initial input buy the user: {self.initial_input}. \n\n Here is the output of the other agents: {self.responses}. \n\n Here is the chat history while brainstorming the idea: {self.chat_history} \n\n Here are the instructions of the ScriptWriter Oschestrator: {input}').response

        self.responses["ContentStructureProductionBlueprint"] = str(response)

        return StartEvent(input=f'I have completed ContentStructureProductionBlueprint task. Here is my output: {response}')

    @step
    async def hookIntro(self, ctx: Context, ev: HookIntroduction) -> FinalCompilation:

        input = ev.input

        agent = OpenAIAgent.from_tools([], verbose=True, system_prompt=prompts.HookIntroduction_Prompt, llm=self.llm)

        response = agent.chat(f'Here is the initial input buy the user: {self.initial_input}. \n\n Here is the output of the other agents: {self.responses}. \n\n Here is the chat history while brainstorming the idea: {self.chat_history} \n\n Here are the instructions of the ScriptWriter Oschestrator: {input}').response

        self.responses["HookIntroduction"] = str(response)

        return FinalCompilation(input=f'I have completed HookIntroduction task.')

    @step
    async def segment1(self, ctx: Context, ev: Segment1) -> FinalCompilation:

        input = ev.input

        agent = OpenAIAgent.from_tools([], verbose=True, system_prompt=prompts.Segment1_Prompt, llm=self.llm)

        response = agent.chat(f'Here is the initial input buy the user: {self.initial_input}. \n\n Here is the output of the other agents: {self.responses}. \n\n Here is the chat history while brainstorming the idea: {self.chat_history} \n\n Here are the instructions of the ScriptWriter Oschestrator: {input}').response

        self.responses["Segment1"] = str(response)

        return FinalCompilation(input=f'I have completed Segment1 task.')

    @step
    async def segment2(self, ctx: Context, ev: Segment2) -> FinalCompilation:

        input = ev.input

        agent = OpenAIAgent.from_tools([], verbose=True, system_prompt=prompts.Segment2_Prompt, llm=self.llm)

        response = agent.chat(f'Here is the initial input buy the user: {self.initial_input}. \n\n Here is the output of the other agents: {self.responses}. \n\n Here is the chat history while brainstorming the idea: {self.chat_history} \n\n Here are the instructions of the ScriptWriter Oschestrator: {input}').response

        self.responses["Segment2"] = str(response)

        return FinalCompilation(input=f'I have completed Segment2 task.')

    @step
    async def segment3(self, ctx: Context, ev: Segment3) -> FinalCompilation:

        input = ev.input

        agent = OpenAIAgent.from_tools([], verbose=True, system_prompt=prompts.Segment3_Prompt, llm=self.llm)

        response = agent.chat(f'Here is the initial input buy the user: {self.initial_input}. \n\n Here is the output of the other agents: {self.responses}. \n\n Here is the chat history while brainstorming the idea: {self.chat_history} \n\n Here are the instructions of the ScriptWriter Oschestrator: {input}').response

        self.responses["Segment3"] = str(response)

        return FinalCompilation(input=f'I have completed Segment3 task.')

    @step
    async def segment4(self, ctx: Context, ev: Segment4) -> FinalCompilation:

        input = ev.input

        agent = OpenAIAgent.from_tools([], verbose=True, system_prompt=prompts.Segment4_Prompt, llm=self.llm)

        response = agent.chat(f'Here is the initial input buy the user: {self.initial_input}. \n\n Here is the output of the other agents: {self.responses}. \n\n Here is the chat history while brainstorming the idea: {self.chat_history} \n\n Here are the instructions of the ScriptWriter Oschestrator: {input}').response

        self.responses["Segment4"] = str(response)

        return FinalCompilation(input=f'I have completed Segment4 task.')

    @step
    async def conclusion(self, ctx: Context, ev: ConclusionCTA) -> FinalCompilation:

        input = ev.input

        agent = OpenAIAgent.from_tools([], verbose=True, system_prompt=prompts.ConclusionCTA_Prompt, llm=self.llm)

        response = agent.chat(f'Here is the initial input buy the user: {self.initial_input}. \n\n Here is the output of the other agents: {self.responses}. \n\n Here is the chat history while brainstorming the idea: {self.chat_history} \n\n Here are the instructions of the ScriptWriter Oschestrator: {input}').response

        self.responses["ConclusionCTA"] = str(response)

        return FinalCompilation(input=f'I have completed ConclusionCTA task.')

    @step
    async def compilation(self, ctx: Context, ev: FinalCompilation) -> StopEvent:

        print("------------SCRIPT WRITING COMPLETED---------------")

        result = ctx.collect_events(ev, [FinalCompilation] * 6)

        print(result)

        print(self.responses)

        return StopEvent(self.responses)



def check_total_mb_score(score_string):
    try:
        # Split the string into lines and find the line with the Total MB Score
        lines = score_string.splitlines()
        for line in lines:
            if "Total MB Score:" in line:
                # Extract the score from the line
                score = float(line.split(":")[1].strip().split('/')[0])
                # Check the score condition
                return score <= 5
        
        # If Total MB Score line is not found
        print("Total MB Score not found.")
        return None

    except (ValueError, IndexError):
        print("Invalid input format.")
        return None

async def modify_script(script: str, input: str, chat_history, provider, model):
    llm = None
    if provider == "openai":
        llm = OpenAI(api_key=get_settings().OPENAI_API_KEY, model=model)
    elif provider == "openrouter":
        llm = OpenRouter(api_key=get_settings().OPENROUTER_API_KEY, model=model, max_tokens=1000)

    exa_tool = ExaToolSpec(
            api_key=get_settings().EXA_API_KEY
        )
    
    # llm = OpenAI(api_key=get_settings().OPENAI_API_KEY, model=get_settings().RESEARCH_LLM_NAME)
    
    tool_list = [FunctionTool.from_defaults(tools.avatar_information, 
                    name="Avatar", 
                    description="use it to find out more about our target audience, our avatars. Their information about interests, age, employment and other information about them."
                    ),
                FunctionTool.from_defaults(tools.sugarbrain_information, 
                    name="Ultimate_Brain", 
                    description="Use it to retrieve all the important information for current script in terms of scientific knowledge. It contains research papers, notes, insights, conclusions, scientific review articles and much more relating to current problem we are trying to tackle in the video. Use it always."
                    ),
                FunctionTool.from_defaults(tools.ultimatebrain_information, 
                    name="scripting_brain", 
                    description="This is a database that contains a lot of curated distilled knowledge about scripting, content creation and optimal way to write youtube video scripts. It contains a lot of viable, useful, crucial, key information for perfect, masterpiece youtube video content creation process."
                    ),
                FunctionTool.from_defaults(tools.search_notion_pages, 
                    name="search_notion_pages", 
                    description="Use this to search for relevent research articles to add references in the script."
                    ),
                FunctionTool.from_defaults(tools.extract_notion_page_content, 
                    name="extract_notion_page_content", 
                    description="Use this to extract the page content from notion"
                    ),
                FunctionTool.from_defaults(tools.perplexity_ai_search,
                    name="perplexity_ai_search",
                    description="You can use this tool, to understand concepts or search for certain queries for elaboration. Useful when conducting research using Perplexity AI online model."),
                # exa_tool.to_tool_list()
        ]
    agent_input = f"The script is:{script}. The modification request is: {input} \n\n The chat history is: {chat_history}"
    # agent = OpenAIAgent.from_tools(tool_list, verbose=True, system_prompt=prompts.SCRIPT_MODIFICATION_PROMPT, llm=llm)
    # response = agent.chat(agent_input)
    workflow = AgentWorkflow.from_tools_or_functions(
            tool_list,
            llm=llm,
            system_prompt=str(prompts.SCRIPT_MODIFICATION_PROMPT),
        )
    response = await workflow.run(user_msg=str(agent_input))
        
    # resp = OpenAI(api_key=get_settings().OPENAI_API_KEY, model=get_settings().RESEARCH_LLM_NAME).chat(messages)

    return str(response)

async def generate_final_new_script(initial_script: str, modification_prompt:str, modified_script: str, provider, model):
    llm = None
    if provider == "openai":
        llm = OpenAI(api_key=get_settings().OPENAI_API_KEY, model=model)
    elif provider == "openrouter":
        llm = OpenRouter(api_key=get_settings().OPENROUTER_API_KEY, model=model, max_tokens=1000)
    messages = [
        ChatMessage(
            role="system", content="You are a skilled script writer and editor tasked with generating a final script based on the initial script, modification request and the modified script"
        ),
        ChatMessage(role="user", content=f"Generate the complete final script. \n\n This is the initial script: {initial_script} \n\n This is was the modification request: {modification_prompt} \n\n This is the modified script response based on the request: {modified_script}"),
    ]
    response = llm.chat(messages)

    return str(response)

async def summarize_chat_history(chat: str):
       
    messages = [
        ChatMessage(
            role="system", content=prompts.SUMMARIZATION_PROMPT
        ),
        ChatMessage(role="user", content=f"{chat}"),
    ]
    response = OpenAI(api_key=get_settings().OPENAI_API_KEY, model=get_settings().RESEARCH_LLM_NAME).chat(messages)

    return str(response)


async def mr_beast_evaluator(script, provider, model) -> Evaluate_Score:
    llm = None
    if provider == "openai":
        llm = OpenAI(api_key=get_settings().OPENAI_API_KEY, model=model)
    elif provider == "openrouter":
        llm = OpenRouter(api_key=get_settings().OPENROUTER_API_KEY, model=model, max_tokens=1000)
        
    system_prompt= prompts.MR_BEAST_EVALUATOR

    tool_list = []

    # agent = OpenAIAgent.from_tools(tool_list, verbose=True, system_prompt=system_prompt, llm=self.llm)

    # response = agent.chat(input)
    workflow = AgentWorkflow.from_tools_or_functions(
        tool_list,
        llm=llm,
        system_prompt=str(system_prompt),
    )
    response = await workflow.run(user_msg=str(script))
    
    return str(response)


async def george_blackman_evaluator(script, provider, model) -> Evaluate_Score:
    llm = None
    if provider == "openai":
        llm = OpenAI(api_key=get_settings().OPENAI_API_KEY, model=model)
    elif provider == "openrouter":
        llm = OpenRouter(api_key=get_settings().OPENROUTER_API_KEY, model=model, max_tokens=1000)
        
    system_prompt= prompts.MR_BEAST_EVALUATOR

    tool_list = []

    # agent = OpenAIAgent.from_tools(tool_list, verbose=True, system_prompt=system_prompt, llm=self.llm)

    # response = agent.chat(input)
    workflow = AgentWorkflow.from_tools_or_functions(
        tool_list,
        llm=llm,
        system_prompt=str(system_prompt),
    )
    response = await workflow.run(user_msg=str(script))
    
    return str(response)
