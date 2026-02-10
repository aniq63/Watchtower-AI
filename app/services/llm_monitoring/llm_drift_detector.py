"""
LLM Drift Detector - Detects token length drift between baseline and monitoring windows
"""
from sqlalchemy import select
from app.database import models
from app.database.connection import get_db
from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser


class LLMDriftDetector:
    """
    Detects drift in LLM response token lengths by comparing baseline average
    with current monitoring window average.
    """

    def __init__(self, project_id: int):
        self.project_id = project_id

    async def detect_drift(self) -> dict:
        """
        Detect drift between baseline and monitor windows.
        Drift is detected if token length change exceeds configured threshold.
        
        Returns:
            dict: {
                "has_drift": bool,
                "baseline_avg": float,
                "monitor_avg": float,
                "change_percentage": float,
                "interpretation": str (optional)
            }
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
                    return {"has_drift": False, "error": "No config found"}

                drift_threshold = llm_config.token_drift_threshold

                # 2. Fetch baseline info
                baseline_result = await db.execute(
                    select(models.LLMBaseline).where(
                        models.LLMBaseline.project_id == self.project_id
                    )
                )
                baseline_info = baseline_result.scalars().first()

                if not baseline_info:
                    print(f"No baseline found for project {self.project_id}")
                    return {"has_drift": False, "error": "No baseline found"}

                baseline_avg = baseline_info.avg_response_token_length

                # 3. Fetch monitor info
                monitor_result = await db.execute(
                    select(models.LLMMonitorInfo).where(
                        models.LLMMonitorInfo.project_id == self.project_id
                    )
                )
                monitor_info = monitor_result.scalars().first()

                if not monitor_info:
                    print(f"No monitor info found for project {self.project_id}")
                    return {"has_drift": False, "error": "No monitor info found"}

                # 4. Calculate current monitor window average
                monitor_avg = await self._calculate_monitor_avg(db, monitor_info)

                if monitor_avg is None or monitor_avg == 0:
                    print(f"Could not calculate monitor average")
                    return {"has_drift": False, "error": "No monitor data"}

                # 5. Calculate percentage change
                change_percentage = abs(baseline_avg - monitor_avg) / baseline_avg * 100

                # 6. Determine if drift detected
                has_drift = (change_percentage / 100) > drift_threshold

                result = {
                    "has_drift": has_drift,
                    "baseline_avg": round(baseline_avg, 2),
                    "monitor_avg": round(monitor_avg, 2),
                    "change_percentage": round(change_percentage, 2),
                    "threshold": drift_threshold * 100
                }

                # 7. Get LLM interpretation if drift detected
                if has_drift:
                    interpretation = await self._get_drift_interpretation(
                        baseline_avg, monitor_avg, change_percentage
                    )
                    result["interpretation"] = interpretation

                    # Save drift record
                    await self._save_drift_record(
                        db,
                        baseline_info,
                        monitor_info,
                        baseline_avg,
                        monitor_avg,
                        change_percentage,
                        interpretation
                    )

                return result

            except Exception as e:
                print(f"Error detecting drift: {str(e)}")
                return {"has_drift": False, "error": str(e)}

    async def _calculate_monitor_avg(self, db, monitor_info) -> float:
        """
        Calculate average token length for current monitoring window.
        
        Args:
            db: Database session
            monitor_info: LLMMonitorInfo object
            
        Returns:
            float: Average token length, or None if no data
        """
        try:
            result = await db.execute(
                select(models.LLMMonitor).where(
                    models.LLMMonitor.project_id == self.project_id,
                    models.LLMMonitor.row_id.between(
                        monitor_info.monitor_start_row,
                        monitor_info.monitor_end_row
                    )
                )
            )
            records = result.scalars().all()

            if not records:
                return None

            total_tokens = sum(r.response_token_length for r in records)
            avg = total_tokens / len(records)

            # Update monitor info with current average
            monitor_info.current_avg_token_length = avg
            await db.commit()

            return avg

        except Exception as e:
            print(f"Error calculating monitor average: {e}")
            return None

    async def _get_drift_interpretation(self, baseline_avg: float, monitor_avg: float, change_pct: float) -> str:
        """
        Use LLM to interpret the drift findings.
        
        Args:
            baseline_avg: Average from baseline window
            monitor_avg: Average from monitor window
            change_pct: Percentage change
            
        Returns:
            str: LLM interpretation
        """
        try:
            llm = ChatGroq(model_name="mixtral-8x7b-32768")
            parser = StrOutputParser()

            prompt = f"""Analyze this LLM response token length drift:

Baseline Average Token Length: {baseline_avg:.2f}
Current Monitor Average Token Length: {monitor_avg:.2f}
Change Percentage: {change_pct:.2f}%

Provide a brief interpretation (2-3 sentences) of what this drift means:
- Is it significant?
- What could cause this change in response lengths?
- Any recommendations?"""

            chain = llm | parser
            interpretation = await chain.ainvoke({})

            return interpretation

        except Exception as e:
            print(f"Error getting LLM interpretation: {e}")
            return f"Token length changed by {change_pct:.2f}%. Baseline: {baseline_avg:.2f}, Current: {monitor_avg:.2f}"

    async def _save_drift_record(
        self,
        db,
        baseline_info,
        monitor_info,
        baseline_avg: float,
        monitor_avg: float,
        change_percentage: float,
        interpretation: str
    ):
        """Save drift detection result to database."""
        try:
            baseline_window = f"rows {baseline_info.baseline_start_row}–{baseline_info.baseline_end_row}"
            monitor_window = f"rows {monitor_info.monitor_start_row}–{monitor_info.monitor_end_row}"

            drift_record = models.LLMDrift(
                project_id=self.project_id,
                baseline_window=baseline_window,
                monitor_window=monitor_window,
                baseline_avg_tokens=baseline_avg,
                monitor_avg_tokens=monitor_avg,
                token_length_change=change_percentage,
                has_drift=True,
                drift_interpretation=interpretation
            )

            db.add(drift_record)
            await db.commit()

            print(f"✓ Saved LLM drift record for project {self.project_id}")

        except Exception as e:
            print(f"Error saving drift record: {e}")

    async def get_drift_history(self, limit: int = 10) -> list:
        """
        Retrieve recent drift detection results.
        
        Args:
            limit: Number of recent records to retrieve
            
        Returns:
            list: Recent drift records
        """
        async for db in get_db():
            try:
                result = await db.execute(
                    select(models.LLMDrift).where(
                        models.LLMDrift.project_id == self.project_id
                    ).order_by(models.LLMDrift.created_at.desc()).limit(limit)
                )
                drifts = result.scalars().all()

                return [
                    {
                        "baseline_window": d.baseline_window,
                        "monitor_window": d.monitor_window,
                        "baseline_avg": d.baseline_avg_tokens,
                        "monitor_avg": d.monitor_avg_tokens,
                        "change_percentage": d.token_length_change,
                        "has_drift": d.has_drift,
                        "interpretation": d.drift_interpretation,
                        "created_at": d.created_at
                    }
                    for d in drifts
                ]

            except Exception as e:
                print(f"Error retrieving drift history: {str(e)}")
                return []
