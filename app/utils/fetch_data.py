import asyncio
import pandas as pd
from sqlalchemy import select
from app.database import models
from app.database.connection import get_db


class ProjectDataFetcher:
    """
    Class to fetch feature input and prediction output data for a project
    and return them as pandas DataFrames.
    """

    def __init__(self, project_id: int):
        self.project_id = project_id

    async def fetch_data_stats(self):
        """Fetch latest feature/prediction row ranges from ProjectDataStats"""
        async for db in get_db():
            result = await db.execute(
                select(models.ProjectDataStats).where(
                    models.ProjectDataStats.project_id == self.project_id
                )
            )
            stats_row = result.scalars().first()
            if not stats_row:
                return None
            return {
                'latest_feature_start_row': stats_row.latest_feature_start_row,
                'latest_feature_end_row': stats_row.latest_feature_end_row,
                'latest_prediction_start_row': stats_row.latest_prediction_start_row,
                'latest_prediction_end_row': stats_row.latest_prediction_end_row,
                'total_batches': stats_row.total_batches,
                'last_ingestion_at': stats_row.last_ingestion_at
            }

    async def fetch_feature_input(self) -> pd.DataFrame:
        """Fetch feature input data as a DataFrame"""
        stats = await self.fetch_data_stats()
        if not stats:
            raise ValueError(f"No stats found for project {self.project_id}")

        start_row = stats['latest_feature_start_row']
        end_row = stats['latest_feature_end_row']
        
        if start_row is None or end_row is None:
            return pd.DataFrame()
            
        async for db in get_db():
            result = await db.execute(
                select(models.FeatureInput).where(
                    models.FeatureInput.project_id == self.project_id,
                    models.FeatureInput.row_id.between(start_row, end_row)
                )
            )
            rows = result.scalars().all()
            # Convert JSON features to dict and then to DataFrame
            data = [row.features for row in rows]
            df = pd.DataFrame(data)
            # Convert None to np.nan for proper pandas handling
            df = df.replace({None: pd.NA})
            df["row_id"] = [row.row_id for row in rows]
            return df

    async def fetch_prediction_output(self) -> pd.DataFrame:
        """Fetch prediction output data as a DataFrame"""
        stats = await self.fetch_data_stats()
        if not stats:
            raise ValueError(f"No stats found for project {self.project_id}")

        start_row = stats['latest_prediction_start_row']
        end_row = stats['latest_prediction_end_row']
        
        if start_row is None or end_row is None:
            return pd.DataFrame()
            
        async for db in get_db():
            result = await db.execute(
                select(models.PredictionOutput).where(
                    models.PredictionOutput.project_id == self.project_id,
                    models.PredictionOutput.row_id.between(start_row, end_row)
                )
            )
            rows = result.scalars().all()
            # Convert JSON predictions to dict and then to DataFrame
            data = [row.prediction for row in rows]
            df = pd.DataFrame(data)
            # Convert None to np.nan for proper pandas handling
            df = df.replace({None: pd.NA})
            df["row_id"] = [row.row_id for row in rows]
            return df
    
    async def get_feature_and_prediction_data(self):
        """Fetch features, predictions, and metadata"""
        stats = await self.fetch_data_stats()
        feature_df = await self.fetch_feature_input()
        predicted_df = await self.fetch_prediction_output()

        return {
            'features': feature_df,
            'predictions': predicted_df,
            'batch_number': stats['total_batches'] if stats else None,
            'ingestion_time': stats['last_ingestion_at'] if stats else None,
            'feature_row_range': (stats['latest_feature_start_row'], stats['latest_feature_end_row']) if stats else (None, None),
            'prediction_row_range': (stats['latest_prediction_start_row'], stats['latest_prediction_end_row']) if stats else (None, None)
        }