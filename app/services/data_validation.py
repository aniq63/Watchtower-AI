import pandas as pd
from sqlalchemy import select
from app.database import models
from app.database.connection import AsyncSessionLocal


class DataValidation:
    """
    Validates incoming data batches against stored schema parameters.
    Ensures data consistency and schema compliance for each ingestion.
    """
    
    def __init__(self, features, project_id):
        """
        Initialize data validator.
        
        Args:
            features: List of feature dictionaries or single dictionary
            project_id: Project identifier for parameter lookup
        """
        self.features = features
        self.project_id = project_id
    
    async def check_data_validation(self, batch_number: int):
        """
        Validate the current batch against stored parameters.
        Stores the result in DataValidation table.
        
        Args:
            batch_number: Current batch number for tracking
            
        Returns:
            bool: True if validation passed, False otherwise
        """
        # Convert features to DataFrame
        if isinstance(self.features, dict):
            self.features = [self.features]
            
        df = pd.DataFrame(self.features)

        if df.empty:
            print("⚠ Skipping validation: Empty batch")
            return False

        # 1. Get Stored Parameters (Rules)
        async with AsyncSessionLocal() as db:
            try:
                result = await db.execute(
                    select(models.DataValidationParameters)
                    .where(models.DataValidationParameters.project_id == self.project_id)
                )
                params = result.scalars().first()
                
                if not params:
                    print(f"⚠ Skipping validation: No parameters found for project {self.project_id}")
                    return False

                expected_len = params.len_columns
                expected_types = params.columns_type
                
                # 2. Perform Checks
                current_len = df.shape[1]
                current_types = {col: str(dtype) for col, dtype in df.dtypes.items()}
                
                # Check 1: Column Count
                len_columns_status = (current_len == expected_len)
                
                # Check 2: Column Types
                columns_type_status = True
                for col, dtype in expected_types.items():
                    if col not in current_types:
                        columns_type_status = False
                        break
                    if current_types[col] != dtype:
                        columns_type_status = False
                        break
                
                # Overall Status
                validation_status = len_columns_status and columns_type_status
                
                # 3. Store Result
                validation_result = models.DataValidation(
                    project_id=self.project_id,
                    batch_number=batch_number,
                    len_columns_status=len_columns_status,
                    columns_type_status=columns_type_status,
                    validation_status=validation_status
                )
                
                db.add(validation_result)
                await db.commit()
                
                status_symbol = "✓" if validation_status else "✗"
                print(f"{status_symbol} Data validation completed for batch {batch_number}")
                
                return validation_status
                
            except Exception as e:
                print(f"✗ Data validation error: {str(e)}")
                raise



            




