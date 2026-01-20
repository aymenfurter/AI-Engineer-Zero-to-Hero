"""
Display helpers for Lab 16: Azure AI Evaluation
Provides formatted display functions for evaluation results
"""
import pandas as pd
from IPython.display import display, Markdown, HTML


def display_metrics_summary(metrics: dict):
    """Display aggregate metrics in a nicely formatted table."""
    display(Markdown("### 📊 Aggregate Metrics Summary"))
    
    # Group metrics by category
    quality_metrics = {}
    rag_metrics = {}
    custom_metrics = {}
    
    for key, value in metrics.items():
        if value is None:
            continue
        # Extract base metric name
        base_name = key.split('.')[0] if '.' in key else key
        
        if base_name in ['coherence', 'fluency', 'relevance']:
            quality_metrics[key] = value
        elif base_name in ['groundedness', 'similarity', 'f1_score', 'bleu_score']:
            rag_metrics[key] = value
        else:
            custom_metrics[key] = value
    
    # Display quality metrics
    if quality_metrics:
        display(Markdown("#### Quality Metrics"))
        df_quality = pd.DataFrame([
            {'Metric': k, 'Score': f"{v:.2f}" if isinstance(v, (int, float)) else v}
            for k, v in quality_metrics.items()
        ])
        display(df_quality.style.hide(axis='index'))
    
    # Display RAG metrics
    if rag_metrics:
        display(Markdown("#### RAG & Similarity Metrics"))
        df_rag = pd.DataFrame([
            {'Metric': k, 'Score': f"{v:.2f}" if isinstance(v, (int, float)) else v}
            for k, v in rag_metrics.items()
        ])
        display(df_rag.style.hide(axis='index'))
    
    # Display custom metrics
    if custom_metrics:
        display(Markdown("#### Custom Metrics"))
        df_custom = pd.DataFrame([
            {'Metric': k, 'Score': f"{v:.2f}" if isinstance(v, (int, float)) else v}
            for k, v in custom_metrics.items()
        ])
        display(df_custom.style.hide(axis='index'))


def display_row_results(rows: list):
    """Display row-level evaluation results."""
    display(Markdown("### 📋 Row-Level Results"))
    
    if not rows:
        print("No row results available")
        return
    
    # Extract key columns for display
    display_data = []
    for i, row in enumerate(rows):
        entry = {'#': i + 1}
        
        # Get query (truncated)
        query = row.get('inputs.query', '')
        entry['Query'] = query[:40] + '...' if len(query) > 40 else query
        
        # Get key scores
        entry['Coherence'] = row.get('outputs.coherence.coherence', 'N/A')
        entry['Fluency'] = row.get('outputs.fluency.fluency', 'N/A')
        entry['Relevance'] = row.get('outputs.relevance.relevance', 'N/A')
        entry['Groundedness'] = row.get('outputs.groundedness.groundedness', 'N/A')
        entry['Similarity'] = row.get('outputs.similarity.similarity', 'N/A')
        
        display_data.append(entry)
    
    df = pd.DataFrame(display_data)
    
    # Style the dataframe (dark mode optimized)
    def highlight_scores(val):
        if isinstance(val, (int, float)):
            if val >= 4:
                return 'background-color: #2e7d32; color: #e8f5e9'  # Dark green bg, light text
            elif val >= 3:
                return 'background-color: #f9a825; color: #1a1a1a'  # Amber bg, dark text
            else:
                return 'background-color: #c62828; color: #ffebee'  # Dark red bg, light text
        return ''
    
    score_columns = ['Coherence', 'Fluency', 'Relevance', 'Groundedness', 'Similarity']
    styled_df = df.style.applymap(highlight_scores, subset=score_columns).hide(axis='index')
    display(styled_df)


