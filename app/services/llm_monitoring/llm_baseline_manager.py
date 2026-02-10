"""
LLM Baseline Manager - Handles baseline creation and monitoring for LLM interactions
"""
import asyncio
from sqlalchemy import select
from app.database import models
from app.database.connection import get_db


class LLMBaselineManager:
    """
    Manages baseline creation and monitoring window tracking for LLM interactions.
    Similar to BaselineManager but tailored for LLM response token length analysis.
    """

    def __init__(self, project_id: int):
        self.project_id = project_id

    async def create_baseline(self):
        """
        Creates or updates baseline information when baseline_batch_size is hit.
        Calculates average response token length for baseline window.
        
        Returns:
            bool: True if baseline was created/updated, False otherwise
        """
        async for db in get_db():
            try:
                # 1. Fetch LLM config
                config_result = await db.execute(
                    select(models.LLMConfig).where(
                        models.LLMConfig.project_id == self.project_id
                    )
                )
                llm_config = config_result.scalars().first()

                if not llm_config:
                    print(f"No LLM config found for project {self.project_id}")
                    return False

                baseline_batch_size = llm_config.baseline_batch_size
                monitor_batch_size = llm_config.monitor_batch_size

                # 2. Get the latest row count
                latest_monitor = await db.execute(
                    select(models.LLMMonitor).where(
                        models.LLMMonitor.project_id == self.project_id
                    ).order_by(models.LLMMonitor.row_id.desc())
                )
                latest_monitor_record = latest_monitor.scalars().first()
                
                if not latest_monitor_record:
                    print(f"No LLM monitor records found for project {self.project_id}")
                    return False

                latest_row = latest_monitor_record.row_id

                # 3. Check if baseline already exists
                baseline_result = await db.execute(
                    select(models.LLMBaseline).where(
                        models.LLMBaseline.project_id == self.project_id
                    )
                )
                baseline_info = baseline_result.scalars().first()

                if not baseline_info:
                    # Create new baseline if we have enough data
                    if latest_row >= baseline_batch_size:
                        baseline_start = 1
                        baseline_end = baseline_batch_size

                        # Calculate average token length for baseline
                        avg_tokens = await self._calculate_avg_tokens(
                            db, baseline_start, baseline_end
                        )

                        new_baseline = models.LLMBaseline(
                            project_id=self.project_id,
                            baseline_start_row=baseline_start,
                            baseline_end_row=baseline_end,
                            avg_response_token_length=avg_tokens
                        )

                        try:
                            db.add(new_baseline)
                            await db.commit()
                            await db.refresh(new_baseline)

                            print(f"✓ Created LLM baseline for project {self.project_id}")
                            print(f"  Rows: {baseline_start} to {baseline_end}")
                            print(f"  Avg token length: {avg_tokens:.2f}")

                            # Create initial monitor info
                            await self._create_monitor_info(db, baseline_batch_size, monitor_batch_size)

                            return True

                        except Exception as e:
                            await db.rollback()
                            # Check if already created by another process
                            baseline_result = await db.execute(
                                select(models.LLMBaseline).where(
                                    models.LLMBaseline.project_id == self.project_id
                                )
                            )
                            baseline_info = baseline_result.scalars().first()
                            if baseline_info:
                                print(f"⚠ Baseline already created by another process")
                                return True
                            raise
                    else:
                        print(f"Not enough data to create baseline (need {baseline_batch_size} rows)")
                        return False

                else:
                    # Update existing baseline if we have new data
                    current_baseline_end = baseline_info.baseline_end_row
                    next_baseline_target = current_baseline_end + baseline_batch_size

                    if latest_row >= next_baseline_target:
                        baseline_start = current_baseline_end + 1
                        baseline_end = next_baseline_target

                        # Calculate new average for extended baseline
                        avg_tokens = await self._calculate_avg_tokens(db, baseline_start, baseline_end)

                        # Update baseline
                        baseline_info.baseline_end_row = baseline_end
                        baseline_info.avg_response_token_length = avg_tokens

                        await db.commit()

                        print(f"✓ Updated LLM baseline for project {self.project_id}")
                        print(f"  New rows: {baseline_start} to {baseline_end}")
                        print(f"  Avg token length: {avg_tokens:.2f}")

                        # Update monitor info
                        await self._update_monitor_info(db, baseline_end, monitor_batch_size)

                        return True
                    else:
                        print(f"Not enough data to update baseline")
                        return False

            except Exception as e:
                await db.rollback()
                print(f"Error in LLM baseline creation: {str(e)}")
                return False

    async def _calculate_avg_tokens(self, db, start_row: int, end_row: int) -> float:
        """
        Calculate average response token length for a row range.
        
        Args:
            db: Database session
            start_row: Starting row number
            end_row: Ending row number
            
        Returns:
            float: Average token length
        """
        try:
            result = await db.execute(
                select(models.LLMMonitor).where(
                    models.LLMMonitor.project_id == self.project_id,
                    models.LLMMonitor.row_id.between(start_row, end_row)
                )
            )
            records = result.scalars().all()

            if not records:
                return 0.0

            total_tokens = sum(r.response_token_length for r in records)
            return total_tokens / len(records)

        except Exception as e:
            print(f"Error calculating average tokens: {e}")
            return 0.0

    async def _create_monitor_info(self, db, baseline_end_row: int, monitor_batch_size: int):
        """Create initial monitor info after baseline is established."""
        try:
            monitor_result = await db.execute(
                select(models.LLMMonitorInfo).where(
                    models.LLMMonitorInfo.project_id == self.project_id
                )
            )
            existing_monitor = monitor_result.scalars().first()

            if not existing_monitor:
                monitor_start = baseline_end_row + 1
                monitor_end = baseline_end_row + monitor_batch_size

                new_monitor = models.LLMMonitorInfo(
                    project_id=self.project_id,
                    monitor_start_row=monitor_start,
                    monitor_end_row=monitor_end
                )

                db.add(new_monitor)
                await db.commit()

                print(f"✓ Created LLM monitor info: rows {monitor_start} to {monitor_end}")

        except Exception as e:
            print(f"Error creating monitor info: {str(e)}")

    async def _update_monitor_info(self, db, baseline_end_row: int, monitor_batch_size: int):
        """Update monitor info when baseline is extended."""
        try:
            monitor_result = await db.execute(
                select(models.LLMMonitorInfo).where(
                    models.LLMMonitorInfo.project_id == self.project_id
                )
            )
            monitor_info = monitor_result.scalars().first()

            if monitor_info:
                monitor_info.monitor_start_row = baseline_end_row + 1
                monitor_info.monitor_end_row = baseline_end_row + monitor_batch_size

                await db.commit()

                print(f"✓ Updated LLM monitor info: rows {monitor_info.monitor_start_row} to {monitor_info.monitor_end_row}")

        except Exception as e:
            print(f"Error updating monitor info: {str(e)}")

    async def get_baseline_data(self):
        """
        Retrieve the current baseline information.
        
        Returns:
            dict: Baseline data with ranges and stats, or None
        """
        async for db in get_db():
            try:
                baseline_result = await db.execute(
                    select(models.LLMBaseline).where(
                        models.LLMBaseline.project_id == self.project_id
                    )
                )
                baseline_info = baseline_result.scalars().first()

                if not baseline_info:
                    return None

                # Fetch baseline records
                records_result = await db.execute(
                    select(models.LLMMonitor).where(
                        models.LLMMonitor.project_id == self.project_id,
                        models.LLMMonitor.row_id.between(
                            baseline_info.baseline_start_row,
                            baseline_info.baseline_end_row
                        )
                    )
                )
                baseline_records = records_result.scalars().all()

                return {
                    "baseline_start_row": baseline_info.baseline_start_row,
                    "baseline_end_row": baseline_info.baseline_end_row,
                    "avg_token_length": baseline_info.avg_response_token_length,
                    "total_records": len(baseline_records),
                    "created_at": baseline_info.created_at
                }

            except Exception as e:
                print(f"Error retrieving baseline data: {str(e)}")
                return None
