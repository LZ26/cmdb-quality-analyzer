import streamlit as st
import pandas as pd
from core.data_loader import CMDBDataLoader
from core.quality_analyzer import CMDBQualityAnalyzer
from core.ai_insights import AIInsightsEngine
import plotly.graph_objects as go
import plotly.express as px
import os
import time

# Page config
st.set_page_config(
    page_title="CMDB Quality Analyzer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Clean, professional CSS
st.markdown("""
<style>
    /* Import professional font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    /* Responsive typography */
    .main-header {
        font-size: clamp(1.75rem, 4vw, 2.25rem);
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 0.5rem;
    }
    
    .sub-header {
        font-size: clamp(0.95rem, 2vw, 1.1rem);
        color: #64748b;
        margin-bottom: 2rem;
    }
    
    /* Mobile responsiveness */
    @media (max-width: 768px) {
        .stTabs [data-baseweb="tab-list"] {
            flex-wrap: wrap;
        }
        
        .stTabs [data-baseweb="tab"] {
            flex: 1 1 45%;
            font-size: 0.9rem;
        }
    }
    
    /* Clean tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 12px 20px;
        background-color: #f8fafc;
        border-radius: 8px;
        color: #475569;
        font-weight: 500;
        border: 1px solid #e2e8f0;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #2563eb;
        color: white;
        border-color: #2563eb;
    }
    
    /* Better info boxes */
    .stAlert {
        border-radius: 8px;
    }
    
    /* Download button */
    .stDownloadButton button {
        background-color: #2563eb;
        color: white;
        border-radius: 8px;
        padding: 0.75rem;
        font-weight: 500;
        border: none;
    }
    
    .stDownloadButton button:hover {
        background-color: #1d4ed8;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<p class="main-header">🔍 CMDB Data Quality Analyzer</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Automated duplicate detection and data quality analysis for ServiceNow CMDB</p>', unsafe_allow_html=True)

# Info banner
st.info("💡 **Quick Start:** Navigate through tabs to explore data quality insights, duplicate detection results, and AI-powered recommendations.")

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    
    api_key_exists = bool(os.getenv('ANTHROPIC_API_KEY'))
    
    if not api_key_exists:
        demo_mode = True
        st.info("Demo mode enabled (No API key)")
    else:
        # Read from Streamlit secrets (deployed) or .env (local)
        demo_mode_env = st.secrets.get("DEMO_MODE", os.getenv('DEMO_MODE', 'true')).lower()
        default_demo = demo_mode_env in ['true', '1', 'yes']
        
        # Show current mode
        if default_demo:
            st.warning("Running in Demo Mode")
        else:
            st.success("Live AI Mode Active")
        
        demo_mode = st.checkbox("Demo Mode (No API)", value=default_demo, 
                            help="Toggle between live AI and demo mode")
    
    similarity_threshold = st.slider(
        "Fuzzy Match Threshold (%)",
        min_value=70,
        max_value=100,
        value=85,
        help="Minimum similarity percentage for fuzzy duplicate detection"
    )
    
    st.divider()
    
    st.markdown("### 📊 Detection Methods")
    st.markdown("""
    - **Exact IP Matching** - Identifies CIs with identical IP addresses
    - **Normalized Name Matching** - Detects naming variations (hyphens, underscores, case)
    - **Fuzzy Similarity** - Finds similar names using Levenshtein distance
    """)
    
    st.divider()
    
    st.caption("Built by Laziz • February 2026")

# Load data
@st.cache_data(ttl=300)
def load_data():
    try:
        loader = CMDBDataLoader(data_dir='data')
        df = loader.load_all_sources()
        
        if df is None or len(df) == 0:
            st.error("⚠️ No data found. Please check the data directory.")
            return None
        
        required_cols = ['ci_name', 'ip_address', 'ci_type', 'source']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            st.error(f"⚠️ Missing required columns: {', '.join(missing_cols)}")
            return None
        
        return df
    except Exception as e:
        st.error(f"❌ Error loading data: {str(e)}")
        return None

@st.cache_resource
def get_analyzer(threshold):
    return CMDBQualityAnalyzer(similarity_threshold=threshold)

def get_ai_engine(demo_mode):
    """Don't cache - recreate each time to respect mode changes"""
    return AIInsightsEngine(demo_mode=demo_mode)

with st.spinner("Loading CMDB data..."):
    df = load_data()

if df is None:
    st.stop()

analyzer = get_analyzer(similarity_threshold)
ai_engine = get_ai_engine(demo_mode)

# Run analysis
@st.cache_data(ttl=300)
def run_analysis(_df, threshold):
    try:
        analyzer = CMDBQualityAnalyzer(similarity_threshold=threshold)
        duplicate_analysis = analyzer.analyze_duplicates(_df)
        quality_scores = analyzer.score_data_quality(_df)
        return duplicate_analysis, quality_scores, None
    except Exception as e:
        return None, None, str(e)

with st.spinner("Analyzing data quality..."):
    duplicate_analysis, quality_scores, error = run_analysis(df, similarity_threshold)

if error:
    st.error(f"❌ Analysis failed: {error}")
    st.stop()

if duplicate_analysis is None or quality_scores is None:
    st.error("❌ Analysis incomplete. Please try again.")
    st.stop()

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Overview", 
    "🔍 Duplicate Detection", 
    "🤖 AI Insights",
    "📈 Data Quality"
])

