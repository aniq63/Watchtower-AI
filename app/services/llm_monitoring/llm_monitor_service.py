"""
LLM Monitor Service - Main service for logging and processing LLM interactions
Uses cached models from llm_model_init for efficient loading
"""
from sqlalchemy import select
from app.database import models
from app.database.connection import get_db
from app.services.llm_monitoring.llm_token_service import LLMTokenizer
from app.services.llm_monitoring.llm_baseline_manager import LLMBaselineManager
from app.services.llm_monitoring.llm_drift_detector import LLMDriftDetector
from app.services.llm_monitoring.llm_model_init import get_cached_detoxify
from langchain_groq import ChatGroq
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
class LLMMonitorService:
    """
    Main service for logging and monitoring LLM interactions.
    Handles toxicity detection, LLM judge metrics, token counting, and drift detection.
    Uses lazy loading for heavy models.
    """

    def __init__(self):
        """
        Initialize service with lazy-loaded tokenizer and detoxify models.
        Models are loaded on first use to minimize initialization time.
        """
        self.tokenizer = LLMTokenizer(model_name="gpt2")
        self._detoxify = None  # Lazy load on first use

    async def log_interaction(
        self,
        project_id: int,
        input_text: str,
        response_text: str,
        metadata: dict = None
    ) -> dict:
        """
        Log and process an LLM interaction.
        
        Args:
            project_id: Project ID
            input_text: User input to LLM
            response_text: LLM response
            metadata: Optional metadata
            
        Returns:
            dict: Processed interaction with all metrics
        """
        async for db in get_db():
            try:
                # 1. Get next row_id
                row_id = await self._get_next_row_id(db, project_id)

                # 2. Count response tokens
                response_token_length = self.tokenizer.count_tokens(response_text)

                # 3. Check toxicity
                toxicity_result, is_toxic = self._check_toxicity(response_text)

                # 4. Get LLM judge metrics
                judge_metrics = await self._llm_as_judge(input_text, response_text)

                # 5. Create LLM monitor record
                llm_record = models.LLMMonitor(
                    project_id=project_id,
                    row_id=row_id,
                    input_text=input_text,
                    response_text=response_text,
                    response_token_length=response_token_length,
                    detoxify=toxicity_result,
                    is_toxic=is_toxic,
                    llm_judge_metrics=judge_metrics,
                    has_drift=False
                )

                db.add(llm_record)
                await db.commit()
                await db.refresh(llm_record)

                print(f"✓ Logged LLM interaction for project {project_id} (row {row_id})")

                # 6. Check if baseline should be created
                baseline_manager = LLMBaselineManager(project_id)
                await baseline_manager.create_baseline()

                # 7. Check if drift detection should run
                await self._check_drift_trigger(db, project_id)

                return {
                    "id": llm_record.id,
                    "project_id": project_id,
                    "row_id": row_id,
                    "response_token_length": response_token_length,
                    "is_toxic": is_toxic,
                    "judge_metrics": judge_metrics,
                    "status": "success"
                }

            except Exception as e:
                await db.rollback()
                print(f"Error logging interaction: {str(e)}")
                raise

    def _check_toxicity(self, response_text: str) -> tuple:
        """
        Check toxicity of response using cached Detoxify model.
        
        Args:
            response_text: Response to check
            
        Returns:
            tuple: (detoxify_results_dict, is_toxic_bool)
        """
        try:
            # Get cached detoxify model (lazy loaded once)
            if self._detoxify is None:
                self._detoxify = get_cached_detoxify()
            
            results = self._detoxify.predict(response_text)

            # results = {
            #     'toxicity': 0.xxx,
            #     'severe_toxicity': 0.xxx,
            #     'obscene': 0.xxx,
            #     'threat': 0.xxx,
            #     'insult': 0.xxx,
            #     'identity_attack': 0.xxx
            # }

            is_toxic = results.get('toxicity', 0) > 0.5

            return results, is_toxic

        except Exception as e:
            print(f"Error checking toxicity: {e}")
            return {
                'toxicity': 0,
                'severe_toxicity': 0,
                'obscene': 0,
                'threat': 0,
                'insult': 0,
                'identity_attack': 0
            }, False

    async def _llm_as_judge(self, input_text: str, response_text: str) -> dict:
        """
        Use LLM to judge response quality with metrics.
        
        Args:
            input_text: User input
            response_text: LLM response
            
        Returns:
            dict: Judge metrics {accuracy, completeness, clarity, relevance, logical_flow, creativity}
        """
        try:
            llm = ChatGroq(model_name="mixtral-8x7b-32768")
            parser = JsonOutputParser()

            prompt_template = """You are a judge for AI-generated responses.

Evaluate the response using the following metrics (score 1–10):
- accuracy: How correct and factually accurate is the response?
- completeness: Does it fully address the input question?
- clarity: Is the response clear and easy to understand?
- relevance: How relevant is the response to the input?
- logical_flow: Is the reasoning presented logically?
- creativity: Does the response show creative thinking?

Return your output strictly in valid JSON with these exact keys:
accuracy, completeness, clarity, relevance, logical_flow, creativity

Input: {input_text}
Response: {response_text}

{format_instructions}"""

            prompt = PromptTemplate(
                input_variables=["input_text", "response_text"],
                partial_variables={"format_instructions": parser.get_format_instructions()},
                template=prompt_template,
            )

            chain = prompt | llm | parser

            judged_scores = await chain.ainvoke({
                "input_text": input_text,
                "response_text": response_text
            })

            # Ensure all keys are present
            default_scores = {
                "accuracy": 0,
                "completeness": 0,
                "clarity": 0,
                "relevance": 0,
                "logical_flow": 0,
                "creativity": 0
            }

            if isinstance(judged_scores, dict):
                default_scores.update(judged_scores)

            return default_scores

        except Exception as e:
            print(f"Error getting LLM judge metrics: {e}")
            return {
                "accuracy": 0,
                "completeness": 0,
                "clarity": 0,
                "relevance": 0,
                "logical_flow": 0,
                "creativity": 0,
                "error": str(e)
            }

    async def _get_next_row_id(self, db, project_id: int) -> int:
        """Get the next row ID for this project."""
        try:
            result = await db.execute(
                select(models.LLMMonitor).where(
                    models.LLMMonitor.project_id == project_id
                ).order_by(models.LLMMonitor.row_id.desc())
            )
            last_record = result.scalars().first()

            if last_record:
                return last_record.row_id + 1
            else:
                return 1

        except Exception as e:
            print(f"Error getting next row id: {e}")
            return 1

    async def _check_drift_trigger(self, db, project_id: int):
        """
        Check if drift detection should be triggered.
        Triggers when monitor window is full.
        """
        try:
            # Get config
            config_result = await db.execute(
                select(models.LLMConfig).where(
                    models.LLMConfig.project_id == project_id
                )
            )
            config = config_result.scalars().first()

            if not config:
                return

            # Get monitor info
            monitor_result = await db.execute(
                select(models.LLMMonitorInfo).where(
                    models.LLMMonitorInfo.project_id == project_id
                )
            )
            monitor_info = monitor_result.scalars().first()

            if not monitor_info:
                return

            # Get latest record count
            latest_result = await db.execute(
                select(models.LLMMonitor).where(
                    models.LLMMonitor.project_id == project_id
                ).order_by(models.LLMMonitor.row_id.desc())
            )
            latest_record = latest_result.scalars().first()

            if not latest_record:
                return

            latest_row = latest_record.row_id

            # Check if monitor window is complete
            if latest_row >= monitor_info.monitor_end_row:
                print(f"Monitor window complete, running drift detection...")
                detector = LLMDriftDetector(project_id)
                drift_result = await detector.detect_drift()

                if drift_result.get("has_drift"):
                    print(f"✓ DRIFT DETECTED: {drift_result['change_percentage']}% change")

                    # Mark records in this window as having drift
                    await self._mark_drift_records(
                        db, project_id,
                        monitor_info.monitor_start_row,
                        monitor_info.monitor_end_row
                    )

                # Update monitor window for next batch
                await self._update_monitor_window(db, project_id, monitor_info)

        except Exception as e:
            print(f"Error checking drift trigger: {e}")

    async def _mark_drift_records(self, db, project_id: int, start_row: int, end_row: int):
        """Mark records that experienced drift."""
        try:
            result = await db.execute(
                select(models.LLMMonitor).where(
                    models.LLMMonitor.project_id == project_id,
                    models.LLMMonitor.row_id.between(start_row, end_row)
                )
            )
            records = result.scalars().all()

            for record in records:
                record.has_drift = True

            await db.commit()
            print(f"✓ Marked {len(records)} records with drift")

        except Exception as e:
            print(f"Error marking drift records: {e}")

    async def _update_monitor_window(self, db, project_id: int, monitor_info):
        """Move monitor window to next batch."""
        try:
            config_result = await db.execute(
                select(models.LLMConfig).where(
                    models.LLMConfig.project_id == project_id
                )
            )
            config = config_result.scalars().first()

            if config:
                monitor_size = config.monitor_batch_size
                current_end = monitor_info.monitor_end_row

                monitor_info.monitor_start_row = current_end + 1
                monitor_info.monitor_end_row = current_end + monitor_size

                await db.commit()
                print(f"✓ Updated monitor window: {monitor_info.monitor_start_row} to {monitor_info.monitor_end_row}")

        except Exception as e:
            print(f"Error updating monitor window: {e}")
