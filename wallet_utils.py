# wallet_utils_simple.py — Lightweight wallet simulation for Streamlit dashboard

import streamlit as st
import random
import time
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict

# ----------------------------
# Data Models
# ----------------------------
@dataclass
class Position:
    id: str
    opportunity_name: str
    chain: str
    amount_invested: float
    current_value: float
    apy: float
    entry_date: datetime
    status: str  # "active" or "closed"
    wallet_type: str


# ----------------------------
# Mock Wallet Class
# ----------------------------
class MockWallet:
    """Lightweight simulation of Web3 wallets"""
    def __init__(self, wallet_type: str):
        self.wallet_type = wallet_type
        self.connected = False
        self.address = ""
        self.balance = 0.0
        self.chain_id = None
        self.network_name = ""

    def connect(self) -> bool:
        """Simulate connecting a wallet"""
        self.connected = True

        if self.wallet_type == "MetaMask":
            self.address = f"0x{random.randint(10**39, 10**40-1):040x}"
            self.balance = round(random.uniform(0.5, 100.0), 4)
            self.chain_id = 1
            self.network_name = "Ethereum Mainnet"

        elif self.wallet_type == "Phantom":
            chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz123456789"
            self.address = ''.join(random.choice(chars) for _ in range(44))
            self.balance = round(random.uniform(10, 2000), 2)
            self.chain_id = 101
            self.network_name = "Solana Mainnet"

        elif self.wallet_type == "SUI":
            self.address = f"0x{random.randint(10**39, 10**40-1):040x}"
            self.balance = round(random.uniform(50, 5000), 2)
            self.chain_id = 1001
            self.network_name = "SUI Network"

        elif self.wallet_type == "TAO":
            self.address = f"5{random.randint(10**39, 10**40-1):040x}"
            self.balance = round(random.uniform(0.1, 50.0), 4)
            self.chain_id = 108
            self.network_name = "Bittensor Network"

        return True

    def get_wallet_icon(self) -> str:
        """Emoji representation of the wallet"""
        icons = {
            "MetaMask": "🦊",
            "Phantom": "👻",
            "SUI": "💧",
            "TAO": "🧠"
        }
        return icons.get(self.wallet_type, "💳")

    def get_balance_symbol(self) -> str:
        """Return token symbol based on wallet type"""
        symbols = {
            "MetaMask": "ETH",
            "Phantom": "SOL",
            "SUI": "SUI",
            "TAO": "TAO"
        }
        return symbols.get(self.wallet_type, "TOKEN")

    def disconnect(self):
        """Simulate disconnecting a wallet"""
        self.connected = False
        self.address = ""
        self.balance = 0.0
        self.chain_id = None
        self.network_name = ""


# ----------------------------
# Wallet Management
# ----------------------------
def init_wallets():
    """Initialize all wallet instances in Streamlit session state"""
    if 'metamask_wallet' not in st.session_state:
        st.session_state.metamask_wallet = MockWallet("MetaMask")
    if 'phantom_wallet' not in st.session_state:
        st.session_state.phantom_wallet = MockWallet("Phantom")
    if 'sui_wallet' not in st.session_state:
        st.session_state.sui_wallet = MockWallet("SUI")
    if 'tao_wallet' not in st.session_state:
        st.session_state.tao_wallet = MockWallet("TAO")
    if 'positions' not in st.session_state:
        st.session_state.positions = []

def get_all_wallets() -> List[MockWallet]:
    """Return a list of all wallet instances"""
    return [
        st.session_state.metamask_wallet,
        st.session_state.phantom_wallet,
        st.session_state.sui_wallet,
        st.session_state.tao_wallet
    ]

def get_connected_wallet() -> Optional[MockWallet]:
    """Return the first connected wallet"""
    for wallet in get_all_wallets():
        if wallet.connected:
            return wallet
    return None


# ----------------------------
# Position & Transaction Management
# ----------------------------
def simulate_transaction(
    amount: float,
    opportunity_name: str,
    wallet: MockWallet,
    chain: str,
    apy: float
) -> Dict:
    """Simulate entering a DeFi position"""
    if not wallet.connected:
        return {"success": False, "error": "Wallet not connected"}
    if wallet.balance < amount:
        return {"success": False, "error": "Insufficient balance"}

    tx_hash = f"0x{random.randint(10**63, 10**64-1):064x}"
    position_id = f"pos_{int(time.time())}_{random.randint(1000, 9999)}"

    position = Position(
        id=position_id,
        opportunity_name=opportunity_name,
        chain=chain,
        amount_invested=amount,
        current_value=amount,
        apy=apy,
        entry_date=datetime.now(),
        status="active",
        wallet_type=wallet.wallet_type
    )

    st.session_state.positions.append(position)
    wallet.balance -= amount

    return {"success": True, "tx_hash": tx_hash, "position_id": position_id}

def update_position_values():
    """Update positions' current values based on APY"""
    now = datetime.now()
    for pos in st.session_state.positions:
        if pos.status == "active":
            days_elapsed = (now - pos.entry_date).days
            daily_rate = pos.apy / 365 / 100
            pos.current_value = pos.amount_invested * ((1 + daily_rate) ** days_elapsed)

def close_position(position_id: str) -> Dict:
    """Close a position and return funds"""
    for pos in st.session_state.positions:
        if pos.id == position_id:
            pos.status = "closed"
            wallet = get_connected_wallet()
            if wallet and wallet.wallet_type == pos.wallet_type:
                wallet.balance += pos.current_value
                tx_hash = f"0x{random.randint(10**63, 10**64-1):064x}"
                return {"success": True, "tx_hash": tx_hash, "amount_returned": pos.current_value}
    return {"success": False, "error": "Position not found or wallet mismatch"}
