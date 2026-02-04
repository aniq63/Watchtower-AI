import pandas as pd
import numpy as np
import asyncio
from app.utils.fetch_data import ProjectDataFetcher

class DataQualityChecker:
    """Main class for running data quality checks"""
    
    def __init__(self, project_id):
        self.project_id = project_id
        self.fetcher = ProjectDataFetcher(project_id)
    
    async def get_data_and_metadata(self):
        """Fetch feature data and metadata from the database"""
        try:
            data = await self.fetcher.get_feature_and_prediction_data()
            return data
        except Exception as e:
            raise Exception(f"Required data couldn't be fetched: {str(e)}")
    
    async def check_missing_values(self):
        """Check for missing values in the latest batch."""
        data = await self.get_data_and_metadata()
        feature_df = data['features']
        
        if len(feature_df) == 0:
            return {
                'missing_values': {},
                'total_columns_checked': 0,
                'columns_with_missing': 0
            }
        
        missing_values_per_column = {}
        
        # Check for missing values in each column
        for col in feature_df.columns:
            if col == 'row_id':  # Skip the row_id column
                continue
            num_missing = feature_df[col].isna().sum()
            if num_missing > 0:
                percent_missing = (num_missing / len(feature_df)) * 100
                missing_values_per_column[col] = {
                    'count': int(num_missing),
                    'percentage': round(percent_missing, 2)
                }
        
        return {
            'missing_values': missing_values_per_column,
            'total_columns_checked': len([c for c in feature_df.columns if c != 'row_id']),
            'columns_with_missing': len(missing_values_per_column)
        }
    
    async def check_duplicate_rows(self):
        """Check for duplicate rows in the latest batch."""
        data = await self.get_data_and_metadata()
        feature_df = data['features']
        
        if len(feature_df) == 0:
            return {
                'total_duplicates': 0,
                'duplicate_percentage': 0.0
            }
        
        # Remove row_id column for duplicate checking (safe even if not present)
        df_for_check = feature_df.drop(columns=['row_id'], errors='ignore')
        
        # Find duplicate rows
        # keep='first' means all occurrences are marked as True except for the first one.
        duplicates_mask = df_for_check.duplicated(keep='first')
        total_duplicates = int(duplicates_mask.sum())
        
        duplicate_percentage = (total_duplicates / len(df_for_check)) * 100
        
        return {
            'total_duplicates': total_duplicates,
            'duplicate_percentage': round(duplicate_percentage, 2)
        }
