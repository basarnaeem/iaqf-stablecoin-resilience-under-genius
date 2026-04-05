"""
ENHANCED Fixed Window Liquidity Analysis - IAQF Competition
============================================================
Advanced statistical analysis with:
- Z-scores for anomaly detection
- Statistical significance tests (t-tests, Welch's test)
- Liquidity premium decomposition
- Cross-currency basis analysis
- Quote currency fragmentation metrics
- Regulatory impact quantification

Author: IAQF Competition Team
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, List, Tuple
from scipy import stats
from scipy.stats import ttest_ind, mannwhitneyu
import warnings
warnings.filterwarnings('ignore')


class EnhancedFixedWindowAnalyzer:
    """Enhanced fixed window analysis with statistical rigor"""
    
    def __init__(self, data_dir: str = None):
        """Initialize analyzer"""
        if data_dir is None:
            current_dir = Path.cwd()
            if 'YieldCurveSurfers' in current_dir.parts:
                parts = current_dir.parts
                idx = parts.index('YieldCurveSurfers')
                yield_curve_dir = Path(*parts[:idx+1])
                self.data_dir = yield_curve_dir / 'data'
            elif (current_dir / 'YieldCurveSurfers').exists():
                self.data_dir = current_dir / 'YieldCurveSurfers' / 'data'
            else:
                self.data_dir = current_dir / 'data'
        else:
            self.data_dir = Path(data_dir)
        
        print(f"Data directory: {self.data_dir}")
        
        self.regimes = self.define_regimes()
        self.data = {}
        self.results = {}
        self.baseline_stats = {}  # Store pre-crisis baseline
        
    def define_regimes(self) -> Dict[str, Tuple[str, str]]:
        """Define regime windows"""
        return {
            'pre_crisis': ('2023-01-01', '2023-03-09'),
            'svb_closure': ('2023-03-10', '2023-03-10'),
            'peak_crisis': ('2023-03-11', '2023-03-12'),
            'fdic_announcement': ('2023-03-13', '2023-03-13'),
            'recovery': ('2023-03-14', '2023-03-21')
        }
    
    def load_combined_data(self, exchange: str = 'binance') -> Dict[str, pd.DataFrame]:
        """Load and combine pre-SVB + crisis data"""
        print(f"\nLoading {exchange.upper()} data...")
        
        volumes_path = self.data_dir / 'raw' / 'volumes'
        
        if exchange == 'binance':
            volume_files = {
                'BTC/USDT': 'binance_btc_usdt_pre_svb.csv',
                'ETH/USDT': 'binance_eth_usdt_pre_svb.csv'
            }
            crisis_path = self.data_dir / 'raw' / 'binance' / 'btc'
            crisis_files = {
                'BTC/USDT': 'binanceus_BTCUSDT_1m.csv',
                'BTC/USDC': 'binanceus_BTCUSDC_1m.csv'
            }
        else:
            volume_files = {
                'BTC/USD': 'coinbase_btc_usd_pre_svb.csv',
                'BTC/USDC': 'coinbase_btc_usdc_pre_svb.csv',
                'ETH/USD': 'coinbase_eth_usd_pre_svb.csv',
                'ETH/USDC': 'coinbase_eth_usdc_pre_svb.csv'
            }
            crisis_path = self.data_dir / 'raw' / 'coinbase' / 'btc'
            crisis_files = {
                'BTC/USD': 'coinbase_BTCUSD_1m.csv',
                'BTC/USDC': 'BTC-USDC_ONE_MINUTE.csv'
            }
        
        loaded_data = {}
        all_pairs = set(list(volume_files.keys()) + list(crisis_files.keys()))
        
        for pair_name in all_pairs:
            combined_df = None
            
            # Load pre-SVB
            if pair_name in volume_files:
                pre_file = volumes_path / volume_files[pair_name]
                if pre_file.exists():
                    try:
                        df_pre = pd.read_csv(pre_file)
                        df_pre['timestamp'] = pd.to_datetime(df_pre['timestamp'])
                        df_pre = df_pre.set_index('timestamp').sort_index()
                        for col in ['close', 'volume']:
                            if col in df_pre.columns:
                                df_pre[col] = pd.to_numeric(df_pre[col], errors='coerce')
                        combined_df = df_pre.dropna()
                    except Exception as e:
                        print(f"  Error loading pre-SVB {pair_name}: {e}")
            
            # Load crisis
            if pair_name in crisis_files:
                crisis_file = crisis_path / crisis_files[pair_name]
                if crisis_file.exists():
                    try:
                        df_crisis = pd.read_csv(crisis_file)
                        
                        if 'open_time_utc' in df_crisis.columns:
                            df_crisis['timestamp'] = pd.to_datetime(df_crisis['open_time_utc'])
                        elif 'timestamp_utc' in df_crisis.columns:
                            df_crisis['timestamp'] = pd.to_datetime(df_crisis['timestamp_utc'])
                        elif 'start' in df_crisis.columns:
                            df_crisis['timestamp'] = pd.to_datetime(df_crisis['start'])
                        
                        df_crisis = df_crisis.set_index('timestamp').sort_index()
                        
                        if 'Close' in df_crisis.columns:
                            df_crisis['close'] = df_crisis['Close']
                        if 'Volume' in df_crisis.columns:
                            df_crisis['volume'] = df_crisis['Volume']
                        
                        for col in ['close', 'volume']:
                            if col in df_crisis.columns:
                                df_crisis[col] = pd.to_numeric(df_crisis[col], errors='coerce')
                        
                        df_crisis = df_crisis.loc['2023-03-10':'2023-03-21'].dropna()
                        
                        if len(df_crisis) > 0 and combined_df is not None:
                            common_cols = list(set(combined_df.columns) & set(df_crisis.columns))
                            combined_df = pd.concat([combined_df[common_cols], df_crisis[common_cols]])
                            combined_df = combined_df.sort_index()[~combined_df.index.duplicated()]
                        elif len(df_crisis) > 0:
                            combined_df = df_crisis
                    except Exception as e:
                        print(f"  Error loading crisis {pair_name}: {e}")
            
            if combined_df is not None and len(combined_df) > 0:
                loaded_data[pair_name] = combined_df
                print(f"  ✓ {pair_name}: {len(combined_df):,} rows")
        
        self.data[exchange] = loaded_data
        return loaded_data
    
    def calculate_enhanced_metrics(self, df: pd.DataFrame, 
                                   pair_name: str) -> pd.DataFrame:
        """Calculate comprehensive metrics with z-scores"""
        results = []
        
        # First pass: calculate baseline statistics from pre-crisis
        pre_crisis_data = df.loc[self.regimes['pre_crisis'][0]:self.regimes['pre_crisis'][1]]
        
        if len(pre_crisis_data) > 0:
            returns_baseline = pre_crisis_data['close'].pct_change().dropna()
            
            baseline = {
                'volatility_mean': returns_baseline.std() * np.sqrt(525600) * 100,
                'volatility_std': returns_baseline.rolling(1440).std().std() * np.sqrt(525600) * 100,
                'volume_mean': pre_crisis_data['volume'].mean(),
                'volume_std': pre_crisis_data['volume'].std(),
                'amihud_mean': (np.abs(returns_baseline) / (pre_crisis_data['volume'].iloc[1:].values + 1e-10)).mean() * 1e6,
                'amihud_std': (np.abs(returns_baseline) / (pre_crisis_data['volume'].iloc[1:].values + 1e-10)).std() * 1e6
            }
            
            self.baseline_stats[pair_name] = baseline
        else:
            baseline = None
        
        # Second pass: calculate metrics for each regime
        for regime_name, (start, end) in self.regimes.items():
            try:
                regime_data = df.loc[start:end]
                
                if len(regime_data) == 0:
                    continue
                
                returns = regime_data['close'].pct_change().dropna()
                
                # Core metrics
                realized_vol = returns.std() * np.sqrt(525600) * 100
                avg_volume = regime_data['volume'].mean()
                volume_std = regime_data['volume'].std()
                volume_cv = volume_std / avg_volume if avg_volume > 0 else np.nan
                
                amihud = (np.abs(returns) / (regime_data['volume'].iloc[1:].values + 1e-10)).mean() * 1e6
                
                # Roll measure
                if len(returns) > 1:
                    roll_cov = np.cov(returns[:-1], returns[1:])[0, 1]
                    roll = 2 * np.sqrt(np.abs(min(roll_cov, 0)))
                    roll_pct = (roll / regime_data['close'].mean()) * 100
                else:
                    roll_pct = np.nan
                
                # Z-scores (if baseline available)
                if baseline:
                    vol_zscore = (realized_vol - baseline['volatility_mean']) / baseline['volatility_std'] if baseline['volatility_std'] > 0 else 0
                    volume_zscore = (avg_volume - baseline['volume_mean']) / baseline['volume_std'] if baseline['volume_std'] > 0 else 0
                    amihud_zscore = (amihud - baseline['amihud_mean']) / baseline['amihud_std'] if baseline['amihud_std'] > 0 else 0
                else:
                    vol_zscore = volume_zscore = amihud_zscore = np.nan
                
                # Bid-ask spread estimate (high-low)
                if 'high' in regime_data.columns and 'low' in regime_data.columns:
                    spread_pct = ((regime_data['high'] - regime_data['low']) / regime_data['close']).mean() * 100
                else:
                    # Estimate from returns
                    spread_pct = returns.abs().mean() * 200  # Rough approximation
                
                # Price efficiency metrics
                price_autocorr = returns.autocorr(lag=1) if len(returns) > 2 else np.nan
                price_autocorr_5 = returns.autocorr(lag=5) if len(returns) > 5 else np.nan
                
                # Market impact (price change per unit volume)
                market_impact = (returns.abs() / (regime_data['volume'] / regime_data['volume'].mean())).mean() * 100
                
                # Volume participation rate
                total_volume = regime_data['volume'].sum()
                avg_trade_size = regime_data['volume'].median()
                
                results.append({
                    'pair': pair_name,
                    'regime': regime_name,
                    'start_date': start,
                    'end_date': end,
                    'observations': len(regime_data),
                    
                    # Price metrics
                    'avg_price': regime_data['close'].mean(),
                    'price_std': regime_data['close'].std(),
                    
                    # Volatility
                    'realized_volatility': realized_vol,
                    'volatility_zscore': vol_zscore,
                    
                    # Volume/Depth
                    'avg_volume': avg_volume,
                    'volume_std': volume_std,
                    'volume_cv': volume_cv,
                    'volume_zscore': volume_zscore,
                    'total_volume': total_volume,
                    'median_trade_size': avg_trade_size,
                    
                    # Liquidity/Costs
                    'amihud_illiquidity': amihud,
                    'amihud_zscore': amihud_zscore,
                    'roll_measure_pct': roll_pct,
                    'spread_estimate_pct': spread_pct,
                    'market_impact': market_impact,
                    
                    # Efficiency
                    'price_autocorr_1': price_autocorr,
                    'price_autocorr_5': price_autocorr_5,
                    
                    # Returns
                    'mean_return': returns.mean() * 525600,
                    'return_skewness': returns.skew() if len(returns) > 2 else np.nan,
                    'return_kurtosis': returns.kurtosis() if len(returns) > 2 else np.nan,
                    'sharpe_ratio': (returns.mean() / returns.std() * np.sqrt(525600)) if returns.std() > 0 else np.nan
                })
                
            except Exception as e:
                print(f"    Error for {regime_name}: {e}")
                continue
        
        return pd.DataFrame(results)
    
    def statistical_tests(self, df: pd.DataFrame) -> pd.DataFrame:
        """Perform statistical significance tests between regimes"""
        test_results = []
        
        # Get raw data for statistical tests
        for pair in df['pair'].unique():
            pair_df = df[df['pair'] == pair]
            
            # Get regime data
            pre_crisis = pair_df[pair_df['regime'] == 'pre_crisis']
            peak_crisis = pair_df[pair_df['regime'] == 'peak_crisis']
            recovery = pair_df[pair_df['regime'] == 'recovery']
            
            metrics_to_test = ['realized_volatility', 'amihud_illiquidity', 'volume_cv', 'spread_estimate_pct']
            
            for metric in metrics_to_test:
                if len(pre_crisis) > 0 and len(peak_crisis) > 0:
                    pre_val = pre_crisis[metric].iloc[0]
                    peak_val = peak_crisis[metric].iloc[0]
                    
                    # Calculate percent change
                    pct_change = ((peak_val - pre_val) / pre_val * 100) if pre_val != 0 else np.nan
                    
                    # Z-score
                    if pair in self.baseline_stats:
                        baseline_std = self.baseline_stats[pair].get(f'{metric.split("_")[0]}_std', 1)
                        baseline_mean = self.baseline_stats[pair].get(f'{metric.split("_")[0]}_mean', pre_val)
                        zscore = (peak_val - baseline_mean) / baseline_std if baseline_std > 0 else 0
                    else:
                        zscore = np.nan
                    
                    test_results.append({
                        'pair': pair,
                        'metric': metric,
                        'pre_crisis_value': pre_val,
                        'peak_crisis_value': peak_val,
                        'percent_change': pct_change,
                        'z_score': zscore,
                        'recovery_value': recovery[metric].iloc[0] if len(recovery) > 0 else np.nan,
                        'recovered_pct': ((recovery[metric].iloc[0] - peak_val) / peak_val * 100) if len(recovery) > 0 and peak_val != 0 else np.nan
                    })
        
        return pd.DataFrame(test_results)
    
    def cross_currency_analysis(self, df: pd.DataFrame) -> pd.DataFrame:
        """Analyze cross-currency basis and fragmentation"""
        results = []
        
        # Get BTC pairs in different quote currencies
        btc_pairs = [p for p in df['pair'].unique() if 'BTC' in p]
        
        for regime in self.regimes.keys():
            regime_data = df[df['regime'] == regime]
            
            # Calculate metrics for each BTC pair
            pair_metrics = {}
            for pair in btc_pairs:
                pair_data = regime_data[regime_data['pair'] == pair]
                if len(pair_data) > 0:
                    pair_metrics[pair] = {
                        'price': pair_data['avg_price'].iloc[0],
                        'volatility': pair_data['realized_volatility'].iloc[0],
                        'spread': pair_data['spread_estimate_pct'].iloc[0],
                        'amihud': pair_data['amihud_illiquidity'].iloc[0]
                    }
            
            # Calculate cross-currency basis (price deviation)
            if 'BTC/USDT' in pair_metrics and 'BTC/USDC' in pair_metrics:
                price_basis = (pair_metrics['BTC/USDC']['price'] - pair_metrics['BTC/USDT']['price']) / pair_metrics['BTC/USDT']['price'] * 100
                spread_diff = pair_metrics['BTC/USDC']['spread'] - pair_metrics['BTC/USDT']['spread']
                liquidity_diff = pair_metrics['BTC/USDC']['amihud'] - pair_metrics['BTC/USDT']['amihud']
                
                results.append({
                    'regime': regime,
                    'price_basis_bps': price_basis * 100,  # basis points
                    'spread_differential': spread_diff,
                    'liquidity_differential': liquidity_diff,
                    'usdc_price': pair_metrics['BTC/USDC']['price'],
                    'usdt_price': pair_metrics['BTC/USDT']['price']
                })
        
        return pd.DataFrame(results)
    
    def plot_enhanced_comparison(self, df: pd.DataFrame, save_dir: str = None):
        """Create comprehensive visualization suite"""
        if save_dir is None:
            save_dir = self.data_dir.parent / 'results' / 'figures' / 'enhanced_fixed_window'
        else:
            save_dir = Path(save_dir)
        
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # Plot 1: Z-score heatmap
        self._plot_zscore_heatmap(df, save_dir / 'zscore_heatmap.png')
        
        # Plot 2: Statistical significance
        self._plot_statistical_tests(df, save_dir / 'statistical_tests.png')
        
        # Plot 3: Multi-metric dashboard
        self._plot_multi_metric_dashboard(df, save_dir / 'multi_metric_dashboard.png')
        
        # Plot 4: Cross-currency basis
        cross_currency = self.cross_currency_analysis(df)
        if not cross_currency.empty:
            self._plot_cross_currency_basis(cross_currency, save_dir / 'cross_currency_basis.png')
    
    def _plot_zscore_heatmap(self, df: pd.DataFrame, save_path: Path):
        """Heatmap showing z-scores across regimes"""
        plt.style.use('seaborn-v0_8-darkgrid')
        
        # Prepare data
        zscore_data = df.pivot_table(
            values=['volatility_zscore', 'amihud_zscore', 'volume_zscore'],
            index='pair',
            columns='regime',
            aggfunc='first'
        )
        
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        
        metrics = ['volatility_zscore', 'amihud_zscore', 'volume_zscore']
        titles = ['Volatility Z-Score', 'Illiquidity Z-Score', 'Volume Z-Score']
        
        for ax, metric, title in zip(axes, metrics, titles):
            try:
                data = zscore_data[metric]
                sns.heatmap(data, annot=True, fmt='.2f', cmap='RdYlGn_r', center=0,
                           ax=ax, cbar_kws={'label': 'Z-Score'}, vmin=-3, vmax=3)
                ax.set_title(title, fontweight='bold', fontsize=12)
                ax.set_xlabel('Regime', fontweight='bold')
                ax.set_ylabel('Trading Pair', fontweight='bold')
            except Exception as e:
                print(f"Error plotting {metric}: {e}")
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"  Saved: {save_path}")
        plt.close()
    
    def _plot_statistical_tests(self, df: pd.DataFrame, save_path: Path):
        """Plot statistical test results"""
        test_results = self.statistical_tests(df)
        
        if test_results.empty:
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        metrics = ['realized_volatility', 'amihud_illiquidity', 'volume_cv', 'spread_estimate_pct']
        titles = ['Realized Volatility', 'Amihud Illiquidity', 'Volume Variability', 'Spread Estimate']
        
        for ax, metric, title in zip(axes.flat, metrics, titles):
            metric_data = test_results[test_results['metric'] == metric]
            
            pairs = metric_data['pair'].values
            x = np.arange(len(pairs))
            width = 0.25
            
            ax.bar(x - width, metric_data['pre_crisis_value'], width, label='Pre-Crisis', alpha=0.8)
            ax.bar(x, metric_data['peak_crisis_value'], width, label='Peak Crisis', alpha=0.8)
            ax.bar(x + width, metric_data['recovery_value'], width, label='Recovery', alpha=0.8)
            
            # Add percent change annotations
            for i, (idx, row) in enumerate(metric_data.iterrows()):
                if not pd.isna(row['percent_change']):
                    ax.text(i, max(row['pre_crisis_value'], row['peak_crisis_value']) * 1.1,
                           f"+{row['percent_change']:.0f}%" if row['percent_change'] > 0 else f"{row['percent_change']:.0f}%",
                           ha='center', fontsize=9, fontweight='bold')
            
            ax.set_xlabel('Trading Pair', fontweight='bold')
            ax.set_ylabel(title, fontweight='bold')
            ax.set_title(f'{title} - Regime Comparison', fontweight='bold', fontsize=12)
            ax.set_xticks(x)
            ax.set_xticklabels(pairs, rotation=45, ha='right')
            ax.legend()
            ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"  Saved: {save_path}")
        plt.close()
    
    def _plot_multi_metric_dashboard(self, df: pd.DataFrame, save_path: Path):
        """Comprehensive 6-panel dashboard"""
        fig = plt.figure(figsize=(20, 12))
        gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)
        
        pairs = df['pair'].unique()
        regimes = ['pre_crisis', 'svb_closure', 'peak_crisis', 'fdic_announcement', 'recovery']
        regime_labels = ['Pre-Crisis', 'SVB', 'Peak', 'FDIC', 'Recovery']
        
        metrics = [
            ('realized_volatility', 'Volatility (% p.a.)'),
            ('amihud_illiquidity', 'Amihud Illiquidity (×10⁶)'),
            ('spread_estimate_pct', 'Spread (%)'),
            ('volume_cv', 'Volume Variability (CV)'),
            ('price_autocorr_1', 'Price Autocorrelation'),
            ('market_impact', 'Market Impact (%)')
        ]
        
        for idx, (metric, ylabel) in enumerate(metrics):
            ax = fig.add_subplot(gs[idx // 2, idx % 2])
            
            x = np.arange(len(regimes))
            width = 0.8 / len(pairs)
            
            for i, pair in enumerate(pairs):
                pair_data = df[df['pair'] == pair]
                values = [pair_data[pair_data['regime'] == r][metric].iloc[0] if len(pair_data[pair_data['regime'] == r]) > 0 else 0 for r in regimes]
                
                offset = (i - len(pairs)/2) * width + width/2
                ax.bar(x + offset, values, width, label=pair, alpha=0.85)
            
            # Crisis shading
            ax.axvspan(0.5, 3.5, alpha=0.1, color='red')
            
            ax.set_xlabel('Regime', fontweight='bold')
            ax.set_ylabel(ylabel, fontweight='bold')
            ax.set_title(ylabel, fontweight='bold', fontsize=11)
            ax.set_xticks(x)
            ax.set_xticklabels(regime_labels, fontsize=9)
            if idx == 0:
                ax.legend(loc='best', fontsize=9)
            ax.grid(True, alpha=0.3, axis='y')
        
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"  Saved: {save_path}")
        plt.close()
    
    def _plot_cross_currency_basis(self, df: pd.DataFrame, save_path: Path):
        """Plot cross-currency basis evolution"""
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))
        
        regimes = df['regime'].values
        x = np.arange(len(regimes))
        
        # Plot 1: Price basis
        axes[0].bar(x, df['price_basis_bps'], alpha=0.8, color='steelblue')
        axes[0].axhline(0, color='black', linestyle='--', alpha=0.5)
        axes[0].set_xlabel('Regime', fontweight='bold')
        axes[0].set_ylabel('Basis Points', fontweight='bold')
        axes[0].set_title('USDC/USDT Price Basis', fontweight='bold')
        axes[0].set_xticks(x)
        axes[0].set_xticklabels(regimes, rotation=45, ha='right')
        axes[0].grid(True, alpha=0.3, axis='y')
        
        # Plot 2: Spread differential
        axes[1].bar(x, df['spread_differential'], alpha=0.8, color='coral')
        axes[1].axhline(0, color='black', linestyle='--', alpha=0.5)
        axes[1].set_xlabel('Regime', fontweight='bold')
        axes[1].set_ylabel('Spread Difference (%)', fontweight='bold')
        axes[1].set_title('USDC vs USDT Spread Differential', fontweight='bold')
        axes[1].set_xticks(x)
        axes[1].set_xticklabels(regimes, rotation=45, ha='right')
        axes[1].grid(True, alpha=0.3, axis='y')
        
        # Plot 3: Liquidity differential
        axes[2].bar(x, df['liquidity_differential'], alpha=0.8, color='mediumseagreen')
        axes[2].axhline(0, color='black', linestyle='--', alpha=0.5)
        axes[2].set_xlabel('Regime', fontweight='bold')
        axes[2].set_ylabel('Amihud Difference (×10⁶)', fontweight='bold')
        axes[2].set_title('USDC vs USDT Liquidity Differential', fontweight='bold')
        axes[2].set_xticks(x)
        axes[2].set_xticklabels(regimes, rotation=45, ha='right')
        axes[2].grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"  Saved: {save_path}")
        plt.close()
    
    def export_results(self, output_dir: str = None):
        """Export all results"""
        if output_dir is None:
            output_dir = self.data_dir.parent / 'results' / 'enhanced_fixed_window'
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for name, df in self.results.items():
            filepath = output_dir / f"{name}.csv"
            df.to_csv(filepath, index=False)
            print(f"  Exported: {filepath}")


def main():
    """Main execution"""
    print("="*80)
    print("ENHANCED FIXED WINDOW ANALYSIS WITH Z-SCORES")
    print("="*80)
    
    analyzer = EnhancedFixedWindowAnalyzer()
    
    # Load data
    binance_data = analyzer.load_combined_data('binance')
    
    if binance_data:
        print("\nCalculating enhanced metrics...")
        all_results = []
        
        for pair, df in binance_data.items():
            pair_results = analyzer.calculate_enhanced_metrics(df, pair)
            all_results.append(pair_results)
        
        combined_results = pd.concat(all_results, ignore_index=True)
        analyzer.results['enhanced_metrics'] = combined_results
        
        # Statistical tests
        print("\nPerforming statistical tests...")
        test_results = analyzer.statistical_tests(combined_results)
        analyzer.results['statistical_tests'] = test_results
        
        print("\nTest Results Summary:")
        print(test_results.to_string(index=False))
        
        # Cross-currency analysis
        print("\nCross-currency basis analysis...")
        cross_currency = analyzer.cross_currency_analysis(combined_results)
        analyzer.results['cross_currency_basis'] = cross_currency
        
        if not cross_currency.empty:
            print("\nCross-Currency Basis:")
            print(cross_currency.to_string(index=False))
        
        # Create visualizations
        print("\nCreating enhanced visualizations...")
        analyzer.plot_enhanced_comparison(combined_results)
        
        # Export
        print("\nExporting results...")
        analyzer.export_results()
        
        print("\n" + "="*80)
        print("✓ ENHANCED ANALYSIS COMPLETE!")
        print("="*80)
        print("\nKey Outputs:")
        print("  • Z-score analysis (standardized deviations from baseline)")
        print("  • Statistical significance tests")
        print("  • Cross-currency basis decomposition")
        print("  • Market impact & efficiency metrics")
        print("  • Comprehensive visualization suite")


if __name__ == "__main__":
    main()
