import pandas as pd
from sqlalchemy import select
from app.database import models
from app.database.connection import get_db, AsyncSessionLocal

class StoreDataValidation:
    def __init__(self, project_id: int):
        self.project_id = project_id

    async def store_validation_data(self, features) -> bool:
        """
        Stores validation parameters (column count + column dtypes)
        for a project if not already present.
        Returns True if stored, False if already exists.
        """
        # Convert list of dicts into DataFrame
        if isinstance(features, dict):
            features = [features]
            
        df = pd.DataFrame(features)

        if df.empty:
            return False # No data to derive schema from

        # Column count
        len_columns = df.shape[1]

        # Column types (convert numpy dtypes to strings)
        # Note: We need to handle 'object' types carefully or map them to 'string'
        columns_type = {col: str(dtype) for col, dtype in df.dtypes.items()}

        async with AsyncSessionLocal() as db:
            # Check if validation parameters already exist for this project
            result = await db.execute(
                select(models.DataValidationParameters)
                .where(models.DataValidationParameters.project_id == self.project_id)
            )
            existing = result.scalars().first()

            if existing:
                return False  # Already stored

            # Create new validation parameters record
            validation_record = models.DataValidationParameters(
                project_id=self.project_id,
                len_columns=len_columns,
                columns_type=columns_type,
            )

            db.add(validation_record)
            await db.commit()
            print(f"✓ Validation parameters stored for project {self.project_id}")
            return True
