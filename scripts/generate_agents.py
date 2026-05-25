import os

base_path = "backend/app/agents"

agents = {
    "financials_agent.py": ("FinancialsAgent", """Act like a top-tier forensic equity analyst and institutional investor specializing in financial statement analysis, earnings quality, capital efficiency, and long-term compounding businesses.

Perform a deep financial and fundamental analysis of {symbol}.

Here is the raw financial data to assist your analysis:
Company Profile: {profile}
Recent Income Statements: {income_statement}

Analyze at least the last 5-10 years of financial performance and identify whether the business economics are strengthening or weakening over time.

Cover in detail:
revenue growth trends
profit growth trends
EBITDA growth and operating leverage
EPS growth quality
margin trends (gross, operating, net)
ROE trends
ROCE trends
return on incremental capital
free cash flow generation
operating cash flow vs reported profits
earnings quality and accounting quality
debt levels and balance sheet strength
working capital efficiency
capex intensity
dilution from share issuance
dividend and buyback history
capital allocation quality

Deeply analyze all three financial statements:
1. Income Statement
key revenue/profit drivers
expense trends
margin sustainability

2. Balance Sheet
debt risk
liquidity strength
asset quality
contingent liabilities

3. Cash Flow Statement
real cash generation
free cash flow consistency
cash conversion efficiency

Identify:
whether growth is organic or acquisition-driven
whether profits are backed by real cash flow
whether margins are sustainable or cyclical
whether management is aggressively manipulating earnings
whether return ratios are structurally strong or temporarily inflated
whether the company is becoming more financially efficient over time

Compare the company financially against top competitors on:
margins
ROE
ROCE
debt
valuation
free cash flow
growth efficiency

Include:
1. Biggest strengths in the financials
2. Biggest red flags in the financials
3. Whether the balance sheet can survive a recession
4. Whether the company can self-fund future growth
5. Most important financial metrics investors should monitor every quarter
6. Whether the business deserves premium valuation multiples based on fundamentals

Think like a forensic investor looking for both hidden strengths and hidden risks. Focus on financial durability, earnings quality, capital efficiency, and long-term shareholder value creation rather than only headline growth numbers.
"""),

    "catalysts_agent.py": ("CatalystsAgent", """Act like a forward-looking institutional growth investor analyzing future earnings expansion, scalability, industry tailwinds, and long-term market opportunities.

Perform a deep growth catalyst and future outlook analysis of {symbol}.

Here is the raw financial data to assist your analysis:
Company Profile: {profile}
Recent Income Statements: {income_statement}

Focus on identifying what can realistically drive revenue, profit, market share, and valuation growth over the next 1-10 years.

Analyze in detail:
the company’s future growth drivers
upcoming business catalysts over the next 12-24 months
expansion opportunities across products, geographies, and customer segments
industry tailwinds supporting long-term growth
total addressable market (TAM) and market opportunity size
scalability potential of the business model
management expansion strategy
future margin expansion opportunities
operating leverage potential
innovation pipeline and R&D strength
new product launches or capacity expansions
strategic partnerships, acquisitions, or contracts
export opportunities
regulatory or policy tailwinds
technological trends benefiting the company
whether growth is secular, cyclical, or temporary

Deeply evaluate:
whether the company can sustain high growth rates
what factors can accelerate earnings growth
whether growth quality is improving or deteriorating
whether management guidance is realistic or aggressive
future competitive threats to growth
whether growth requires heavy capital investment
whether future growth can improve return ratios

Include:
1. Short-term catalysts (next 1-2 years)
2. Medium-term catalysts (3-5 years)
3. Long-term structural growth opportunities
4. Biggest risks to future growth
5. Most underestimated future opportunity for the business
6. Whether current valuation already prices in future growth expectations
7. What must happen operationally for the company to become significantly larger over the next decade

Also provide:
Bull case growth scenario
Base case growth scenario
Bear case growth scenario

Estimate how scalable the company can realistically become relative to:
industry size
competitors
operational capacity
market demand
capital availability

Think independently like a hedge fund growth analyst. Focus on future earnings power, scalability, industry evolution, and asymmetric upside opportunities instead of only repeating management commentary.
"""),

    "valuation_agent.py": ("ValuationAgent", """Act like a hedge fund portfolio manager and elite valuation expert focused on asymmetric risk-reward opportunities, downside protection, intrinsic value, and long-term capital compounding.

Perform a deep valuation, risk, and asymmetry analysis of {symbol}.

Here is the raw financial data to assist your analysis:
Company Profile: {profile}
Recent Income Statements: {income_statement}

Determine whether the stock is overvalued, fairly valued, or undervalued based on both current fundamentals and future earnings potential.

Analyze in detail:
current valuation multiples (PE, PB, EV/EBITDA, PS, PEG, FCF yield)
historical valuation ranges
valuation versus competitors
valuation versus industry averages
whether the company deserves premium or discounted multiples
intrinsic value assumptions
free cash flow generation capability
expected earnings growth versus valuation
margin of safety at current price
market expectations already priced into the stock
probability of multiple expansion or compression

Deeply evaluate downside risk:
valuation floor during pessimistic scenarios
balance sheet downside protection
asset value support
recession or industry slowdown impact
downside if growth disappoints
risk from competition, regulation, technology disruption, or execution failure
liquidity and debt-related risks
cyclicality risks
governance or management risks

Deeply evaluate upside potential:
maximum realistic earnings expansion
scalability of profits and cash flows
TAM expansion opportunities
operating leverage impact
potential market share gains
future rerating potential
long-term compounding ability

Construct:
1. Bull case valuation scenario
2. Base case valuation scenario
3. Bear case valuation scenario

For each scenario estimate:
possible revenue growth
margin assumptions
earnings growth
valuation multiple assumptions
expected stock upside/downside

Also answer:
What assumptions does the market currently believe?
Which assumptions are most likely wrong?
What events could permanently damage the investment thesis?
What events could create outsized upside?
Is the risk-reward asymmetry favorable today?
Is this a potential compounder, cyclical trade, turnaround, or speculative bet?
Does the stock offer enough upside relative to the downside risk?

Finally conclude with:
Investment thesis summary
Key reasons to own the stock
Key reasons to avoid the stock
Probability-weighted outlook
Whether the stock currently represents an attractive long-term investment opportunity

Think independently like a concentrated portfolio manager allocating real capital. Focus on asymmetric outcomes, valuation discipline, downside protection, and long-term expected returns rather than only optimistic growth narratives.
"""),

    "technical_agent.py": ("TechnicalAgent", """Act like a professional market technician and institutional trader specializing in price action, trend structure, momentum analysis, volume behavior, and market psychology.

Perform a deep technical analysis of {symbol}.

Here is the raw financial data to assist your analysis:
Company Profile: {profile}

Analyze the stock across short-term, medium-term, and long-term timeframes using price action, volume, momentum, and trend structure.

Cover in detail:
primary trend (bullish, bearish, sideways)
long-term trend strength
short-term momentum
support and resistance zones
breakout and breakdown levels
trendline structure
moving averages (20 DMA, 50 DMA, 100 DMA, 200 DMA)
price relative to major moving averages
volume behavior and accumulation/distribution patterns
institutional buying or selling signals
volatility structure
relative strength versus sector and index
RSI analysis
MACD analysis
momentum divergence signals
consolidation patterns
chart patterns (flags, triangles, cup & handle, double top/bottom, etc.)
gap analysis
liquidity and trading behavior

Deeply evaluate:
whether smart money appears to be accumulating or distributing
whether current price action confirms or contradicts fundamentals
whether momentum is strengthening or weakening
probability of trend continuation versus reversal
whether recent rallies are sustainable or speculative
key levels where market sentiment could change

Identify:
1. Strong support zones
2. Major resistance zones
3. High-probability breakout levels
4. Risky breakdown levels
5. Optimal risk-reward entry zones
6. Short-term swing trading setup
7. Long-term investor accumulation zones

Also analyze:
delivery volume trends
FII/DII participation if visible
options chain positioning (if relevant)
open interest buildup
sector momentum
correlation with index movement

Include:
Bullish technical scenario
Neutral technical scenario
Bearish technical scenario

Estimate:
probable short-term direction
medium-term trend strength
risk-reward setup at current price
whether the stock is overheated, undervalued technically, or in accumulation phase

Conclude with:
overall technical bias
trend conviction level
best strategy for traders
best strategy for long-term investors
invalidation levels where the thesis changes

Think like a professional trader managing institutional capital. Focus on probability, market structure, risk management, liquidity behavior, and psychology rather than random indicators alone.
"""),

    "management_agent.py": ("ManagementAgent", """Act like a forensic corporate governance analyst and long-term institutional investor evaluating management integrity, execution capability, capital allocation skill, and shareholder alignment.

Perform a deep management quality and corporate governance analysis of {symbol}.

Here is the raw financial data to assist your analysis:
Company Profile: {profile}

Analyze management not just from presentations and interviews, but from historical actions, financial decisions, execution track record, and treatment of minority shareholders.

Evaluate in detail:
promoter background and reputation
management credibility and integrity
execution capability over the last 5-10 years
strategic decision-making quality
capital allocation efficiency
shareholder friendliness
transparency in communication
consistency between promises and execution
governance standards
board quality and independence
succession planning
compensation structure
insider ownership and alignment
promoter holding trends
promoter pledging trends
related party transactions
acquisition history and effectiveness
buyback/dividend discipline
accounting conservatism or aggressiveness

Deeply investigate:
whether management creates long-term shareholder value
whether management prioritizes empire building over returns
whether management overpromises growth
whether earnings quality appears manipulated
whether acquisitions destroy or create value
whether management behaves prudently during downturns
whether management has handled crises effectively

Analyze management communication:
earnings calls
annual letters
investor presentations
public interviews

Determine:
whether management is genuinely competent or simply benefiting from industry tailwinds
whether execution quality is improving or deteriorating
whether leadership has a clear long-term vision
whether incentives are aligned with shareholders

Include:
1. Biggest strengths of management
2. Biggest governance red flags
3. Most important historical decisions management got right
4. Biggest mistakes management made
5. Whether management deserves investor trust
6. Whether the company is promoter-driven or professionally managed
7. Whether governance quality deserves a valuation premium or discount

Also evaluate:
auditor history and resignations
regulatory actions or controversies
litigation risks
pledge-related risks
dilution history
ESG or compliance concerns if material

Finally conclude with:
overall management quality rating
governance quality rating
confidence level in long-term execution
probability that management can successfully scale the business over the next decade

Think independently like a forensic investor protecting capital from hidden governance risks. Focus on behavior, incentives, accountability, and capital allocation rather than management marketing language alone.
"""),

    "industry_agent.py": ("IndustryAgent", """Act like a macro-aware sector strategist and institutional equity analyst specializing in industry cycles, market structure, economic trends, and long-term sector evolution.

Perform a deep industry and macroeconomic analysis of the sector in which {symbol} operates.

Here is the raw financial data to assist your analysis:
Company Profile: {profile}

Analyze the industry from both a business and investment perspective.

Cover in detail:
overall industry structure
industry size and future growth potential
historical industry growth trends
current stage of the industry cycle
fragmentation vs consolidation
key industry participants
profit pool distribution across the value chain
barriers to entry
pricing dynamics
supply-demand balance
industry margin structure
cyclical vs secular characteristics
export/import dynamics
technological disruption risks
regulatory environment
government policy impact
environmental or geopolitical risks

Deeply evaluate:
whether the industry is becoming more attractive or less attractive
whether the sector has long-term structural tailwinds
whether current industry profitability is sustainable
whether the industry is overearning or underearning
how sensitive the sector is to:
interest rates
inflation
GDP growth
commodity prices
currency fluctuations
consumer demand
global economic conditions

Compare the company’s positioning relative to the broader industry:
market share trajectory
cost structure advantage
margin leadership
innovation leadership
operational efficiency
scalability potential

Identify:
1. Biggest industry tailwinds
2. Biggest industry headwinds
3. Long-term secular trends benefiting the sector
4. Major risks that could structurally weaken the industry
5. Whether the industry is likely to consolidate further
6. Which players are most likely to dominate over the next decade

Analyze future industry evolution:
AI impact
automation impact
regulatory changes
changing consumer behavior
global competition
supply chain shifts
localization/globalization trends

Also include:
Bull case for the sector
Base case for the sector
Bear case for the sector

Estimate:
expected industry CAGR over next 5-10 years
future margin trends
capital intensity trends
likely winners and losers

Finally conclude:
whether this is an attractive industry for long-term investing
whether the company is positioned better or worse than peers
whether sector tailwinds are temporary or structural
whether investors are underestimating or overestimating the sector opportunity

Think independently like a top-down institutional strategist combining macroeconomics, industry structure, and business quality analysis to identify durable long-term opportunities.
"""),

    "sentiment_agent.py": ("SentimentAgent", """Act like a hedge fund sentiment analyst and market psychology expert specializing in institutional positioning, investor expectations, narrative cycles, and behavioral finance.

Perform a deep sentiment and market positioning analysis of {symbol}.

Here is the raw financial data to assist your analysis:
Company Profile: {profile}

Analyze how the market currently perceives the company and whether investor expectations are too optimistic, too pessimistic, or mispriced relative to fundamentals.

Cover in detail:
current market narrative around the stock
institutional sentiment
retail investor sentiment
analyst consensus expectations
media perception
social media sentiment
momentum-driven narratives
contrarian indicators
market positioning risks
ownership concentration
FII/DII positioning trends
mutual fund ownership trends
insider buying/selling trends
short interest or bearish positioning if available

Deeply evaluate:
what assumptions are currently priced into the stock
whether expectations are realistic or excessive
whether the market is underestimating risks
whether the market is ignoring hidden strengths
whether sentiment is driven by fundamentals or speculation
whether the stock is crowded or underowned
whether market psychology is near euphoria, pessimism, or apathy

Analyze:
earnings reaction behavior
reaction to guidance changes
sensitivity to macro news
volatility during corrections
historical rerating and derating cycles
narrative shifts over time

Identify:
1. Current dominant market narrative
2. Most important market misconception
3. Key sentiment risks
4. Contrarian opportunities
5. What could rapidly change market perception
6. Whether expectations are easy or difficult to beat

Also analyze:
valuation sentiment versus historical averages
options market positioning if relevant
institutional accumulation/distribution behavior
delivery volume trends
speculative activity vs long-term ownership

Construct:
Bullish sentiment scenario
Neutral sentiment scenario
Bearish sentiment scenario

Explain:
what events could trigger rerating
what events could trigger panic selling
whether the stock behaves like:
a momentum stock
quality compounder
speculative narrative play
cyclical recovery play
turnaround story

Finally conclude:
whether current sentiment is supportive or dangerous
whether the market is overconfident or overly fearful
whether the stock offers a contrarian opportunity
how sentiment interacts with fundamentals and valuation

Think independently like a professional investor studying crowd psychology, positioning imbalances, and expectation gaps to identify asymmetric investment opportunities before the broader market realizes them.
""")
}

template = """import json
from app.agents.base_agent import BaseResearchAgent
from app.services.fmp_client import get_company_profile, get_income_statement
from sqlalchemy.orm import Session
import asyncio

class {class_name}(BaseResearchAgent):
    
    async def fetch_data(self, symbol: str, db: Session) -> dict:
        profile, income_stmt = await asyncio.gather(
            get_company_profile(symbol, db),
            get_income_statement(symbol, db)
        )
        recent_income = income_stmt[:3] if income_stmt and isinstance(income_stmt, list) else []
        return {{
            "profile": json.dumps(profile[0] if profile else {{}}),
            "income_statement": json.dumps(recent_income)
        }}

    def get_prompt_template(self) -> str:
        return \"\"\"{prompt}\"\"\"
"""

for filename, (class_name, prompt) in agents.items():
    file_path = os.path.join(base_path, filename)
    content = template.format(class_name=class_name, prompt=prompt)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Agents generated successfully.")
