"""
Liquidity Analysis Module for IAQF Competition
================================================
Analyzes liquidity fragmentation across quote currencies (USD, USDT, USDC)
during the March 2023 USDC depeg event.

Metrics Implemented:
1. Bid-Ask Spread (quoted and effective)
2. Order Book Depth
3. Roll Measure (effective spread estimator)
4. Order Book Imbalance (OBI)
5. Volume-based liquidity metrics
6. Volatility patterns

Author: IAQF Competition Team
Date: 2026
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')


class LiquidityAnalyzer:
    """
    Comprehensive liquidity analysis for cryptocurrency markets
    """
    
    def __init__(self, data_dir: str = None):
        """
        Initialize the liquidity analyzer
        
        Parameters:
        -----------
        data_dir : str
            Path to the data directory containing raw data
        """
        if data_dir is None:
            # Auto-detect by searching for YieldCurveSurfers directory
            current_dir = Path.cwd()
            
            # Check if we're in src/ directory
            if current_dir.name == 'src':
                self.data_dir = current_dir.parent / 'data'
            # Check if we're in YieldCurveSurfers directory
            elif current_dir.name == 'YieldCurveSurfers':
                self.data_dir = current_dir / 'data'
            # Search upwards for YieldCurveSurfers
            elif 'YieldCurveSurfers' in str(current_dir):
                # Find the YieldCurveSurfers directory in the path
                parts = current_dir.parts
                try:
                    idx = parts.index('YieldCurveSurfers')
                    yield_curve_dir = Path(*parts[:idx+1])
                    self.data_dir = yield_curve_dir / 'data'
                except ValueError:
                    self.data_dir = current_dir / 'data'
            else:
                self.data_dir = current_dir / 'data'
        else:
            self.data_dir = Path(data_dir)
            
        print(f"Data directory set to: {self.data_dir}")
        print(f"Data directory exists: {self.data_dir.exists()}")
        
        self.binance_data = {}
        self.coinbase_data = {}
        self.cryptocom_data = {}
        self.results = {}
        
    def load_data(self, exchange: str = "binance") -> Dict[str, pd.DataFrame]:
        """
        Load OHLCV data from CSV files
        
        Parameters:
        -----------
        exchange : str
            'binance', 'coinbase', or 'cryptocom'
            
        Returns:
        --------
        Dict of DataFrames for each trading pair
        """
        print(f"Loading {exchange} data...")
        
        if exchange == "binance":
            data_path = self.data_dir / "raw" / "binance" / "btc"
            pairs = {
                'BTC/USD': 'binanceus_BTCUSD_1m.csv',
                'BTC/USDC': 'binanceus_BTCUSDC_1m.csv', 
                'BTC/USDT': 'binanceus_BTCUSDT_1m.csv'
            }
        elif exchange == "coinbase":
            data_path = self.data_dir / "raw" / "coinbase" / "btc"
            pairs = {
                'BTC/USD': 'coinbase_BTCUSD_1m.csv',
                'BTC/USDC': 'BTC-USDC_ONE_MINUTE.csv',
                'BTC/EUR': 'coinbase_BTCEUR_1m.csv'
            }
        elif exchange == "cryptocom":
            data_path = self.data_dir / "raw" / "cryptocom" / "btc"
            pairs = {
                'BTC/USD': 'crypto_com_BTCUSD_1m.csv',
                'BTC/USDC': 'crypto_com_BTCUSDC_1m.csv',
                'BTC/USDT': 'crypto_com_BTCUSDT_1m.csv'
            }
        else:
            raise ValueError(f"Unknown exchange: {exchange}")
        
        print(f"Looking in directory: {data_path}")
        print(f"Directory exists: {data_path.exists()}")
        
        loaded_data = {}
        
        for pair_name, filename in pairs.items():
            file_path = data_path / filename
            
            if not file_path.exists():
                print(f"  Warning: {filename} not found, skipping...")
                continue
                
            try:
                print(f"  Loading {filename}...")
                df = pd.read_csv(file_path)
                print(f"    Initial rows: {len(df)}")
                
                # Standardize column names
                df = self._standardize_columns(df, exchange)
                
                # Parse timestamp with flexible handling
                df = self._parse_timestamp(df)
                
                df = df.set_index('timestamp')
                df = df.sort_index()
                
                print(f"    Rows after indexing: {len(df)}")
                
                # Filter to March 1-21, 2023
                start_date = '2023-03-01'
                end_date = '2023-03-21 23:59:59'
                df = df.loc[start_date:end_date]
                
                print(f"    Rows in March 2023 range: {len(df)}")
                
                # Ensure numeric columns are properly typed
                numeric_cols = ['open', 'high', 'low', 'close', 'volume']
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # Drop rows with missing critical data
                df = df.dropna(subset=['close'])
                
                if len(df) == 0:
                    print(f"  Warning: No data in date range for {filename}")
                    continue
                
                loaded_data[pair_name] = df
                print(f"  ✓ Loaded {pair_name}: {len(df)} rows from {df.index.min()} to {df.index.max()}")
                
            except Exception as e:
                print(f"  ✗ Error loading {filename}: {str(e)}")
                import traceback
                traceback.print_exc()
                
        if exchange == "binance":
            self.binance_data = loaded_data
        elif exchange == "coinbase":
            self.coinbase_data = loaded_data
        elif exchange == "cryptocom":
            self.cryptocom_data = loaded_data
            
        return loaded_data
    
    def _standardize_columns(self, df: pd.DataFrame, exchange: str) -> pd.DataFrame:
        """
        Standardize column names across exchanges
        """
        # Common mapping
        column_mapping = {
            'open_time_utc': 'timestamp',
            'timestamp_utc': 'timestamp',
            'start': 'timestamp',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume',
            'num_trades': 'trade_count',
            'close_time_ms': 'close_time'
        }
        
        df = df.rename(columns=column_mapping)
        
        # Handle duplicate columns (keep first occurrence)
        df = df.loc[:, ~df.columns.duplicated()]
        
        return df
    
    def _parse_timestamp(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Parse timestamp column with flexible handling of different formats
        """
        timestamp_col = None
        
        # Prefer UTC string columns first (they're already formatted)
        priority_cols = ['open_time_utc', 'timestamp_utc', 'start', 'timestamp', 'open_time_ms']
        
        for col in priority_cols:
            if col in df.columns:
                timestamp_col = col
                break
        
        if timestamp_col is None:
            raise ValueError(f"No timestamp column found. Available columns: {df.columns.tolist()}")
        
        print(f"    Using timestamp column: {timestamp_col}")
        print(f"    Sample value: {df[timestamp_col].iloc[0]}")
        
        # Try to parse timestamp
        try:
            # Check if it's already a string date format
            sample = str(df[timestamp_col].iloc[0])
            if '-' in sample or '/' in sample:
                # It's already a date string
                df['timestamp'] = pd.to_datetime(df[timestamp_col], errors='coerce')
            else:
                # It's numeric - try to convert
                df[timestamp_col] = pd.to_numeric(df[timestamp_col], errors='coerce')
                
                # If values are large (> year 2100 in seconds), assume milliseconds
                if df[timestamp_col].max() > 4e9:
                    df['timestamp'] = pd.to_datetime(df[timestamp_col], unit='ms', errors='coerce')
                else:
                    # Try seconds
                    df['timestamp'] = pd.to_datetime(df[timestamp_col], unit='s', errors='coerce')
        except Exception as e:
            print(f"    Error parsing timestamp: {e}")
            # Last resort - try direct datetime parsing
            df['timestamp'] = pd.to_datetime(df[timestamp_col], errors='coerce')
        
        # Drop rows with invalid timestamps
        before_count = len(df)
        df = df.dropna(subset=['timestamp'])
        after_count = len(df)
        
        if before_count != after_count:
            print(f"    Dropped {before_count - after_count} rows with invalid timestamps")
        
        print(f"    Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        
        return df
    
    def calculate_quoted_spread(self, df: pd.DataFrame, 
                               window: int = 1) -> pd.Series:
        """
        Calculate quoted bid-ask spread from high-low range
        
        Parameters:
        -----------
        df : pd.DataFrame
            OHLCV data
        window : int
            Rolling window size (minutes)
            
        Returns:
        --------
        pd.Series of quoted spreads (as % of mid-price)
        """
        # Estimate bid-ask spread from high-low range
        spread = df['high'] - df['low']
        mid_price = (df['high'] + df['low']) / 2
        
        # As percentage
        spread_pct = (spread / mid_price) * 100
        
        if window > 1:
            spread_pct = spread_pct.rolling(window=window).mean()
            
        return spread_pct
    
    def calculate_roll_measure(self, df: pd.DataFrame, 
                               window: int = 60) -> pd.Series:
        """
        Calculate Roll (1984) measure of effective spread
        
        Roll = 2 * sqrt(-Cov(ΔP_t, ΔP_{t-1}))
        
        Parameters:
        -----------
        df : pd.DataFrame
            OHLCV data with 'close' prices
        window : int
            Rolling window for calculation (minutes)
            
        Returns:
        --------
        pd.Series of Roll measure values
        """
        # Calculate price changes
        price_changes = df['close'].diff()
        
        # Calculate rolling covariance of consecutive price changes
        def rolling_autocov(series, window):
            """Calculate rolling autocovariance"""
            result = pd.Series(index=series.index, dtype=float)
            
            for i in range(window, len(series)):
                window_data = series.iloc[i-window:i]
                cov = np.cov(window_data[:-1], window_data[1:])[0, 1]
                result.iloc[i] = cov
                
            return result
        
        autocov = rolling_autocov(price_changes, window)
        
        # Roll measure (set negative covariances to zero)
        roll = 2 * np.sqrt(np.abs(np.minimum(autocov, 0)))
        
        # As percentage of price
        roll_pct = (roll / df['close']) * 100
        
        return roll_pct
    
    def calculate_amihud_illiquidity(self, df: pd.DataFrame,
                                    window: int = 60) -> pd.Series:
        """
        Calculate Amihud (2002) illiquidity measure
        
        ILLIQ = |Return| / Volume
        
        Parameters:
        -----------
        df : pd.DataFrame
            OHLCV data
        window : int
            Rolling window for averaging
            
        Returns:
        --------
        pd.Series of illiquidity values
        """
        # Calculate returns
        returns = df['close'].pct_change()
        
        # Amihud measure
        illiq = np.abs(returns) / (df['volume'] + 1e-10)
        
        # Rolling average
        illiq_avg = illiq.rolling(window=window).mean()
        
        # Scale by 1e6 for readability
        illiq_scaled = illiq_avg * 1e6
        
        return illiq_scaled
    
    def calculate_depth_metrics(self, df: pd.DataFrame,
                                window: int = 60) -> Dict[str, pd.Series]:
        """
        Calculate volume-based depth metrics
        
        Parameters:
        -----------
        df : pd.DataFrame
            OHLCV data
        window : int
            Rolling window
            
        Returns:
        --------
        Dictionary of depth metrics
        """
        metrics = {}
        
        # Average volume per minute
        metrics['avg_volume'] = df['volume'].rolling(window=window).mean()
        
        # Volume volatility
        metrics['volume_std'] = df['volume'].rolling(window=window).std()
        
        # Trade count (if available)
        if 'trade_count' in df.columns:
            metrics['avg_trades'] = df['trade_count'].rolling(window=window).mean()
            metrics['avg_trade_size'] = metrics['avg_volume'] / (metrics['avg_trades'] + 1e-10)
        
        # Volume-weighted average price (VWAP) deviation
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).rolling(window=window).sum() / \
               df['volume'].rolling(window=window).sum()
        metrics['vwap_deviation'] = ((df['close'] - vwap) / vwap * 100)
        
        return metrics
    
    def calculate_volatility(self, df: pd.DataFrame,
                            window: int = 60) -> Dict[str, pd.Series]:
        """
        Calculate various volatility measures
        
        Parameters:
        -----------
        df : pd.DataFrame
            OHLCV data
        window : int
            Rolling window
            
        Returns:
        --------
        Dictionary of volatility metrics
        """
        volatility = {}
        
        # Close-to-close volatility
        returns = df['close'].pct_change()
        volatility['realized_vol'] = returns.rolling(window=window).std() * np.sqrt(525600) * 100  # Annualized %
        
        # Parkinson (1980) high-low volatility
        hl_ratio = np.log(df['high'] / df['low'])
        volatility['parkinson_vol'] = hl_ratio.rolling(window=window).std() * \
                                     np.sqrt(525600 / (4 * np.log(2))) * 100
        
        # Garman-Klass volatility (more efficient)
        gk = 0.5 * (np.log(df['high'] / df['low']))**2 - \
             (2*np.log(2) - 1) * (np.log(df['close'] / df['open']))**2
        volatility['garman_klass_vol'] = np.sqrt(gk.rolling(window=window).mean()) * \
                                        np.sqrt(525600) * 100
        
        return volatility
    
    def compare_liquidity_across_pairs(self, 
                                       exchange: str = "binance",
                                       window: int = 60) -> pd.DataFrame:
        """
        Compare liquidity metrics across different quote currencies
        
        Parameters:
        -----------
        exchange : str
            'binance', 'coinbase', or 'cryptocom'
        window : int
            Rolling window for calculations
            
        Returns:
        --------
        DataFrame with comparison metrics
        """
        if exchange == "binance":
            data = self.binance_data
        elif exchange == "coinbase":
            data = self.coinbase_data
        elif exchange == "cryptocom":
            data = self.cryptocom_data
        else:
            data = {}
        
        if not data:
            print(f"No data loaded for {exchange}. Run load_data() first.")
            return pd.DataFrame()
        
        results = []
        
        for pair_name, df in data.items():
            print(f"\nAnalyzing {pair_name}...")
            
            # Calculate all metrics
            spread_quoted = self.calculate_quoted_spread(df, window=1)
            roll = self.calculate_roll_measure(df, window=window)
            amihud = self.calculate_amihud_illiquidity(df, window=window)
            depth = self.calculate_depth_metrics(df, window=window)
            volatility = self.calculate_volatility(df, window=window)
            
            # Create comprehensive metrics DataFrame
            metrics_df = pd.DataFrame({
                'pair': pair_name,
                'timestamp': df.index,
                'price': df['close'],
                'volume': df['volume'],
                'spread_quoted_pct': spread_quoted,
                'roll_measure_pct': roll,
                'amihud_illiq': amihud,
                'avg_volume': depth['avg_volume'],
                'volume_std': depth['volume_std'],
                'vwap_deviation': depth['vwap_deviation'],
                'realized_vol': volatility['realized_vol'],
                'parkinson_vol': volatility['parkinson_vol'],
                'garman_klass_vol': volatility['garman_klass_vol']
            })
            
            if 'avg_trades' in depth:
                metrics_df['avg_trades'] = depth['avg_trades']
                metrics_df['avg_trade_size'] = depth['avg_trade_size']
            
            results.append(metrics_df)
        
        # Combine all pairs
        combined_df = pd.concat(results, ignore_index=False)
        
        # Store results
        self.results[f'{exchange}_liquidity'] = combined_df
        
        return combined_df
    
    def identify_crisis_periods(self, df: pd.DataFrame) -> Dict[str, Tuple]:
        """
        Identify key time periods during the March 2023 crisis
        
        Returns:
        --------
        Dictionary of period names and date ranges
        """
        periods = {
            'pre_crisis': ('2023-03-01', '2023-03-09'),
            'svb_closure': ('2023-03-10', '2023-03-10'),  # March 10
            'peak_crisis': ('2023-03-11', '2023-03-12'),  # March 11-12
            'fdic_announcement': ('2023-03-13', '2023-03-13'),  # March 13
            'recovery': ('2023-03-14', '2023-03-21')
        }
        
        return periods
    
    def generate_summary_statistics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate summary statistics by pair and crisis period
        
        Parameters:
        -----------
        df : pd.DataFrame
            Combined liquidity metrics
            
        Returns:
        --------
        Summary statistics DataFrame
        """
        periods = self.identify_crisis_periods(df)
        
        summary_rows = []
        
        for pair in df['pair'].unique():
            pair_data = df[df['pair'] == pair]
            
            for period_name, (start, end) in periods.items():
                period_data = pair_data.loc[start:end]
                
                if len(period_data) == 0:
                    continue
                
                summary = {
                    'pair': pair,
                    'period': period_name,
                    'start_date': start,
                    'end_date': end,
                    'observations': len(period_data),
                    
                    # Price metrics
                    'avg_price': period_data['price'].mean(),
                    'price_std': period_data['price'].std(),
                    
                    # Spread metrics
                    'avg_spread_quoted': period_data['spread_quoted_pct'].mean(),
                    'max_spread_quoted': period_data['spread_quoted_pct'].max(),
                    'avg_roll_measure': period_data['roll_measure_pct'].mean(),
                    'max_roll_measure': period_data['roll_measure_pct'].max(),
                    
                    # Liquidity metrics
                    'avg_amihud': period_data['amihud_illiq'].mean(),
                    'avg_volume': period_data['avg_volume'].mean(),
                    'avg_volume_std': period_data['volume_std'].mean(),
                    
                    # Volatility metrics
                    'avg_realized_vol': period_data['realized_vol'].mean(),
                    'avg_parkinson_vol': period_data['parkinson_vol'].mean(),
                    'avg_gk_vol': period_data['garman_klass_vol'].mean(),
                }
                
                summary_rows.append(summary)
        
        summary_df = pd.DataFrame(summary_rows)
        
        return summary_df
    
    def plot_liquidity_comparison(self, df: pd.DataFrame, 
                                  metric: str = 'roll_measure_pct',
                                  save_path: str = None):
        """
        Plot liquidity metric comparison across pairs
        
        Parameters:
        -----------
        df : pd.DataFrame
            Combined liquidity metrics
        metric : str
            Metric to plot
        save_path : str
            Path to save figure (auto-created if None)
        """
        plt.style.use('seaborn-v0_8-darkgrid')
        fig, ax = plt.subplots(figsize=(14, 6))
        
        # Plot each pair
        for pair in df['pair'].unique():
            pair_data = df[df['pair'] == pair]
            ax.plot(pair_data.index, pair_data[metric], 
                   label=pair, linewidth=1.5, alpha=0.8)
        
        # Add crisis period shading
        periods = self.identify_crisis_periods(df)
        crisis_start = pd.to_datetime(periods['svb_closure'][0])
        crisis_end = pd.to_datetime(periods['recovery'][1])
        
        ax.axvspan(crisis_start, crisis_end, alpha=0.2, color='red', 
                  label='Crisis Period')
        
        # FDIC announcement
        fdic_date = pd.to_datetime('2023-03-13')
        ax.axvline(fdic_date, color='green', linestyle='--', 
                  linewidth=2, alpha=0.7, label='FDIC Backstop')
        
        ax.set_xlabel('Date', fontsize=12, fontweight='bold')
        ax.set_ylabel(metric.replace('_', ' ').title(), 
                     fontsize=12, fontweight='bold')
        ax.set_title(f'Liquidity Comparison: {metric.replace("_", " ").title()}\nMarch 2023 USDC Depeg Event',
                    fontsize=14, fontweight='bold')
        ax.legend(loc='best', frameon=True, fontsize=10)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Figure saved to {save_path}")
        
        plt.show()
    
    def plot_multi_metric_dashboard(self, df: pd.DataFrame,
                                   pair: str = 'BTC/USDC',
                                   save_path: str = None):
        """
        Create 4-panel dashboard for single pair
        
        Parameters:
        -----------
        df : pd.DataFrame
            Combined liquidity metrics
        pair : str
            Trading pair to analyze
        save_path : str
            Path to save figure (auto-created if None)
        """
        plt.style.use('seaborn-v0_8-darkgrid')
        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        
        pair_data = df[df['pair'] == pair]
        
        # Crisis period shading function
        def add_crisis_shading(ax):
            periods = self.identify_crisis_periods(df)
            crisis_start = pd.to_datetime(periods['svb_closure'][0])
            crisis_end = pd.to_datetime(periods['recovery'][1])
            ax.axvspan(crisis_start, crisis_end, alpha=0.15, color='red')
            
            fdic_date = pd.to_datetime('2023-03-13')
            ax.axvline(fdic_date, color='green', linestyle='--', 
                      linewidth=1.5, alpha=0.6)
        
        # Panel A: Spreads
        ax = axes[0, 0]
        ax.plot(pair_data.index, pair_data['spread_quoted_pct'], 
               label='Quoted Spread', linewidth=1.5, color='blue', alpha=0.7)
        ax.plot(pair_data.index, pair_data['roll_measure_pct'], 
               label='Roll Measure', linewidth=1.5, color='orange', alpha=0.7)
        add_crisis_shading(ax)
        ax.set_ylabel('Spread (%)', fontweight='bold')
        ax.set_title('A. Bid-Ask Spreads', fontweight='bold', fontsize=12)
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        
        # Panel B: Volume
        ax = axes[0, 1]
        ax.plot(pair_data.index, pair_data['avg_volume'], 
               linewidth=1.5, color='purple', alpha=0.7)
        add_crisis_shading(ax)
        ax.set_ylabel('Volume (BTC)', fontweight='bold')
        ax.set_title('B. Average Trading Volume (60-min window)', 
                    fontweight='bold', fontsize=12)
        ax.grid(True, alpha=0.3)
        
        # Panel C: Amihud Illiquidity
        ax = axes[1, 0]
        ax.plot(pair_data.index, pair_data['amihud_illiq'], 
               linewidth=1.5, color='darkred', alpha=0.7)
        add_crisis_shading(ax)
        ax.set_ylabel('Amihud Measure (×10⁶)', fontweight='bold')
        ax.set_title('C. Amihud Illiquidity Measure', 
                    fontweight='bold', fontsize=12)
        ax.grid(True, alpha=0.3)
        
        # Panel D: Volatility
        ax = axes[1, 1]
        ax.plot(pair_data.index, pair_data['realized_vol'], 
               label='Realized Vol', linewidth=1.5, color='darkgreen', alpha=0.7)
        ax.plot(pair_data.index, pair_data['garman_klass_vol'], 
               label='Garman-Klass Vol', linewidth=1.5, color='teal', alpha=0.7)
        add_crisis_shading(ax)
        ax.set_ylabel('Volatility (% p.a.)', fontweight='bold')
        ax.set_title('D. Volatility Measures', fontweight='bold', fontsize=12)
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        
        # Common xlabel
        for ax in axes[1, :]:
            ax.set_xlabel('Date', fontweight='bold')
        
        fig.suptitle(f'Market Microstructure Dashboard: {pair}\nMarch 2023 USDC Depeg Event',
                    fontsize=16, fontweight='bold', y=0.995)
        
        plt.tight_layout()
        
        if save_path:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Dashboard saved to {save_path}")
        
        plt.show()
    
    def export_results(self, output_dir: str = None):
        """
        Export all results to CSV files
        
        Parameters:
        -----------
        output_dir : str
            Directory to save results
        """
        if output_dir is None:
            # Auto-detect results directory
            current_dir = Path.cwd()
            if current_dir.name == 'src':
                output_path = current_dir.parent / 'results'
            else:
                output_path = current_dir / 'results'
        else:
            output_path = Path(output_dir)
            
        output_path.mkdir(parents=True, exist_ok=True)
        
        for name, df in self.results.items():
            filepath = output_path / f"{name}.csv"
            df.to_csv(filepath)
            print(f"Exported {name} to {filepath}")
        
        print(f"\nAll results exported to {output_dir}/")


def main():
    """
    Main execution function
    """
    print("="*80)
    print("IAQF 2026 Competition - Liquidity Analysis")
    print("Cross-Currency Dynamics in Cryptocurrency Markets")
    print("="*80)
    
    # Detect correct data directory
    current_dir = Path.cwd()
    print(f"\nCurrent working directory: {current_dir}")
    
    # Try multiple possible locations
    possible_data_dirs = [
        current_dir / 'YieldCurveSurfers' / 'data',  # If running from IAQF/
        current_dir / 'data',  # If running from YieldCurveSurfers/
        current_dir.parent / 'data',  # If running from src/
    ]
    
    data_dir = None
    for possible_dir in possible_data_dirs:
        if possible_dir.exists():
            data_dir = possible_dir
            print(f"Found data directory at: {data_dir}")
            break
    
    if data_dir is None:
        print("\nERROR: Could not find data directory!")
        print("Searched in:")
        for d in possible_data_dirs:
            print(f"  - {d}")
        print("\nPlease run this script from one of these locations:")
        print("  1. YieldCurveSurfers/src/")
        print("  2. YieldCurveSurfers/")
        print("  3. IAQF/ (parent directory)")
        return
    
    # Initialize analyzer with explicit path
    analyzer = LiquidityAnalyzer(data_dir=str(data_dir))
    
    # Load Binance data
    print("\n" + "="*80)
    print("STEP 1: Loading Data")
    print("="*80)
    binance_data = analyzer.load_data(exchange="binance")
    
    # Try Coinbase as well
    try:
        coinbase_data = analyzer.load_data(exchange="coinbase")
    except Exception as e:
        print(f"Could not load Coinbase data: {e}")
        coinbase_data = {}
    
    # Try Crypto.com as well
    try:
        cryptocom_data = analyzer.load_data(exchange="cryptocom")
    except Exception as e:
        print(f"Could not load Crypto.com data: {e}")
        cryptocom_data = {}
    
    # Determine which exchange has the most data
    exchanges_to_analyze = []
    if binance_data:
        exchanges_to_analyze.append(("binance", binance_data))
    if coinbase_data:
        exchanges_to_analyze.append(("coinbase", coinbase_data))
    if cryptocom_data:
        exchanges_to_analyze.append(("cryptocom", cryptocom_data))
    
    if not exchanges_to_analyze:
        print("\n" + "="*80)
        print("ERROR: No data loaded from any exchange!")
        print("="*80)
        return
    
    # Analyze each exchange
    for exchange_name, exchange_data in exchanges_to_analyze:
        print("\n" + "="*80)
        print(f"STEP 2: Calculating Liquidity Metrics - {exchange_name.upper()}")
        print("="*80)
        liquidity_df = analyzer.compare_liquidity_across_pairs(
            exchange=exchange_name, 
            window=60
        )
        
        if liquidity_df.empty:
            print(f"No liquidity data calculated for {exchange_name}")
            continue
        
        # Generate summary statistics
        print("\n" + "="*80)
        print(f"STEP 3: Generating Summary Statistics - {exchange_name.upper()}")
        print("="*80)
        summary_stats = analyzer.generate_summary_statistics(liquidity_df)
        print(f"\nSummary Statistics Preview for {exchange_name}:")
        print(summary_stats.head(10))
        
        # Store summary
        analyzer.results[f'{exchange_name}_liquidity'] = liquidity_df
        analyzer.results[f'{exchange_name}_summary'] = summary_stats
        
        # Create visualizations
        print("\n" + "="*80)
        print(f"STEP 4: Creating Visualizations - {exchange_name.upper()}")
        print("="*80)
        
        # Determine results path based on where data was found
        results_path = data_dir.parent / 'results' / 'figures' / exchange_name
        results_path.mkdir(parents=True, exist_ok=True)
        print(f"Saving {exchange_name} results to: {results_path}")
        
        # Plot 1: Roll measure comparison
        print(f"\nGenerating Roll Measure comparison plot for {exchange_name}...")
        analyzer.plot_liquidity_comparison(
            liquidity_df,
            metric='roll_measure_pct',
            save_path=str(results_path / 'roll_measure_comparison.png')
        )
        
        # Plot 2: Amihud illiquidity comparison
        print(f"\nGenerating Amihud Illiquidity comparison plot for {exchange_name}...")
        analyzer.plot_liquidity_comparison(
            liquidity_df,
            metric='amihud_illiq',
            save_path=str(results_path / 'amihud_comparison.png')
        )
        
        # Plot 3: Dashboard for BTC/USDC
        if 'BTC/USDC' in exchange_data:
            print(f"\nGenerating BTC/USDC dashboard for {exchange_name}...")
            analyzer.plot_multi_metric_dashboard(
                liquidity_df,
                pair='BTC/USDC',
                save_path=str(results_path / 'btcusdc_dashboard.png')
            )
        
        # Plot 4: Dashboard for BTC/USDT
        if 'BTC/USDT' in exchange_data:
            print(f"\nGenerating BTC/USDT dashboard for {exchange_name}...")
            analyzer.plot_multi_metric_dashboard(
                liquidity_df,
                pair='BTC/USDT',
                save_path=str(results_path / 'btcusdt_dashboard.png')
            )
    
    # Export all results
    if analyzer.results:
        print("\n" + "="*80)
        print("STEP 5: Exporting Results")
        print("="*80)
        analyzer.export_results(output_dir=str(data_dir.parent / 'results'))
        
        print("\n" + "="*80)
        print("Analysis Complete!")
        print("="*80)
        print(f"\nAnalyzed {len(exchanges_to_analyze)} exchange(s):")
        for exchange_name, _ in exchanges_to_analyze:
            print(f"  - {exchange_name.upper()}")
        
        print("\nKey Findings to Investigate:")
        print("1. Compare Roll measure across BTC/USD, BTC/USDT, BTC/USDC")
        print("2. Identify which quote currency had worst liquidity during crisis")
        print("3. Quantify liquidity recovery after FDIC announcement")
        print("4. Calculate liquidity premium (spread difference) for USDC pairs")
        print("5. Compare liquidity across exchanges (Binance vs Coinbase vs Crypto.com)")
        print(f"\nResults saved to: {data_dir.parent / 'results'}")
        print(f"Figures organized by exchange in: {data_dir.parent / 'results' / 'figures'}")
    
    else:
        print("\n" + "="*80)
        print("ERROR: No data could be analyzed!")
        print("="*80)


if __name__ == "__main__":
    main()
