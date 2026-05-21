"""
Blood demand forecast generator for monthly and yearly forecasting.
Supports filtering by blood type and component type.
"""

import pandas as pd
import os
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

# Default growth rate for yearly projection
DEFAULT_GROWTH_RATE = 0.08  # 8% annually


class SimulationDataLoader:
    """Load and manage simulation data with component types."""
    
    @staticmethod
    def load_simulation_data(data_path: Optional[str] = None) -> pd.DataFrame:
        """
        Load simulation data with blood type and component type.
        
        Args:
            data_path: Path to CSV file. If None, uses default location.
            
        Returns:
            DataFrame with columns: date, blood_type, component_type, demand_units
        """
        if data_path is None:
            data_path = os.path.join("data", "simulation_data_with_components.csv")
        
        if not os.path.exists(data_path):
            raise FileNotFoundError(
                f"Simulation data not found at {data_path}. "
                "Please ensure the simulation dataset with component types exists."
            )
        
        df = pd.read_csv(data_path)
        df['date'] = pd.to_datetime(df['date'])
        
        # Validate required columns
        required_cols = ['date', 'blood_type', 'component_type', 'demand_units']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(
                f"Missing required columns: {missing_cols}. "
                "DataFrame must have: date, blood_type, component_type, demand_units"
            )
        
        return df


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
        # Add month and year columns
        self.df['year'] = self.df['date'].dt.year
        self.df['month'] = self.df['date'].dt.month
        self.df['month_name'] = self.df['date'].dt.strftime('%B')
        self.df['year_month'] = self.df['date'].dt.to_period('M')
    
    def get_monthly_forecast(
        self,
        blood_type: Optional[str] = None,
        component_type: Optional[str] = None,
        months_ahead: int = 12
    ) -> List[Dict]:
        """
        Generate monthly forecast for specified blood type and component type.
        
        Args:
            blood_type: Blood type (e.g., 'O+', 'A-'). If None, returns all types.
            component_type: Component type. If None, returns all types.
            months_ahead: Number of months to forecast
            
        Returns:
            List of forecast records with format:
            {
                'blood_type': str,
                'component_type': str,
                'month': int,
                'month_name': str,
                'year': int,
                'predicted_units': int
            }
        """
        # Filter data
        filtered_df = self.df.copy()
        
        if blood_type:
            if blood_type not in BLOOD_TYPES:
                raise ValueError(f"Invalid blood type: {blood_type}. Must be one of {BLOOD_TYPES}")
            filtered_df = filtered_df[filtered_df['blood_type'] == blood_type]
        
        if component_type:
            if component_type not in COMPONENT_TYPES:
                raise ValueError(f"Invalid component type: {component_type}. Must be one of {COMPONENT_TYPES}")
            filtered_df = filtered_df[filtered_df['component_type'] == component_type]
        
        # Group by year-month, blood_type, component_type and sum demand
        grouped = filtered_df.groupby(
            ['year_month', 'blood_type', 'component_type']
        )['demand_units'].sum().reset_index()
        
        grouped['year'] = grouped['year_month'].dt.year
        grouped['month'] = grouped['year_month'].dt.month
        grouped['month_name'] = grouped['year_month'].dt.strftime('%B')
        
        # Sort by date
        grouped = grouped.sort_values(['year', 'month'])
        
        # Generate forecast using simple averaging
        forecast_records = []
        
        # Get unique combinations
        unique_combos = grouped[['blood_type', 'component_type']].drop_duplicates()
        
        for _, combo in unique_combos.iterrows():
            bt = combo['blood_type']
            ct = combo['component_type']
            
            # Filter for this combination
            combo_data = grouped[
                (grouped['blood_type'] == bt) & 
                (grouped['component_type'] == ct)
            ].copy()
            
            if len(combo_data) == 0:
                continue
            
            # Calculate average demand per month for this combination
            avg_demand = combo_data['demand_units'].mean()
            
            # Get the last known month
            last_month = combo_data.iloc[-1]
            current_year = last_month['year']
            current_month = last_month['month']
            
            # Generate forecast for next months_ahead months
            for i in range(1, months_ahead + 1):
                current_month += 1
                if current_month > 12:
                    current_month = 1
                    current_year += 1
                
                # Apply slight growth trend (8% annually)
                growth_factor = (1 + DEFAULT_GROWTH_RATE) ** (i / 12)
                predicted = int(avg_demand * growth_factor)
                
                month_name = pd.Timestamp(year=current_year, month=current_month, day=1).strftime('%B')
                
                forecast_records.append({
                    'blood_type': str(bt),
                    'component_type': str(ct),
                    'month': int(current_month),
                    'month_name': str(month_name),
                    'year': int(current_year),
                    'predicted_units': max(0, int(predicted))
                })
        
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
            
            # Generate forecast for years_ahead
            previous_demand = baseline_demand
            for i in range(1, years_ahead + 1):
                forecast_year = baseline_year + i
                # Apply growth: previous_year * (1 + growth_rate)
                predicted = int(previous_demand * (1 + self.growth_rate))
                
                forecast_records.append({
                    'blood_type': str(bt),
                    'component_type': str(ct),
                    'year': int(forecast_year),
                    'predicted_units': max(0, int(predicted)),
                    'growth_rate': float(self.growth_rate)
                })
                
                previous_demand = predicted
        
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
