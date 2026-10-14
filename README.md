# Multi-Tool AI Agent for Bangladesh

A **Google Colab-compatible** LangChain `AgentExecutor` that routes natural-language questions to three read-only SQLite datasets or Tavily web search.

## Capabilities

| Question type | Tool | Data source |
| --- | --- | --- |
| Educational institute names, counts, districts, MPO | `InstitutionsDBTool` | `institutions.db` |
| Healthcare facility names, counts, locations, agency | `HospitalsDBTool` | `hospitals.db` |
| Restaurant names, ratings, addresses, review counts | `RestaurantsDBTool` | `restaurants.db` |
| Definitions, government policy, DGHS role, general knowledge | `WebSearchTool` | Tavily web search |

## Original datasets

- [Institutional Information of Bangladesh](https://huggingface.co/datasets/Mahadih534/Institutional-Information-of-Bangladesh)
- [All Bangladeshi Hospitals](https://huggingface.co/datasets/Mahadih534/all-bangladeshi-hospitals)
- [Bangladeshi Restaurant Data](https://huggingface.co/datasets/Mahadih534/Bangladeshi-Restaurant-Data)

Dataset records are third-party and may be outdated, incomplete, or include categories beyond the dataset title. The hospitals dataset does **not** provide verified numbers of beds, doctors, or specific treatment facilities. The restaurant dataset does **not** supply a verified cuisine column. Never infer those missing values.

## Quick start in Google Colab

1. Create a new Google Colab notebook, upload the repository ZIP to `/content/`, and unzip it, **or** clone your GitHub repository after publishing it.
2. Change directory into the extracted repository:
   ```python
   %cd /content/bangladesh-multitool-agent
   ```
3. Install dependencies with Colab's Pandas compatibility preserved:
   ```python
   %pip install -q -r requirements.txt
   %pip check
   ```
   If the installed runtime's packages are inconsistent, repair only the reported conflicts; restart the runtime after significant installs. Pandas is pinned at 2.2.3 for the Colab environment used for the assignment.
4. In the Colab **Secrets** panel, add `OPENAI_API_KEY` and `TAVILY_API_KEY`. Enable notebook access. The OpenAI API may incur charges; Tavily has its own usage limits.
5. Generate the databases (internet connection required):
   ```python
   !python -m src.build_databases --data-dir data
   ```
6. Load secrets and launch the executor:
   ```python
   import os
   from google.colab import userdata
   os.environ["OPENAI_API_KEY"] = userdata.get("OPENAI_API_KEY")
   os.environ["TAVILY_API_KEY"] = userdata.get("TAVILY_API_KEY")
   from src.agent import create_executor
   agent_executor = create_executor()
   result = agent_executor.invoke({"input": "How many healthcare facilities are in Dhaka district?"})
   print(result["output"])
   print([action.tool for action, _ in result["intermediate_steps"]])
   ```
7. Run the bundled `Bangladesh_MultiTool_Agent.ipynb` for a guided demo.

**No local GPU, XAMPP, MySQL server, or Docker is needed.** SQLite works as a file-based database.

## Example queries

### Dataset questions (must use the corresponding DB tool)

- How many healthcare facilities are listed in Dhaka district? → `HospitalsDBTool`
- List five hospitals in Sylhet district. → `HospitalsDBTool`
- Count educational institutions in Rajshahi district. → `InstitutionsDBTool`
- Find institutions whose names contain “College” in Dhaka. → `InstitutionsDBTool`
- Show five restaurants in Dhaka with the highest recorded ratings, excluding unrated entries. → `RestaurantsDBTool`
- Count restaurant records with rating at least 4.0. → `RestaurantsDBTool`

### General knowledge (must use web search)

- What is the role of DGHS in Bangladesh? → `WebSearchTool`
- Explain the National Health Policy 2011 in Bangladesh. → `WebSearchTool`
- What is MPO in the Bangladesh education system? → `WebSearchTool`
- What is the difference between a hospital and a community clinic? → `WebSearchTool`

### Multi-tool or unsupported-data questions

- Explain MPO, then count institutions in Dhaka district with MPO status. → `WebSearchTool` + `InstitutionsDBTool` (if source column exists)
- How many beds are in each Dhaka hospital? → **Not answerable from the supplied DB**. Explain the data limitation; web search may provide independently sourced figures for specific hospitals, but should not be presented as a complete DB result.
- Which restaurants in Chattogram serve Italian cuisine? → Cuisine is not a verified dataset field. Seek independent sources, clearly label them, or state the limitation.
- What is Bangladesh's healthcare policy *today*? → Web search, prefer official publications; distinguish current changes from historical policy documents.

## Internal architecture

```
User question
    ↓
LLM selects tool / writes restricted SQLite SELECT or web query
    ↓
AgentExecutor dispatches call
    ├─ InstitutionsDBTool → institutions.db
    ├─ HospitalsDBTool    → hospitals.db
    ├─ RestaurantsDBTool  → restaurants.db
    └─ WebSearchTool      → Tavily API
    ↓
Tool results returned to LLM → evidence-grounded answer
```

The execution trace (`intermediate_steps`) records which tools the agent selected. This provides *routing evidence*, not a guarantee that the final answer is factually correct.

## Testing

Run offline tests:

```python
!python -m unittest discover -s tests -v
```

Inspect source columns after database generation:

```python
import sqlite3
for table in ["institutions", "hospitals", "restaurants"]:
    with sqlite3.connect(f"data/{table}.db") as db:
        print(table, db.execute(f'PRAGMA table_info("{table}")').fetchall())
```

## Security and limitations

- API keys come from Colab Secrets; **never commit them to GitHub**.
- SQLite database files are opened in read-only mode. Tool code allows only a restricted single `SELECT`, with an authorizer, row cap, and query-progress limit.
- SQL generated by a language model can still be inefficient or semantically incorrect. Review queries and add a stricter allowlist for production.
- Missing values and dataset coverage must be represented faithfully; no hallucinated beds, doctors, cuisines, or live restaurant availability.
- User requests that require live information should rely on up-to-date sources and citations.
- A public Colab link can be provided **after** uploading this notebook to GitHub or Google Drive; no public link is pre-created here.

## License / attribution

This educational scaffold is supplied for assignment use. Review the individual Hugging Face dataset cards for their licenses and redistribution permissions before publicly distributing raw data.
