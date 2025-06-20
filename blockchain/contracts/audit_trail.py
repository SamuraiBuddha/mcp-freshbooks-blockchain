"""Smart contract for immutable audit trail enforcement."""

import json
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import asyncio


@dataclass
class AuditEntry:
    """Represents an audit log entry."""
    
    entry_id: str
    timestamp: int
    action: str  # create, update, delete, access
    entity_type: str  # invoice, payment, expense, client
    entity_id: str
    user_id: str
    ip_address: Optional[str]
    changes: Optional[Dict[str, Any]]  # before/after values
    metadata: Dict[str, Any]
    hash: Optional[str] = None


class AuditTrailContract:
    """Smart contract for enforcing immutable audit trails."""
    
    def __init__(self, blockchain_core):
        self.blockchain = blockchain_core
        self.audit_entries: Dict[str, AuditEntry] = {}
        self.entity_hashes: Dict[str, str] = {}  # entity_id -> current_hash
        self.access_logs: List[Dict[str, Any]] = []
        
    async def log_action(self, 
                        action: str,
                        entity_type: str,
                        entity_id: str,
                        user_id: str,
                        changes: Optional[Dict[str, Any]] = None,
                        ip_address: Optional[str] = None,
                        metadata: Optional[Dict[str, Any]] = None) -> str:
        """Log an auditable action."""
        
        entry_id = f"audit_{int(datetime.now().timestamp() * 1000000)}"
        
        audit_entry = AuditEntry(
            entry_id=entry_id,
            timestamp=int(datetime.now().timestamp() * 1000000),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            ip_address=ip_address,
            changes=changes,
            metadata=metadata or {}
        )
        
        # Calculate entry hash
        entry_data = {
            "entry_id": audit_entry.entry_id,
            "timestamp": audit_entry.timestamp,
            "action": audit_entry.action,
            "entity_type": audit_entry.entity_type,
            "entity_id": audit_entry.entity_id,
            "user_id": audit_entry.user_id,
            "changes": audit_entry.changes,
            "previous_hash": self.entity_hashes.get(entity_id, "genesis")
        }
        
        entry_hash = hashlib.sha256(
            json.dumps(entry_data, sort_keys=True).encode()
        ).hexdigest()
        
        audit_entry.hash = entry_hash
        
        # Store entry
        self.audit_entries[entry_id] = audit_entry
        self.entity_hashes[entity_id] = entry_hash
        
        # Record on blockchain
        transaction = {
            "transaction_id": entry_id,
            "timestamp": audit_entry.timestamp,
            "transaction_type": "audit_trail",
            "data": {
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "user_id": user_id,
                "entry_hash": entry_hash,
                "changes_summary": self._summarize_changes(changes) if changes else None
            }
        }
        
        await self.blockchain.add_transaction(transaction)
        
        # Log access if it's an access action
        if action == "access":
            self.access_logs.append({
                "timestamp": audit_entry.timestamp,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "user_id": user_id,
                "ip_address": ip_address
            })
        
        return entry_id
    
    def _summarize_changes(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """Create a summary of changes for blockchain storage."""
        summary = {
            "fields_changed": [],
            "change_count": 0
        }
        
        if "before" in changes and "after" in changes:
            before = changes["before"]
            after = changes["after"]
            
            for key in after:
                if key not in before or before[key] != after[key]:
                    summary["fields_changed"].append(key)
                    summary["change_count"] += 1
        
        return summary
    
    async def verify_audit_trail(self, entity_id: str) -> Tuple[bool, List[str]]:
        """Verify the complete audit trail for an entity."""
        issues = []
        
        # Get all audit entries for this entity
        entity_entries = [
            entry for entry in self.audit_entries.values()
            if entry.entity_id == entity_id
        ]
        
        # Sort by timestamp
        entity_entries.sort(key=lambda x: x.timestamp)
        
        # Verify hash chain
        previous_hash = "genesis"
        for entry in entity_entries:
            # Recalculate hash
            entry_data = {
                "entry_id": entry.entry_id,
                "timestamp": entry.timestamp,
                "action": entry.action,
                "entity_type": entry.entity_type,
                "entity_id": entry.entity_id,
                "user_id": entry.user_id,
                "changes": entry.changes,
                "previous_hash": previous_hash
            }
            
            expected_hash = hashlib.sha256(
                json.dumps(entry_data, sort_keys=True).encode()
            ).hexdigest()
            
            if entry.hash != expected_hash:
                issues.append(f"Hash mismatch for entry {entry.entry_id}")
            
            previous_hash = entry.hash
        
        # Verify current entity hash matches
        if entity_id in self.entity_hashes:
            if self.entity_hashes[entity_id] != previous_hash:
                issues.append("Current entity hash doesn't match audit trail")
        
        return len(issues) == 0, issues
    
    async def get_entity_history(self, entity_id: str) -> List[AuditEntry]:
        """Get complete audit history for an entity."""
        entries = [
            entry for entry in self.audit_entries.values()
            if entry.entity_id == entity_id
        ]
        
        # Sort by timestamp
        entries.sort(key=lambda x: x.timestamp)
        return entries
    
    async def get_user_activity(self, user_id: str, 
                               start_time: Optional[datetime] = None,
                               end_time: Optional[datetime] = None) -> List[AuditEntry]:
        """Get all activities by a specific user."""
        entries = []
        
        start_ts = int(start_time.timestamp() * 1000000) if start_time else 0
        end_ts = int(end_time.timestamp() * 1000000) if end_time else float('inf')
        
        for entry in self.audit_entries.values():
            if entry.user_id == user_id and start_ts <= entry.timestamp <= end_ts:
                entries.append(entry)
        
        entries.sort(key=lambda x: x.timestamp)
        return entries
    
    async def detect_anomalies(self) -> List[Dict[str, Any]]:
        """Detect potential security anomalies in audit trail."""
        anomalies = []
        
        # Check for rapid sequential actions
        user_actions = {}
        for entry in self.audit_entries.values():
            if entry.user_id not in user_actions:
                user_actions[entry.user_id] = []
            user_actions[entry.user_id].append(entry)
        
        for user_id, actions in user_actions.items():
            actions.sort(key=lambda x: x.timestamp)
            
            for i in range(1, len(actions)):
                time_diff = (actions[i].timestamp - actions[i-1].timestamp) / 1000000  # Convert to seconds
                
                # Flag if actions are less than 1 second apart
                if time_diff < 1:
                    anomalies.append({
                        "type": "rapid_actions",
                        "user_id": user_id,
                        "entries": [actions[i-1].entry_id, actions[i].entry_id],
                        "time_difference": time_diff
                    })
        
        # Check for unusual access patterns
        for log in self.access_logs[-100:]:  # Check last 100 accesses
            # Flag access outside business hours (simplified)
            access_hour = datetime.fromtimestamp(log["timestamp"] / 1000000).hour
            if access_hour < 6 or access_hour > 22:
                anomalies.append({
                    "type": "after_hours_access",
                    "user_id": log["user_id"],
                    "timestamp": log["timestamp"],
                    "entity": f"{log['entity_type']}:{log['entity_id']}"
                })
        
        return anomalies
    
    async def generate_compliance_report(self, 
                                       start_date: datetime,
                                       end_date: datetime,
                                       compliance_type: str = "SOX") -> Dict[str, Any]:
        """Generate compliance report for audit requirements."""
        
        start_ts = int(start_date.timestamp() * 1000000)
        end_ts = int(end_date.timestamp() * 1000000)
        
        report = {
            "compliance_type": compliance_type,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {
                "total_entries": 0,
                "by_action": {},
                "by_entity_type": {},
                "by_user": {}
            },
            "critical_changes": [],
            "access_logs": [],
            "anomalies": []
        }
        
        # Analyze entries in period
        for entry in self.audit_entries.values():
            if start_ts <= entry.timestamp <= end_ts:
                report["summary"]["total_entries"] += 1
                
                # Count by action
                if entry.action not in report["summary"]["by_action"]:
                    report["summary"]["by_action"][entry.action] = 0
                report["summary"]["by_action"][entry.action] += 1
                
                # Count by entity type
                if entry.entity_type not in report["summary"]["by_entity_type"]:
                    report["summary"]["by_entity_type"][entry.entity_type] = 0
                report["summary"]["by_entity_type"][entry.entity_type] += 1
                
                # Count by user
                if entry.user_id not in report["summary"]["by_user"]:
                    report["summary"]["by_user"][entry.user_id] = 0
                report["summary"]["by_user"][entry.user_id] += 1
                
                # Flag critical changes
                if entry.action in ["delete", "update"] and entry.entity_type in ["invoice", "payment"]:
                    report["critical_changes"].append({
                        "entry_id": entry.entry_id,
                        "timestamp": datetime.fromtimestamp(entry.timestamp / 1000000).isoformat(),
                        "action": entry.action,
                        "entity": f"{entry.entity_type}:{entry.entity_id}",
                        "user": entry.user_id
                    })
        
        # Get anomalies for period
        all_anomalies = await self.detect_anomalies()
        report["anomalies"] = [
            a for a in all_anomalies 
            if start_ts <= a.get("timestamp", 0) <= end_ts
        ]
        
        # Verification status
        report["blockchain_verified"] = self.blockchain.validate_chain()
        
        return report