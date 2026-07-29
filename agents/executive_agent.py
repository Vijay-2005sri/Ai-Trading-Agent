import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

# Define the expected JSON output format
class TradeDecision(BaseModel):
    action: str = Field(description="The action to take: 'BUY', 'SELL', or 'HOLD'")
    pair: str = Field(description="The Forex pair, e.g., 'EURUSD'")
    confidence: int = Field(description="Confidence score from 0 to 100")
    reasoning: str = Field(description="Detailed explanation of why this decision was made, referencing news and quant data")
    suggested_sl: float = Field(description="Suggested Stop Loss price")
    suggested_tp: float = Field(description="Suggested Take Profit price")

class ExecutiveAgent:
    def __init__(self, provider="openai"):
        self.provider = provider
        # Initialize the LLM (The "Brain")
        if self.provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            self.llm = ChatOpenAI(api_key=api_key, model="gpt-4o", temperature=0.1)
        else:
            raise NotImplementedError("Only OpenAI is currently configured in this stub.")
            
        # We enforce the output to be JSON matching the TradeDecision schema
        self.structured_llm = self.llm.with_structured_output(TradeDecision)
        
        self.system_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are the Executive AI Agent of a quantitative hedge fund. "
                       "Your job is to read the reports from your Sub-Agents (Quant, Fundamental, Risk) "
                       "and historical context from the RAG memory system. "
                       "You must synthesize this information and make a final trading decision. "
                       "Always prioritize capital preservation. If the agents disagree strongly, vote HOLD."),
            ("human", "Here is the current market context:\n\n"
                      "1. RAG Context: {rag_context}\n"
                      "2. Quant Agent Report: {quant_report}\n"
                      "3. Fundamental Agent Report: {fundamental_report}\n\n"
                      "What is your decision?")
        ])
        
    def evaluate_trade(self, rag_context, quant_report, fundamental_report):
        print("Executive Agent is evaluating the trade...")
        chain = self.system_prompt | self.structured_llm
        
        decision = chain.invoke({
            "rag_context": rag_context,
            "quant_report": quant_report,
            "fundamental_report": fundamental_report
        })
        
        return decision

if __name__ == "__main__":
    pass
