-- Phase 2.1 runtime hardening: make safety-control changes auditable.

CREATE TABLE system_control_events (
  event_id INTEGER PRIMARY KEY,
  collection_enabled INTEGER NOT NULL CHECK(collection_enabled IN (0, 1)),
  publication_enabled INTEGER NOT NULL CHECK(publication_enabled IN (0, 1)),
  change_reason TEXT NOT NULL CHECK(length(trim(change_reason)) > 0),
  changed_by TEXT NOT NULL CHECK(length(trim(changed_by)) > 0),
  changed_at TEXT NOT NULL
) STRICT;

CREATE TRIGGER system_controls_require_audit_metadata
BEFORE UPDATE ON system_controls
WHEN NEW.updated_at = OLD.updated_at
  OR length(trim(NEW.change_reason)) = 0
  OR length(trim(NEW.updated_by)) = 0
BEGIN
  SELECT RAISE(ABORT, 'Safety-control changes require updated audit metadata');
END;

CREATE TRIGGER system_controls_record_event
AFTER UPDATE ON system_controls
BEGIN
  INSERT INTO system_control_events(
    collection_enabled,
    publication_enabled,
    change_reason,
    changed_by,
    changed_at
  ) VALUES (
    NEW.collection_enabled,
    NEW.publication_enabled,
    NEW.change_reason,
    NEW.updated_by,
    NEW.updated_at
  );
END;

CREATE TRIGGER system_controls_no_delete
BEFORE DELETE ON system_controls
BEGIN
  SELECT RAISE(ABORT, 'system_controls singleton cannot be deleted');
END;