# TAB 1: Overview
with tab1:
    st.markdown("### Key Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    duplicate_count = duplicate_analysis.get('total_duplicate_records', 0)
    completeness = quality_scores.get('completeness', {}).get('overall_score', 0)
    consistency = quality_scores.get('consistency', {}).get('score', 0)
    issues = quality_scores.get('consistency', {}).get('issues_found', 0)
    
    # Clean, readable metric cards
    with col1:
        st.markdown(f"""
        <div style='background-color: white; 
                    padding: 20px; 
                    border-radius: 12px; 
                    border: 2px solid #e5e7eb;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);'>
            <p style='color: #6b7280; margin: 0; font-size: 0.875rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em;'>Total Records</p>
            <p style='color: #111827; margin: 10px 0 5px 0; font-size: 2.5rem; font-weight: 700;'>{len(df)}</p>
            <p style='color: #10b981; margin: 0; font-size: 0.875rem; font-weight: 500;'>✓ Loaded successfully</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style='background-color: white; 
                    padding: 20px; 
                    border-radius: 12px; 
                    border: 2px solid #e5e7eb;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);'>
            <p style='color: #6b7280; margin: 0; font-size: 0.875rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em;'>Duplicates</p>
            <p style='color: #ef4444; margin: 10px 0 5px 0; font-size: 2.5rem; font-weight: 700;'>{duplicate_count}</p>
            <p style='color: #6b7280; margin: 0; font-size: 0.875rem; font-weight: 500;'>{duplicate_count} records to clean</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        completeness_color = '#10b981' if completeness >= 90 else '#f59e0b' if completeness >= 75 else '#ef4444'
        st.markdown(f"""
        <div style='background-color: white; 
                    padding: 20px; 
                    border-radius: 12px; 
                    border: 2px solid #e5e7eb;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);'>
            <p style='color: #6b7280; margin: 0; font-size: 0.875rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em;'>Completeness</p>
            <p style='color: {completeness_color}; margin: 10px 0 5px 0; font-size: 2.5rem; font-weight: 700;'>{completeness:.1f}%</p>
            <p style='color: #6b7280; margin: 0; font-size: 0.875rem; font-weight: 500;'>Target: 90%</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        consistency_color = '#10b981' if consistency >= 90 else '#f59e0b' if consistency >= 75 else '#ef4444'
        st.markdown(f"""
        <div style='background-color: white; 
                    padding: 20px; 
                    border-radius: 12px; 
                    border: 2px solid #e5e7eb;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);'>
            <p style='color: #6b7280; margin: 0; font-size: 0.875rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em;'>Consistency</p>
            <p style='color: {consistency_color}; margin: 10px 0 5px 0; font-size: 2.5rem; font-weight: 700;'>{consistency:.1f}%</p>
            <p style='color: #6b7280; margin: 0; font-size: 0.875rem; font-weight: 500;'>{issues} issues found</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Records by Discovery Source")
        try:
            source_counts = df['source'].value_counts()
            if len(source_counts) > 0:
                fig = px.pie(
                    values=source_counts.values,
                    names=source_counts.index,
                    hole=0.4,
                    color_discrete_sequence=['#2563eb', '#10b981', '#f59e0b']
                )
                fig.update_traces(
                    textposition='inside',
                    textinfo='percent+label',
                    textfont_size=13,
                    marker=dict(line=dict(color='white', width=2))
                )
                fig.update_layout(
                    height=350,
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
                    paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(t=20, b=20, l=20, r=20)
                )
                st.plotly_chart(fig, width="stretch")
        except Exception as e:
            st.error(f"Chart error: {str(e)}")
    
    with col2:
        st.markdown("#### Duplicate Groups by Detection Method")
        try:
            method_counts = duplicate_analysis.get('duplicates_by_method', {})
            if method_counts:
                methods_df = pd.DataFrame([
                    {'Method': k.replace('_', ' ').title(), 'Count': v}
                    for k, v in method_counts.items()
                ])
                
                fig = px.bar(
                    methods_df,
                    x='Method',
                    y='Count',
                    text='Count',
                    color_discrete_sequence=['#2563eb']
                )
                fig.update_traces(
                    texttemplate='%{text}',
                    textposition='outside',
                    textfont_size=14
                )
                fig.update_layout(
                    height=350,
                    showlegend=False,
                    xaxis_title="Detection Method",
                    yaxis_title="Number of Groups",
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(showgrid=False),
                    yaxis=dict(showgrid=True, gridcolor='#f3f4f6'),
                    margin=dict(t=20, b=20, l=20, r=20)
                )
                st.plotly_chart(fig, width="stretch")
            else:
                st.success("✅ No duplicates detected")
        except Exception as e:
            st.error(f"Chart error: {str(e)}")

# TAB 2: Duplicate Detection
with tab2:
    st.markdown("### Duplicate Configuration Items")
    
    duplicate_groups = duplicate_analysis.get('duplicate_groups', [])
    
    if duplicate_groups:
        st.success(f"Found **{duplicate_analysis.get('unique_duplicate_groups', 0)}** duplicate groups affecting **{duplicate_analysis.get('total_duplicate_records', 0)}** records")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        for i, group in enumerate(duplicate_groups, 1):
            ci_list = group.get('cis', [])
            if not ci_list:
                continue
            
            confidence = group.get('confidence', 0)
            if confidence >= 90:
                badge = "High Confidence"
                badge_color = "#10b981"
            elif confidence >= 80:
                badge = "Medium Confidence"
                badge_color = "#f59e0b"
            else:
                badge = "Review Recommended"
                badge_color = "#6b7280"
                
            with st.expander(f"**Group {i}** • {', '.join(ci_list[:2])}{'...' if len(ci_list) > 2 else ''} • {badge}", expanded=(i <= 3)):
                
                # Info box
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Detection Method", group.get('method', 'Unknown').replace('_', ' ').title())
                
                with col2:
                    st.metric("Confidence", f"{confidence}%")
                
                with col3:
                    st.metric("Affected CIs", len(ci_list))
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # CI details table
                try:
                    ci_details_list = []
                    for ci_name in ci_list:
                        ci_matches = df[df['ci_name'] == ci_name]
                        if len(ci_matches) > 0:
                            ci_data = ci_matches.iloc[0]
                            ci_details_list.append({
                                'CI Name': ci_name,
                                'IP Address': ci_data.get('ip_address', 'N/A'),
                                'Type': ci_data.get('ci_type', 'N/A'),
                                'Source': ci_data.get('source', 'N/A'),
                                'Owner': ci_data.get('owner', 'N/A')
                            })
                    
                    if ci_details_list:
                        st.dataframe(
                            pd.DataFrame(ci_details_list),
                            width="stretch",
                            height=min(len(ci_details_list) * 35 + 38, 250)
                        )
                except Exception as e:
                    st.error(f"Error loading details: {str(e)}")
    else:
        st.success("🎉 No duplicates detected! Your CMDB data quality is excellent.")

# TAB 3: AI Insights
with tab3:
    st.markdown("### AI-Powered Recommendations")
    
    # Initialize session state
    if 'ai_insights_generated' not in st.session_state:
        st.session_state.ai_insights_generated = False
    if 'ai_insights_data' not in st.session_state:
        st.session_state.ai_insights_data = None
    if 'show_generate_button' not in st.session_state:
        st.session_state.show_generate_button = True
    
    # Local variable to track if we just generated THIS render
    just_generated_now = False
    current_results = None
    
    # Show Generate button only if we should
    if st.session_state.show_generate_button and not st.session_state.ai_insights_generated:
        st.info("💡 **Ready to analyze:** Click below to generate AI-powered insights from your CMDB data.")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🤖 Generate AI Insights", type="primary", use_container_width=True, help="Analyze duplicates and generate recommendations using Claude AI"):
                # Hide button for next renders
                st.session_state.show_generate_button = False
                
                # Loading UI
                progress_container = st.empty()
                status_container = st.empty()
                
                with progress_container.container():
                    st.markdown("""
                    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                padding: 30px; border-radius: 12px; text-align: center; color: white;'>
                        <h2 style='margin: 0; color: white;'>🤖 AI Analysis in Progress</h2>
                        <p style='margin: 10px 0 0 0; opacity: 0.9;'>Processing your CMDB data with Claude AI...</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                progress_bar = status_container.progress(0)
                status_text = st.empty()
                
                steps = [
                    ("📊 Loading duplicate groups...", 0.5),
                    ("🔍 Analyzing data quality patterns...", 1.0),
                    ("🧠 Identifying root causes...", 1.5),
                    ("💡 Generating recommendations...", 1.5),
                    ("📈 Calculating impact estimates...", 1.0),
                    ("✨ Finalizing insights...", 0.5)
                ]
                
                for i, (step_text, delay) in enumerate(steps):
                    status_text.markdown(f"**{step_text}**")
                    progress_bar.progress((i + 1) / len(steps))
                    time.sleep(delay)
                
                # Generate AI insights
                try:
                    root_cause = ai_engine.analyze_root_causes(duplicate_analysis, quality_scores)
                    st.session_state.ai_insights_data = root_cause
                    st.session_state.ai_insights_generated = True
                    
                    # Clear loading UI
                    progress_container.empty()
                    status_container.empty()
                    status_text.empty()
                    
                    # Success message
                    st.success("✅ AI analysis complete! Insights generated successfully.")
                    
                    # Set local flag and data for immediate display
                    just_generated_now = True
                    current_results = root_cause
                    
                except Exception as e:
                    progress_container.empty()
                    status_container.empty()
                    status_text.empty()
                    st.error(f"❌ AI insights generation failed: {str(e)}")
                    st.info("💡 Tip: Check your API key and try again, or switch to Demo Mode in the sidebar.")
                    # Reset button on error
                    st.session_state.show_generate_button = True
    
    # Display results (either just generated OR from session state)
    if just_generated_now or (st.session_state.ai_insights_generated and st.session_state.ai_insights_data):
        # Use just-generated data if available, otherwise use cached
        root_cause_to_display = current_results if just_generated_now else st.session_state.ai_insights_data
        
        if root_cause_to_display:
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Header with Regenerate
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown("#### 🎯 Analysis Results")
            with col2:
                if st.button("🔄 Regenerate", help="Generate fresh AI insights"):
                    st.session_state.ai_insights_generated = False
                    st.session_state.ai_insights_data = None
                    st.session_state.show_generate_button = True
                    st.rerun()
            
            # Executive summary
            st.info(f"**Executive Summary:** {root_cause_to_display.get('summary', 'Analysis complete')}")
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Root causes
            st.markdown("#### Root Causes Identified")
            root_causes = root_cause_to_display.get('root_causes', [])
            if root_causes:
                for i, cause in enumerate(root_causes, 1):
                    with st.expander(f"**{i}. {cause.get('cause', 'Unknown')}** (Impact: {cause.get('impact', 'Unknown')})", expanded=(i == 1)):
                        st.markdown(f"**Affected Records:** {cause.get('affected_records', 0)}")
                        st.markdown(f"**Explanation:** {cause.get('explanation', 'No details')}")
            else:
                st.info("No root causes identified")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Recommendations
            st.markdown("#### Actionable Recommendations")
            recommendations = root_cause_to_display.get('recommendations', [])
            if recommendations:
                for i, rec in enumerate(recommendations, 1):
                    priority = rec.get('priority', 'Medium')
                    priority_icon = "🔴" if priority == 'High' else "🟡" if priority == 'Medium' else "🟢"
                    with st.expander(f"{priority_icon} **[{priority}] {rec.get('recommendation', 'Recommendation')}**", expanded=(i == 1)):
                        st.markdown(rec.get('details', 'No details available'))
            else:
                st.info("No recommendations at this time")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Estimated impact
            st.markdown("#### Estimated Impact")
            estimated_impact = root_cause_to_display.get('estimated_impact', {})
            if estimated_impact:
                cols = st.columns(len(estimated_impact))
                for col, (metric, value) in zip(cols, estimated_impact.items()):
                    with col:
                        st.markdown(f"""
                        <div style='background-color: white; padding: 16px; border-radius: 8px; 
                                    border: 2px solid #e5e7eb; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center;'>
                            <p style='color: #6b7280; margin: 0 0 8px 0; font-size: 0.75rem; font-weight: 500; 
                                       text-transform: uppercase; letter-spacing: 0.05em;'>{metric.replace('_', ' ').title()}</p>
                            <p style='color: #2563eb; margin: 0; font-size: 1.5rem; font-weight: 700; line-height: 1.2;'>{value}</p>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("Impact estimates not available")
            
            # Sample resolution
            if duplicate_groups and len(duplicate_groups) > 0:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("#### Sample Duplicate Resolution")
                
                sample_group = max(duplicate_groups, key=lambda x: len(x.get('cis', [])))
                if sample_group.get('cis'):
                    sample_ci_details = []
                    for ci_name in sample_group['cis']:
                        ci_matches = df[df['ci_name'] == ci_name]
                        if len(ci_matches) > 0:
                            sample_ci_details.append(ci_matches.iloc[0].to_dict())
                    
                    if sample_ci_details:
                        with st.spinner("Analyzing duplicate group..."):
                            try:
                                recommendation = ai_engine.analyze_duplicate_group(sample_group, sample_ci_details)
                                st.markdown(f"**Duplicate Group:** {', '.join(sample_group['cis'])}")
                                st.success(f"**Recommended Primary:** {recommendation.get('primary_record', 'N/A')}")
                                
                                records_to_merge = recommendation.get('records_to_merge', [])
                                if records_to_merge:
                                    st.warning(f"**Records to Merge:** {', '.join(records_to_merge)}")
                                
                                st.markdown(f"**Reasoning:** {recommendation.get('reasoning', 'N/A')}")
                                
                                remediation_steps = recommendation.get('remediation_steps', [])
                                if remediation_steps:
                                    st.markdown("**Remediation Steps:**")
                                    for step in remediation_steps:
                                        st.markdown(f"- {step}")
                            except Exception as e:
                                st.error(f"Failed to generate recommendation: {str(e)}")

# TAB 4: Data Quality
with tab4:
    st.markdown("### Field Completeness Analysis")
    
    try:
        completeness_by_field = quality_scores.get('completeness', {}).get('by_field', {})
        
        if completeness_by_field:
            completeness_df = pd.DataFrame([
                {'Field': field, 'Completeness': score}
                for field, score in completeness_by_field.items()
            ]).sort_values('Completeness', ascending=True)
            
            # Clean bar chart
            fig = px.bar(
                completeness_df,
                y='Field',
                x='Completeness',
                orientation='h',
                text='Completeness',
                color='Completeness',
                color_continuous_scale=['#ef4444', '#f59e0b', '#10b981'],
                range_color=[0, 100]
            )
            fig.update_traces(
                texttemplate='%{text:.1f}%',
                textposition='outside',
                textfont_size=12
            )
            fig.update_layout(
                height=400,
                showlegend=False,
                xaxis_title="Completeness (%)",
                yaxis_title="Field Name",
                xaxis=dict(range=[0, 105]),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(t=20, b=20, l=20, r=20)
            )
            st.plotly_chart(fig, width="stretch")
    except Exception as e:
        st.error(f"Chart error: {str(e)}")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Sample data
    st.markdown("### Sample CMDB Data")
    try:
        display_cols = ['ci_name', 'ip_address', 'ci_type', 'environment', 'owner', 'source']
        available_cols = [col for col in display_cols if col in df.columns]
        
        if available_cols:
            st.dataframe(df[available_cols].head(10), width="stretch", height=400)
    except Exception as e:
        st.error(f"Display error: {str(e)}")
    
    # Download
    try:
        if len(df) < 10000:
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download Full Dataset (CSV)",
                data=csv,
                file_name="cmdb_data_analysis.csv",
                mime="text/csv",
                width="stretch"
            )
    except Exception as e:
        st.error(f"Download error: {str(e)}")

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #6b7280; padding: 1.5rem;'>
    <p style='margin: 0; font-weight: 500;'>Built by Laziz • February 2026</p>
</div>
""", unsafe_allow_html=True)