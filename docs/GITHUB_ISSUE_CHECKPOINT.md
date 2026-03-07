# TypeError: string indices must be integers, not 'str' in checkpoint retrieval

## Description

When using `langgraph-checkpoint-surrealdb` v2.0.0 with SurrealDB 2.1.x, checkpoint retrieval fails with a `TypeError` indicating that the checkpoint adapter receives a string response from SurrealDB when it expects a dictionary.

## Error Details

**Error Message:**
```
TypeError: string indices must be integers, not 'str'
File: langgraph_checkpoint_surrealdb/__init__.py:705
thread_id = result_dict["thread_id"]
```

**Location:** `langgraph_checkpoint_surrealdb/__init__.py:705`

**Stack Trace:**
```
File "backend/app/api/routes_ask.py", line 107, in ask
    final_state = await graph.ainvoke(initial_state, config=config)
File "langgraph/graph/graph.py", line ...
    ...
File "langgraph_checkpoint_surrealdb/__init__.py", line 705
    thread_id = result_dict["thread_id"]
TypeError: string indices must be integers, not 'str'
```

## Environment

- **Python Version:** 3.x
- **langgraph-checkpoint-surrealdb Version:** 2.0.0
- **SurrealDB Version:** 2.1.x
- **LangGraph Version:** >=0.2.69
- **langchain-core Version:** >=0.3.33

## Reproduction Steps

1. Install dependencies:
   ```bash
   pip install langgraph-checkpoint-surrealdb>=2.0.0 surrealdb>=1.0.0
   ```

2. Initialize SurrealSaver checkpointer:
   ```python
   from langgraph_checkpoint_surrealdb import SurrealSaver
   
   checkpointer = SurrealSaver(
       url="ws://localhost:8000/rpc",
       user="root",
       password="root",
       namespace="researchgraph",
       database="main",
   )
   ```

3. Create a LangGraph with checkpointing:
   ```python
   from langgraph.graph import StateGraph
   
   graph = StateGraph(...)
   compiled_graph = graph.compile(checkpointer=checkpointer)
   ```

4. Invoke the graph with a config containing `thread_id`:
   ```python
   config = {"configurable": {"thread_id": "session:123"}}
   result = await compiled_graph.ainvoke(initial_state, config=config)
   ```

5. The error occurs during checkpoint retrieval.

## Expected Behavior

The checkpoint adapter should successfully retrieve checkpoint data from SurrealDB as a dictionary and extract the `thread_id` field.

## Actual Behavior

The checkpoint adapter receives a string response from SurrealDB instead of a dictionary, causing the `TypeError` when trying to access `result_dict["thread_id"]`.

## Investigation

- ✅ Verified using latest version (2.0.0)
- ✅ Cleared all checkpoint data from SurrealDB (`DELETE checkpoint WHERE true;`, `DELETE checkpoint_blob WHERE true;`)
- ✅ Restarted services
- ❌ Error still occurs - indicates upstream library bug

## Workaround

As a temporary workaround, checkpointing can be disabled by modifying `get_checkpointer()` to return `None` when checkpointing is disabled:

```python
def get_checkpointer() -> Optional[SurrealSaver]:
    if not settings.enable_checkpointing:
        return None
    # ... rest of initialization
```

**Note:** This workaround disables state persistence across sessions but allows the agent to function.

## Additional Context

- The error occurs specifically during checkpoint retrieval, not during checkpoint creation
- SurrealDB queries return data in a specific format that may need deserialization
- The checkpoint adapter may need to handle SurrealDB's response format differently

## Related

- SurrealDB 2.1.x may have changed response format
- Checkpoint data structure in SurrealDB may need verification