def analyze_evaluation_results(result: dict):
    """Provide detailed analysis and recommendations based on evaluation results."""
    display(Markdown("### 🔍 Evaluation Analysis"))
    
    metrics = result.get('metrics', {})
    rows = result.get('rows', [])
    
    # Calculate pass rates
    analysis = []
    
    # Check quality scores
    coherence_avg = metrics.get('coherence.coherence', 0)
    if coherence_avg:
        status = "✅ Good" if coherence_avg >= 4 else "⚠️ Needs improvement" if coherence_avg >= 3 else "❌ Poor"
        analysis.append(f"**Coherence:** {coherence_avg:.2f}/5 - {status}")
    
    fluency_avg = metrics.get('fluency.fluency', 0)
    if fluency_avg:
        status = "✅ Good" if fluency_avg >= 4 else "⚠️ Needs improvement" if fluency_avg >= 3 else "❌ Poor"
        analysis.append(f"**Fluency:** {fluency_avg:.2f}/5 - {status}")
    
    relevance_avg = metrics.get('relevance.relevance', 0)
    if relevance_avg:
        status = "✅ Good" if relevance_avg >= 4 else "⚠️ Needs improvement" if relevance_avg >= 3 else "❌ Poor"
        analysis.append(f"**Relevance:** {relevance_avg:.2f}/5 - {status}")
    
    groundedness_avg = metrics.get('groundedness.groundedness', 0)
    if groundedness_avg:
        status = "✅ Good" if groundedness_avg >= 4 else "⚠️ Needs improvement" if groundedness_avg >= 3 else "❌ Poor"
        analysis.append(f"**Groundedness:** {groundedness_avg:.2f}/5 - {status}")
    
    similarity_avg = metrics.get('similarity.similarity', 0)
    if similarity_avg:
        status = "✅ Good" if similarity_avg >= 4 else "⚠️ Needs improvement" if similarity_avg >= 3 else "❌ Poor"
        analysis.append(f"**Similarity:** {similarity_avg:.2f}/5 - {status}")
    
    display(Markdown("#### Score Summary\n" + "\n".join(analysis)))
    
    # Recommendations
    recommendations = []
    
    if coherence_avg and coherence_avg < 4:
        recommendations.append("- Improve response structure and logical flow")
    
    if fluency_avg and fluency_avg < 4:
        recommendations.append("- Work on natural language generation quality")
    
    if relevance_avg and relevance_avg < 4:
        recommendations.append("- Ensure responses directly address the query")
    
    if groundedness_avg and groundedness_avg < 4:
        recommendations.append("- Reduce hallucinations by improving retrieval or adding guardrails")
    
    if similarity_avg and similarity_avg < 3:
        recommendations.append("- Responses diverge significantly from expected answers - review knowledge base")
    
    if recommendations:
        display(Markdown("#### 💡 Recommendations\n" + "\n".join(recommendations)))
    else:
        display(Markdown("#### ✅ All metrics look good! Your agent is performing well."))
    
    # Identify lowest scoring queries
    if rows:
        display(Markdown("#### ⚠️ Queries with Lowest Scores"))
        
        lowest_scores = []
        for i, row in enumerate(rows):
            avg_score = 0
            count = 0
            for key in ['outputs.coherence.coherence', 'outputs.relevance.relevance', 'outputs.groundedness.groundedness']:
                if key in row and isinstance(row[key], (int, float)):
                    avg_score += row[key]
                    count += 1
            
            if count > 0:
                lowest_scores.append({
                    'index': i,
                    'query': row.get('inputs.query', '')[:50],
                    'avg_score': avg_score / count
                })
        
        # Sort by average score and show bottom 3
        lowest_scores.sort(key=lambda x: x['avg_score'])
        for item in lowest_scores[:3]:
            display(Markdown(f"- Query {item['index']+1}: \"{item['query']}...\" (avg: {item['avg_score']:.2f})"))


def format_score(score, max_score=5):
    """Format a score with visual indicator."""
    if score is None or not isinstance(score, (int, float)):
        return "N/A"
    
    pct = score / max_score
    if pct >= 0.8:
        return f"🟢 {score:.1f}"
    elif pct >= 0.6:
        return f"🟡 {score:.1f}"
    else:
        return f"🔴 {score:.1f}"


def display_comparison_table(results: dict):
    """Display comparison of multiple evaluation runs."""
    display(Markdown("### 📈 Evaluation Comparison"))
    
    df_data = []
    for run_name, run_metrics in results.items():
        entry = {'Run': run_name}
        entry['Coherence'] = run_metrics.get('coherence.coherence', 'N/A')
        entry['Fluency'] = run_metrics.get('fluency.fluency', 'N/A')
        entry['Relevance'] = run_metrics.get('relevance.relevance', 'N/A')
        entry['Groundedness'] = run_metrics.get('groundedness.groundedness', 'N/A')
        df_data.append(entry)
    
    df = pd.DataFrame(df_data)
    display(df.style.hide(axis='index'))
