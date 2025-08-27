import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

from defi_scanner import (
    classify_yield_opportunities, 
    get_meme_coins, 
    get_top_picks,
    YieldEntry,
    MemeEntry
)
from wallet_utils import (
    init_wallets, get_connected_wallet, get_all_wallets, 
    simulate_transaction, update_position_values, close_position, Position
)

# Configure page
st.set_page_config(
    page_title="DeFi Protocol Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern look
st.markdown("""
<style>
    /* Main theme colors */
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    /* Wallet connection cards */
    .wallet-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
        transition: all 0.3s ease;
    }
    
    .wallet-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        transform: translateY(-2px);
    }
    
    .wallet-connected {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
    }
    
    /* Metrics styling */
    .metric-container {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1a202c;
    }
    
    .metric-label {
        color: #718096;
        font-size: 0.875rem;
        margin-top: 0.5rem;
    }
    
    /* Position cards */
    .position-card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid #e2e8f0;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    .position-profit {
        background: linear-gradient(135deg, #48bb78, #38a169);
        color: white;
    }
    
    .position-loss {
        background: linear-gradient(135deg, #f56565, #e53e3e);
        color: white;
    }
    
    /* Risk indicators */
    .risk-low { 
        background-color: #48bb78; 
        color: white; 
        padding: 0.25rem 0.75rem; 
        border-radius: 20px; 
        font-size: 0.75rem; 
        font-weight: bold;
    }
    
    .risk-medium { 
        background-color: #ed8936; 
        color: white; 
        padding: 0.25rem 0.75rem; 
        border-radius: 20px; 
        font-size: 0.75rem; 
        font-weight: bold;
    }
    
    .risk-high { 
        background-color: #f56565; 
        color: white; 
        padding: 0.25rem 0.75rem; 
        border-radius: 20px; 
        font-size: 0.75rem; 
        font-weight: bold;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: #f7fafc;
    }
    
    /* Hide streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
</style>
""", unsafe_allow_html=True)

# Initialize wallets and update positions
init_wallets()
update_position_values()

def get_risk_badge(risk: str) -> str:
    """Get styled risk badge"""
    risk_lower = risk.lower()
    if risk_lower == "low":
        return f'<span class="risk-low">🟢 {risk}</span>'
    elif risk_lower == "medium":
        return f'<span class="risk-medium">🟡 {risk}</span>'
    else:
        return f'<span class="risk-high">🔴 {risk}</span>'

def display_modern_header():
    """Display modern header section"""
    st.markdown("""
        <div class="main-header">
            <h1>⚡ DeFi Protocol Dashboard</h1>
            <p>Professional DeFi yield opportunities with advanced position management</p>
        </div>
    """, unsafe_allow_html=True)

def display_wallet_sidebar():
    """Enhanced wallet sidebar with modern design"""
    st.sidebar.markdown("## 💳 Multi-Chain Wallets")
    
    wallets = get_all_wallets()
    connected_wallet = get_connected_wallet()
    
    for wallet in wallets:
        with st.sidebar.container():
            if wallet.connected:
                st.markdown(f"""
                    <div class="wallet-card wallet-connected">
                        <div style="display: flex; align-items: center; justify-content: space-between;">
                            <div>
                                <strong>{wallet.get_wallet_icon()} {wallet.wallet_type}</strong><br>
                                <small>{wallet.address[:10]}...{wallet.address[-6:]}</small><br>
                                <small>{wallet.balance} {wallet.get_balance_symbol()}</small>
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                if st.sidebar.button(f"Disconnect {wallet.wallet_type}", key=f"disconnect_{wallet.wallet_type}"):
                    wallet.disconnect()
                    st.rerun()
            else:
                st.markdown(f"""
                    <div class="wallet-card">
                        <div style="text-align: center;">
                            <strong>{wallet.get_wallet_icon()} {wallet.wallet_type}</strong><br>
                            <small>{wallet.network_name if hasattr(wallet, 'network_name') else 'Not connected'}</small>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                if st.sidebar.button(f"Connect {wallet.wallet_type}", key=f"connect_{wallet.wallet_type}"):
                    if wallet.connect():
                        st.sidebar.success(f"{wallet.wallet_type} connected!")
                        st.rerun()
    
    # Portfolio summary
    if connected_wallet:
        st.sidebar.markdown("---")
        st.sidebar.markdown("## 📊 Portfolio Summary")
        
        positions = [pos for pos in st.session_state.positions if pos.status == "active"]
        total_invested = sum(pos.amount_invested for pos in positions)
        total_current = sum(pos.current_value for pos in positions)
        total_pnl = total_current - total_invested if total_invested > 0 else 0
        pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            st.metric("Total Invested", f"{total_invested:.2f}")
            st.metric("Active Positions", len(positions))
        with col2:
            st.metric("Current Value", f"{total_current:.2f}")
            st.metric("P&L", f"{pnl_pct:+.1f}%", delta=f"{total_pnl:+.2f}")

def display_opportunity_card(opp: YieldEntry, key_suffix: str):
    """Display enhanced opportunity card"""
    connected_wallet = get_connected_wallet()
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown(f"""
            **{opp.project.title()}** `{opp.chain.upper()}`  
            *{opp.symbol}* • {opp.type}
        """)
    
    with col2:
        st.markdown(f"**APY:** {opp.apy_str}")
        st.markdown(f"**TVL:** {opp.tvl_str}")
    
    with col3:
        st.markdown(f"**Risk:** {get_risk_badge(opp.risk)}", unsafe_allow_html=True)
        st.markdown(f"**ROR:** {opp.ror:.2f}")
    
    # Action button
    if connected_wallet:
        if st.button(f"🚀 Enter Position", key=f"enter_{key_suffix}", type="primary"):
            st.session_state.selected_opportunity = opp
            st.session_state.show_position_modal = True
            st.rerun()
    else:
        st.button("🔒 Connect Wallet", disabled=True, key=f"disabled_{key_suffix}")

def display_position_entry_modal():
    """Enhanced position entry modal"""
    if not st.session_state.get('show_position_modal', False):
        return
    
    opportunity = st.session_state.get('selected_opportunity')
    connected_wallet = get_connected_wallet()
    
    if not opportunity or not connected_wallet:
        st.session_state.show_position_modal = False
        return
    
    st.markdown("---")
    st.subheader(f"🚀 Enter Position: {opportunity.project.title()}")
    
    # Opportunity details
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"""
            **Chain:** {opportunity.chain.upper()}  
            **Symbol:** {opportunity.symbol}  
            **Type:** {opportunity.type}
        """)
    with col2:
        st.success(f"""
            **APY:** {opportunity.apy_str}  
            **TVL:** {opportunity.tvl_str}  
            **ROR:** {opportunity.ror:.2f}
        """)
    with col3:
        risk_color = "success" if opportunity.risk.lower() == "low" else "warning" if opportunity.risk.lower() == "medium" else "error"
        st.markdown(f"""
            **Risk Level:** {opportunity.risk}  
            **Wallet:** {connected_wallet.get_wallet_icon()} {connected_wallet.wallet_type}  
            **Balance:** {connected_wallet.balance} {connected_wallet.get_balance_symbol()}
        """)
    
    # Investment amount
    max_amount = connected_wallet.balance * 0.9
    amount = st.number_input(
        f"Investment Amount ({connected_wallet.get_balance_symbol()})",
        min_value=0.01,
        max_value=max_amount,
        value=min(1.0, max_amount),
        step=0.01,
        help=f"Maximum available: {max_amount:.2f} {connected_wallet.get_balance_symbol()}"
    )
    
    # Expected returns calculation
    daily_return = (opportunity.apy_value() / 365) * amount / 100
    monthly_return = daily_return * 30
    yearly_return = daily_return * 365
    
    st.markdown("### 📈 Expected Returns")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Daily", f"+{daily_return:.4f} {connected_wallet.get_balance_symbol()}")
    with col2:
        st.metric("Monthly", f"+{monthly_return:.2f} {connected_wallet.get_balance_symbol()}")
    with col3:
        st.metric("Yearly", f"+{yearly_return:.2f} {connected_wallet.get_balance_symbol()}")
    
    # Action buttons
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("✅ Confirm Transaction", type="primary"):
            with st.spinner("Processing transaction..."):
                time.sleep(2)  # Simulate network delay
                tx_result = simulate_transaction(
                    amount, 
                    opportunity.project, 
                    connected_wallet, 
                    opportunity.chain, 
                    opportunity.apy_value()
                )
                
                if tx_result["success"]:
                    st.success(f"""
                        🎉 Position entered successfully!  
                        **TX Hash:** `{tx_result['tx_hash'][:20]}...`  
                        **Position ID:** `{tx_result['position_id']}`
                    """)
                    st.balloons()
                    time.sleep(2)
                    st.session_state.show_position_modal = False
                    st.rerun()
    
    with col2:
        if st.button("❌ Cancel"):
            st.session_state.show_position_modal = False
            st.rerun()

def display_positions_tab():
    """Display active positions management"""
    st.header("🏦 Position Management")
    
    active_positions = [pos for pos in st.session_state.positions if pos.status == "active"]
    
    if not active_positions:
        st.info("No active positions. Start by entering a position from the opportunities tabs.")
        return
    
    # Portfolio overview metrics
    col1, col2, col3, col4 = st.columns(4)
    total_invested = sum(pos.amount_invested for pos in active_positions)
    total_current = sum(pos.current_value for pos in active_positions)
    total_pnl = total_current - total_invested
    avg_apy = sum(pos.apy for pos in active_positions) / len(active_positions)
    
    with col1:
        st.metric("Total Invested", f"{total_invested:.2f}", help="Total amount invested across all positions")
    with col2:
        st.metric("Current Value", f"{total_current:.2f}", delta=f"{total_pnl:+.2f}")
    with col3:
        pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0
        st.metric("Total P&L", f"{pnl_pct:+.2f}%", delta=f"{total_pnl:+.2f}")
    with col4:
        st.metric("Avg APY", f"{avg_apy:.1f}%", help="Average APY across all positions")
    
    st.markdown("---")
    
    # Position cards
    for i, position in enumerate(active_positions):
        pnl = position.current_value - position.amount_invested
        pnl_pct = (pnl / position.amount_invested * 100) if position.amount_invested > 0 else 0
        
        # Determine card styling based on P&L
        card_class = "position-profit" if pnl >= 0 else "position-loss"
        
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
            
            with col1:
                st.markdown(f"""
                    **{position.opportunity_name.title()}**  
                    *{position.chain.upper()} • APY: {position.apy:.1f}%*  
                    **Wallet:** {position.wallet_type}
                """)
                
            with col2:
                st.markdown(f"""
                    **Invested:** {position.amount_invested:.4f}  
                    **Current:** {position.current_value:.4f}  
                    **Entry Date:** {position.entry_date.strftime('%Y-%m-%d %H:%M')}
                """)
            
            with col3:
                pnl_color = "🟢" if pnl >= 0 else "🔴"
                st.markdown(f"""
                    **P&L:** {pnl_color} {pnl:+.4f} ({pnl_pct:+.2f}%)  
                    **Status:** {'🟢 Active' if position.status == 'active' else '🔴 Closed'}  
                    **Position ID:** `{position.id[-8:]}`
                """)
            
            with col4:
                connected_wallet = get_connected_wallet()
                if connected_wallet and connected_wallet.wallet_type == position.wallet_type:
                    if st.button(f"💰 Close", key=f"close_{position.id}"):
                        result = close_position(position.id)
                        if result["success"]:
                            st.success(f"Position closed! Returned: {result['amount_returned']:.4f}")
                            st.balloons()
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"Error: {result['error']}")
                else:
                    st.button("🔒 Connect Wallet", disabled=True, key=f"disabled_close_{i}")
        
        st.markdown("---")

