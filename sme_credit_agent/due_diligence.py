"""
Layered Due Diligence System (分层尽调系统).

The right panel of the diagram. Manages the three investigation methods:
  - 电话核查  (Phone Verification)  — basic facts confirmation
  - 视频尽调  (Video Due Diligence) — management interview and document review
  - 下户调查  (On-Site Investigation) — physical verification at company premises

Outputs feed back to the decision engine as 尽调结果 (Due Diligence Results)
and are archived as 资料留档 (Document Archives) for the simplified approval flow
(简易化审批).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .models import (
    DueDiligenceMethod,
    DueDiligenceRequest,
    DueDiligenceResult,
    DueDiligenceStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class InvestigationChecklist:
    """Standard checklist items for each due diligence method."""
    method: DueDiligenceMethod
    required_items: list[str]
    optional_items: list[str] = field(default_factory=list)

    @classmethod
    def for_method(cls, method: DueDiligenceMethod) -> "InvestigationChecklist":
        checklists = {
            DueDiligenceMethod.PHONE: cls(
                method=method,
                required_items=[
                    "Confirm legal representative identity",
                    "Verify business registration status",
                    "Confirm loan purpose and repayment source",
                    "Check for undisclosed debts",
                    "Confirm no significant pending litigation",
                ],
                optional_items=[
                    "Verify major customer relationship",
                    "Confirm production/operation status",
                ]
            ),
            DueDiligenceMethod.VIDEO: cls(
                method=method,
                required_items=[
                    "Video identity verification of legal representative",
                    "Screen share review of key financial statements",
                    "Management team interview (min 30 minutes)",
                    "Verification of business license and permits",
                    "Review of major contracts and accounts receivable aging",
                ],
                optional_items=[
                    "Interview with CFO on cash flow",
                    "Review of tax filing documents",
                    "Supplier/customer reference call",
                ]
            ),
            DueDiligenceMethod.ON_SITE: cls(
                method=method,
                required_items=[
                    "Physical visit to registered business address",
                    "Verify production facilities and equipment",
                    "Interview actual controller and key management",
                    "Inspect inventory and assets",
                    "Review original copies of contracts and invoices",
                    "Photograph premises and operations",
                    "Verify headcount and employee records",
                ],
                optional_items=[
                    "Visit major customer/supplier sites",
                    "Interview key employees independently",
                    "Third-party asset appraisal",
                ]
            ),
        }
        return checklists[method]


@dataclass
class DocumentArchive:
    """
    资料留档 — Document archive for simplified approval (简易化审批).
    Stores all evidence collected during due diligence.
    """
    application_id: str
    request_id: str
    documents: list[dict] = field(default_factory=list)
    archived_at: datetime = field(default_factory=datetime.utcnow)
    archive_id: str = field(default_factory=lambda: f"ARC-{__import__('uuid').uuid4().hex[:8].upper()}")

    def add_document(self, doc_type: str, filename: str, verified: bool = True) -> None:
        self.documents.append({
            "type": doc_type,
            "filename": filename,
            "verified": verified,
            "added_at": datetime.utcnow().isoformat(),
        })


class DueDiligenceSystem:
    """
    Implements the 分层尽调系统 (Layered Due Diligence System).

    Manages work order lifecycle:
      dispatch → assign → investigate → complete → archive → feed back

    Architecture:
      标准尽调工单 ──▶ 电话核查 / 视频尽调 / 下户调查
                                │
                                ▼
                          尽调结果 ──▶ 风控决策引擎
                                │
                                ▼
                          资料留档 ──▶ 简易化审批
    """

    def __init__(self):
        self._requests: dict[str, DueDiligenceRequest] = {}
        self._results: dict[str, DueDiligenceResult] = {}
        self._archives: dict[str, DocumentArchive] = {}

    def create_work_order(
        self,
        application_id: str,
        method: DueDiligenceMethod,
        focus_areas: list[str],
        priority: str = "normal",
        assigned_to: Optional[str] = None,
    ) -> DueDiligenceRequest:
        """
        Create a standard due diligence work order (标准尽调工单).
        The work order is model-triggered from the decision engine.
        """
        from datetime import timedelta
        deadline_days = {"urgent": 1, "normal": 3, "low": 7}[priority]

        req = DueDiligenceRequest(
            application_id=application_id,
            method=method,
            focus_areas=focus_areas,
            priority=priority,
            assigned_to=assigned_to,
            deadline=datetime.utcnow() + timedelta(days=deadline_days),
        )
        self._requests[req.request_id] = req
        logger.info(
            "Work order %s created: method=%s priority=%s",
            req.request_id, method.value, priority
        )
        return req

    def get_checklist(self, method: DueDiligenceMethod) -> InvestigationChecklist:
        """Return the standard checklist for the given investigation method."""
        return InvestigationChecklist.for_method(method)

    def submit_result(
        self,
        request_id: str,
        findings: dict,
        overall_assessment: str,
        red_flags: list[str] | None = None,
        supporting_documents: list[str] | None = None,
        investigator: Optional[str] = None,
    ) -> DueDiligenceResult:
        """
        Submit investigation results (尽调结果) from the field investigator.
        Triggers document archiving and updates the request status.
        """
        req = self._requests.get(request_id)
        if not req:
            raise ValueError(f"Work order {request_id} not found")

        result = DueDiligenceResult(
            request_id=request_id,
            application_id=req.application_id,
            method=req.method,
            findings=findings,
            overall_assessment=overall_assessment,
            red_flags=red_flags or [],
            supporting_documents=supporting_documents or [],
            investigator=investigator,
        )
        self._results[request_id] = result
        req.status = DueDiligenceStatus.COMPLETED

        # Auto-archive documents
        self._archive_documents(result)
        logger.info(
            "Due diligence %s completed: assessment=%s red_flags=%d",
            request_id, overall_assessment, len(result.red_flags)
        )
        return result

    def get_result(self, request_id: str) -> Optional[DueDiligenceResult]:
        """Retrieve a completed due diligence result."""
        return self._results.get(request_id)

    def get_request(self, request_id: str) -> Optional[DueDiligenceRequest]:
        """Retrieve a due diligence work order."""
        return self._requests.get(request_id)

    def get_archive(self, application_id: str) -> list[DocumentArchive]:
        """Retrieve all document archives for an application (资料留档)."""
        return [a for a in self._archives.values() if a.application_id == application_id]

    def is_eligible_for_simplified_approval(self, application_id: str) -> bool:
        """
        Check if an application qualifies for simplified approval (简易化审批).

        Criteria:
        - All DD requests completed
        - No negative assessments
        - No unresolved red flags
        - Documents archived
        """
        app_requests = [r for r in self._requests.values() if r.application_id == application_id]
        if not app_requests:
            return False

        for req in app_requests:
            if req.status != DueDiligenceStatus.COMPLETED:
                return False
            result = self._results.get(req.request_id)
            if not result:
                return False
            if result.overall_assessment == "negative":
                return False
            if result.red_flags:
                return False

        return len(self.get_archive(application_id)) > 0

    def _archive_documents(self, result: DueDiligenceResult) -> DocumentArchive:
        """Create a document archive entry (资料留档)."""
        archive = DocumentArchive(
            application_id=result.application_id,
            request_id=result.request_id,
        )
        for doc_name in result.supporting_documents:
            doc_type = _infer_document_type(doc_name)
            archive.add_document(doc_type=doc_type, filename=doc_name)

        self._archives[archive.archive_id] = archive
        return archive

    def summary(self) -> dict:
        """Return a summary of current system state."""
        return {
            "total_requests": len(self._requests),
            "completed": sum(1 for r in self._requests.values() if r.status == DueDiligenceStatus.COMPLETED),
            "in_progress": sum(1 for r in self._requests.values() if r.status == DueDiligenceStatus.IN_PROGRESS),
            "pending": sum(1 for r in self._requests.values() if r.status == DueDiligenceStatus.PENDING),
            "total_archives": len(self._archives),
        }


def _infer_document_type(filename: str) -> str:
    """Infer document type from filename."""
    lower = filename.lower()
    if "contract" in lower:
        return "contract"
    if "invoice" in lower or "receipt" in lower:
        return "financial_document"
    if "photo" in lower or "img" in lower:
        return "site_photo"
    if "license" in lower or "permit" in lower:
        return "legal_document"
    return "supporting_document"
