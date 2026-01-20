"""
Display helpers for Lab 6: Foundry IQ
"""
import pandas as pd
from IPython.display import display, Markdown, HTML


def show_config(title: str, data: dict):
    """Display a configuration table."""
    df = pd.DataFrame({'Setting': list(data.keys()), 'Value': list(data.values())})
    display(Markdown(f'### {title}'))
    display(df.style.hide(axis='index'))


def show_sources(sources: list):
    """Display knowledge sources as a table."""
    if not sources:
        print("No sources found")
        return
    
    df = pd.DataFrame([{
        'Name': s.get('name', ''),
        'Kind': s.get('kind', ''),
        'Status': '✅ Ready' if s.get('status') == 'ready' else '⏳ Indexing'
    } for s in sources])
    
    display(Markdown('### 📚 Knowledge Sources'))
    display(df.style.hide(axis='index'))


def show_query_result(query: str, result: dict):
    """Display a knowledge base query result nicely."""
    display(Markdown(f'**Query:** *"{query}"*'))
    display(Markdown('---'))
    
    # Extract the response text
    if 'response' in result and result['response']:
        content = result['response'][0].get('content', [])
        if content:
            answer = content[0].get('text', 'No response')
            display(Markdown(f'**Answer:**\n\n{answer}'))
    elif 'error' in result:
        display(Markdown(f'❌ **Error:** {result["error"]}'))
    
    # Show references if present
    refs = result.get('references', [])
    if refs:
        display(Markdown(f'\n**📖 References:** {len(refs)} source(s) used'))


def show_agent_response(query: str, response_text: str):
    """Display an agent's response with formatting."""
    display(Markdown(f'''
---
**🙋 You:** {query}

**🤖 Agent:** {response_text}
'''))


def show_success(message: str):
    """Display a success message."""
    display(Markdown(f'### ✅ {message}'))


def show_error(message: str):
    """Display an error message."""
    display(Markdown(f'### ❌ Error\n```\n{message}\n```'))


def show_step(number: int, title: str, description: str = ""):
    """Display a step header."""
    desc = f"\n{description}" if description else ""
    display(Markdown(f'## Step {number}: {title}{desc}'))