def create_opportunities_table(opportunities: list) -> pd.DataFrame:
    """Create enhanced opportunities table"""
    if not opportunities:
        return pd.DataFrame()
    
    data = []
    for opp in opportunities:
        data.append({
            "🏛️ Project": opp.project.title(),
            "⛓️ Chain": opp.chain.upper(),
            "💎 Symbol": opp.symbol,
            "📊 Type": opp.type,
            "📈 APY": opp.apy_str,
            "💰 TVL": opp.tvl_str,
            "⚠️ Risk": opp.risk,
            "🎯 ROR": f"{opp.ror:.2f}"
        })
    return pd.DataFrame(data)

def main():
    # Modern header
    display_modern_header()
    
    # Enhanced sidebar
    display_wallet_sidebar()
    
    # Position entry modal
    display_position_entry_modal()
    
    # Main content tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "🏦 Positions", 
        "🏆 Top Picks", 
        "🌱 Long-term", 
        "⚡ Short-term", 
        "🎯 Focus Protocols", 
        "🌉 Layer 2", 
        "🚀 Meme Coins"
    ])
    
    # Positions tab (first tab for easy access)
    with tab1:
        display_positions_tab()
    
    # Fetch opportunities data
    with st.spinner("🔄 Fetching latest DeFi opportunities..."):
        opportunities = classify_yield_opportunities()
        meme_coins = get_meme_coins()
    
    # Combine all opportunities for top picks
    all_opportunities = []
    for category in opportunities.values():
        all_opportunities.extend(category)
    top_picks = get_top_picks(all_opportunities)
    
    # Top Picks Tab
    with tab2:
        st.header("🏆 Top Picks (Highest ROR)")
        if top_picks:
            # Quick stats
            col1, col2, col3 = st.columns(3)
            with col1:
                avg_apy = sum(opp.apy_value() for opp in top_picks) / len(top_picks)
                st.metric("Average APY", f"{avg_apy:.1f}%")
            with col2:
                total_tvl = sum(opp.tvl_value() for opp in top_picks)
                st.metric("Total TVL", f"${total_tvl:,.0f}")
            with col3:
                avg_ror = sum(opp.ror for opp in top_picks) / len(top_picks)
                st.metric("Average ROR", f"{avg_ror:.2f}")
            
            st.markdown("---")
            
            # Opportunities grid
            for i, opp in enumerate(top_picks):
                with st.container():
                    display_opportunity_card(opp, f"top_{i}")
                    if i < len(top_picks) - 1:
                        st.markdown("---")
        else:
            st.warning("No opportunities available at the moment.")
    
    # Long-term Tab
    with tab3:
        st.header("🌱 Long-term Opportunities (Low Risk)")
        long_term_opps = opportunities.get("long_term", [])
        if long_term_opps:
            df = create_opportunities_table(long_term_opps)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Chart
            if len(long_term_opps) > 1:
                apy_data = [opp.apy_value() for opp in long_term_opps]
                projects = [opp.project.title() for opp in long_term_opps]
                fig = px.bar(x=projects, y=apy_data, title="📈 APY Comparison", 
                            color=apy_data, color_continuous_scale="viridis")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No long-term opportunities available.")
    
    # Short-term Tab
    with tab4:
        st.header("⚡ Short-term Opportunities (Medium Risk)")
        short_term_opps = opportunities.get("short_term", [])
        if short_term_opps:
            df = create_opportunities_table(short_term_opps)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No short-term opportunities available.")
    
    # Focus Protocols Tab
    with tab5:
        st.header("🎯 Focus Protocols")
        focus_opps = opportunities.get("focus", [])
        if focus_opps:
            df = create_opportunities_table(focus_opps)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Protocol distribution
            if len(focus_opps) > 1:
                protocol_counts = {}
                for opp in focus_opps:
                    protocol_counts[opp.project.title()] = protocol_counts.get(opp.project.title(), 0) + 1
                
                fig = px.pie(values=list(protocol_counts.values()),
                           names=list(protocol_counts.keys()),
                           title="🎯 Protocol Distribution")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No focus protocol opportunities available.")
    
    # Layer 2 Tab
    with tab6:
        st.header("🌉 Layer 2 Opportunities")
        layer2_opps = opportunities.get("layer2", [])
        if layer2_opps:
            df = create_opportunities_table(layer2_opps)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Chain distribution
            if len(layer2_opps) > 1:
                chain_counts = {}
                for opp in layer2_opps:
                    chain_counts[opp.chain.upper()] = chain_counts.get(opp.chain.upper(), 0) + 1
                
                fig = px.bar(x=list(chain_counts.keys()), y=list(chain_counts.values()),
                           title="🌉 Opportunities by Layer 2 Chain",
                           color=list(chain_counts.values()), color_continuous_scale="plasma")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No Layer 2 opportunities available.")
    
    # Meme Coins Tab
    with tab7:
        st.header("🚀 Trending Meme Coins")
        if meme_coins:
            # Meme coins table
            meme_data = []
            for meme in meme_coins:
                meme_data.append({
                    "🪙 Symbol": meme.symbol,
                    "⛓️ Chain": meme.chain.upper(),
                    "💰 Price": meme.price_usd,
                    "💧 Liquidity": meme.liquidity_usd,
                    "📊 24h Volume": meme.volume_24h_usd,
                    "📈 24h Change": meme.change_24h_pct,
                    "⚠️ Risk": meme.risk
                })
            
            df = pd.DataFrame(meme_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Price change chart
            if len(meme_coins) > 1:
                changes = []
                symbols = []
                for meme in meme_coins:
                    try:
                        change_val = float(meme.change_24h_pct.replace("%", ""))
                        changes.append(change_val)
                        symbols.append(meme.symbol)
                    except:
                        continue
                
                if changes:
                    colors = ['#48bb78' if x > 0 else '#f56565' for x in changes]
                    fig = go.Figure(data=[go.Bar(x=symbols, y=changes, marker_color=colors)])
                    fig.update_layout(title="🚀 24h Price Changes (%)", 
                                    xaxis_title="Meme Coins", 
                                    yaxis_title="Change (%)")
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No meme coins data available.")
    
    # Auto-refresh button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🔄 Refresh All Data", type="primary"):
            st.cache_data.clear()
            st.rerun()
    
    # Footer info
    st.markdown("---")
    st.markdown("""
        <div style="text-align: center; color: #718096; font-size: 0.875rem;">
            ⚡ DeFi Protocol Dashboard • Real-time opportunities across multiple chains<br>
            Always DYOR (Do Your Own Research) before investing in DeFi protocols
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()