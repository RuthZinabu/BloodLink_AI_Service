"""
Blood demand forecast generator for monthly and yearly forecasting.
Supports filtering by blood type and component type.
"""

import pandas as pd
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np

# Blood types and component types
BLOOD_TYPES = ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"]
COMPONENT_TYPES = [
    "Whole Blood",
    "Packed Red Cells",
    "Fresh Frozen Plasma",
    "Platelets Concentrate",
    "Cryoprecipitate"
]

# Forecast constraints
MAX_FORECAST_YEAR = 2027
# Default growth rate for yearly projection
DEFAULT_GROWTH_RATE = 0.08  # 8% annually


class SimulationDataLoader:
    """Load and manage simulation and real demand data with component types."""

    @staticmethod
    def _normalize_data(df: pd.DataFrame) -> Optional[pd.DataFrame]:
        if 'ds' in df.columns and 'date' not in df.columns:
            df = df.rename(columns={'ds': 'date'})

        if 'date' not in df.columns:
            return None

        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        if df['date'].isna().any():
            return None

        long_format = {'date', 'blood_type', 'component_type', 'demand_units'}
        if long_format.issubset(df.columns):
            df = df[['date', 'blood_type', 'component_type', 'demand_units']].copy()
            df['demand_units'] = pd.to_numeric(df['demand_units'], errors='coerce')
            return df.dropna(subset=['demand_units'])

        broad_format = {'date'} | set(BLOOD_TYPES)
        if broad_format.issubset(df.columns):
            melted = df[['date'] + BLOOD_TYPES].copy()
            melted['date'] = pd.to_datetime(melted['date'], errors='coerce')
            melted = melted.melt(
                id_vars=['date'],
                value_vars=BLOOD_TYPES,
                var_name='blood_type',
                value_name='demand_units'
            )
            melted['demand_units'] = pd.to_numeric(melted['demand_units'], errors='coerce').fillna(0)
            melted['component_type'] = 'Total'
            return melted[['date', 'blood_type', 'component_type', 'demand_units']]

        return None

    @staticmethod
    def load_simulation_data(data_path: Optional[str] = None) -> pd.DataFrame:
        """
        Load simulation data or real historical demand data.

        Args:
            data_path: Path to CSV file. If None, uses default locations.

        Returns:
            DataFrame with columns: date, blood_type, component_type, demand_units
        """
        ROOT_DIR = Path(__file__).resolve().parent.parent
        candidates = []
        if data_path:
            candidates.append(Path(data_path))
        else:
            candidates.extend([
                ROOT_DIR / 'data' / 'blood_demand_data.csv',
                ROOT_DIR / 'data' / 'download.csv',
                ROOT_DIR / 'data' / 'simulation_data_with_components.csv',
            ])

        uploads_dir = ROOT_DIR / 'data' / 'uploads'
        if uploads_dir.exists():
            upload_candidates = sorted(
                [p for p in uploads_dir.glob('*.csv') if p.is_file()],
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            candidates = upload_candidates + candidates

        for candidate in candidates:
            candidate_path = Path(candidate)
            if not candidate_path.exists():
                continue
            try:
                df = pd.read_csv(candidate_path)
            except Exception:
                continue

            normalized = SimulationDataLoader._normalize_data(df)
            if normalized is not None:
                return normalized

        raise FileNotFoundError(
            "No valid demand dataset found. Please place a valid blood demand CSV at "
            f"{ROOT_DIR / 'data' / 'blood_demand_data.csv'} or "
            f"{ROOT_DIR / 'data' / 'simulation_data_with_components.csv'}.")


class MonthlyForecastGenerator:
    """Generate monthly forecasts grouped by blood type and component type."""
    
    def __init__(self, data_path: Optional[str] = None):
        """
        Initialize monthly forecast generator.
        
        Args:
            data_path: Path to simulation dataset
        """
        self.df = SimulationDataLoader.load_simulation_data(data_path)
        self._prepare_data()
    
    def _prepare_data(self):
        """Prepare data for monthly forecasting."""
        self.df['year'] = self.df['date'].dt.year
        self.df['month'] = self.df['date'].dt.month
        self.df['month_name'] = self.df['date'].dt.strftime('%B')
        self.df['year_month'] = self.df['date'].dt.to_period('M')
        self.df = self.df.sort_values('date')
        self.data_end_date = self.df['date'].max()

    def _get_forecast_period(self, months_ahead: int, start_year: Optional[int], start_month: Optional[int]) -> Tuple[int, int, int]:
        if start_year is None or start_month is None:
            today = datetime.today()
            start_year, start_month = today.year, today.month

        if start_year > MAX_FORECAST_YEAR:
            return start_year, start_month, 0

        months_until_end = (MAX_FORECAST_YEAR - start_year) * 12 + (12 - start_month + 1)
        months_ahead = min(months_ahead, max(0, months_until_end))
        return start_year, start_month, months_ahead

    def _get_monthly_profile(self, combo_data: pd.DataFrame) -> pd.Series:
        if combo_data.empty:
            return pd.Series(1.0, index=range(1, 13))

        month_avg = combo_data.groupby('month')['demand_units'].mean()
        if month_avg.empty:
            return pd.Series(1.0, index=range(1, 13))

        seasonal_index = month_avg / month_avg.mean()
        full_index = pd.Series(1.0, index=range(1, 13))
        for month, value in seasonal_index.items():
            full_index.loc[month] = max(value, 0.1)
        return full_index

    def get_monthly_forecast(
        self,
        blood_type: Optional[str] = None,
        component_type: Optional[str] = None,
        months_ahead: int = 12,
        start_year: Optional[int] = None,
        start_month: Optional[int] = None
    ) -> List[Dict]:
        """
        Generate monthly forecast for specified blood type and component type.
        """
        filtered_df = self.df.copy()

        if blood_type:
            if blood_type not in BLOOD_TYPES:
                raise ValueError(f"Invalid blood type: {blood_type}. Must be one of {BLOOD_TYPES}")
            filtered_df = filtered_df[filtered_df['blood_type'] == blood_type]

        if component_type:
            if component_type not in COMPONENT_TYPES:
                raise ValueError(f"Invalid component type: {component_type}. Must be one of {COMPONENT_TYPES}")
            filtered_df = filtered_df[filtered_df['component_type'] == component_type]

        grouped = filtered_df.groupby(
            ['year_month', 'blood_type', 'component_type']
        )['demand_units'].sum().reset_index()

        if grouped.empty:
            return []

        grouped['year'] = grouped['year_month'].dt.year
        grouped['month'] = grouped['year_month'].dt.month
        grouped['month_name'] = grouped['year_month'].dt.strftime('%B')
        grouped = grouped.sort_values(['year', 'month'])

        start_year, start_month, months_ahead = self._get_forecast_period(months_ahead, start_year, start_month)
        if months_ahead <= 0:
            return []

        forecast_records = []
        unique_combos = grouped[['blood_type', 'component_type']].drop_duplicates()

        for _, combo in unique_combos.iterrows():
            bt = combo['blood_type']
            ct = combo['component_type']

            combo_data = grouped[
                (grouped['blood_type'] == bt) & 
                (grouped['component_type'] == ct)
            ].copy()

            if combo_data.empty:
                continue

            monthly_profile = self._get_monthly_profile(combo_data)
            last_year_data = combo_data[combo_data['year'] == combo_data['year'].max()]
            if not last_year_data.empty:
                base_demand = last_year_data['demand_units'].mean()
            else:
                base_demand = combo_data['demand_units'].mean()

            base_demand = max(base_demand, combo_data['demand_units'].mean(), 1)

            forecast_year = start_year
            forecast_month = start_month
            for i in range(months_ahead):
                if i > 0:
                    forecast_month += 1
                    if forecast_month > 12:
                        forecast_month = 1
                        forecast_year += 1

                month_factor = monthly_profile.get(forecast_month, 1.0)
                growth_factor = (1 + DEFAULT_GROWTH_RATE) ** (i / 12)
                predicted = int(round(base_demand * month_factor * growth_factor))

                forecast_records.append({
                    'blood_type': str(bt),
                    'component_type': str(ct),
                    'month': int(forecast_month),
                    'month_name': pd.Timestamp(year=forecast_year, month=forecast_month, day=1).strftime('%B'),
                    'year': int(forecast_year),
                    'predicted_units': max(0, int(predicted))
                })

        return forecast_records
    
    def get_monthly_forecast_table(
        self,
        blood_type: Optional[str] = None,
        component_type: Optional[str] = None,
        months_ahead: int = 12,
        start_year: Optional[int] = None,
        start_month: Optional[int] = None
    ) -> pd.DataFrame:
        records = self.get_monthly_forecast(blood_type, component_type, months_ahead, start_year, start_month)
        if not records:
            return pd.DataFrame()
        return pd.DataFrame(records)


class YearlyForecastGenerator:
    """Generate yearly forecasts using trend-based projection."""
    
    def __init__(self, data_path: Optional[str] = None, growth_rate: float = DEFAULT_GROWTH_RATE):
        """
        Initialize yearly forecast generator.
        
        Args:
            data_path: Path to simulation dataset
            growth_rate: Annual growth rate for projection (default 8%)
        """
        self.df = SimulationDataLoader.load_simulation_data(data_path)
        self.growth_rate = growth_rate
        self._prepare_data()
    
    def _prepare_data(self):
        """Prepare data for yearly forecasting."""
        self.df['year'] = self.df['date'].dt.year
        self.df['month'] = self.df['date'].dt.month
        self.df = self.df.sort_values('date')

    def _aggregate_yearly_demand(self) -> pd.DataFrame:
        """
        Aggregate monthly demand into yearly totals for each blood type and component.
        
        Returns:
            DataFrame with columns: year, blood_type, component_type, total_demand
        """
        yearly = self.df.groupby(
            ['year', 'blood_type', 'component_type']
        )['demand_units'].sum().reset_index()
        yearly = yearly.rename(columns={'demand_units': 'total_demand'})
        return yearly.sort_values(['blood_type', 'component_type', 'year'])

    def _get_forecast_years(self, years_ahead: int) -> List[int]:
        current_year = datetime.today().year
        if current_year >= MAX_FORECAST_YEAR:
            return []
        max_target = min(current_year + years_ahead, MAX_FORECAST_YEAR)
        return list(range(current_year + 1, max_target + 1))

    def get_yearly_forecast(
        self,
        blood_type: Optional[str] = None,
        component_type: Optional[str] = None,
        years_ahead: int = 3
    ) -> List[Dict]:
        """
        Generate yearly forecast for specified blood type and component type.
        Uses trend-based projection with configurable growth rate.
        """
        yearly_data = self._aggregate_yearly_demand()

        if blood_type:
            if blood_type not in BLOOD_TYPES:
                raise ValueError(f"Invalid blood type: {blood_type}. Must be one of {BLOOD_TYPES}")
            yearly_data = yearly_data[yearly_data['blood_type'] == blood_type]

        if component_type:
            if component_type not in COMPONENT_TYPES:
                raise ValueError(f"Invalid component type: {component_type}. Must be one of {COMPONENT_TYPES}")
            yearly_data = yearly_data[yearly_data['component_type'] == component_type]

        forecast_years = self._get_forecast_years(years_ahead)
        if not forecast_years:
            return []

        forecast_records = []
        unique_combos = yearly_data[['blood_type', 'component_type']].drop_duplicates()

        for _, combo in unique_combos.iterrows():
            bt = combo['blood_type']
            ct = combo['component_type']
            combo_data = yearly_data[
                (yearly_data['blood_type'] == bt) & 
                (yearly_data['component_type'] == ct)
            ].copy()

            if combo_data.empty:
                continue

            combo_data = combo_data.sort_values('year')
            baseline_year = combo_data['year'].max()
            baseline_demand = combo_data.loc[combo_data['year'] == baseline_year, 'total_demand'].values[0]

            if len(combo_data) > 1:
                years_span = combo_data['year'].max() - combo_data['year'].min()
                demand_change = combo_data['total_demand'].iloc[-1] - combo_data['total_demand'].iloc[0]
                if years_span > 0 and combo_data['total_demand'].iloc[0] > 0:
                    annual_trend = demand_change / combo_data['total_demand'].iloc[0] / years_span
                else:
                    annual_trend = self.growth_rate
            else:
                annual_trend = self.growth_rate

            previous_demand = baseline_demand
            for year in forecast_years:
                if year <= baseline_year:
                    continue
                predicted = int(round(previous_demand * (1 + self.growth_rate)))
                forecast_records.append({
                    'blood_type': str(bt),
                    'component_type': str(ct),
                    'year': int(year),
                    'predicted_units': max(0, int(predicted)),
                    'growth_rate': float(self.growth_rate)
                })
                previous_demand = predicted

        return forecast_records
    
    def get_monthly_forecast_table(
        self,
        blood_type: Optional[str] = None,
        component_type: Optional[str] = None,
        months_ahead: int = 12
    ) -> pd.DataFrame:
        """
        Get monthly forecast as a pandas DataFrame (convenient for dashboard).
        
        Returns:
            DataFrame with columns: blood_type, component_type, month, month_name, year, predicted_units
        """
        records = self.get_monthly_forecast(blood_type, component_type, months_ahead)
        if not records:
            return pd.DataFrame()
        return pd.DataFrame(records)


class YearlyForecastGenerator:
    """Generate yearly forecasts using trend-based projection."""
    
    def __init__(self, data_path: Optional[str] = None, growth_rate: float = DEFAULT_GROWTH_RATE):
        """
        Initialize yearly forecast generator.
        
        Args:
            data_path: Path to simulation dataset
            growth_rate: Annual growth rate for projection (default 8%)
        """
        self.df = SimulationDataLoader.load_simulation_data(data_path)
        self.growth_rate = growth_rate
        self._prepare_data()
    
    def _prepare_data(self):
        """Prepare data for yearly forecasting."""
        self.df['year'] = self.df['date'].dt.year
        self.df['month'] = self.df['date'].dt.month
    
    def _aggregate_yearly_demand(self) -> pd.DataFrame:
        """
        Aggregate monthly demand into yearly totals for each blood type and component.
        
        Returns:
            DataFrame with columns: year, blood_type, component_type, total_demand
        """
        yearly = self.df.groupby(
            ['year', 'blood_type', 'component_type']
        )['demand_units'].sum().reset_index()
        yearly = yearly.rename(columns={'demand_units': 'total_demand'})
        
        return yearly.sort_values(['blood_type', 'component_type', 'year'])
    
    def get_yearly_forecast(
        self,
        blood_type: Optional[str] = None,
        component_type: Optional[str] = None,
        years_ahead: int = 3
    ) -> List[Dict]:
        """
        Generate yearly forecast for specified blood type and component type.
        Uses trend-based projection with configurable growth rate.
        
        Args:
            blood_type: Blood type (e.g., 'O+', 'A-'). If None, returns all types.
            component_type: Component type. If None, returns all types.
            years_ahead: Number of years to forecast
            
        Returns:
            List of forecast records with format:
            {
                'blood_type': str,
                'component_type': str,
                'year': int,
                'predicted_units': int,
                'growth_rate': float
            }
        """
        # Get aggregated yearly data
        yearly_data = self._aggregate_yearly_demand()
        
        # Filter by blood type and component
        if blood_type:
            if blood_type not in BLOOD_TYPES:
                raise ValueError(f"Invalid blood type: {blood_type}. Must be one of {BLOOD_TYPES}")
            yearly_data = yearly_data[yearly_data['blood_type'] == blood_type]
        
        if component_type:
            if component_type not in COMPONENT_TYPES:
                raise ValueError(f"Invalid component type: {component_type}. Must be one of {COMPONENT_TYPES}")
            yearly_data = yearly_data[yearly_data['component_type'] == component_type]
        
        # Generate forecast
        forecast_records = []
        
        # Get unique combinations
        unique_combos = yearly_data[['blood_type', 'component_type']].drop_duplicates()
        
        for _, combo in unique_combos.iterrows():
            bt = combo['blood_type']
            ct = combo['component_type']
            
            # Get historical data for this combination
            combo_data = yearly_data[
                (yearly_data['blood_type'] == bt) & 
                (yearly_data['component_type'] == ct)
            ].copy()
            
            if len(combo_data) == 0:
                continue
            
            combo_data = combo_data.sort_values('year')
            
            # Get baseline (last known year)
            baseline_year = combo_data['year'].max()
            baseline_demand = combo_data.loc[combo_data['year'] == baseline_year, 'total_demand'].values[0]
            
            # Calculate growth trend from available data
            if len(combo_data) > 1:
                # Use simple linear trend
                years_span = combo_data['year'].max() - combo_data['year'].min()
                demand_change = combo_data['total_demand'].max() - combo_data['total_demand'].min()
                if years_span > 0:
                    annual_change_rate = demand_change / (combo_data['total_demand'].min() * years_span)
                else:
                    annual_change_rate = self.growth_rate
            else:
                annual_change_rate = self.growth_rate
            
            # Generate forecast for years_ahead starting from current_year + 1
            current_year = datetime.today().year
            for i in range(1, years_ahead + 1):
                forecast_year = current_year + i
                # Apply compound growth from baseline_year to forecast_year
                years_from_baseline = forecast_year - baseline_year
                predicted = int(baseline_demand * ((1 + self.growth_rate) ** years_from_baseline))
                
                forecast_records.append({
                    'blood_type': str(bt),
                    'component_type': str(ct),
                    'year': int(forecast_year),
                    'predicted_units': max(0, int(predicted)),
                    'growth_rate': float(self.growth_rate)
                })
        
        return forecast_records
    
    def get_yearly_forecast_table(
        self,
        blood_type: Optional[str] = None,
        component_type: Optional[str] = None,
        years_ahead: int = 3
    ) -> pd.DataFrame:
        """
        Get yearly forecast as a pandas DataFrame (convenient for dashboard).
        
        Returns:
            DataFrame with columns: blood_type, component_type, year, predicted_units, growth_rate
        """
        records = self.get_yearly_forecast(blood_type, component_type, years_ahead)
        if not records:
            return pd.DataFrame()
        return pd.DataFrame(records)
    
    def get_historical_and_forecast(
        self,
        blood_type: Optional[str] = None,
        component_type: Optional[str] = None,
        years_ahead: int = 3
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Get both historical yearly data and forecast for trend visualization.
        
        Returns:
            Tuple of (historical_df, forecast_df)
        """
        # Get aggregated yearly data
        yearly_data = self._aggregate_yearly_demand()
        
        if blood_type:
            yearly_data = yearly_data[yearly_data['blood_type'] == blood_type]
        if component_type:
            yearly_data = yearly_data[yearly_data['component_type'] == component_type]
        
        # Rename for consistency
        yearly_data = yearly_data.copy()
        yearly_data = yearly_data.rename(columns={'total_demand': 'predicted_units'})
        
        # Get forecast
        forecast_data = pd.DataFrame(self.get_yearly_forecast(blood_type, component_type, years_ahead))
        
        return yearly_data, forecast_data
